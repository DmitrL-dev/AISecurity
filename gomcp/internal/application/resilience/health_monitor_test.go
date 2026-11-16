package resilience

import (
	"context"
	"fmt"
	"math"
	"testing"
	"time"
)

// --- MetricsDB Tests ---

func TestRingBuffer_AddAndAll(t *testing.T) {
	rb := newRingBuffer(5)
	now := time.Now()

	for i := 0; i < 3; i++ {
		rb.Add(DataPoint{Timestamp: now.Add(time.Duration(i) * time.Second), Value: float64(i)})
	}

	if rb.Len() != 3 {
		t.Fatalf("expected 3, got %d", rb.Len())
	}

	all := rb.All()
	if len(all) != 3 {
		t.Fatalf("expected 3 points, got %d", len(all))
	}
	for i, dp := range all {
		if dp.Value != float64(i) {
			t.Errorf("point %d: expected %f, got %f", i, float64(i), dp.Value)
		}
	}
}

func TestRingBuffer_Wrap(t *testing.T) {
	rb := newRingBuffer(3)
	now := time.Now()

	for i := 0; i < 5; i++ {
		rb.Add(DataPoint{Timestamp: now.Add(time.Duration(i) * time.Second), Value: float64(i)})
	}

	if rb.Len() != 3 {
		t.Fatalf("expected 3 (buffer size), got %d", rb.Len())
	}

	all := rb.All()
	// Should contain values 2, 3, 4 (oldest 0, 1 overwritten).
	expected := []float64{2, 3, 4}
	for i, dp := range all {
		if dp.Value != expected[i] {
			t.Errorf("point %d: expected %f, got %f", i, expected[i], dp.Value)
		}
	}
}

func TestMetricsDB_AddAndBaseline(t *testing.T) {
	db := NewMetricsDB(time.Hour, 100)
	for i := 0; i < 20; i++ {
		db.AddDataPoint("soc-ingest", "cpu", 30.0+float64(i%5))
	}

	baseline := db.GetBaseline("soc-ingest", "cpu", time.Hour)
	if baseline.Count != 20 {
		t.Fatalf("expected 20 points, got %d", baseline.Count)
	}
	if baseline.Mean < 30 || baseline.Mean > 35 {
		t.Errorf("mean out of expected range: %f", baseline.Mean)
	}
	if baseline.StdDev == 0 {
		t.Error("expected non-zero stddev")
	}
}

func TestMetricsDB_EmptyBaseline(t *testing.T) {
	db := NewMetricsDB(time.Hour, 100)
	baseline := db.GetBaseline("nonexistent", "cpu", time.Hour)
	if baseline.Count != 0 {
		t.Errorf("expected 0 count for nonexistent, got %d", baseline.Count)
	}
}

func TestCalculateZScore(t *testing.T) {
	baseline := Baseline{Mean: 30.0, StdDev: 5.0, Count: 100}

	// Normal value (Z = 1.0).
	z := CalculateZScore(35.0, baseline)
	if math.Abs(z-1.0) > 0.01 {
		t.Errorf("expected Z≈1.0, got %f", z)
	}

	// Anomalous value (Z = 4.0).
	z = CalculateZScore(50.0, baseline)
	if math.Abs(z-4.0) > 0.01 {
		t.Errorf("expected Z≈4.0, got %f", z)
	}

	// Insufficient data → 0.
	z = CalculateZScore(50.0, Baseline{Mean: 30, StdDev: 5, Count: 5})
	if z != 0 {
		t.Errorf("expected 0 for insufficient data, got %f", z)
	}
}

func TestIsAnomaly(t *testing.T) {
	baseline := Baseline{Mean: 30.0, StdDev: 5.0, Count: 100}

	if IsAnomaly(35.0, baseline, 3.0) {
		t.Error("35 should not be anomaly (Z=1.0)")
	}
	if !IsAnomaly(50.0, baseline, 3.0) {
		t.Error("50 should be anomaly (Z=4.0)")
	}
	if !IsAnomaly(10.0, baseline, 3.0) {
		t.Error("10 should be anomaly (Z=-4.0)")
	}
}

