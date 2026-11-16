package resilience

import (
	"context"
	"testing"
	"time"
)

// IM-01: Goroutine leak detection.
func TestBehavioral_IM01_GoroutineLeak(t *testing.T) {
	ba := NewBehavioralAnalyzer("soc-ingest", 10)

	// Build baseline of 10 goroutines.
	for i := 0; i < 50; i++ {
		ba.InjectMetric("goroutines", 10)
	}

	// Spike to 1000 goroutines — should trigger anomaly.
	ba.metricsDB.AddDataPoint("soc-ingest", "goroutines", 1000)
	profile := BehaviorProfile{Goroutines: 1000}
	ba.detectAnomalies(profile)

	select {
	case alert := <-ba.alertBus:
		if alert.AnomalyType != "goroutine_leak" {
			t.Errorf("expected goroutine_leak, got %s", alert.AnomalyType)
		}
		if alert.ZScore <= 3 {
			t.Errorf("expected Z > 3, got %f", alert.ZScore)
		}
	default:
		t.Error("expected goroutine leak alert")
	}
}

// IM-02: Memory leak detection.
func TestBehavioral_IM02_MemoryLeak(t *testing.T) {
	ba := NewBehavioralAnalyzer("soc-correlate", 10)

	// Baseline: 50 MB.
	for i := 0; i < 50; i++ {
		ba.InjectMetric("heap_alloc_mb", 50)
	}

	// Spike to 500 MB.
	ba.metricsDB.AddDataPoint("soc-correlate", "heap_alloc_mb", 500)
	profile := BehaviorProfile{HeapAllocMB: 500}
	ba.detectAnomalies(profile)

	select {
	case alert := <-ba.alertBus:
		if alert.AnomalyType != "memory_leak" {
			t.Errorf("expected memory_leak, got %s", alert.AnomalyType)
		}
		if alert.Severity != "CRITICAL" {
			t.Errorf("expected CRITICAL severity, got %s", alert.Severity)
		}
	default:
		t.Error("expected memory leak alert")
	}
}

// IM-03: GC pressure detection.
func TestBehavioral_IM03_GCPressure(t *testing.T) {
	ba := NewBehavioralAnalyzer("soc-respond", 10)

	// Baseline: 1ms GC pause.
	for i := 0; i < 50; i++ {
		ba.InjectMetric("gc_pause_ms", 1)
	}

	// Spike to 100ms.
	ba.metricsDB.AddDataPoint("soc-respond", "gc_pause_ms", 100)
	profile := BehaviorProfile{GCPauseMs: 100}
	ba.detectAnomalies(profile)

	select {
	case alert := <-ba.alertBus:
		if alert.AnomalyType != "gc_pressure" {
			t.Errorf("expected gc_pressure, got %s", alert.AnomalyType)
		}
	default:
		t.Error("expected gc_pressure alert")
	}
}

// IM-04: Object leak detection.
func TestBehavioral_IM04_ObjectLeak(t *testing.T) {
	ba := NewBehavioralAnalyzer("shield", 10)

	for i := 0; i < 50; i++ {
		ba.InjectMetric("heap_objects_k", 100)
	}

	ba.metricsDB.AddDataPoint("shield", "heap_objects_k", 5000)
	profile := BehaviorProfile{HeapObjectsK: 5000}
	ba.detectAnomalies(profile)

	select {
	case alert := <-ba.alertBus:
		if alert.AnomalyType != "object_leak" {
			t.Errorf("expected object_leak, got %s", alert.AnomalyType)
		}
	default:
		t.Error("expected object leak alert")
	}
}

// IM-05: Normal behavior — no alerts.
func TestBehavioral_IM05_NormalBehavior(t *testing.T) {
	ba := NewBehavioralAnalyzer("sidecar", 10)

	for i := 0; i < 50; i++ {
		ba.InjectMetric("goroutines", 10)
		ba.InjectMetric("heap_alloc_mb", 50)
		ba.InjectMetric("heap_objects_k", 100)
		ba.InjectMetric("gc_pause_ms", 1)
	}

	profile := BehaviorProfile{
		Goroutines:   10,
		HeapAllocMB:  50,
		HeapObjectsK: 100,
		GCPauseMs:    1,
	}
	ba.detectAnomalies(profile)

	select {
	case alert := <-ba.alertBus:
		t.Errorf("expected no alerts for normal behavior, got %+v", alert)
	default:
		// Good — no alerts.
	}
}

// IM-06: Start/Stop lifecycle.
func TestBehavioral_IM06_StartStop(t *testing.T) {
	ba := NewBehavioralAnalyzer("test", 10)
	ba.interval = 50 * time.Millisecond

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})

	go func() {
		ba.Start(ctx)
		close(done)
	}()

	time.Sleep(100 * time.Millisecond)
	cancel()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("Start() did not return after context cancellation")
	}
}

// IM-07: CurrentProfile returns valid data.
func TestBehavioral_IM07_CurrentProfile(t *testing.T) {
	ba := NewBehavioralAnalyzer("test", 10)
	profile := ba.CurrentProfile()

	if profile.Goroutines <= 0 {
		t.Error("expected positive goroutine count")
	}
	if profile.HeapAllocMB <= 0 {
		t.Error("expected positive heap alloc")
	}
}

// IM-08: Alert bus overflow (non-blocking).
func TestBehavioral_IM08_AlertBusOverflow(t *testing.T) {
	ba := NewBehavioralAnalyzer("test", 2)

	// Fill bus.
	ba.alertBus <- BehavioralAlert{AnomalyType: "fill1"}
	ba.alertBus <- BehavioralAlert{AnomalyType: "fill2"}

	// Build baseline.
	for i := 0; i < 50; i++ {
		ba.InjectMetric("goroutines", 10)
	}

	// This should not panic.
	ba.metricsDB.AddDataPoint("test", "goroutines", 10000)
	ba.detectAnomalies(BehaviorProfile{Goroutines: 10000})
}

// Test collectAndAnalyze runs without error.
func TestBehavioral_CollectAndAnalyze(t *testing.T) {
	ba := NewBehavioralAnalyzer("test", 10)
	// Should not panic.
	ba.collectAndAnalyze()
}

// Test InjectMetric stores data.
func TestBehavioral_InjectMetric(t *testing.T) {
	ba := NewBehavioralAnalyzer("test", 10)
	ba.InjectMetric("custom", 42.0)

	recent := ba.metricsDB.GetRecent("test", "custom", 1)
	if len(recent) != 1 || recent[0].Value != 42.0 {
		t.Errorf("expected 42.0, got %v", recent)
	}
}
