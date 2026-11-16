package resilience

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// ComponentStatus defines the health state of a monitored component.
type ComponentStatus string

const (
	StatusHealthy  ComponentStatus = "HEALTHY"
	StatusDegraded ComponentStatus = "DEGRADED"
	StatusCritical ComponentStatus = "CRITICAL"
	StatusOffline  ComponentStatus = "OFFLINE"
)

// AlertSeverity defines the severity of a health alert.
type AlertSeverity string

const (
	SeverityInfo     AlertSeverity = "INFO"
	SeverityWarning  AlertSeverity = "WARNING"
	SeverityCritical AlertSeverity = "CRITICAL"
)

// OverallStatus aggregates component statuses into a system-wide status.
type OverallStatus string

const (
	OverallHealthy  OverallStatus = "HEALTHY"
	OverallDegraded OverallStatus = "DEGRADED"
	OverallCritical OverallStatus = "CRITICAL"
)

// Default intervals per ТЗ §3.1.2.
const (
	MetricsCollectionInterval = 10 * time.Second
	HealthCheckInterval       = 30 * time.Second
	QuorumValidationInterval  = 60 * time.Second

	// AnomalyZScoreThreshold — Z > 3.0 = anomaly (99.7% confidence).
	AnomalyZScoreThreshold = 3.0

	// QuorumThreshold — 2/3 must be healthy.
	QuorumThreshold = 0.66

	// MaxConsecutiveFailures before marking CRITICAL.
	MaxConsecutiveFailures = 3
)

// ComponentConfig defines monitoring thresholds for a component.
type ComponentConfig struct {
	Name       string             `json:"name"`
	Type       string             `json:"type"` // go_binary, c_binary, c_kernel_module
	Thresholds map[string]float64 `json:"thresholds"`
	// Whether threshold is an upper bound (true) or lower bound (false).
	ThresholdIsMax map[string]bool `json:"threshold_is_max"`
}

// ComponentHealth tracks the health state of a single component.
type ComponentHealth struct {
	Name        string            `json:"name"`
	Status      ComponentStatus   `json:"status"`
	Metrics     map[string]float64 `json:"metrics"`
	LastCheck   time.Time         `json:"last_check"`
	Consecutive int               `json:"consecutive_failures"`
	Config      ComponentConfig   `json:"-"`
}

// HealthAlert represents a detected health anomaly.
type HealthAlert struct {
	Component       string        `json:"component"`
	Severity        AlertSeverity `json:"severity"`
	Metric          string        `json:"metric"`
	Current         float64       `json:"current"`
	Threshold       float64       `json:"threshold"`
	ZScore          float64       `json:"z_score,omitempty"`
	Timestamp       time.Time     `json:"timestamp"`
	SuggestedAction string        `json:"suggested_action"`
}

// HealthResponse is the API response for GET /api/v1/resilience/health.
type HealthResponse struct {
	OverallStatus     OverallStatus     `json:"overall_status"`
	Components        []ComponentHealth `json:"components"`
	QuorumValid       bool              `json:"quorum_valid"`
	LastCheck         time.Time         `json:"last_check"`
	AnomaliesDetected []HealthAlert     `json:"anomalies_detected"`
}

// MetricsCollector is the interface for collecting metrics from components.
// Implementations can use /healthz endpoints, /metrics, or runtime stats.
type MetricsCollector interface {
	Collect(ctx context.Context, component string) (map[string]float64, error)
}

// HealthMonitor is the L1 Self-Monitoring orchestrator.
// It collects metrics, runs anomaly detection, validates quorum,
// and emits HealthAlerts to the alert bus.
type HealthMonitor struct {
	mu         sync.RWMutex
	components map[string]*ComponentHealth
	metricsDB  *MetricsDB
	alertBus   chan HealthAlert
	collector  MetricsCollector
	logger     *slog.Logger

	// anomalyWindow is the baseline window for Z-score calculation.
	anomalyWindow time.Duration
}

// NewHealthMonitor creates a new health monitor.
func NewHealthMonitor(collector MetricsCollector, alertBufSize int) *HealthMonitor {
	if alertBufSize <= 0 {
		alertBufSize = 100
	}
	return &HealthMonitor{
		components:    make(map[string]*ComponentHealth),
		metricsDB:     NewMetricsDB(DefaultMetricsWindow, DefaultMetricsMaxSize),
		alertBus:      make(chan HealthAlert, alertBufSize),
		collector:     collector,
		logger:        slog.Default().With("component", "sarl-health-monitor"),
		anomalyWindow: 24 * time.Hour,
	}
}

