package soc

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"

	"github.com/stretchr/testify/require"
)

// TestLoadTest_SustainedThroughput measures SOC pipeline throughput and latency
// under sustained concurrent load. Reports p50/p95/p99 latencies and events/sec.
func TestLoadTest_SustainedThroughput(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping load test in short mode")
	}

	// Setup service with file-based SQLite for concurrency safety.
	tmpDir := t.TempDir()
	db, err := sqlite.Open(tmpDir + "/loadtest.db")
	require.NoError(t, err)

	repo, err := sqlite.NewSOCRepo(db)
	require.NoError(t, err)

	logger, err := audit.NewDecisionLogger(tmpDir)
	require.NoError(t, err)

	t.Cleanup(func() {
		logger.Close()
		db.Close()
	})

	svc := NewService(repo, logger)
	svc.DisableRateLimit() // bypass rate limiter for raw throughput

	// Load test parameters.
	const (
		numWorkers   = 16
		eventsPerWkr = 200
		totalEvents  = numWorkers * eventsPerWkr
	)

	categories := []string{"jailbreak", "injection", "exfiltration", "auth_bypass", "tool_abuse"}
	sources := []domsoc.EventSource{domsoc.SourceSentinelCore, domsoc.SourceShield, domsoc.SourceGoMCP}

	var (
		wg           sync.WaitGroup
		latencies    = make([]time.Duration, totalEvents)
		realErrors   int64
		backpressure int64
		incidents    int64
	)

	start := time.Now()

	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for i := 0; i < eventsPerWkr; i++ {
				idx := workerID*eventsPerWkr + i
				evt := domsoc.NewSOCEvent(
					sources[idx%len(sources)],
					domsoc.SeverityHigh,
					categories[idx%len(categories)],
					fmt.Sprintf("load-test w%d-e%d", workerID, i),
				)
				evt.SensorID = fmt.Sprintf("load-sensor-%d", workerID)

				t0 := time.Now()
				_, inc, err := svc.IngestEvent(evt)
				latencies[idx] = time.Since(t0)

				if err != nil {
					if errors.Is(err, domsoc.ErrCapacityFull) {
						atomic.AddInt64(&backpressure, 1)
					} else {
						atomic.AddInt64(&realErrors, 1)
					}
				}
				if inc != nil {
					atomic.AddInt64(&incidents, 1)
				}
			}
		}(w)
	}

	wg.Wait()
	totalDuration := time.Since(start)

	// Compute latency percentiles.
	sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })

	p50 := percentile(latencies, 50)
	p95 := percentile(latencies, 95)
	p99 := percentile(latencies, 99)
	mean := meanDuration(latencies)
	eventsPerSec := float64(totalEvents) / totalDuration.Seconds()

	// Report results.
	t.Logf("═══════════════════════════════════════════════")
	t.Logf("  SENTINEL SOC Load Test Results")
	t.Logf("═══════════════════════════════════════════════")
	t.Logf("  Workers:      %d", numWorkers)
	t.Logf("  Events/worker: %d", eventsPerWkr)
	t.Logf("  Total events: %d", totalEvents)
	t.Logf("  Duration:     %s", totalDuration.Round(time.Millisecond))
	t.Logf("  Throughput:   %.0f events/sec", eventsPerSec)
	t.Logf("───────────────────────────────────────────────")
	t.Logf("  Mean:         %s", mean.Round(time.Microsecond))
	t.Logf("  P50:          %s", p50.Round(time.Microsecond))
	t.Logf("  P95:          %s", p95.Round(time.Microsecond))
	t.Logf("  P99:          %s", p99.Round(time.Microsecond))
	t.Logf("  Min:          %s", latencies[0].Round(time.Microsecond))
	t.Logf("  Max:          %s", latencies[len(latencies)-1].Round(time.Microsecond))
	t.Logf("───────────────────────────────────────────────")
	t.Logf("  Real Errors:  %d (%.1f%%)", realErrors, float64(realErrors)/float64(totalEvents)*100)
	t.Logf("  Backpressure: %d (%.1f%%) [§20.1 semaphore]", backpressure, float64(backpressure)/float64(totalEvents)*100)
	t.Logf("  Incidents:    %d", incidents)
	t.Logf("═══════════════════════════════════════════════")

	// Assertions: backpressure rejections are expected; only real errors are failures.
	require.Less(t, float64(realErrors)/float64(totalEvents), 0.05, "real error rate should be < 5%")
	require.Greater(t, eventsPerSec, float64(100), "should sustain > 100 events/sec")
}

func percentile(sorted []time.Duration, p int) time.Duration {
	if len(sorted) == 0 {
		return 0
	}
	idx := int(math.Ceil(float64(p)/100.0*float64(len(sorted)))) - 1
	if idx < 0 {
		idx = 0
	}
	if idx >= len(sorted) {
		idx = len(sorted) - 1
	}
	return sorted[idx]
}

func meanDuration(ds []time.Duration) time.Duration {
	if len(ds) == 0 {
		return 0
	}
	var total time.Duration
	for _, d := range ds {
		total += d
	}
	return total / time.Duration(len(ds))
}
