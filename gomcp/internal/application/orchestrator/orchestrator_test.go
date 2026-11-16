package orchestrator

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

func newTestOrchestrator(t *testing.T, cfg Config) (*Orchestrator, *inMemoryStore) {
	t.Helper()
	store := newInMemoryStore()
	peerReg := peer.NewRegistry("test-node", 30*time.Minute)

	// Bootstrap genes into store.
	ctx := context.Background()
	for _, gd := range memory.HardcodedGenes {
		gene := memory.NewGene(gd.Content, gd.Domain)
		gene.ID = gd.ID
		_ = store.Add(ctx, gene)
	}

	return New(cfg, peerReg, store), store
}

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	assert.Equal(t, 5*time.Minute, cfg.HeartbeatInterval)
	assert.Equal(t, 30, cfg.JitterPercent)
	assert.Equal(t, 0.95, cfg.EntropyThreshold)
	assert.True(t, cfg.SyncOnChange)
	assert.Equal(t, 100, cfg.MaxSyncBatchSize)
}

func TestNew_WithDefaults(t *testing.T) {
	o, _ := newTestOrchestrator(t, DefaultConfig())
	assert.False(t, o.IsRunning())
	assert.Equal(t, 0, o.cycle)
}

func TestHeartbeat_SingleCycle(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HeartbeatInterval = 100 * time.Millisecond
	cfg.EntropyThreshold = 1.1 // Above max normalized — won't trigger apoptosis.
	o, _ := newTestOrchestrator(t, cfg)

	result := o.heartbeat(context.Background())
	assert.Equal(t, 1, result.Cycle)
	assert.True(t, result.GenomeIntact, "Genome must be intact with all hardcoded genes")
	assert.GreaterOrEqual(t, result.Duration, time.Duration(0))
	assert.Greater(t, result.NextInterval, time.Duration(0))
}

func TestHeartbeat_GenomeIntact(t *testing.T) {
	cfg := DefaultConfig()
	cfg.EntropyThreshold = 1.1 // Above max normalized — won't trigger apoptosis.
	o, _ := newTestOrchestrator(t, cfg)
	result := o.heartbeat(context.Background())
	assert.True(t, result.GenomeIntact)
	assert.False(t, result.ApoptosisTriggered)
	assert.Empty(t, result.Errors)
}

func TestAutoDiscover_ConfiguredPeersAreNotAcknowledgements(t *testing.T) {
	cfg := DefaultConfig()
	cfg.KnownPeers = []string{"node-alpha:" + memory.CompiledGenomeHash(), "node-short:abc"}
	o, _ := newTestOrchestrator(t, cfg)
	assert.NotPanics(t, func() { assert.Equal(t, 0, o.autoDiscover(context.Background())) })
	assert.Equal(t, 0, o.peerReg.TrustedCount(), "configuration alone cannot verify or touch a peer")
	result := HeartbeatResult{}
	assert.Equal(t, 0, o.syncManager(context.Background(), &result))
	assert.Equal(t, "unavailable", result.PeerSyncStatus)
	assert.Contains(t, result.Errors, "peer synchronization unavailable: no delivery transport configured")
}

func TestSyncManager_NoTrustedPeers(t *testing.T) {
	o, _ := newTestOrchestrator(t, DefaultConfig())
	result := HeartbeatResult{}
	assert.Equal(t, 0, o.syncManager(context.Background(), &result))
	assert.Equal(t, "no_trusted_peers", result.PeerSyncStatus)
	assert.Empty(t, result.Errors)
}

