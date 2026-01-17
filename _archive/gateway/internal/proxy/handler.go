package proxy

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"sentinel-gateway/internal/brain"
)

func NewHandler(b *brain.Client) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Generate request ID for tracing
		requestID := uuid.New().String()
		c.Set("X-Request-ID", requestID)

		var req struct {
			Messages []struct {
				Role    string `json:"role"`
				Content string `json:"content"`
			} `json:"messages"`
			Model string `json:"model,omitempty"`
		}

		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":      "Invalid request",
				"request_id": requestID,
			})
		}

		// Extract last user message
		lastMsg := ""
		for i := len(req.Messages) - 1; i >= 0; i-- {
			if req.Messages[i].Role == "user" {
				lastMsg = req.Messages[i].Content
				break
			}
		}

		// 1. INGRESS ANALYSIS
		ingressResp, err := b.Analyze(c.Context(), lastMsg, nil)
		if err != nil {
			println("Brain ingress error:", err.Error())
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Brain analysis failed: " + err.Error()})
		}

		if !ingressResp.Allowed {
			return c.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"error":   "Request blocked by Sentinel (Ingress)",
				"reason":  ingressResp.VerdictReason,
				"threats": ingressResp.DetectedThreats,
			})
		}

		// 2. FORWARD TO LLM (if configured)
		llmEndpoint := os.Getenv("LLM_ENDPOINT")
		llmAPIKey := os.Getenv("LLM_API_KEY")

		if llmEndpoint == "" {
			// No LLM configured - return mock response for testing
			return c.JSON(fiber.Map{
				"message":            "Sentinel Gateway: Request Allowed (no LLM configured)",
				"risk_score":         ingressResp.RiskScore,
				"anonymized_content": ingressResp.AnonymizedContent,
			})
		}

		// Call LLM
		llmResponse, err := callLLM(llmEndpoint, llmAPIKey, req.Messages, req.Model)
		if err != nil || strings.Contains(llmResponse, "RESOURCE_EXHAUSTED") || strings.Contains(llmResponse, "error") {
			// LLM unavailable or quota exceeded - return mock response for MVP demo
			mockResponse := "Это демо-ответ от SENTINEL. LLM API временно недоступен, но система защиты работает! Ваш запрос был проанализирован и признан безопасным."
			return c.JSON(fiber.Map{
				"response":           mockResponse,
				"ingress_risk_score": ingressResp.RiskScore,
				"egress_risk_score":  0.0,
				"demo_mode":          true,
				"original_error":     llmResponse,
			})
		}

		// 3. EGRESS ANALYSIS
		egressResp, err := b.AnalyzeOutput(c.Context(), llmResponse, lastMsg, nil)
		if err != nil {
			println("Brain egress error:", err.Error())
			// Graceful degradation for MVP: return response with warning
			return c.JSON(fiber.Map{
				"response":           llmResponse,
				"warning":            "Egress analysis unavailable",
				"ingress_risk_score": ingressResp.RiskScore,
				"egress_risk_score":  0.0,
			})
		}

		if !egressResp.Allowed {
			return c.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"error":   "Response blocked by Sentinel (Egress)",
				"reason":  "LLM response contained unsafe content",
				"threats": egressResp.DetectedThreats,
			})
		}

		// 4. RETURN SANITIZED RESPONSE
		return c.JSON(fiber.Map{
			"response":           egressResp.SanitizedResponse,
			"ingress_risk_score": ingressResp.RiskScore,
			"egress_risk_score":  egressResp.RiskScore,
		})
	}
}

// callLLM calls an OpenAI-compatible API endpoint
func callLLM(endpoint, apiKey string, messages []struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}, model string) (string, error) {

	if model == "" {
		model = os.Getenv("LLM_MODEL")
		if model == "" {
			model = "gemini-3-pro-preview"
		}
	}

	reqBody := map[string]interface{}{
		"model":    model,
		"messages": messages,
	}

	jsonBody, _ := json.Marshal(reqBody)

	req, err := http.NewRequest("POST", endpoint, bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	// Parse OpenAI response
	var llmResp struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.Unmarshal(body, &llmResp); err != nil {
		return string(body), nil // Return raw if can't parse
	}

	if len(llmResp.Choices) > 0 {
		return llmResp.Choices[0].Message.Content, nil
	}

	return string(body), nil
}
