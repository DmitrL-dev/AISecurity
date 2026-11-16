package sidecar

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// ── Parser Tests ─────────────────────────────────────────────────────────────

func TestSentinelCoreParser(t *testing.T) {
	p := &SentinelCoreParser{}

	tests := []struct {
		line     string
		wantOK   bool
		category string
		confMin  float64
	}{
		{"[DETECT] engine=jailbreak confidence=0.95 pattern=DAN prompt", true, "jailbreak", 0.9},
		{"[DETECT] engine=injection confidence=0.6 pattern=ignore_previous", true, "injection", 0.5},
		{"[DETECT] engine=exfiltration confidence=0.3 pattern=tool_call severity=HIGH", true, "exfiltration", 0.2},
		{"INFO: Engine loaded successfully", false, "", 0},
		{"", false, "", 0},
	}

	for _, tt := range tests {
		evt, ok := p.Parse(tt.line)
		if ok != tt.wantOK {
			t.Errorf("Parse(%q) ok=%v, want %v", tt.line, ok, tt.wantOK)
			continue
		}
		if !ok {
			continue
		}
		if evt.Category != tt.category {
			t.Errorf("Parse(%q) category=%q, want %q", tt.line, evt.Category, tt.category)
		}
		if evt.Confidence < tt.confMin {
			t.Errorf("Parse(%q) confidence=%.2f, want >=%.2f", tt.line, evt.Confidence, tt.confMin)
		}
	}
}

func TestShieldParser(t *testing.T) {
	p := &ShieldParser{}

	tests := []struct {
		line   string
		wantOK bool
		proto  string
		ip     string
	}{
		{"BLOCKED protocol=tcp reason=port_scan source_ip=192.168.1.100", true, "tcp", "192.168.1.100"},
		{"BLOCKED protocol=udp reason=dns_exfil source_ip=10.0.0.5", true, "udp", "10.0.0.5"},
		{"ALLOWED protocol=https from 1.2.3.4", false, "", ""},
		{"", false, "", ""},
	}

	for _, tt := range tests {
		evt, ok := p.Parse(tt.line)
		if ok != tt.wantOK {
			t.Errorf("Parse(%q) ok=%v, want %v", tt.line, ok, tt.wantOK)
			continue
		}
		if !ok {
			continue
		}
		if evt.Metadata["protocol"] != tt.proto {
			t.Errorf("protocol=%q, want %q", evt.Metadata["protocol"], tt.proto)
		}
		if evt.Metadata["source_ip"] != tt.ip {
			t.Errorf("source_ip=%q, want %q", evt.Metadata["source_ip"], tt.ip)
		}
	}
}

func TestImmuneParser(t *testing.T) {
	p := &ImmuneParser{}

	tests := []struct {
		line     string
		wantOK   bool
		category string
	}{
		{"[ANOMALY] type=drift score=0.85 detail=behavior shift detected", true, "anomaly"},
		{"[RESPONSE] action=quarantine target=session-123 reason=high risk", true, "immune_response"},
		{"[INFO] system healthy", false, ""},
	}

	for _, tt := range tests {
		evt, ok := p.Parse(tt.line)
		if ok != tt.wantOK {
			t.Errorf("Parse(%q) ok=%v, want %v", tt.line, ok, tt.wantOK)
			continue
		}
		if !ok {
			continue
		}
		if evt.Category != tt.category {
			t.Errorf("category=%q, want %q", evt.Category, tt.category)
		}
	}
}

func TestGenericParser(t *testing.T) {
	p, err := NewGenericParser(
		`ALERT\s+(?P<category>\S+)\s+(?P<severity>\S+)\s+(?P<description>.+)`,
		"external",
	)
	if err != nil {
		t.Fatalf("NewGenericParser: %v", err)
	}

	evt, ok := p.Parse("ALERT injection HIGH suspicious sql in query string")
	if !ok {
		t.Fatal("expected match")
	}
	if evt.Category != "injection" {
		t.Errorf("category=%q, want injection", evt.Category)
	}
	if string(evt.Severity) != "HIGH" {
		t.Errorf("severity=%q, want HIGH", evt.Severity)
	}
}

func TestParserForSensor(t *testing.T) {
	tests := map[string]string{
		"sentinel-core": "*sidecar.SentinelCoreParser",
		"shield":        "*sidecar.ShieldParser",
		"immune":        "*sidecar.ImmuneParser",
		"unknown":       "*sidecar.SentinelCoreParser", // fallback
	}
	for sensorType, wantType := range tests {
		p := ParserForSensor(sensorType)
		if p == nil {
			t.Errorf("ParserForSensor(%q) returned nil", sensorType)
			continue
		}
		gotType := fmt.Sprintf("%T", p)
		if gotType != wantType {
			t.Errorf("ParserForSensor(%q) = %s, want %s", sensorType, gotType, wantType)
		}
	}
}