func TestSyncManager_NoDeliveryNoFalsePeerLiveness(t *testing.T) {
	o, store := newTestOrchestrator(t, DefaultConfig())
	_, err := o.peerReg.ProcessHandshake(peer.HandshakeRequest{FromPeerID: "peer-local-test", FromNode: "peer", GenomeHash: memory.CompiledGenomeHash()}, memory.CompiledGenomeHash())
	assert.NoError(t, err)
	before, err := o.peerReg.GetPeer("peer-local-test")
	assert.NoError(t, err)
	fact := memory.NewFact("fixture-original", memory.LevelProject, "fixture", "test")
	assert.NoError(t, store.Add(context.Background(), fact))
	result := HeartbeatResult{}
	assert.Equal(t, 0, o.syncManager(context.Background(), &result))
	assert.Equal(t, "unavailable", result.PeerSyncStatus)
	assert.NotEmpty(t, result.Errors)
	after, err := o.peerReg.GetPeer("peer-local-test")
	assert.NoError(t, err)
	assert.Equal(t, before.LastSeen, after.LastSeen)
	assert.Equal(t, before.LastSyncAt, after.LastSyncAt)
	assert.Equal(t, before.FactCount, after.FactCount)
	assert.True(t, o.lastSync.IsZero())
	assert.Zero(t, o.lastFactCount)
	// An in-place mutation preserves count. It must never turn an unacknowledged
	// attempt into an apparent completed or skipped sync.
	fact.Content = "fixture-changed"
	assert.NoError(t, store.Update(context.Background(), fact))
	again := HeartbeatResult{}
	assert.Equal(t, 0, o.syncManager(context.Background(), &again))
	assert.Equal(t, "unavailable", again.PeerSyncStatus)
	assert.NotEmpty(t, again.Errors)
	assert.True(t, o.lastSync.IsZero())
	assert.Zero(t, o.lastFactCount)
}

func TestSyncManager_Cancelled(t *testing.T) {
	o, _ := newTestOrchestrator(t, DefaultConfig())
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result := HeartbeatResult{}
	assert.Equal(t, 0, o.syncManager(ctx, &result))
	assert.Equal(t, "cancelled", result.PeerSyncStatus)
	assert.True(t, o.lastSync.IsZero())
}

func TestJitteredInterval(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HeartbeatInterval = 1 * time.Second
	cfg.JitterPercent = 50
	o, _ := newTestOrchestrator(t, cfg)

	intervals := make(map[time.Duration]bool)
	for i := 0; i < 20; i++ {
		interval := o.jitteredInterval()
		intervals[interval] = true
		// Must be between 500ms and 1500ms.
		assert.GreaterOrEqual(t, interval, 500*time.Millisecond)
		assert.LessOrEqual(t, interval, 1500*time.Millisecond)
	}
	// With 20 samples and 50% jitter, we should get some variety.
	assert.Greater(t, len(intervals), 1, "Jitter should produce varied intervals")
}

