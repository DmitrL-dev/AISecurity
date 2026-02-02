package metrics

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

// Counter tests
func TestNewCounter(t *testing.T) {
	c := NewCounter("test_counter", "Test counter", nil)
	if c == nil {
		t.Fatal("counter should not be nil")
	}
	if c.Name() != "test_counter" {
		t.Errorf("expected test_counter, got %s", c.Name())
	}
}

func TestCounter_Inc(t *testing.T) {
	c := NewCounter("test", "test", nil)
	c.Inc()
	if c.Value() != 1 {
		t.Errorf("expected 1, got %f", c.Value())
	}
	c.Inc()
	c.Inc()
	if c.Value() != 3 {
		t.Errorf("expected 3, got %f", c.Value())
	}
}

func TestCounter_Add(t *testing.T) {
	c := NewCounter("test", "test", nil)
	c.Add(5)
	if c.Value() != 5 {
		t.Errorf("expected 5, got %f", c.Value())
	}
	c.Add(2.5)
	if c.Value() != 7.5 {
		t.Errorf("expected 7.5, got %f", c.Value())
	}
}

func TestCounter_Add_Negative(t *testing.T) {
	c := NewCounter("test", "test", nil)
	c.Add(5)
	c.Add(-3) // Should be ignored
	if c.Value() != 5 {
		t.Errorf("expected 5, got %f", c.Value())
	}
}

func TestCounter_Concurrent(t *testing.T) {
	c := NewCounter("test", "test", nil)
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c.Inc()
		}()
	}
	wg.Wait()

	if c.Value() != 100 {
		t.Errorf("expected 100, got %f", c.Value())
	}
}

// Gauge tests
func TestNewGauge(t *testing.T) {
	g := NewGauge("test_gauge", "Test gauge", nil)
	if g == nil {
		t.Fatal("gauge should not be nil")
	}
	if g.Name() != "test_gauge" {
		t.Errorf("expected test_gauge, got %s", g.Name())
	}
}

func TestGauge_Set(t *testing.T) {
	g := NewGauge("test", "test", nil)
	g.Set(42)
	if g.Value() != 42 {
		t.Errorf("expected 42, got %f", g.Value())
	}
	g.Set(-10)
	if g.Value() != -10 {
		t.Errorf("expected -10, got %f", g.Value())
	}
}

func TestGauge_Inc(t *testing.T) {
	g := NewGauge("test", "test", nil)
	g.Inc()
	if g.Value() != 1 {
		t.Errorf("expected 1, got %f", g.Value())
	}
}

func TestGauge_Dec(t *testing.T) {
	g := NewGauge("test", "test", nil)
	g.Set(5)
	g.Dec()
	if g.Value() != 4 {
		t.Errorf("expected 4, got %f", g.Value())
	}
}

func TestGauge_Add(t *testing.T) {
	g := NewGauge("test", "test", nil)
	g.Add(10)
	if g.Value() != 10 {
		t.Errorf("expected 10, got %f", g.Value())
	}
}

func TestGauge_Sub(t *testing.T) {
	g := NewGauge("test", "test", nil)
	g.Set(10)
	g.Sub(3)
	if g.Value() != 7 {
		t.Errorf("expected 7, got %f", g.Value())
	}
}

func TestGauge_Concurrent(t *testing.T) {
	g := NewGauge("test", "test", nil)
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(2)
		go func() {
			defer wg.Done()
			g.Inc()
		}()
		go func() {
			defer wg.Done()
			g.Dec()
		}()
	}
	wg.Wait()

	// Should end up at 0
	if g.Value() != 0 {
		t.Errorf("expected 0, got %f", g.Value())
	}
}

// Histogram tests
func TestNewHistogram(t *testing.T) {
	h := NewHistogram("test_histogram", "Test histogram", nil, nil)
	if h == nil {
		t.Fatal("histogram should not be nil")
	}
	if h.Name() != "test_histogram" {
		t.Errorf("expected test_histogram, got %s", h.Name())
	}
}

func TestNewHistogram_CustomBuckets(t *testing.T) {
	buckets := []float64{1, 5, 10}
	h := NewHistogram("test", "test", nil, buckets)
	if len(h.buckets) != 3 {
		t.Errorf("expected 3 buckets, got %d", len(h.buckets))
	}
}