// RegisterComponent adds a component to be monitored.
func (hm *HealthMonitor) RegisterComponent(config ComponentConfig) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	hm.components[config.Name] = &ComponentHealth{
		Name:    config.Name,
		Status:  StatusHealthy,
		Metrics: make(map[string]float64),
		Config:  config,
	}
	hm.logger.Info("component registered", "name", config.Name, "type", config.Type)
}

// AlertBus returns the channel for consuming health alerts.
func (hm *HealthMonitor) AlertBus() <-chan HealthAlert {
	return hm.alertBus
}

// Start begins the monitoring loops. Blocks until ctx is cancelled.
func (hm *HealthMonitor) Start(ctx context.Context) {
	hm.logger.Info("health monitor started")

	metricsTicker := time.NewTicker(MetricsCollectionInterval)
	healthTicker := time.NewTicker(HealthCheckInterval)
	quorumTicker := time.NewTicker(QuorumValidationInterval)
	defer metricsTicker.Stop()
	defer healthTicker.Stop()
	defer quorumTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			hm.logger.Info("health monitor stopped")
			return
		case <-metricsTicker.C:
			hm.collectMetrics(ctx)
		case <-healthTicker.C:
			hm.checkHealth()
		case <-quorumTicker.C:
			hm.validateQuorum()
		}
	}
}

// collectMetrics gathers metrics from all registered components.
func (hm *HealthMonitor) collectMetrics(ctx context.Context) {
	hm.mu.RLock()
	names := make([]string, 0, len(hm.components))
	for name := range hm.components {
		names = append(names, name)
	}
	hm.mu.RUnlock()

	for _, name := range names {
		metrics, err := hm.collector.Collect(ctx, name)
		if err != nil {
			hm.logger.Warn("metrics collection failed", "component", name, "error", err)
			hm.mu.Lock()
			if comp, ok := hm.components[name]; ok {
				comp.Consecutive++
			}
			hm.mu.Unlock()
			continue
		}

		hm.mu.Lock()
		comp, ok := hm.components[name]
		if ok {
			comp.Metrics = metrics
			comp.LastCheck = time.Now()
			// Store each metric in time-series DB.
			for metric, value := range metrics {
				hm.metricsDB.AddDataPoint(name, metric, value)
			}
		}
		hm.mu.Unlock()
	}
}

// checkHealth evaluates each component against thresholds and anomalies.
func (hm *HealthMonitor) checkHealth() {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	for _, comp := range hm.components {
		alerts := hm.evaluateComponent(comp)
		for _, alert := range alerts {
			hm.emitAlert(alert)
		}
	}
}

// evaluateComponent checks a single component's metrics against thresholds
// and runs Z-score anomaly detection. Returns any generated alerts.
func (hm *HealthMonitor) evaluateComponent(comp *ComponentHealth) []HealthAlert {
	var alerts []HealthAlert
	breached := false

	for metric, value := range comp.Metrics {
		threshold, hasThreshold := comp.Config.Thresholds[metric]
		if !hasThreshold {
			continue
		}

		isMax := comp.Config.ThresholdIsMax[metric]
		var exceeded bool
		if isMax {
			exceeded = value > threshold
		} else {
			exceeded = value < threshold
		}

		if exceeded {
			breached = true
			action := "restart"
			if metric == "error_rate" || metric == "latency_p99" {
				action = "investigate"
			}

			alerts = append(alerts, HealthAlert{
				Component:       comp.Name,
				Severity:        SeverityWarning,
				Metric:          metric,
				Current:         value,
				Threshold:       threshold,
				Timestamp:       time.Now(),
				SuggestedAction: action,
			})
		}

		// Z-score anomaly detection.
		baseline := hm.metricsDB.GetBaseline(comp.Name, metric, hm.anomalyWindow)
		if IsAnomaly(value, baseline, AnomalyZScoreThreshold) {
			zscore := CalculateZScore(value, baseline)
			alerts = append(alerts, HealthAlert{
				Component:       comp.Name,
				Severity:        SeverityCritical,
				Metric:          metric,
				Current:         value,
				Threshold:       baseline.Mean + AnomalyZScoreThreshold*baseline.StdDev,
				ZScore:          zscore,
				Timestamp:       time.Now(),
				SuggestedAction: fmt.Sprintf("anomaly detected (Z=%.2f), investigate %s", zscore, metric),
			})
		}
	}

	// Update component status.
	if breached {
		comp.Consecutive++
		if comp.Consecutive >= MaxConsecutiveFailures {
			comp.Status = StatusCritical
		} else {
			comp.Status = StatusDegraded
		}
	} else {
		comp.Consecutive = 0
		comp.Status = StatusHealthy
	}

	return alerts
}