func TestMetricsDB_Purge(t *testing.T) {
	db := NewMetricsDB(100*time.Millisecond, 100)
	db.AddDataPoint("comp", "cpu", 50)
	time.Sleep(150 * time.Millisecond)
	db.AddDataPoint("comp", "cpu", 60)

	removed := db.Purge()
	if removed != 1 {
		t.Errorf("expected 1 purged, got %d", removed)
	}
}

func TestMetricsDB_GetRecent(t *testing.T) {
	db := NewMetricsDB(time.Hour, 100)
	for i := 0; i < 10; i++ {
		db.AddDataPoint("comp", "mem", float64(i*10))
	}

	recent := db.GetRecent("comp", "mem", 3)
	if len(recent) != 3 {
		t.Fatalf("expected 3 recent, got %d", len(recent))
	}
	// Should be last 3: 70, 80, 90.
	if recent[0].Value != 70 || recent[2].Value != 90 {
		t.Errorf("unexpected recent values: %v", recent)
	}
}

// --- MockCollector for HealthMonitor tests ---

type mockCollector struct {
	results map[string]map[string]float64
	errors  map[string]error
}

func (m *mockCollector) Collect(_ context.Context, component string) (map[string]float64, error) {
	if err, ok := m.errors[component]; ok && err != nil {
		return nil, err
	}
	if metrics, ok := m.results[component]; ok {
		return metrics, nil
	}
	return map[string]float64{}, nil
}

// --- HealthMonitor Tests ---

// HM-01: Normal health check — all HEALTHY.
func TestHealthMonitor_HM01_AllHealthy(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	registerTestComponents(hm, 6)

	health := hm.GetHealth()
	if health.OverallStatus != OverallHealthy {
		t.Errorf("expected HEALTHY, got %s", health.OverallStatus)
	}
	if !health.QuorumValid {
		t.Error("expected quorum valid")
	}
	if len(health.Components) != 6 {
		t.Errorf("expected 6 components, got %d", len(health.Components))
	}
}

// HM-02: Single component DEGRADED.
func TestHealthMonitor_HM02_SingleDegraded(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	registerTestComponents(hm, 6)
	hm.SetComponentStatus("comp-0", StatusDegraded)

	health := hm.GetHealth()
	if health.OverallStatus != OverallDegraded {
		t.Errorf("expected DEGRADED, got %s", health.OverallStatus)
	}
	if !health.QuorumValid {
		t.Error("expected quorum still valid with 5/6 healthy")
	}
}

// HM-03: Multiple components CRITICAL → quorum lost.
func TestHealthMonitor_HM03_MultipleCritical(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	registerTestComponents(hm, 6)
	hm.SetComponentStatus("comp-0", StatusCritical)
	hm.SetComponentStatus("comp-1", StatusCritical)
	hm.SetComponentStatus("comp-2", StatusCritical)

	health := hm.GetHealth()
	if health.OverallStatus != OverallCritical {
		t.Errorf("expected CRITICAL, got %s", health.OverallStatus)
	}
	if health.QuorumValid {
		t.Error("expected quorum INVALID with 3/6 critical")
	}
}

// HM-04: Anomaly detection (CPU spike).
func TestHealthMonitor_HM04_CPUAnomaly(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 100)
	hm.RegisterComponent(ComponentConfig{
		Name:           "soc-ingest",
		Type:           "go_binary",
		Thresholds:     map[string]float64{"cpu": 80},
		ThresholdIsMax: map[string]bool{"cpu": true},
	})

	// Build baseline of normal CPU (30%).
	for i := 0; i < 50; i++ {
		hm.metricsDB.AddDataPoint("soc-ingest", "cpu", 30.0)
	}

	// Spike to 95%.
	hm.UpdateMetrics("soc-ingest", map[string]float64{"cpu": 95.0})
	hm.checkHealth()

	// Should have alert(s).
	select {
	case alert := <-hm.alertBus:
		if alert.Component != "soc-ingest" {
			t.Errorf("expected soc-ingest, got %s", alert.Component)
		}
		if alert.Metric != "cpu" {
			t.Errorf("expected cpu metric, got %s", alert.Metric)
		}
	default:
		t.Error("expected alert for CPU spike")
	}
}

