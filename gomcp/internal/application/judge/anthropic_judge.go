package judge

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// anthropicJudge is the Anthropic Messages-API adapter (a first-class second
// vendor). Mirrors the aggregator Anthropic adapter's wire shape (POST
// /v1/messages, x-api-key + anthropic-version headers, top-level system prompt,
// content blocks), minus streaming.
type anthropicJudge struct {
	cfg     Config
	version string
	client  *http.Client
}

const (
	defaultAnthropicBase    = "https://api.anthropic.com/v1"
	defaultAnthropicVersion = "2023-06-01"
)

// newAnthropicJudge builds the adapter. httpClient is optional (tests inject an
// httptest-backed client); nil → a default client bounded by cfg.TimeoutSeconds.
func newAnthropicJudge(cfg Config, httpClient *http.Client) (*anthropicJudge, error) {
	if cfg.APIKey == "" {
		return nil, ErrMissingAPIKey
	}
	if cfg.BaseURL == "" {
		cfg.BaseURL = defaultAnthropicBase
	}
	if err := ValidateBaseURL(cfg.BaseURL); err != nil {
		return nil, err
	}
	client := httpClient
	if client == nil {
		client = &http.Client{Timeout: judgeTimeout(cfg)}
	}
	return &anthropicJudge{cfg: cfg, version: defaultAnthropicVersion, client: client}, nil
}

func (*anthropicJudge) Name() string { return VendorAnthropic }

type anthropicReq struct {
	Model       string            `json:"model"`
	System      string            `json:"system,omitempty"`
	Messages    []anthropicReqMsg `json:"messages"`
	MaxTokens   int               `json:"max_tokens"`
	Temperature float64           `json:"temperature"`
}

type anthropicReqMsg struct {
	Role    string `json:"role"`
	Content string `json:"content"` // Anthropic accepts a plain string for a single text block.
}

type anthropicResp struct {
	Content []struct {
		Type string `json:"type"`
		Text string `json:"text"`
	} `json:"content"`
}

// Evaluate sends one Messages call and strictly parses the JSON verdict.
// FAIL-HONEST on any transport error, non-2xx, empty body, or non-strict JSON.
func (a *anthropicJudge) Evaluate(ctx context.Context, redactedPrompt string, engine EngineVerdict) (JudgeVerdict, error) {
	body := anthropicReq{
		Model:       a.cfg.Model,
		System:      SystemPrompt,
		MaxTokens:   200,
		Temperature: 0,
		Messages: []anthropicReqMsg{
			{Role: "user", Content: BuildUserPrompt(redactedPrompt, engine)},
		},
	}
	raw, err := json.Marshal(body)
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): marshal: %w", err)
	}

	url := strings.TrimRight(a.cfg.BaseURL, "/") + "/messages"
	reqCtx, cancel := context.WithTimeout(ctx, judgeTimeout(a.cfg))
	defer cancel()
	httpReq, err := http.NewRequestWithContext(reqCtx, http.MethodPost, url, bytes.NewReader(raw))
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): build request: %w", err)
	}
	httpReq.Header.Set("x-api-key", a.cfg.APIKey) // key in header, never logged
	httpReq.Header.Set("anthropic-version", a.version)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := a.client.Do(httpReq)
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): transport: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(io.LimitReader(resp.Body, 256*1024))
	if err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): read body: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		// Surface status only — the error body may echo the prompt. Fail honest.
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): upstream status %d", resp.StatusCode)
	}

	var parsed anthropicResp
	if err := json.Unmarshal(respBody, &parsed); err != nil {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): decode envelope: %w", err)
	}
	// Concatenate text blocks (normally one).
	var text strings.Builder
	for _, c := range parsed.Content {
		if c.Type == "text" {
			text.WriteString(c.Text)
		}
	}
	if text.Len() == 0 {
		return JudgeVerdict{}, fmt.Errorf("judge(anthropic): %w", ErrEmptyResponse)
	}
	verdict, err := ParseVerdict(text.String())
	if err != nil {
		return JudgeVerdict{}, err
	}
	verdict.Vendor = a.Name()
	return verdict, nil
}

var _ SecurityJudge = (*anthropicJudge)(nil)
