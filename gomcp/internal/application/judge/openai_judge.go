package judge

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// openAIJudge is the OpenAI-COMPATIBLE adapter. The OpenAI /v1/chat/completions
// wire shape is the de-facto standard, so this one adapter covers OpenAI,
// DeepSeek, Mistral, Together, Groq, a local vLLM/Ollama OpenAI shim, etc. — the
// operator just points BaseURL + APIKey + Model at their vendor (BYO-key,
// on-prem). Mirrors the aggregator OpenAI adapter's shape, minus streaming.
type openAIJudge struct {
	cfg    Config
	client *http.Client
}

const defaultOpenAIBase = "https://api.openai.com/v1"

// newOpenAIJudge builds the adapter. httpClient is optional (tests inject an
// httptest-backed client); nil → a default client bounded by cfg.TimeoutSeconds.
func newOpenAIJudge(cfg Config, httpClient *http.Client) (*openAIJudge, error) {
	if cfg.APIKey == "" {
		return nil, ErrMissingAPIKey
	}
	if cfg.BaseURL == "" {
		cfg.BaseURL = defaultOpenAIBase
	}
	if err := ValidateBaseURL(cfg.BaseURL); err != nil {
		return nil, err
	}
	client := httpClient
	if client == nil {
		client = &http.Client{Timeout: judgeTimeout(cfg)}
	}
	return &openAIJudge{cfg: cfg, client: client}, nil
}

func (*openAIJudge) Name() string { return VendorOpenAICompatible }

// openaiChatReq is the minimal request body we send.
type openaiChatReq struct {
	Model          string          `json:"model"`
	Messages       []openaiChatMsg `json:"messages"`
	Temperature    float64         `json:"temperature"`
	MaxTokens      int             `json:"max_tokens"`
	ResponseFormat *openaiRespFmt  `json:"response_format,omitempty"`
}

type openaiChatMsg struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openaiRespFmt struct {
	Type string `json:"type"` // "json_object" — ask compatible servers for strict JSON.
}

// openaiChatResp is the minimal response shape we parse.
type openaiChatResp struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

// Evaluate sends one chat completion and strictly parses the JSON verdict.
// FAIL-HONEST: any transport error, non-2xx, empty body, or non-strict JSON
// returns (JudgeVerdict{}, err) — never a fabricated verdict.
func (a *openAIJudge) Evaluate(ctx context.Context, redactedPrompt string, engine EngineVerdict) (JudgeVerdict, error) {
	body := openaiChatReq{
		Model:       a.cfg.Model,
		Temperature: 0,
		MaxTokens:   200,
		Messages: []openaiChatMsg{
			{Role: "system", Content: SystemPrompt},
			{Role: "user", Content: BuildUserPrompt(redactedPrompt, engine)},
		},
		// Request strict JSON. Most OpenAI-compatible servers honor this; the ones
		// that ignore it still get our explicit "single JSON object" instruction,
		// and ParseVerdict enforces strictness regardless.
		ResponseFormat: &openaiRespFmt{Type: "json_object"},
	}
	raw, err := json.Marshal(body)
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(openai): marshal: %w", err)
	}

	url := strings.TrimRight(a.cfg.BaseURL, "/") + "/chat/completions"
	// Bound the call even if the injected client has no timeout.
	reqCtx, cancel := context.WithTimeout(ctx, judgeTimeout(a.cfg))
	defer cancel()
	httpReq, err := http.NewRequestWithContext(reqCtx, http.MethodPost, url, bytes.NewReader(raw))
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(openai): build request: %w", err)
	}
	httpReq.Header.Set("Authorization", "Bearer "+a.cfg.APIKey) // key in header, never logged
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := a.client.Do(httpReq)
	if err != nil {
		// Includes context deadline/cancel → fail honest.
		return JudgeVerdict{}, fmt.Errorf("judge(openai): transport: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(io.LimitReader(resp.Body, 256*1024))
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(openai): read body: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		// Do NOT echo the body verbatim (it can contain the request, hence the
		// prompt). Surface only the status — fail honest.
		return JudgeVerdict{}, fmt.Errorf("judge(openai): upstream status %d", resp.StatusCode)
	}

	var parsed openaiChatResp
	if err := json.Unmarshal(respBody, &parsed); err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(openai): decode envelope: %w", err)
	}
	if len(parsed.Choices) == 0 {
		return JudgeVerdict{}, fmt.Errorf("judge(openai): %w", ErrEmptyResponse)
	}
	verdict, err := ParseVerdict(parsed.Choices[0].Message.Content)
	if err != nil {
		return JudgeVerdict{}, err // already fail-honest, descriptive
	}
	verdict.Vendor = a.Name()
	return verdict, nil
}

// judgeTimeout returns the bounded per-call timeout (default 8s, floor 1s).
func judgeTimeout(cfg Config) time.Duration {
	if cfg.TimeoutSeconds <= 0 {
		return 8 * time.Second
	}
	return time.Duration(cfg.TimeoutSeconds) * time.Second
}

// ensure interface satisfaction at compile time.
var _ SecurityJudge = (*openAIJudge)(nil)

// errEnvelopeShape is unused but documents that we deliberately ignore the
// vendor error envelope body (it may contain the echoed prompt). Kept as a guard
// against a future refactor re-introducing a body leak.
var _ = errors.New