// HM-05: Memory leak detection.
func TestHealthMonitor_HM05_MemoryLeak(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 100)
	hm.RegisterComponent(ComponentConfig{
		Name:           "soc-correlate",
		Type:           "go_binary",
		Thresholds:     map[string]float64{"memory": 90},
		ThresholdIsMax: map[string]bool{"memory": true},
	})

	// Build baseline of normal memory (40%).
	for i := 0; i < 50; i++ {
		hm.metricsDB.AddDataPoint("soc-correlate", "memory", 40.0)
	}

	// Memory spike to 95%.
	hm.UpdateMetrics("soc-correlate", map[string]float64{"memory": 95.0})
	hm.checkHealth()

	select {
	case alert := <-hm.alertBus:
		if alert.Metric != "memory" {
			t.Errorf("expected memory metric, got %s", alert.Metric)
		}
	default:
		t.Error("expected alert for memory spike")
	}
}

// HM-06: Quorum validation failure.
func TestHealthMonitor_HM06_QuorumFailure(t *testing.T) {
	statuses := map[string]ComponentStatus{
		"a": StatusOffline,
		"b": StatusOffline,
		"c": StatusOffline,
		"d": StatusOffline,
		"e": StatusHealthy,
		"f": StatusHealthy,
	}
	if ValidateQuorum(statuses) {
		t.Error("expected quorum invalid with 4/6 offline")
	}
}

// HM-06b: Quorum validation success (edge case: exactly 2/3).
func TestHealthMonitor_HM06b_QuorumEdge(t *testing.T) {
	statuses := map[string]ComponentStatus{
		"a": StatusHealthy,
		"b": StatusHealthy,
		"c": StatusCritical,
	}
	if !ValidateQuorum(statuses) {
		t.Error("expected quorum valid with 2/3 healthy (exact threshold)")
	}
}

// HM-06c: Empty quorum.
func TestHealthMonitor_HM06c_EmptyQuorum(t *testing.T) {
	if ValidateQuorum(map[string]ComponentStatus{}) {
		t.Error("expected quorum invalid with 0 components")
	}
}

// HM-07: Metrics collection (no data loss).
func TestHealthMonitor_HM07_MetricsCollection(t *testing.T) {
	collector := &mockCollector{
		results: map[string]map[string]float64{
			"comp-0": {"cpu": 25, "memory": 40},
		},
	}
	hm := NewHealthMonitor(collector, 10)
	hm.RegisterComponent(ComponentConfig{Name: "comp-0", Type: "go_binary"})

	hm.collectMetrics(context.Background())

	hm.mu.RLock()
	comp := hm.components["comp-0"]
	hm.mu.RUnlock()

	if comp.Metrics["cpu"] != 25 {
		t.Errorf("expected cpu=25, got %f", comp.Metrics["cpu"])
	}
	if comp.Metrics["memory"] != 40 {
		t.Errorf("expected memory=40, got %f", comp.Metrics["memory"])
	}
}

// HM-07b: Collection error increments consecutive failures.
func TestHealthMonitor_HM07b_CollectionError(t *testing.T) {
	collector := &mockCollector{
		errors: map[string]error{
			"comp-0": fmt.Errorf("connection refused"),
		},
	}
	hm := NewHealthMonitor(collector, 10)
	hm.RegisterComponent(ComponentConfig{Name: "comp-0", Type: "go_binary"})

	hm.collectMetrics(context.Background())

	hm.mu.RLock()
	comp := hm.components["comp-0"]
	hm.mu.RUnlock()

	if comp.Consecutive != 1 {
		t.Errorf("expected 1 consecutive failure, got %d", comp.Consecutive)
	}
}