func TestHistogram_Observe(t *testing.T) {
	h := NewHistogram("test", "test", nil, []float64{1, 5, 10})
	h.Observe(0.5)
	h.Observe(3)
	h.Observe(7)

	if h.Count() != 3 {
		t.Errorf("expected 3, got %d", h.Count())
	}
	if h.Sum() != 10.5 {
		t.Errorf("expected 10.5, got %f", h.Sum())
	}
}

func TestHistogram_Concurrent(t *testing.T) {
	h := NewHistogram("test", "test", nil, nil)
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(v int) {
			defer wg.Done()
			h.Observe(float64(v) / 100.0)
		}(i)
	}
	wg.Wait()

	if h.Count() != 100 {
		t.Errorf("expected 100, got %d", h.Count())
	}
}

// Timer tests
func TestNewTimer(t *testing.T) {
	h := NewHistogram("test", "test", nil, nil)
	timer := NewTimer(h)
	if timer == nil {
		t.Fatal("timer should not be nil")
	}
}

func TestTimer_ObserveDuration(t *testing.T) {
	h := NewHistogram("test", "test", nil, nil)
	timer := NewTimer(h)
	time.Sleep(10 * time.Millisecond)
	d := timer.ObserveDuration()

	if d < 10*time.Millisecond {
		t.Errorf("duration should be at least 10ms, got %v", d)
	}
	if h.Count() != 1 {
		t.Errorf("expected 1 observation, got %d", h.Count())
	}
}

func TestTimer_NilHistogram(t *testing.T) {
	timer := NewTimer(nil)
	d := timer.ObserveDuration()
	if d < 0 {
		t.Error("duration should be non-negative")
	}
}

// Registry tests
func TestNewRegistry(t *testing.T) {
	r := NewRegistry()
	if r == nil {
		t.Fatal("registry should not be nil")
	}
}

func TestRegistry_RegisterCounter(t *testing.T) {
	r := NewRegistry()
	c := NewCounter("test", "test", nil)
	r.RegisterCounter(c)

	got := r.GetCounter("test")
	if got != c {
		t.Error("counter not found in registry")
	}
}

func TestRegistry_RegisterGauge(t *testing.T) {
	r := NewRegistry()
	g := NewGauge("test", "test", nil)
	r.RegisterGauge(g)

	got := r.GetGauge("test")
	if got != g {
		t.Error("gauge not found in registry")
	}
}

func TestRegistry_RegisterHistogram(t *testing.T) {
	r := NewRegistry()
	h := NewHistogram("test", "test", nil, nil)
	r.RegisterHistogram(h)

	got := r.GetHistogram("test")
	if got != h {
		t.Error("histogram not found in registry")
	}
}

func TestRegistry_GetCounter_NotFound(t *testing.T) {
	r := NewRegistry()
	if r.GetCounter("nonexistent") != nil {
		t.Error("expected nil for nonexistent counter")
	}
}

func TestRegistry_Handler(t *testing.T) {
	r := NewRegistry()
	c := NewCounter("test_counter", "Test counter", nil)
	c.Inc()
	r.RegisterCounter(c)

	handler := r.Handler()
	req := httptest.NewRequest("GET", "/metrics", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), "test_counter") {
		t.Error("response should contain test_counter")
	}
}

// GoMCPMetrics tests
func TestNewGoMCPMetrics(t *testing.T) {
	m := NewGoMCPMetrics()
	if m == nil {
		t.Fatal("metrics should not be nil")
	}
	if m.Registry == nil {
		t.Error("registry should not be nil")
	}
}

func TestGoMCPMetrics_Counters(t *testing.T) {
	m := NewGoMCPMetrics()

	if m.ToolCallsTotal == nil {
		t.Error("ToolCallsTotal should not be nil")
	}
	if m.ToolErrorsTotal == nil {
		t.Error("ToolErrorsTotal should not be nil")
	}
	if m.ValidationFails == nil {
		t.Error("ValidationFails should not be nil")
	}
	if m.RateLimitHits == nil {
		t.Error("RateLimitHits should not be nil")
	}
}

func TestGoMCPMetrics_Gauges(t *testing.T) {
	m := NewGoMCPMetrics()

	if m.ActiveWorkers == nil {
		t.Error("ActiveWorkers should not be nil")
	}
	if m.ActiveTenants == nil {
		t.Error("ActiveTenants should not be nil")
	}
	if m.QueuedCalls == nil {
		t.Error("QueuedCalls should not be nil")
	}
}

