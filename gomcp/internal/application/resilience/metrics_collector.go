// Package resilience implements the Sentinel Autonomous Resilience Layer (SARL).
//
// Five levels of autonomous self-recovery:
//
//	L1 — Self-Monitoring: health checks, quorum, anomaly detection
//	L2 — Self-Healing: restart, rollback, recovery strategies
//	L3 — Self-Preservation: emergency modes (safe/lockdown/apoptosis)
//	L4 — Immune Integration: behavioral anomaly detection
//	L5 — Autonomous Recovery: playbooks for resurrection, consensus, crypto
package resilience

import (
	"math"
	"sync"
	"time"
)

// MetricsDB provides an in-memory time-series store with ring buffers
// for each component/metric pair. Supports rolling baselines (mean/stddev)
// for Z-score anomaly detection.
type MetricsDB struct {
	mu      sync.RWMutex
	series  map[string]*RingBuffer // key = "component:metric"
	window  time.Duration          // retention window (default 1h)
	maxSize int                    // max data points per series
}

// DataPoint is a single timestamped metric value.
type DataPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

// Baseline holds rolling statistics for anomaly detection.
type Baseline struct {
	Mean   float64 `json:"mean"`
	StdDev float64 `json:"std_dev"`
	Count  int     `json:"count"`
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
}

// RingBuffer is a fixed-size circular buffer for DataPoints.
type RingBuffer struct {
	data  []DataPoint
	head  int
	count int
	size  int
}

// DefaultMetricsWindow is the default retention window (1 hour).
const DefaultMetricsWindow = 1 * time.Hour

// DefaultMetricsMaxSize is the default max points per series (1h / 10s = 360).
const DefaultMetricsMaxSize = 360

// NewMetricsDB creates a new in-memory time-series store.
func NewMetricsDB(window time.Duration, maxSize int) *MetricsDB {
	if window <= 0 {
		window = DefaultMetricsWindow
	}
	if maxSize <= 0 {
		maxSize = DefaultMetricsMaxSize
	}
	return &MetricsDB{
		series:  make(map[string]*RingBuffer),
		window:  window,
		maxSize: maxSize,
	}
}

// AddDataPoint records a metric value for a component.
func (db *MetricsDB) AddDataPoint(component, metric string, value float64) {
	key := component + ":" + metric
	db.mu.Lock()
	defer db.mu.Unlock()

	rb, ok := db.series[key]
	if !ok {
		rb = newRingBuffer(db.maxSize)
		db.series[key] = rb
	}
	rb.Add(DataPoint{Timestamp: time.Now(), Value: value})
}

// GetBaseline returns rolling mean/stddev for a component metric
// calculated over the specified window duration.
func (db *MetricsDB) GetBaseline(component, metric string, window time.Duration) Baseline {
	key := component + ":" + metric
	db.mu.RLock()
	defer db.mu.RUnlock()

	rb, ok := db.series[key]
	if !ok {
		return Baseline{}
	}

	cutoff := time.Now().Add(-window)
	points := rb.After(cutoff)

	if len(points) == 0 {
		return Baseline{}
	}

	return calculateBaseline(points)
}

// GetRecent returns the most recent N data points for a component metric.
func (db *MetricsDB) GetRecent(component, metric string, n int) []DataPoint {
	key := component + ":" + metric
	db.mu.RLock()
	defer db.mu.RUnlock()

	rb, ok := db.series[key]
	if !ok {
		return nil
	}

	all := rb.All()
	if len(all) <= n {
		return all
	}
	return all[len(all)-n:]
}

// CalculateZScore returns the Z-score for a value against the baseline.
// Returns 0 if baseline has insufficient data or zero stddev.
func CalculateZScore(value float64, baseline Baseline) float64 {
	if baseline.Count < 10 || baseline.StdDev == 0 {
		return 0
	}
	return (value - baseline.Mean) / baseline.StdDev
}

// IsAnomaly returns true if the Z-score exceeds the threshold (default 3.0).
func IsAnomaly(value float64, baseline Baseline, threshold float64) bool {
	if threshold <= 0 {
		threshold = 3.0
	}
	zscore := CalculateZScore(value, baseline)
	return math.Abs(zscore) > threshold
}

// SeriesCount returns the number of tracked series.
func (db *MetricsDB) SeriesCount() int {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return len(db.series)
}

// Purge removes data points older than the retention window.
func (db *MetricsDB) Purge() int {
	db.mu.Lock()
	defer db.mu.Unlock()

	cutoff := time.Now().Add(-db.window)
	total := 0
	for key, rb := range db.series {
		removed := rb.RemoveBefore(cutoff)
		total += removed
		if rb.Len() == 0 {
			delete(db.series, key)
		}
	}
	return total
}

// --- RingBuffer implementation ---

func newRingBuffer(size int) *RingBuffer {
	return &RingBuffer{
		data: make([]DataPoint, size),
		size: size,
	}
}

// Add inserts a DataPoint, overwriting the oldest if full.
func (rb *RingBuffer) Add(dp DataPoint) {
	rb.data[rb.head] = dp
	rb.head = (rb.head + 1) % rb.size
	if rb.count < rb.size {
		rb.count++
	}
}

// Len returns the number of data points in the buffer.
func (rb *RingBuffer) Len() int {
	return rb.count
}

// All returns all data points in chronological order.
func (rb *RingBuffer) All() []DataPoint {
	if rb.count == 0 {
		return nil
	}

	result := make([]DataPoint, rb.count)
	if rb.count < rb.size {
		// Buffer not yet full — data starts at 0.
		copy(result, rb.data[:rb.count])
	} else {
		// Buffer wrapped — oldest is at head.
		n := copy(result, rb.data[rb.head:rb.size])
		copy(result[n:], rb.data[:rb.head])
	}
	return result
}

// After returns points with timestamp after the cutoff.
func (rb *RingBuffer) After(cutoff time.Time) []DataPoint {
	all := rb.All()
	result := make([]DataPoint, 0, len(all))
	for _, dp := range all {
		if dp.Timestamp.After(cutoff) {
			result = append(result, dp)
		}
	}
	return result
}

// RemoveBefore removes data points before the cutoff by compacting.
// Returns the number of points removed.
func (rb *RingBuffer) RemoveBefore(cutoff time.Time) int {
	all := rb.All()
	kept := make([]DataPoint, 0, len(all))
	for _, dp := range all {
		if !dp.Timestamp.Before(cutoff) {
			kept = append(kept, dp)
		}
	}

	removed := len(all) - len(kept)
	if removed == 0 {
		return 0
	}

	// Rebuild the ring buffer with kept data.
	rb.count = 0
	rb.head = 0
	for _, dp := range kept {
		rb.Add(dp)
	}
	return removed
}

// --- Statistics ---

func calculateBaseline(points []DataPoint) Baseline {
	n := len(points)
	if n == 0 {
		return Baseline{}
	}

	var sum, min, max float64
	min = points[0].Value
	max = points[0].Value

	for _, p := range points {
		sum += p.Value
		if p.Value < min {
			min = p.Value
		}
		if p.Value > max {
			max = p.Value
		}
	}
	mean := sum / float64(n)

	var variance float64
	for _, p := range points {
		diff := p.Value - mean
		variance += diff * diff
	}
	variance /= float64(n)

	return Baseline{
		Mean:   mean,
		StdDev: math.Sqrt(variance),
		Count:  n,
		Min:    min,
		Max:    max,
	}
}
