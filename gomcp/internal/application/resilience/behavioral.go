package resilience

import (
	"context"
	"log/slog"
	"runtime"
	"time"
)

// BehaviorProfile captures the runtime behavior of a component.
type BehaviorProfile struct {
	Goroutines      int                `json:"goroutines"`
	HeapAllocMB     float64            `json:"heap_alloc_mb"`
	HeapObjectsK    float64            `json:"heap_objects_k"`
	GCPauseMs       float64            `json:"gc_pause_ms"`
	NumGC           uint32             `json:"num_gc"`
	FileDescriptors int                `json:"file_descriptors,omitempty"`
	CustomMetrics   map[string]float64 `json:"custom_metrics,omitempty"`
}

// BehavioralAlert is emitted when a behavioral anomaly is detected.
type BehavioralAlert struct {
	Component   string    `json:"component"`
	AnomalyType string    `json:"anomaly_type"` // goroutine_leak, memory_leak, gc_pressure, etc.
	Metric      string    `json:"metric"`
	Current     float64   `json:"current"`
	Baseline    float64   `json:"baseline"`
	ZScore      float64   `json:"z_score"`
	Severity    string    `json:"severity"`
	Timestamp   time.Time `json:"timestamp"`
}

// BehavioralAnalyzer provides Go-side runtime behavioral analysis.
// It profiles the current process and compares against learned baselines.
// On Linux, eBPF hooks (immune/resilience_hooks.c) extend this to kernel level.
type BehavioralAnalyzer struct {
	metricsDB *MetricsDB
	alertBus  chan BehavioralAlert
	interval  time.Duration
	component string // self component name
	logger    *slog.Logger
}

// NewBehavioralAnalyzer creates a new behavioral analyzer.
func NewBehavioralAnalyzer(component string, alertBufSize int) *BehavioralAnalyzer {
	if alertBufSize <= 0 {
		alertBufSize = 50
	}
	return &BehavioralAnalyzer{
		metricsDB: NewMetricsDB(DefaultMetricsWindow, DefaultMetricsMaxSize),
		alertBus:  make(chan BehavioralAlert, alertBufSize),
		interval:  1 * time.Minute,
		component: component,
		logger:    slog.Default().With("component", "sarl-behavioral"),
	}
}

// AlertBus returns the channel for consuming behavioral alerts.
func (ba *BehavioralAnalyzer) AlertBus() <-chan BehavioralAlert {
	return ba.alertBus
}

// Start begins continuous behavioral monitoring. Blocks until ctx cancelled.
func (ba *BehavioralAnalyzer) Start(ctx context.Context) {
	ba.logger.Info("behavioral analyzer started", "interval", ba.interval)

	ticker := time.NewTicker(ba.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			ba.logger.Info("behavioral analyzer stopped")
			return
		case <-ticker.C:
			ba.collectAndAnalyze()
		}
	}
}

// collectAndAnalyze profiles runtime and checks for anomalies.
func (ba *BehavioralAnalyzer) collectAndAnalyze() {
	profile := ba.collectProfile()
	ba.storeMetrics(profile)
	ba.detectAnomalies(profile)
}

// collectProfile gathers current Go runtime stats.
func (ba *BehavioralAnalyzer) collectProfile() BehaviorProfile {
	var mem runtime.MemStats
	runtime.ReadMemStats(&mem)

	return BehaviorProfile{
		Goroutines:   runtime.NumGoroutine(),
		HeapAllocMB:  float64(mem.HeapAlloc) / (1024 * 1024),
		HeapObjectsK: float64(mem.HeapObjects) / 1000,
		GCPauseMs:    float64(mem.PauseNs[(mem.NumGC+255)%256]) / 1e6,
		NumGC:        mem.NumGC,
	}
}

// storeMetrics records profile data in the time-series DB.
func (ba *BehavioralAnalyzer) storeMetrics(p BehaviorProfile) {
	ba.metricsDB.AddDataPoint(ba.component, "goroutines", float64(p.Goroutines))
	ba.metricsDB.AddDataPoint(ba.component, "heap_alloc_mb", p.HeapAllocMB)
	ba.metricsDB.AddDataPoint(ba.component, "heap_objects_k", p.HeapObjectsK)
	ba.metricsDB.AddDataPoint(ba.component, "gc_pause_ms", p.GCPauseMs)
}

// detectAnomalies checks each metric against its baseline via Z-score.
func (ba *BehavioralAnalyzer) detectAnomalies(p BehaviorProfile) {
	checks := []struct {
		metric      string
		value       float64
		anomalyType string
		severity    string
	}{
		{"goroutines", float64(p.Goroutines), "goroutine_leak", "WARNING"},
		{"heap_alloc_mb", p.HeapAllocMB, "memory_leak", "CRITICAL"},
		{"heap_objects_k", p.HeapObjectsK, "object_leak", "WARNING"},
		{"gc_pause_ms", p.GCPauseMs, "gc_pressure", "WARNING"},
	}

	for _, c := range checks {
		baseline := ba.metricsDB.GetBaseline(ba.component, c.metric, DefaultMetricsWindow)
		if !IsAnomaly(c.value, baseline, AnomalyZScoreThreshold) {
			continue
		}

		zscore := CalculateZScore(c.value, baseline)
		alert := BehavioralAlert{
			Component:   ba.component,
			AnomalyType: c.anomalyType,
			Metric:      c.metric,
			Current:     c.value,
			Baseline:    baseline.Mean,
			ZScore:      zscore,
			Severity:    c.severity,
			Timestamp:   time.Now(),
		}

		select {
		case ba.alertBus <- alert:
			ba.logger.Warn("behavioral anomaly detected",
				"type", c.anomalyType,
				"metric", c.metric,
				"z_score", zscore,
			)
		default:
			ba.logger.Error("behavioral alert bus full")
		}
	}
}

// InjectMetric allows manually injecting a metric for testing.
func (ba *BehavioralAnalyzer) InjectMetric(metric string, value float64) {
	ba.metricsDB.AddDataPoint(ba.component, metric, value)
}

// CurrentProfile returns a snapshot of the current runtime profile.
func (ba *BehavioralAnalyzer) CurrentProfile() BehaviorProfile {
	return ba.collectProfile()
}
