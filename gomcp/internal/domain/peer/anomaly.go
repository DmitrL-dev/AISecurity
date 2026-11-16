package peer

import (
	"math"
	"sync"
	"time"
)

// AnomalyLevel represents the severity of peer behavior anomaly.
type AnomalyLevel string

const (
	AnomalyNone     AnomalyLevel = "NONE"     // Normal behavior
	AnomalyLow      AnomalyLevel = "LOW"      // Slightly unusual
	AnomalyHigh     AnomalyLevel = "HIGH"     // Suspicious pattern
	AnomalyCritical AnomalyLevel = "CRITICAL" // Active threat (auto-demote)
)

// AnomalyResult is the analysis of a peer's request patterns.
type AnomalyResult struct {
	PeerID       string       `json:"peer_id"`
	Entropy      float64      `json:"entropy"` // Shannon entropy H(P) in bits
	RequestCount int          `json:"request_count"`
	Level        AnomalyLevel `json:"level"`
	Details      string       `json:"details"`
}

// AnomalyDetector tracks per-peer request patterns and detects anomalies
// using Shannon entropy analysis (v3.7 Cerebro).
//
// Normal sync pattern: low entropy (0.3-0.6), predictable request types.
// Anomaly: high entropy (>0.85), chaotic request spam / brute force.
type AnomalyDetector struct {
	mu       sync.RWMutex
	counters map[string]*peerRequestCounter // peerID → counter
}

type peerRequestCounter struct {
	types     map[string]int // request type → count
	total     int
	firstSeen time.Time
	lastSeen  time.Time
}

// NewAnomalyDetector creates a peer anomaly detector.
func NewAnomalyDetector() *AnomalyDetector {
	return &AnomalyDetector{
		counters: make(map[string]*peerRequestCounter),
	}
}

// RecordRequest records a request from a peer for entropy analysis.
func (d *AnomalyDetector) RecordRequest(peerID, requestType string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	c, ok := d.counters[peerID]
	if !ok {
		c = &peerRequestCounter{
			types:     make(map[string]int),
			firstSeen: time.Now(),
		}
		d.counters[peerID] = c
	}
	c.types[requestType]++
	c.total++
	c.lastSeen = time.Now()
}

// Analyze computes Shannon entropy for a peer's request distribution.
func (d *AnomalyDetector) Analyze(peerID string) AnomalyResult {
	// Snapshot the peer's counter under the read lock. Reading c.types/c.total
	// after releasing the lock races RecordRequest's locked map writes
	// (concurrent map iteration + write → fatal). All writers hold d.mu.Lock,
	// so copying under RLock is safe; compute on the copy outside the lock.
	d.mu.RLock()
	c, ok := d.counters[peerID]
	if !ok {
		d.mu.RUnlock()
		return AnomalyResult{PeerID: peerID, Level: AnomalyNone, Details: "no requests recorded"}
	}
	typesCopy := make(map[string]int, len(c.types))
	for k, v := range c.types {
		typesCopy[k] = v
	}
	total := c.total
	d.mu.RUnlock()

	entropy := shannonEntropy(typesCopy, total)
	level, details := classifyAnomaly(entropy, total, typesCopy)

	return AnomalyResult{
		PeerID:       peerID,
		Entropy:      entropy,
		RequestCount: total,
		Level:        level,
		Details:      details,
	}
}

// AnalyzeAll returns anomaly results for all tracked peers.
func (d *AnomalyDetector) AnalyzeAll() []AnomalyResult {
	d.mu.RLock()
	peerIDs := make([]string, 0, len(d.counters))
	for id := range d.counters {
		peerIDs = append(peerIDs, id)
	}
	d.mu.RUnlock()

	results := make([]AnomalyResult, 0, len(peerIDs))
	for _, id := range peerIDs {
		results = append(results, d.Analyze(id))
	}
	return results
}

// Reset clears all recorded data for a peer.
func (d *AnomalyDetector) Reset(peerID string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	delete(d.counters, peerID)
}

// AutoDemoteResult describes a peer that was auto-demoted due to anomaly.
type AutoDemoteResult struct {
	PeerID  string       `json:"peer_id"`
	Level   AnomalyLevel `json:"level"`
	Entropy float64      `json:"entropy"`
}

// CheckAndDemote runs anomaly analysis on all peers and returns any
// that should be demoted (CRITICAL level). The caller is responsible
// for actually updating TrustLevel and recording to decisions.log.
func (d *AnomalyDetector) CheckAndDemote() []AutoDemoteResult {
	results := d.AnalyzeAll()
	var demoted []AutoDemoteResult
	for _, r := range results {
		if r.Level == AnomalyCritical {
			demoted = append(demoted, AutoDemoteResult{
				PeerID:  r.PeerID,
				Level:   r.Level,
				Entropy: r.Entropy,
			})
		}
	}
	return demoted
}

// shannonEntropy computes H(P) = -Σ p(x) * log2(p(x)) for request type distribution.
func shannonEntropy(types map[string]int, total int) float64 {
	if total == 0 {
		return 0
	}
	var h float64
	for _, count := range types {
		p := float64(count) / float64(total)
		if p > 0 {
			h -= p * math.Log2(p)
		}
	}
	return h
}

func classifyAnomaly(entropy float64, total int, types map[string]int) (AnomalyLevel, string) {
	numTypes := len(types)

	// Normalize entropy to [0, 1] range relative to max possible.
	maxEntropy := math.Log2(float64(numTypes))
	if maxEntropy == 0 {
		maxEntropy = 1
	}
	normalizedH := entropy / maxEntropy

	switch {
	case total < 5:
		return AnomalyNone, "insufficient data"
	case normalizedH < 0.3:
		return AnomalyNone, "very predictable pattern (single dominant request type)"
	case normalizedH <= 0.6:
		return AnomalyLow, "normal sync pattern"
	case normalizedH <= 0.85:
		return AnomalyHigh, "elevated diversity — unusual request pattern"
	default:
		return AnomalyCritical, "chaotic request distribution — possible brute force or memory poisoning"
	}
}
