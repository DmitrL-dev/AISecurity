package soc

import (
	"testing"
)

func TestAnomalyDetector_NoAlertDuringWarmup(t *testing.T) {
	d := NewAnomalyDetector()
	// First 10 observations are warmup — should never alert
	for i := 0; i < 10; i++ {
		alert := d.Observe("cpu", 50.0)
		if alert != nil {
			t.Fatalf("should not alert during warmup, got alert at observation %d", i)
		}
	}
}

func TestAnomalyDetector_NormalValues(t *testing.T) {
	d := NewAnomalyDetector()
	// Build baseline with consistent values
	for i := 0; i < 20; i++ {
		d.Observe("rps", 100.0+float64(i%3)) // values: 100, 101, 102
	}

	// Normal value should not trigger
	alert := d.Observe("rps", 103.0)
	if alert != nil {
		t.Fatal("normal value should not trigger anomaly")
	}
}

func TestAnomalyDetector_ExtremeValue(t *testing.T) {
	d := NewAnomalyDetector()
	// Build tight baseline
	for i := 0; i < 30; i++ {
		d.Observe("latency_ms", 10.0)
	}

	// Extreme spike should trigger
	alert := d.Observe("latency_ms", 1000.0)
	if alert == nil {
		t.Fatal("extreme value should trigger anomaly")
	}
	if alert.Severity != "CRITICAL" {
		t.Fatalf("extreme deviation should be CRITICAL, got %s", alert.Severity)
	}
	if alert.ZScore < 3.0 {
		t.Fatalf("Z-score should be >= 3.0, got %f", alert.ZScore)
	}
}

func TestAnomalyDetector_CustomThreshold(t *testing.T) {
	d := NewAnomalyDetector()
	d.SetThreshold(2.0) // More sensitive

	for i := 0; i < 30; i++ {
		d.Observe("mem", 50.0)
	}

	// Moderate deviation should trigger with lower threshold
	alert := d.Observe("mem", 80.0)
	if alert == nil {
		t.Fatal("moderate deviation should trigger with Z=2.0 threshold")
	}
}

func TestAnomalyDetector_Baselines(t *testing.T) {
	d := NewAnomalyDetector()
	d.Observe("metric_a", 10.0)
	d.Observe("metric_b", 20.0)

	baselines := d.Baselines()
	if len(baselines) != 2 {
		t.Fatalf("expected 2 baselines, got %d", len(baselines))
	}
}

func TestAnomalyDetector_Alerts(t *testing.T) {
	d := NewAnomalyDetector()
	for i := 0; i < 30; i++ {
		d.Observe("test", 10.0)
	}
	d.Observe("test", 10000.0) // trigger alert

	alerts := d.Alerts(10)
	if len(alerts) != 1 {
		t.Fatalf("expected 1 alert, got %d", len(alerts))
	}
}

func TestAnomalyDetector_Stats(t *testing.T) {
	d := NewAnomalyDetector()
	d.Observe("x", 1.0)
	stats := d.Stats()
	if stats["metrics_tracked"].(int) != 1 {
		t.Fatal("should track 1 metric")
	}
	if stats["z_threshold"].(float64) != 3.0 {
		t.Fatal("default threshold should be 3.0")
	}
}
