package soc

import (
	"math"
	"sync"
	"time"
)

// AnomalyDetector implements §5 — statistical baseline anomaly detection.
// Uses exponentially weighted moving average (EWMA) with Z-score thresholds.
type AnomalyDetector struct {
	mu         sync.RWMutex
	baselines  map[string]*Baseline
	alerts     []AnomalyAlert
	zThreshold float64 // Z-score threshold for anomaly (default: 3.0)
	maxAlerts  int
}

// Baseline tracks statistical properties of a metric.
type Baseline struct {
	Name       string    `json:"name"`
	Mean       float64   `json:"mean"`
	Variance   float64   `json:"variance"`
	StdDev     float64   `json:"std_dev"`
	Count      int64     `json:"count"`
	LastValue  float64   `json:"last_value"`
	LastUpdate time.Time `json:"last_update"`
	Alpha      float64   `json:"alpha"` // EWMA smoothing factor
}

// AnomalyAlert is raised when a metric deviates beyond the threshold.
type AnomalyAlert struct {
	ID        string    `json:"id"`
	Metric    string    `json:"metric"`
	Value     float64   `json:"value"`
	Expected  float64   `json:"expected"`
	StdDev    float64   `json:"std_dev"`
	ZScore    float64   `json:"z_score"`
	Severity  string    `json:"severity"`
	Timestamp time.Time `json:"timestamp"`
}

// NewAnomalyDetector creates the detector with default Z-score threshold of 3.0.
func NewAnomalyDetector() *AnomalyDetector {
	return &AnomalyDetector{
		baselines:  make(map[string]*Baseline),
		zThreshold: 3.0,
		maxAlerts:  500,
	}
}

// SetThreshold configures the Z-score anomaly threshold.
func (d *AnomalyDetector) SetThreshold(z float64) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.zThreshold = z
}

// Observe records a new data point for a metric and checks for anomalies.
// Returns an AnomalyAlert if the value exceeds the threshold, nil otherwise.
func (d *AnomalyDetector) Observe(metric string, value float64) *AnomalyAlert {
	d.mu.Lock()
	defer d.mu.Unlock()

	b, exists := d.baselines[metric]
	if !exists {
		// First observation: initialize baseline
		d.baselines[metric] = &Baseline{
			Name:       metric,
			Mean:       value,
			Count:      1,
			LastValue:  value,
			LastUpdate: time.Now(),
			Alpha:      0.1, // EWMA smoothing factor
		}
		return nil
	}

	b.Count++
	b.LastValue = value
	b.LastUpdate = time.Now()

	// Need minimum observations for meaningful statistics
	if b.Count < 10 {
		// Update running variance (Welford's online algorithm)
		// delta MUST be computed BEFORE updating the mean
		delta := value - b.Mean
		b.Mean = b.Mean + delta/float64(b.Count)
		delta2 := value - b.Mean
		b.Variance = b.Variance + (delta*delta2-b.Variance)/float64(b.Count)
		b.StdDev = math.Sqrt(b.Variance)
		return nil
	}

	// Calculate Z-score
	if b.StdDev == 0 {
		b.StdDev = 0.001 // prevent division by zero
	}
	zScore := math.Abs(value-b.Mean) / b.StdDev

	// Update baseline using EWMA
	b.Mean = b.Alpha*value + (1-b.Alpha)*b.Mean
	delta := value - b.Mean
	b.Variance = b.Alpha*(delta*delta) + (1-b.Alpha)*b.Variance
	b.StdDev = math.Sqrt(b.Variance)

	// Check threshold
	if zScore >= d.zThreshold {
		alert := &AnomalyAlert{
			ID:        genID("anomaly"),
			Metric:    metric,
			Value:     value,
			Expected:  b.Mean,
			StdDev:    b.StdDev,
			ZScore:    math.Round(zScore*100) / 100,
			Severity:  d.classifySeverity(zScore),
			Timestamp: time.Now(),
		}

		if len(d.alerts) >= d.maxAlerts {
			copy(d.alerts, d.alerts[1:])
			d.alerts[len(d.alerts)-1] = *alert
		} else {
			d.alerts = append(d.alerts, *alert)
		}
		return alert
	}

	return nil
}

// classifySeverity maps Z-score to severity level.
func (d *AnomalyDetector) classifySeverity(z float64) string {
	switch {
	case z >= 5.0:
		return "CRITICAL"
	case z >= 4.0:
		return "HIGH"
	case z >= 3.0:
		return "MEDIUM"
	default:
		return "LOW"
	}
}

// Alerts returns recent anomaly alerts.
func (d *AnomalyDetector) Alerts(limit int) []AnomalyAlert {
	d.mu.RLock()
	defer d.mu.RUnlock()
	if limit <= 0 || limit > len(d.alerts) {
		limit = len(d.alerts)
	}
	start := len(d.alerts) - limit
	result := make([]AnomalyAlert, limit)
	copy(result, d.alerts[start:])
	return result
}

// Baselines returns all tracked metric baselines.
func (d *AnomalyDetector) Baselines() map[string]Baseline {
	d.mu.RLock()
	defer d.mu.RUnlock()
	result := make(map[string]Baseline, len(d.baselines))
	for k, v := range d.baselines {
		result[k] = *v
	}
	return result
}

// Stats returns detector statistics.
func (d *AnomalyDetector) Stats() map[string]any {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return map[string]any{
		"metrics_tracked": len(d.baselines),
		"total_alerts":    len(d.alerts),
		"z_threshold":     d.zThreshold,
	}
}
