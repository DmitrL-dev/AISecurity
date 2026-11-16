package peer

import (
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestAnomalyDetector_ConcurrentRecordAndAnalyze is a race regression test.
// Analyze previously released the read lock before iterating the per-peer
// types map, so a concurrent RecordRequest (which writes that map under the
// write lock) caused a fatal "concurrent map read and map write". This test
// hammers both paths against the same peer; run with -race to detect the race.
func TestAnomalyDetector_ConcurrentRecordAndAnalyze(t *testing.T) {
	d := NewAnomalyDetector()

	const iters = 2000
	var wg sync.WaitGroup
	wg.Add(3)

	// Writer: continuously records varied request types for "hot" peer.
	go func() {
		defer wg.Done()
		types := []string{"sync", "ping", "handshake", "delta", "status"}
		for i := 0; i < iters; i++ {
			d.RecordRequest("hot", types[i%len(types)])
		}
	}()

	// Reader 1: Analyze the same peer the writer is mutating.
	go func() {
		defer wg.Done()
		for i := 0; i < iters; i++ {
			_ = d.Analyze("hot")
		}
	}()

	// Reader 2: AnalyzeAll walks every counter.
	go func() {
		defer wg.Done()
		for i := 0; i < iters; i++ {
			_ = d.AnalyzeAll()
		}
	}()

	wg.Wait()

	result := d.Analyze("hot")
	assert.Equal(t, iters, result.RequestCount)
}

func TestAnomalyDetector_NormalPattern(t *testing.T) {
	d := NewAnomalyDetector()

	// Simulate normal sync: mostly "sync" requests with some "ping".
	for i := 0; i < 20; i++ {
		d.RecordRequest("peer-1", "sync")
	}
	for i := 0; i < 3; i++ {
		d.RecordRequest("peer-1", "ping")
	}

	result := d.Analyze("peer-1")
	assert.Equal(t, 23, result.RequestCount)
	assert.True(t, result.Entropy > 0)
	// Low entropy with 2 types, dominated by one → should be LOW or NONE.
	assert.NotEqual(t, AnomalyCritical, result.Level)
}

func TestAnomalyDetector_ChaoticPattern(t *testing.T) {
	d := NewAnomalyDetector()

	// Simulate chaotic pattern: many diverse request types equally distributed.
	types := []string{"sync", "ping", "handshake", "delta_sync", "status", "genome", "unknown1", "unknown2", "brute1", "brute2"}
	for _, rt := range types {
		for i := 0; i < 5; i++ {
			d.RecordRequest("attacker", rt)
		}
	}

	result := d.Analyze("attacker")
	assert.Equal(t, 50, result.RequestCount)
	// Uniform distribution → max entropy → CRITICAL.
	assert.Equal(t, AnomalyCritical, result.Level)
}

func TestAnomalyDetector_UnknownPeer(t *testing.T) {
	d := NewAnomalyDetector()
	result := d.Analyze("nonexistent")
	assert.Equal(t, AnomalyNone, result.Level)
	assert.Equal(t, 0, result.RequestCount)
}

func TestAnomalyDetector_InsufficientData(t *testing.T) {
	d := NewAnomalyDetector()
	d.RecordRequest("peer-new", "sync")
	d.RecordRequest("peer-new", "ping")

	result := d.Analyze("peer-new")
	assert.Equal(t, AnomalyNone, result.Level)
	assert.Contains(t, result.Details, "insufficient data")
}

func TestAnomalyDetector_Reset(t *testing.T) {
	d := NewAnomalyDetector()
	d.RecordRequest("peer-x", "sync")
	d.RecordRequest("peer-x", "sync")
	d.Reset("peer-x")

	result := d.Analyze("peer-x")
	assert.Equal(t, AnomalyNone, result.Level)
	assert.Equal(t, 0, result.RequestCount)
}

func TestAnomalyDetector_AnalyzeAll(t *testing.T) {
	d := NewAnomalyDetector()
	d.RecordRequest("peer-a", "sync")
	d.RecordRequest("peer-b", "ping")

	results := d.AnalyzeAll()
	assert.Len(t, results, 2)
}

func TestShannonEntropy_Uniform(t *testing.T) {
	// Uniform distribution over 4 types → H = log2(4) = 2.0.
	types := map[string]int{"a": 10, "b": 10, "c": 10, "d": 10}
	h := shannonEntropy(types, 40)
	assert.InDelta(t, 2.0, h, 0.01)
}

func TestShannonEntropy_SingleType(t *testing.T) {
	// Single type → H = 0.
	types := map[string]int{"sync": 100}
	h := shannonEntropy(types, 100)
	assert.Equal(t, 0.0, h)
}