func TestStartAndStop(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HeartbeatInterval = 50 * time.Millisecond
	cfg.JitterPercent = 10
	o, _ := newTestOrchestrator(t, cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	assert.False(t, o.IsRunning())
	go o.Start(ctx)

	time.Sleep(50 * time.Millisecond)
	assert.True(t, o.IsRunning())

	<-ctx.Done()
	time.Sleep(100 * time.Millisecond)
	assert.False(t, o.IsRunning())
	assert.GreaterOrEqual(t, o.cycle, 1, "At least one cycle should have completed")
}

func TestStats(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HeartbeatInterval = 50 * time.Millisecond
	cfg.JitterPercent = 10
	o, _ := newTestOrchestrator(t, cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()
	go o.Start(ctx)
	time.Sleep(100 * time.Millisecond)

	stats := o.Stats()
	assert.True(t, stats["running"].(bool) || stats["total_cycles"].(int) >= 1)
	assert.GreaterOrEqual(t, stats["total_cycles"].(int), 1)
}

func TestHistory(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HeartbeatInterval = 30 * time.Millisecond
	cfg.JitterPercent = 10
	o, _ := newTestOrchestrator(t, cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	go o.Start(ctx)
	<-ctx.Done()
	time.Sleep(50 * time.Millisecond)

	history := o.History()
	assert.GreaterOrEqual(t, len(history), 2, "Should have at least 2 cycles")
	assert.Equal(t, 1, history[0].Cycle)
}

func TestParsePeerSpec(t *testing.T) {
	tests := []struct {
		spec     string
		wantNode string
		wantHash string
	}{
		{"alpha:abc123", "alpha", "abc123"},
		{"abc123", "unknown", "abc123"},
		{"node-1:hash:with:colons", "node-1", "hash:with:colons"},
	}
	for _, tt := range tests {
		node, hash := parsePeerSpec(tt.spec)
		assert.Equal(t, tt.wantNode, node, "spec=%s", tt.spec)
		assert.Equal(t, tt.wantHash, hash, "spec=%s", tt.spec)
	}
}

// --- In-memory FactStore for testing ---

type inMemoryStore struct {
	facts map[string]*memory.Fact
}

func newInMemoryStore() *inMemoryStore {
	return &inMemoryStore{facts: make(map[string]*memory.Fact)}
}

func (s *inMemoryStore) Add(_ context.Context, fact *memory.Fact) error {
	if _, exists := s.facts[fact.ID]; exists {
		return fmt.Errorf("duplicate: %s", fact.ID)
	}
	f := *fact
	s.facts[fact.ID] = &f
	return nil
}

func (s *inMemoryStore) Get(_ context.Context, id string) (*memory.Fact, error) {
	f, ok := s.facts[id]
	if !ok {
		return nil, fmt.Errorf("not found: %s", id)
	}
	return f, nil
}

func (s *inMemoryStore) Update(_ context.Context, fact *memory.Fact) error {
	s.facts[fact.ID] = fact
	return nil
}

func (s *inMemoryStore) Delete(_ context.Context, id string) error {
	delete(s.facts, id)
	return nil
}

func (s *inMemoryStore) ListByDomain(_ context.Context, domain string, _ bool) ([]*memory.Fact, error) {
	var result []*memory.Fact
	for _, f := range s.facts {
		if f.Domain == domain {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryStore) ListByLevel(_ context.Context, level memory.HierLevel) ([]*memory.Fact, error) {
	var result []*memory.Fact
	for _, f := range s.facts {
		if f.Level == level {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryStore) ListDomains(_ context.Context) ([]string, error) {
	domains := make(map[string]bool)
	for _, f := range s.facts {
		domains[f.Domain] = true
	}
	result := make([]string, 0, len(domains))
	for d := range domains {
		result = append(result, d)
	}
	return result, nil
}

func (s *inMemoryStore) GetStale(_ context.Context, _ bool) ([]*memory.Fact, error) {
	return nil, nil
}

func (s *inMemoryStore) Search(_ context.Context, _ string, _ int) ([]*memory.Fact, error) {
	return nil, nil
}

func (s *inMemoryStore) SearchByVector(_ context.Context, _ []float64, _ int) ([]*memory.Fact, error) {
	return nil, nil
}

func (s *inMemoryStore) ListGenes(_ context.Context) ([]*memory.Fact, error) {
	var result []*memory.Fact
	for _, f := range s.facts {
		if f.IsGene {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryStore) GetExpired(_ context.Context) ([]*memory.Fact, error) {
	return nil, nil
}

func (s *inMemoryStore) RefreshTTL(_ context.Context, _ string) error {
	return nil
}

func (s *inMemoryStore) TouchFact(_ context.Context, _ string) error { return nil }
func (s *inMemoryStore) GetColdFacts(_ context.Context, _ int) ([]*memory.Fact, error) {
	return nil, nil
}
func (s *inMemoryStore) CompressFacts(_ context.Context, _ []string, _ string) (string, error) {
	return "", nil
}

func (s *inMemoryStore) Stats(_ context.Context) (*memory.FactStoreStats, error) {
	return &memory.FactStoreStats{TotalFacts: len(s.facts)}, nil
}