func TestGoMCPMetrics_Histograms(t *testing.T) {
	m := NewGoMCPMetrics()

	if m.ToolCallDuration == nil {
		t.Error("ToolCallDuration should not be nil")
	}
	if m.ValidationTime == nil {
		t.Error("ValidationTime should not be nil")
	}
	if m.BatchSize == nil {
		t.Error("BatchSize should not be nil")
	}
}

func TestGoMCPMetrics_RecordToolCall_Success(t *testing.T) {
	m := NewGoMCPMetrics()
	m.RecordToolCall(100*time.Millisecond, true)

	if m.ToolCallsTotal.Value() != 1 {
		t.Errorf("expected 1, got %f", m.ToolCallsTotal.Value())
	}
	if m.ToolErrorsTotal.Value() != 0 {
		t.Errorf("expected 0, got %f", m.ToolErrorsTotal.Value())
	}
	if m.ToolCallDuration.Count() != 1 {
		t.Errorf("expected 1, got %d", m.ToolCallDuration.Count())
	}
}

func TestGoMCPMetrics_RecordToolCall_Failure(t *testing.T) {
	m := NewGoMCPMetrics()
	m.RecordToolCall(50*time.Millisecond, false)

	if m.ToolCallsTotal.Value() != 1 {
		t.Errorf("expected 1, got %f", m.ToolCallsTotal.Value())
	}
	if m.ToolErrorsTotal.Value() != 1 {
		t.Errorf("expected 1, got %f", m.ToolErrorsTotal.Value())
	}
}

func TestGoMCPMetrics_Handler(t *testing.T) {
	m := NewGoMCPMetrics()
	m.ToolCallsTotal.Inc()
	m.ActiveWorkers.Set(5)

	handler := m.Handler()
	req := httptest.NewRequest("GET", "/metrics", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	if !strings.Contains(bodyStr, "gomcp_tool_calls_total") {
		t.Error("should contain gomcp_tool_calls_total")
	}
	if !strings.Contains(bodyStr, "gomcp_active_workers") {
		t.Error("should contain gomcp_active_workers")
	}
}

// Label tests
func TestLabels_Format(t *testing.T) {
	labels := Labels{"method": "GET", "status": "200"}
	result := formatLabels(labels)

	if !strings.Contains(result, "method=") {
		t.Error("should contain method label")
	}
	if !strings.Contains(result, "status=") {
		t.Error("should contain status label")
	}
}

func TestLabels_Empty(t *testing.T) {
	result := formatLabels(nil)
	if result != "" {
		t.Errorf("expected empty string, got %s", result)
	}
}

func TestCopyLabels(t *testing.T) {
	original := Labels{"key": "value"}
	copied := copyLabels(original)

	if copied["key"] != "value" {
		t.Error("copied label should have same value")
	}

	copied["key"] = "modified"
	if original["key"] == "modified" {
		t.Error("original should not be modified")
	}
}

// Format tests
func TestFormatFloat(t *testing.T) {
	result := formatFloat(5.5)
	if result == "" {
		t.Error("should not be empty")
	}
}

func TestFormatUint(t *testing.T) {
	result := formatUint(42)
	if result != "42" {
		t.Errorf("expected 42, got %s", result)
	}
}

func TestFormatUint_Zero(t *testing.T) {
	result := formatUint(0)
	if result != "0" {
		t.Errorf("expected 0, got %s", result)
	}
}

func TestUintToString(t *testing.T) {
	tests := []struct {
		input    uint64
		expected string
	}{
		{0, "0"},
		{1, "1"},
		{42, "42"},
		{123, "123"},
		{1000, "1000"},
	}

	for _, tt := range tests {
		result := uintToString(tt.input)
		if result != tt.expected {
			t.Errorf("uintToString(%d): expected %s, got %s", tt.input, tt.expected, result)
		}
	}
}

// Benchmark tests
func BenchmarkCounter_Inc(b *testing.B) {
	c := NewCounter("test", "test", nil)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		c.Inc()
	}
}

func BenchmarkGauge_Set(b *testing.B) {
	g := NewGauge("test", "test", nil)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		g.Set(float64(i))
	}
}

func BenchmarkHistogram_Observe(b *testing.B) {
	h := NewHistogram("test", "test", nil, nil)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		h.Observe(float64(i) / 1000.0)
	}
}

func BenchmarkRegistry_Handler(b *testing.B) {
	m := NewGoMCPMetrics()
	m.ToolCallsTotal.Add(1000)
	m.ActiveWorkers.Set(10)

	handler := m.Handler()
	req := httptest.NewRequest("GET", "/metrics", nil)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, req)
	}
}
