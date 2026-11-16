package sidecar

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// BusClient sends security events to the SOC Event Bus via HTTP POST.
type BusClient struct {
	baseURL    string
	sensorID   string
	apiKey     string
	httpClient *http.Client
	maxRetries int
}

// NewBusClient creates a client for the SOC Event Bus.
func NewBusClient(baseURL, sensorID, apiKey string) *BusClient {
	return &BusClient{
		baseURL:  baseURL,
		sensorID: sensorID,
		apiKey:   apiKey,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        10,
				IdleConnTimeout:     90 * time.Second,
				MaxIdleConnsPerHost: 5,
			},
		},
		maxRetries: 3,
	}
}

// ingestPayload matches the SOC ingest API expected JSON.
type ingestPayload struct {
	Source      string            `json:"source"`
	SensorID   string            `json:"sensor_id"`
	SensorKey  string            `json:"sensor_key,omitempty"`
	Severity   string            `json:"severity"`
	Category   string            `json:"category"`
	Subcategory string           `json:"subcategory,omitempty"`
	Confidence float64           `json:"confidence"`
	Description string           `json:"description"`
	SessionID  string            `json:"session_id,omitempty"`
	Metadata   map[string]string `json:"metadata,omitempty"`
}

// SendEvent posts a SOCEvent to the Event Bus.
// Accepts context for graceful cancellation during retries (L-2 fix).
func (c *BusClient) SendEvent(ctx context.Context, evt *domsoc.SOCEvent) error {
	payload := ingestPayload{
		Source:      string(evt.Source),
		SensorID:   c.sensorID,
		SensorKey:  c.apiKey,
		Severity:   string(evt.Severity),
		Category:   evt.Category,
		Subcategory: evt.Subcategory,
		Confidence: evt.Confidence,
		Description: evt.Description,
		SessionID:  evt.SessionID,
		Metadata:   evt.Metadata,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("sidecar: marshal event: %w", err)
	}

	url := c.baseURL + "/api/v1/soc/events"

	var lastErr error
	for attempt := 0; attempt <= c.maxRetries; attempt++ {
		if attempt > 0 {
			// Context-aware backoff: cancellable during shutdown (H-1 fix).
			backoff := time.Duration(attempt*attempt) * 500 * time.Millisecond
			select {
			case <-ctx.Done():
				return fmt.Errorf("sidecar: send cancelled during retry: %w", ctx.Err())
			case <-time.After(backoff):
			}
		}

		req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(body))
		if err != nil {
			return fmt.Errorf("sidecar: create request: %w", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			slog.Warn("sidecar: bus POST failed, retrying",
				"attempt", attempt+1, "error", err)
			continue
		}
		resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			return nil
		}

		lastErr = fmt.Errorf("bus returned %d", resp.StatusCode)
		if resp.StatusCode >= 400 && resp.StatusCode < 500 {
			// Client error — don't retry.
			return lastErr
		}
		slog.Warn("sidecar: bus returned server error, retrying",
			"attempt", attempt+1, "status", resp.StatusCode)
	}

	return fmt.Errorf("sidecar: exhausted retries: %w", lastErr)
}

// Heartbeat sends a sensor heartbeat to the Event Bus.
func (c *BusClient) Heartbeat() error {
	payload := map[string]string{
		"sensor_id": c.sensorID,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("sidecar: marshal heartbeat: %w", err)
	}

	url := c.baseURL + "/api/soc/sensors/heartbeat"
	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return nil
	}
	return fmt.Errorf("heartbeat returned %d", resp.StatusCode)
}

// Healthy checks if the bus is reachable (M-4 fix: /healthz not /health).
func (c *BusClient) Healthy() bool {
	resp, err := c.httpClient.Get(c.baseURL + "/healthz")
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