// emitAlert sends an alert to the bus (non-blocking).
func (hm *HealthMonitor) emitAlert(alert HealthAlert) {
	select {
	case hm.alertBus <- alert:
		hm.logger.Warn("health alert emitted",
			"component", alert.Component,
			"severity", alert.Severity,
			"metric", alert.Metric,
			"current", alert.Current,
			"threshold", alert.Threshold,
		)
	default:
		hm.logger.Error("alert bus full, dropping alert",
			"component", alert.Component,
			"metric", alert.Metric,
		)
	}
}

// validateQuorum checks if 2/3 of components are healthy.
func (hm *HealthMonitor) validateQuorum() {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	if len(hm.components) == 0 {
		return
	}

	valid := ValidateQuorum(hm.componentStatuses())

	if !valid {
		hm.logger.Error("QUORUM LOST — entering degraded state",
			"healthy_ratio", hm.healthyRatio(),
			"threshold", QuorumThreshold,
		)
		hm.emitAlert(HealthAlert{
			Component:       "system",
			Severity:        SeverityCritical,
			Metric:          "quorum",
			Current:         hm.healthyRatio(),
			Threshold:       QuorumThreshold,
			Timestamp:       time.Now(),
			SuggestedAction: "activate safe mode",
		})
	}
}

// ValidateQuorum checks if the healthy ratio meets the 2/3 threshold.
func ValidateQuorum(statuses map[string]ComponentStatus) bool {
	if len(statuses) == 0 {
		return false
	}

	healthy := 0
	for _, status := range statuses {
		if status == StatusHealthy {
			healthy++
		}
	}
	return float64(healthy)/float64(len(statuses)) >= QuorumThreshold
}

// componentStatuses returns current status map (caller must hold RLock).
func (hm *HealthMonitor) componentStatuses() map[string]ComponentStatus {
	statuses := make(map[string]ComponentStatus, len(hm.components))
	for name, comp := range hm.components {
		statuses[name] = comp.Status
	}
	return statuses
}

// healthyRatio returns the fraction of healthy components (caller must hold RLock).
func (hm *HealthMonitor) healthyRatio() float64 {
	if len(hm.components) == 0 {
		return 0
	}
	healthy := 0
	for _, comp := range hm.components {
		if comp.Status == StatusHealthy {
			healthy++
		}
	}
	return float64(healthy) / float64(len(hm.components))
}

// GetHealth returns a snapshot of the entire system health.
func (hm *HealthMonitor) GetHealth() HealthResponse {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	components := make([]ComponentHealth, 0, len(hm.components))
	for _, comp := range hm.components {
		cp := *comp
		// Deep copy metrics.
		cp.Metrics = make(map[string]float64, len(comp.Metrics))
		for k, v := range comp.Metrics {
			cp.Metrics[k] = v
		}
		components = append(components, cp)
	}

	overall := OverallHealthy
	for _, comp := range components {
		switch comp.Status {
		case StatusCritical, StatusOffline:
			overall = OverallCritical
		case StatusDegraded:
			if overall != OverallCritical {
				overall = OverallDegraded
			}
		}
	}

	return HealthResponse{
		OverallStatus: overall,
		Components:    components,
		QuorumValid:   ValidateQuorum(hm.componentStatuses()),
		LastCheck:     time.Now(),
	}
}

// SetComponentStatus manually sets a component's status (for testing/override).
func (hm *HealthMonitor) SetComponentStatus(name string, status ComponentStatus) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	if comp, ok := hm.components[name]; ok {
		comp.Status = status
	}
}

// UpdateMetrics manually updates a component's metrics (for testing/override).
func (hm *HealthMonitor) UpdateMetrics(name string, metrics map[string]float64) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	if comp, ok := hm.components[name]; ok {
		comp.Metrics = metrics
		comp.LastCheck = time.Now()
		for metric, value := range metrics {
			hm.metricsDB.AddDataPoint(name, metric, value)
		}
	}
}

// ComponentCount returns the number of registered components.
func (hm *HealthMonitor) ComponentCount() int {
	hm.mu.RLock()
	defer hm.mu.RUnlock()
	return len(hm.components)
}
