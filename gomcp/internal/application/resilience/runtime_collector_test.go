package resilience

import (
	"context"
	"testing"
)

func TestRuntimeMetricsCollector_SelfComponentReturnsRealMetrics(t *testing.T) {
	c := NewRuntimeMetricsCollector("soc-server", nil)
	m, err := c.Collect(context.Background(), "soc-server")
	if err != nil {
		t.Fatalf("Collect(self) error: %v", err)
	}
	for _, key := range []string{"heap_alloc_mb", "goroutines", "num_gc", "gc_pause_ms"} {
		if _, ok := m[key]; !ok {
			t.Errorf("missing real metric %q", key)
		}
	}
	if m["goroutines"] < 1 {
		t.Errorf("goroutines should be >= 1, got %v", m["goroutines"])
	}
	// scan_saturation must be ABSENT when no source is wired (not faked as 0).
	if _, ok := m["scan_saturation"]; ok {
		t.Error("scan_saturation must be omitted when no source is wired (no fabrication)")
	}
}

func TestRuntimeMetricsCollector_UnknownComponentErrors(t *testing.T) {
	c := NewRuntimeMetricsCollector("soc-server", nil)
	m, err := c.Collect(context.Background(), "postgres")
	if err == nil {
		t.Fatal("unknown component must return an error (never fabricate metrics)")
	}
	if m != nil {
		t.Errorf("expected nil metrics for unknown component, got %#v", m)
	}
}

func TestRuntimeMetricsCollector_ScanSaturationWiredIsReported(t *testing.T) {
	c := NewRuntimeMetricsCollector("soc-server", func() float64 { return 0.42 })
	m, err := c.Collect(context.Background(), "soc-server")
	if err != nil {
		t.Fatalf("Collect error: %v", err)
	}
	if got, ok := m["scan_saturation"]; !ok || got != 0.42 {
		t.Errorf("expected scan_saturation=0.42 when wired, got %v ok=%v", got, ok)
	}
}

func TestRuntimeMetricsCollector_DefaultComponentName(t *testing.T) {
	c := NewRuntimeMetricsCollector("", nil)
	if c.SelfComponent() != "soc-server" {
		t.Errorf("expected default self component 'soc-server', got %q", c.SelfComponent())
	}
}
