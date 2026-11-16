package soc

import (
	"context"
	"encoding/json"
	"net"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"
)

func init() {
	// Disable SSRF verification for localized httptest servers during unit tests.
	ValidateWebhookURL = func(string) error { return nil }
	SafeDialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, network, addr)
	}
}

func TestWebhookEngine_Fire(t *testing.T) {
	var received atomic.Int32

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		received.Add(1)

		var payload WebhookPayload
		json.NewDecoder(r.Body).Decode(&payload)

		if payload.EventType == "" {
			t.Error("missing event_type in payload")
		}

		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	engine := NewWebhookEngine()
	engine.AddWebhook(WebhookConfig{
		ID:      "wh-1",
		URL:     srv.URL,
		Events:  []WebhookEventType{WebhookIncidentCreated, WebhookCriticalEvent},
		Active:  true,
		Retries: 1,
	})

	// Fire matching event
	engine.Fire(WebhookIncidentCreated, WebhookPayload{
		IncidentID: "inc-001",
		Severity:   "CRITICAL",
		Title:      "Test incident",
	})

	// Fire non-matching event — should NOT trigger
	engine.Fire(WebhookSensorOffline, WebhookPayload{
		Title: "Sensor down",
	})

	// Wait for async delivery
	time.Sleep(300 * time.Millisecond)

	if received.Load() != 1 {
		t.Fatalf("expected 1 webhook delivery, got %d", received.Load())
	}
}

func TestWebhookEngine_Stats(t *testing.T) {
	engine := NewWebhookEngine()
	engine.AddWebhook(WebhookConfig{
		ID:     "wh-stats",
		URL:    "http://localhost:1/nope",
		Events: []WebhookEventType{WebhookCriticalEvent},
		Active: true,
	})

	stats := engine.Stats()
	if stats["webhooks_configured"].(int) != 1 {
		t.Fatalf("expected 1 configured, got %v", stats["webhooks_configured"])
	}
}

func TestWebhookEngine_InactiveSkipped(t *testing.T) {
	var received atomic.Int32

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		received.Add(1)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	engine := NewWebhookEngine()
	engine.AddWebhook(WebhookConfig{
		ID:     "wh-inactive",
		URL:    srv.URL,
		Events: []WebhookEventType{WebhookKillChainAlert},
		Active: false, // Inactive!
	})

	engine.Fire(WebhookKillChainAlert, WebhookPayload{Title: "Kill chain C2"})
	time.Sleep(200 * time.Millisecond)

	if received.Load() != 0 {
		t.Fatalf("inactive webhook should not fire, got %d", received.Load())
	}
}

func TestWebhookEngine_RemoveWebhook(t *testing.T) {
	var received atomic.Int32

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		received.Add(1)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	engine := NewWebhookEngine()
	engine.AddWebhook(WebhookConfig{
		ID:     "wh-remove",
		URL:    srv.URL,
		Events: []WebhookEventType{WebhookIncidentResolved},
		Active: true,
	})

	engine.RemoveWebhook("wh-remove")

	engine.Fire(WebhookIncidentResolved, WebhookPayload{Title: "Resolved"})
	time.Sleep(200 * time.Millisecond)

	if received.Load() != 0 {
		t.Fatalf("removed webhook should not fire, got %d", received.Load())
	}
}

func TestWebhookEngine_ListWebhooks(t *testing.T) {
	engine := NewWebhookEngine()
	engine.AddWebhook(WebhookConfig{URL: "http://a.com", Active: true})
	engine.AddWebhook(WebhookConfig{URL: "http://b.com", Active: true})

	webhooks := engine.Webhooks()
	if len(webhooks) != 2 {
		t.Fatalf("expected 2, got %d", len(webhooks))
	}
}