// HM-08: Alert bus fan-out (non-blocking).
func TestHealthMonitor_HM08_AlertBusFanOut(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 5)
	hm.RegisterComponent(ComponentConfig{
		Name:           "comp",
		Type:           "go_binary",
		Thresholds:     map[string]float64{"cpu": 50},
		ThresholdIsMax: map[string]bool{"cpu": true},
	})

	// Fill alert bus.
	for i := 0; i < 5; i++ {
		hm.alertBus <- HealthAlert{Component: fmt.Sprintf("test-%d", i)}
	}

	// Emit one more — should be dropped (non-blocking).
	hm.emitAlert(HealthAlert{Component: "overflow"})
	// No panic = success.
}

// Test GetHealth returns a deep copy.
func TestHealthMonitor_GetHealthDeepCopy(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	hm.RegisterComponent(ComponentConfig{Name: "test", Type: "go_binary"})
	hm.UpdateMetrics("test", map[string]float64{"cpu": 50})

	health := hm.GetHealth()
	health.Components[0].Metrics["cpu"] = 999

	// Original should be unchanged.
	hm.mu.RLock()
	original := hm.components["test"].Metrics["cpu"]
	hm.mu.RUnlock()

	if original != 50 {
		t.Errorf("deep copy failed: original modified to %f", original)
	}
}

// Test threshold breach transitions status to DEGRADED then CRITICAL.
func TestHealthMonitor_StatusTransitions(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 100)
	hm.RegisterComponent(ComponentConfig{
		Name:           "comp",
		Type:           "go_binary",
		Thresholds:     map[string]float64{"error_rate": 5},
		ThresholdIsMax: map[string]bool{"error_rate": true},
	})

	// Breach once → DEGRADED.
	hm.UpdateMetrics("comp", map[string]float64{"error_rate": 10})
	hm.checkHealth()

	hm.mu.RLock()
	status := hm.components["comp"].Status
	hm.mu.RUnlock()
	if status != StatusDegraded {
		t.Errorf("expected DEGRADED after 1 breach, got %s", status)
	}

	// Breach 3× → CRITICAL.
	for i := 0; i < 3; i++ {
		hm.checkHealth()
	}
	hm.mu.RLock()
	status = hm.components["comp"].Status
	hm.mu.RUnlock()
	if status != StatusCritical {
		t.Errorf("expected CRITICAL after repeated breaches, got %s", status)
	}
}

// Test lower-bound threshold (ThresholdIsMax=false).
func TestHealthMonitor_LowerBoundThreshold(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 100)
	hm.RegisterComponent(ComponentConfig{
		Name:           "immune",
		Type:           "c_kernel_module",
		Thresholds:     map[string]float64{"hooks_active": 10},
		ThresholdIsMax: map[string]bool{"hooks_active": false},
	})

	// hooks_active = 5 (below threshold of 10) → warning.
	hm.UpdateMetrics("immune", map[string]float64{"hooks_active": 5})
	hm.checkHealth()

	select {
	case alert := <-hm.alertBus:
		if alert.Component != "immune" || alert.Metric != "hooks_active" {
			t.Errorf("unexpected alert: %+v", alert)
		}
	default:
		t.Error("expected alert for hooks_active below threshold")
	}
}

// Test ComponentCount.
func TestHealthMonitor_ComponentCount(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	if hm.ComponentCount() != 0 {
		t.Error("expected 0 initially")
	}
	registerTestComponents(hm, 4)
	if hm.ComponentCount() != 4 {
		t.Errorf("expected 4, got %d", hm.ComponentCount())
	}
}

// Test Start/Stop lifecycle.
func TestHealthMonitor_StartStop(t *testing.T) {
	hm := NewHealthMonitor(&mockCollector{}, 10)
	registerTestComponents(hm, 2)

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})

	go func() {
		hm.Start(ctx)
		close(done)
	}()

	// Let it run briefly.
	time.Sleep(50 * time.Millisecond)
	cancel()

	select {
	case <-done:
		// Clean shutdown.
	case <-time.After(time.Second):
		t.Fatal("Start() did not return after context cancellation")
	}
}

// --- Helpers ---

func registerTestComponents(hm *HealthMonitor, n int) {
	for i := 0; i < n; i++ {
		hm.RegisterComponent(ComponentConfig{
			Name: fmt.Sprintf("comp-%d", i),
			Type: "go_binary",
		})
	}
}
