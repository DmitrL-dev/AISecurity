package soc

import (
	"fmt"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// newBenchService creates a minimal SOC service for benchmarking.
// Disables rate limiting to measure raw pipeline throughput.
func newBenchService(b *testing.B) *Service {
	b.Helper()

	tmpDir := b.TempDir()
	dbPath := tmpDir + "/bench.db"

	db, err := sqlite.Open(dbPath)
	require.NoError(b, err)
	b.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewSOCRepo(db)
	require.NoError(b, err)

	logger, err := audit.NewDecisionLogger(tmpDir)
	require.NoError(b, err)
	b.Cleanup(func() { logger.Close() })

	svc := NewService(repo, logger)
	svc.DisableRateLimit() // benchmarks measure throughput, not rate limiting
	return svc
}

// BenchmarkIngestEvent measures single-event pipeline throughput.
func BenchmarkIngestEvent(b *testing.B) {
	svc := newBenchService(b)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityMedium, "injection",
			fmt.Sprintf("Bench event #%d", i))
		event.ID = fmt.Sprintf("bench-evt-%d", i)
		_, _, err := svc.IngestEvent(event)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkIngestEvent_WithCorrelation measures pipeline with correlation active.
// Pre-loads events to trigger correlation matching.
func BenchmarkIngestEvent_WithCorrelation(b *testing.B) {
	svc := newBenchService(b)

	// Pre-load events to make correlation rules meaningful.
	for i := 0; i < 50; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "jailbreak",
			fmt.Sprintf("Pre-load jailbreak #%d", i))
		event.ID = fmt.Sprintf("preload-%d", i)
		svc.IngestEvent(event)
		time.Sleep(time.Microsecond)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityHigh, "jailbreak",
			fmt.Sprintf("Corr bench event #%d", i))
		event.ID = fmt.Sprintf("bench-corr-%d", i)
		_, _, err := svc.IngestEvent(event)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkIngestEvent_Parallel measures concurrent ingest throughput.
func BenchmarkIngestEvent_Parallel(b *testing.B) {
	svc := newBenchService(b)
	var counter atomic.Int64

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			n := counter.Add(1)
			event := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityLow, "jailbreak",
				fmt.Sprintf("Parallel bench #%d", n))
			event.ID = fmt.Sprintf("bench-par-%d", n)
			_, _, err := svc.IngestEvent(event)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}