// ── Tailer Tests ─────────────────────────────────────────────────────────────

func TestTailer_FollowReader(t *testing.T) {
	input := "[DETECT] engine=jailbreak confidence=0.95 pattern=DAN\nINFO: done\n[DETECT] engine=exfil confidence=0.7 pattern=tool_call\n"
	reader := strings.NewReader(input)

	tailer := NewTailer(50 * time.Millisecond)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	ch := tailer.FollowReader(ctx, reader)

	var lines []string
	for line := range ch {
		lines = append(lines, line)
	}

	if len(lines) != 3 {
		t.Fatalf("expected 3 lines, got %d: %v", len(lines), lines)
	}

	if lines[0] != "[DETECT] engine=jailbreak confidence=0.95 pattern=DAN" {
		t.Errorf("line[0]=%q", lines[0])
	}
}

// ── BusClient Tests ──────────────────────────────────────────────────────────

func TestBusClient_SendEvent(t *testing.T) {
	var received []map[string]any

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/soc/events" {
			var payload map[string]any
			json.NewDecoder(r.Body).Decode(&payload)
			received = append(received, payload)
			w.WriteHeader(http.StatusCreated)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	client := NewBusClient(ts.URL, "test-sensor", "test-key")

	p := &SentinelCoreParser{}
	evt, ok := p.Parse("[DETECT] engine=jailbreak confidence=0.95 pattern=DAN")
	if !ok {
		t.Fatal("parse failed")
	}

	err := client.SendEvent(context.Background(), evt)
	if err != nil {
		t.Fatalf("SendEvent: %v", err)
	}

	if len(received) != 1 {
		t.Fatalf("expected 1 received event, got %d", len(received))
	}

	if received[0]["source"] != "sentinel-core" {
		t.Errorf("source=%v, want sentinel-core", received[0]["source"])
	}
	if received[0]["category"] != "jailbreak" {
		t.Errorf("category=%v, want jailbreak", received[0]["category"])
	}
	if received[0]["sensor_id"] != "test-sensor" {
		t.Errorf("sensor_id=%v, want test-sensor", received[0]["sensor_id"])
	}
}

func TestBusClient_Healthy(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	client := NewBusClient(ts.URL, "s1", "k1")
	if !client.Healthy() {
		t.Error("expected healthy")
	}

	// Unreachable server.
	client2 := NewBusClient("http://localhost:1", "s2", "k2")
	if client2.Healthy() {
		t.Error("expected unhealthy")
	}
}

// ── E2E Pipeline Test ────────────────────────────────────────────────────────

func TestSidecar_E2E_Pipeline(t *testing.T) {
	var receivedEvents []map[string]any

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/soc/events":
			var payload map[string]any
			json.NewDecoder(r.Body).Decode(&payload)
			receivedEvents = append(receivedEvents, payload)
			w.WriteHeader(http.StatusCreated)
		case "/health":
			w.WriteHeader(http.StatusOK)
		default:
			w.WriteHeader(http.StatusOK)
		}
	}))
	defer ts.Close()

	input := strings.Join([]string{
		"[DETECT] engine=jailbreak confidence=0.95 pattern=DAN",
		"INFO: processing complete",
		"[DETECT] engine=injection confidence=0.7 pattern=ignore_previous",
		"DEBUG: internal state update",
		"[DETECT] engine=exfiltration confidence=0.5 pattern=tool_call",
	}, "\n")

	cfg := Config{
		SensorType: "sentinel-core",
		LogPath:    "stdin",
		BusURL:     ts.URL,
		SensorID:   "e2e-test-sensor",
		APIKey:     "test-key",
	}

	sc := New(cfg)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := sc.RunReader(ctx, strings.NewReader(input))
	if err != nil {
		t.Fatalf("RunReader: %v", err)
	}

	stats := sc.GetStats()
	if stats.LinesRead != 5 {
		t.Errorf("LinesRead=%d, want 5", stats.LinesRead)
	}
	if stats.EventsSent != 3 {
		t.Errorf("EventsSent=%d, want 3 (3 DETECT lines, 2 skipped)", stats.EventsSent)
	}

	if len(receivedEvents) != 3 {
		t.Fatalf("received %d events, want 3", len(receivedEvents))
	}

	// Verify first event.
	first := receivedEvents[0]
	if first["category"] != "jailbreak" {
		t.Errorf("first event category=%v, want jailbreak", first["category"])
	}
	if first["sensor_id"] != "e2e-test-sensor" {
		t.Errorf("first event sensor_id=%v, want e2e-test-sensor", first["sensor_id"])
	}
}
