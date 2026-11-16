// Package orchestrator implements the DIP Heartbeat Orchestrator.
//
// The orchestrator runs a background loop with 4 modules:
//  1. Auto-Discovery — monitors configured peer endpoints for new Merkle-compatible nodes
//  2. Sync Manager — reports unavailable until peer delivery has an acknowledgement
//  3. Stability Watchdog — monitors entropy and triggers apoptosis recovery
//  4. Jittered Heartbeat — randomizes intervals to avoid detection patterns
//
// The orchestrator works with domain-level components directly (not through MCP tools).
// It is started as a goroutine from main.go and runs until context cancellation.
package orchestrator

import (
	"context"
	"fmt"
	"log"
	"math/rand"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/domain/alert"
	"github.com/syntrex/gomcp/internal/domain/entropy"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/synapse"
)

// Config holds orchestrator configuration.
type Config struct {
	// HeartbeatInterval is the base interval between heartbeat cycles.
	HeartbeatInterval time.Duration `json:"heartbeat_interval"`

	// JitterPercent is the percentage of HeartbeatInterval to add/subtract randomly.
	// e.g., 30 means ±30% jitter around the base interval.
	JitterPercent int `json:"jitter_percent"`

	// EntropyThreshold triggers apoptosis recovery when exceeded (0.0-1.0).
	EntropyThreshold float64 `json:"entropy_threshold"`

	// KnownPeers are pre-configured peer genome hashes for auto-discovery.
	// Format: "node_name:genome_hash"
	KnownPeers []string `json:"known_peers"`

	// SyncOnChange is retained for compatibility; no peer delivery channel is wired.
	SyncOnChange bool `json:"sync_on_change"`

	// MaxSyncBatchSize is reserved for a future acknowledged delivery channel.
	MaxSyncBatchSize int `json:"max_sync_batch_size"`
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() Config {
	return Config{
		HeartbeatInterval: 5 * time.Minute,
		JitterPercent:     30,
		EntropyThreshold:  0.95,
		SyncOnChange:      true,
		MaxSyncBatchSize:  100,
	}
}

// HeartbeatResult records what happened in one heartbeat cycle.
type HeartbeatResult struct {
	Cycle              int           `json:"cycle"`
	StartedAt          time.Time     `json:"started_at"`
	Duration           time.Duration `json:"duration"`
	PeersDiscovered    int           `json:"peers_discovered"`
	FactsSynced        int           `json:"facts_synced"`
	PeerSyncStatus     string        `json:"peer_sync_status"`
	EntropyLevel       float64       `json:"entropy_level"`
	ApoptosisTriggered bool          `json:"apoptosis_triggered"`
	GenomeIntact       bool          `json:"genome_intact"`
	GenesHealed        int           `json:"genes_healed"`
	FactsExpired       int           `json:"facts_expired"`
	FactsArchived      int           `json:"facts_archived"`
	SynapsesCreated    int           `json:"synapses_created"` // v3.4: Module 9
	NextInterval       time.Duration `json:"next_interval"`
	Errors             []string      `json:"errors,omitempty"`
}

// Orchestrator runs the DIP heartbeat pipeline.
type Orchestrator struct {
	mu                   sync.RWMutex
	config               Config
	peerReg              *peer.Registry
	cache                memory.HotCache
	store                memory.FactStore
	scope                rlmscope.Scope
	synapseStore         synapse.SynapseStore // v3.4: Module 9
	alertBus             *alert.Bus
	running              bool
	cycle                int
	history              []HeartbeatResult
	lastSync             time.Time
	lastFactCount        int
	lastApoptosisWritten time.Time // debounce: prevents WATCHDOG_RECOVERY flood
}

// New creates a new orchestrator.
func New(cfg Config, peerReg *peer.Registry, store memory.FactStore) *Orchestrator {
	if cfg.HeartbeatInterval <= 0 {
		cfg.HeartbeatInterval = 5 * time.Minute
	}
	if cfg.JitterPercent <= 0 || cfg.JitterPercent > 100 {
		cfg.JitterPercent = 30
	}
	if cfg.EntropyThreshold <= 0 {
		cfg.EntropyThreshold = 0.8
	}
	if cfg.MaxSyncBatchSize <= 0 {
		cfg.MaxSyncBatchSize = 100
	}

	return &Orchestrator{
		config:  cfg,
		peerReg: peerReg,
		store:   store,
		scope:   rlmscope.Default(),
		history: make([]HeartbeatResult, 0, 64),
	}
}

// WithScope binds background memory writes to a tenant/project boundary.
func (o *Orchestrator) WithScope(sc rlmscope.Scope) *Orchestrator {
	o.scope = sc.Normalize()
	return o
}

// WithCache connects lifecycle mutations to the shared L0 cache. Set before Start.
func (o *Orchestrator) WithCache(cache memory.HotCache) *Orchestrator {
	o.cache = cache
	return o
}

// NewWithAlerts creates an orchestrator with an alert bus for DIP-Watcher.
func NewWithAlerts(cfg Config, peerReg *peer.Registry, store memory.FactStore, bus *alert.Bus) *Orchestrator {
	o := New(cfg, peerReg, store)
	o.alertBus = bus
	return o
}

// OrchestratorStatus is the v3.4 observability snapshot.
type OrchestratorStatus struct {
	Running         bool             `json:"running"`
	Cycle           int              `json:"cycle"`
	Config          Config           `json:"config"`
	LastResult      *HeartbeatResult `json:"last_result,omitempty"`
	HistorySize     int              `json:"history_size"`
	HasSynapseStore bool             `json:"has_synapse_store"`
}

// Status returns current orchestrator state (v3.4: observability).
func (o *Orchestrator) Status() OrchestratorStatus {
	o.mu.RLock()
	defer o.mu.RUnlock()
	status := OrchestratorStatus{
		Running:         o.running,
		Cycle:           o.cycle,
		Config:          o.config,
		HistorySize:     len(o.history),
		HasSynapseStore: o.synapseStore != nil,
	}
	if len(o.history) > 0 {
		last := o.history[len(o.history)-1]
		status.LastResult = &last
	}
	return status
}

// AlertBus returns the alert bus (may be nil).
func (o *Orchestrator) AlertBus() *alert.Bus {
	return o.alertBus
}

// Start begins the heartbeat loop. Blocks until context is cancelled.
func (o *Orchestrator) Start(ctx context.Context) {
	ctx = rlmscope.WithScope(ctx, o.scope)
	o.mu.Lock()
	o.running = true
	o.mu.Unlock()

	defer func() {
		o.mu.Lock()
		o.running = false
		o.mu.Unlock()
	}()

	log.Printf("orchestrator: started (interval=%s, jitter=±%d%%, entropy_threshold=%.2f)",
		o.config.HeartbeatInterval, o.config.JitterPercent, o.config.EntropyThreshold)

	for {
		result := o.heartbeat(ctx)
		o.mu.Lock()
		o.history = append(o.history, result)
		// Keep last 64 results.
		if len(o.history) > 64 {
			o.history = o.history[len(o.history)-64:]
		}
		o.mu.Unlock()

		if result.ApoptosisTriggered {
			log.Printf("orchestrator: apoptosis triggered at cycle %d, entropy=%.4f",
				result.Cycle, result.EntropyLevel)
		}

		// Jittered sleep.
		select {
		case <-ctx.Done():
			log.Printf("orchestrator: stopped after %d cycles", o.cycle)
			return
		case <-time.After(result.NextInterval):
		}
	}
}

// heartbeat executes one cycle of the pipeline.
func (o *Orchestrator) heartbeat(ctx context.Context) HeartbeatResult {
	o.mu.Lock()
	o.cycle++
	cycle := o.cycle
	o.mu.Unlock()

	start := time.Now()
	result := HeartbeatResult{
		Cycle:          cycle,
		StartedAt:      start,
		PeerSyncStatus: "not_run",
	}

	// --- Module 1: Auto-Discovery ---
	discovered := o.autoDiscover(ctx)
	result.PeersDiscovered = discovered

	// --- Module 2: Stability Watchdog (genome + entropy check) ---
	genomeOK, entropyLevel := o.stabilityCheck(ctx, &result)
	result.GenomeIntact = genomeOK
	result.EntropyLevel = entropyLevel

	// --- Module 3: Sync Manager ---
	if genomeOK && !result.ApoptosisTriggered {
		synced := o.syncManager(ctx, &result)
		result.FactsSynced = synced
	}

	// --- Module 4: Self-Healing (auto-restore missing genes) ---
	healed := o.selfHeal(ctx, &result)
	result.GenesHealed = healed

	// --- Module 5: Memory Hygiene (expire stale, archive old) ---
	expired, archived := o.memoryHygiene(ctx, &result)
	result.FactsExpired = expired
	result.FactsArchived = archived

	// --- Module 6: State Persistence (auto-snapshot) ---
	o.statePersistence(ctx, &result)

	// --- Module 7: Jittered interval ---
	result.NextInterval = o.jitteredInterval()
	result.Duration = time.Since(start)

	// --- Module 8: DIP-Watcher (proactive alert generation) ---
	o.dipWatcher(&result)

	// --- Module 9: Synapse Scanner (v3.4) ---
	if o.synapseStore != nil && cycle%12 == 0 {
		created := o.synapseScanner(ctx, &result)
		result.SynapsesCreated = created
	}

	log.Printf("orchestrator: cycle=%d peers=%d synced=%d healed=%d expired=%d archived=%d synapses=%d entropy=%.4f genome=%v next=%s",
		cycle, discovered, result.FactsSynced, healed, expired, archived, result.SynapsesCreated, entropyLevel, genomeOK, result.NextInterval)

	return result
}

// dipWatcher is Module 8: proactive monitoring that generates alerts
// based on heartbeat metrics. Feeds the TUI alert panel.
func (o *Orchestrator) dipWatcher(result *HeartbeatResult) {
	if o.alertBus == nil {
		return
	}
	cycle := result.Cycle

	// --- Entropy monitoring ---
	if result.EntropyLevel > 0.9 {
		o.alertBus.Emit(alert.New(alert.SourceEntropy, alert.SeverityCritical,
			fmt.Sprintf("CRITICAL entropy: %.4f (threshold: 0.90)", result.EntropyLevel), cycle).
			WithValue(result.EntropyLevel))
	} else if result.EntropyLevel > 0.7 {
		o.alertBus.Emit(alert.New(alert.SourceEntropy, alert.SeverityWarning,
			fmt.Sprintf("Elevated entropy: %.4f", result.EntropyLevel), cycle).
			WithValue(result.EntropyLevel))
	}

	// --- Genome integrity ---
	if !result.GenomeIntact {
		o.alertBus.Emit(alert.New(alert.SourceGenome, alert.SeverityCritical,
			"Genome integrity FAILED — Merkle root mismatch", cycle))
	}

	if result.ApoptosisTriggered {
		o.alertBus.Emit(alert.New(alert.SourceSystem, alert.SeverityCritical,
			"APOPTOSIS triggered — emergency genome preservation", cycle))
	}

	// --- Self-healing events ---
	if result.GenesHealed > 0 {
		o.alertBus.Emit(alert.New(alert.SourceGenome, alert.SeverityWarning,
			fmt.Sprintf("Self-healed %d missing genes", result.GenesHealed), cycle))
	}

	// --- Memory hygiene ---
	if result.FactsExpired > 5 {
		o.alertBus.Emit(alert.New(alert.SourceMemory, alert.SeverityWarning,
			fmt.Sprintf("Memory cleanup: %d expired, %d archived",
				result.FactsExpired, result.FactsArchived), cycle))
	}

	// --- Heartbeat health ---
	if result.Duration > 2*o.config.HeartbeatInterval {
		o.alertBus.Emit(alert.New(alert.SourceSystem, alert.SeverityWarning,
			fmt.Sprintf("Slow heartbeat: %s (expected <%s)",
				result.Duration, o.config.HeartbeatInterval), cycle))
	}

	// --- Peer discovery ---
	if result.PeersDiscovered > 0 {
		o.alertBus.Emit(alert.New(alert.SourcePeer, alert.SeverityInfo,
			fmt.Sprintf("Discovered %d new peer(s)", result.PeersDiscovered), cycle))
	}

	// --- Sync events ---
	if result.FactsSynced > 0 {
		o.alertBus.Emit(alert.New(alert.SourcePeer, alert.SeverityInfo,
			fmt.Sprintf("Synced %d facts to peers", result.FactsSynced), cycle))
	}

	// --- Status heartbeat (every cycle) ---
	if len(result.Errors) == 0 && result.GenomeIntact {
		o.alertBus.Emit(alert.New(alert.SourceWatcher, alert.SeverityInfo,
			fmt.Sprintf("Heartbeat OK (cycle=%d, entropy=%.4f)", cycle, result.EntropyLevel), cycle))
	}
}

// autoDiscover does not treat configured strings as a remote handshake. The
// timeout sweep remains active for peers registered by actual inbound paths.
func (o *Orchestrator) autoDiscover(ctx context.Context) int {
	genes, _ := o.store.ListGenes(ctx)
	syncFacts := genesToSyncFacts(genes)
	backups := o.peerReg.CheckTimeouts(syncFacts)
	if len(backups) > 0 {
		log.Printf("orchestrator: %d peers timed out, gene backups created", len(backups))
	}
	return 0
}

// stabilityCheck verifies genome integrity and measures entropy.
func (o *Orchestrator) stabilityCheck(ctx context.Context, result *HeartbeatResult) (bool, float64) {
	// Check genome integrity via gene count.
	genes, err := o.store.ListGenes(ctx)
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("list genes: %v", err))
		return false, 0
	}

	genomeOK := len(genes) >= len(memory.HardcodedGenes)

	// Compute entropy on USER-CREATED facts only.
	// System facts (genes, watchdog, heartbeat, session-history) are excluded —
	// their entropy is irrelevant for anomaly detection.
	l0Facts, _ := o.store.ListByLevel(ctx, memory.LevelProject)
	l1Facts, _ := o.store.ListByLevel(ctx, memory.LevelDomain)

	var dynamicContent string
	for _, f := range append(l0Facts, l1Facts...) {
		if f.IsGene {
			continue
		}
		// Only include user-created content — source "manual" (add_fact) or "mcp".
		if f.Source != "manual" && f.Source != "mcp" {
			continue
		}
		dynamicContent += f.Content + " "
	}

	// No dynamic facts = healthy (entropy 0).
	if dynamicContent == "" {
		return genomeOK, 0
	}

	entropyLevel := entropy.ShannonEntropy(dynamicContent)

	// Normalize entropy to 0-1 range (typical text: 3-5 bits/char).
	normalizedEntropy := entropyLevel / 5.0
	if normalizedEntropy > 1.0 {
		normalizedEntropy = 1.0
	}

	if normalizedEntropy >= o.config.EntropyThreshold {
		result.ApoptosisTriggered = true

		// Debounce: write a recovery marker at most once per 24h.
		// Without this guard, every heartbeat cycle (~5 min) that has high
		// entropy writes a new record, flooding the DB with thousands of
		// identical WATCHDOG_RECOVERY entries and causing context deadline
		// exceeded on the next server startup.
		o.mu.RLock()
		lastWritten := o.lastApoptosisWritten
		o.mu.RUnlock()

		if time.Since(lastWritten) >= 24*time.Hour {
			currentHash := memory.CompiledGenomeHash()
			recoveryMarker := memory.NewFact(
				fmt.Sprintf("[WATCHDOG_RECOVERY] genome_hash=%s entropy=%.4f cycle=%d",
					currentHash, normalizedEntropy, result.Cycle),
				memory.LevelProject,
				"recovery",
				"watchdog",
			)
			recoveryMarker.Source = "watchdog"
			// Derived: our own runtime state, computed by us, carrying no third-party text.
			recoveryMarker.Origin = memory.OriginDerived
			if err := o.store.Add(ctx, recoveryMarker); err == nil {
				o.mu.Lock()
				o.lastApoptosisWritten = time.Now()
				o.mu.Unlock()
			}
		}
	}

	return genomeOK, normalizedEntropy
}

// syncManager has no transport or remote acknowledgement. Never advance a
// synced count, last-sync watermark or peer liveness on local preparation.
func (o *Orchestrator) syncManager(ctx context.Context, result *HeartbeatResult) int {
	if err := ctx.Err(); err != nil {
		result.PeerSyncStatus = "cancelled"
		result.Errors = append(result.Errors, "peer sync cancelled")
		return 0
	}
	if len(o.config.KnownPeers) > 0 {
		result.PeerSyncStatus = "unavailable"
		result.Errors = append(result.Errors, "peer synchronization unavailable: no delivery transport configured")
		return 0
	}
	for _, p := range o.peerReg.ListPeers() {
		if p.Trust == peer.TrustVerified {
			result.PeerSyncStatus = "unavailable"
			result.Errors = append(result.Errors, "peer synchronization unavailable: no delivery transport configured")
			return 0
		}
	}
	result.PeerSyncStatus = "no_trusted_peers"
	return 0
}

// jitteredInterval returns the next heartbeat interval with random jitter.
func (o *Orchestrator) jitteredInterval() time.Duration {
	base := o.config.HeartbeatInterval
	jitterRange := time.Duration(float64(base) * float64(o.config.JitterPercent) / 100.0)
	jitter := time.Duration(rand.Int63n(int64(jitterRange)*2)) - jitterRange
	interval := base + jitter
	if interval < 10*time.Millisecond {
		interval = 10 * time.Millisecond
	}
	return interval
}

// IsRunning returns whether the orchestrator is active.
func (o *Orchestrator) IsRunning() bool {
	o.mu.RLock()
	defer o.mu.RUnlock()
	return o.running
}

// Stats returns current orchestrator status.
func (o *Orchestrator) Stats() map[string]interface{} {
	o.mu.RLock()
	defer o.mu.RUnlock()

	stats := map[string]interface{}{
		"running":         o.running,
		"total_cycles":    o.cycle,
		"config":          o.config,
		"last_sync":       o.lastSync,
		"last_fact_count": o.lastFactCount,
		"history_size":    len(o.history),
	}

	if len(o.history) > 0 {
		last := o.history[len(o.history)-1]
		stats["last_heartbeat"] = last
	}

	return stats
}

// History returns recent heartbeat results.
func (o *Orchestrator) History() []HeartbeatResult {
	o.mu.RLock()
	defer o.mu.RUnlock()

	result := make([]HeartbeatResult, len(o.history))
	copy(result, o.history)
	return result
}

// selfHeal checks for missing hardcoded genes and re-bootstraps them.
// Returns the number of genes restored.
func (o *Orchestrator) selfHeal(ctx context.Context, result *HeartbeatResult) int {
	genes, err := o.store.ListGenes(ctx)
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("self-heal list genes: %v", err))
		return 0
	}

	// Check if all hardcoded genes are present.
	if len(genes) >= len(memory.HardcodedGenes) {
		return 0 // All present, nothing to heal.
	}

	// Some genes missing — re-bootstrap.
	healed, err := memory.BootstrapGenome(ctx, o.store, "")
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("self-heal bootstrap: %v", err))
		return 0
	}

	if healed > 0 {
		log.Printf("orchestrator: self-healed %d missing genes", healed)
	}
	return healed
}

// memoryHygiene processes expired TTL facts and archives stale ones.
// Returns (expired_count, archived_count).
func (o *Orchestrator) memoryHygiene(ctx context.Context, result *HeartbeatResult) (int, int) {
	expired := 0
	archived := 0

	// Step 1: Mark expired TTL facts as stale.
	expiredFacts, err := o.store.GetExpired(ctx)
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("hygiene get-expired: %v", err))
		return 0, 0
	}
	for _, f := range expiredFacts {
		if f.IsGene {
			continue // Never expire genes.
		}
		candidate := *f
		candidate.IsStale = true
		if err := o.store.Update(ctx, &candidate); err != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("hygiene expire %s: %v", f.ID, err))
			continue
		}
		expired++
		o.invalidateHygieneCache(ctx, result, f.ID)
	}

	// Step 2: Purge aged watchdog recovery markers (domain=recovery, source=watchdog).
	// These are purely diagnostic breadcrumbs — they accumulate forever and bloat
	// the DB. Delete any that are older than 24h; only the latest is ever useful.
	watchdogCutoff := time.Now().Add(-24 * time.Hour)
	wdFacts, wdErr := o.store.ListByLevel(ctx, memory.LevelProject)
	if wdErr != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("hygiene list-watchdog: %v", wdErr))
	} else {
		for _, f := range wdFacts {
			if f.Domain == "recovery" && f.Source == "watchdog" && f.CreatedAt.Before(watchdogCutoff) {
				if delErr := o.store.Delete(ctx, f.ID); delErr != nil {
					result.Errors = append(result.Errors, fmt.Sprintf("hygiene delete-watchdog %s: %v", f.ID, delErr))
					continue
				}
				archived++ // Successful diagnostic purge shares the archived counter.
				o.invalidateHygieneCache(ctx, result, f.ID)
			}
		}
	}

	// Step 3: Archive facts that have been stale for a while.
	staleFacts, err := o.store.GetStale(ctx, false) // exclude already-archived
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("hygiene get-stale: %v", err))
		return expired, archived
	}
	staleThreshold := time.Now().Add(-24 * time.Hour) // Archive if stale > 24h.
	for _, f := range staleFacts {
		if f.IsGene {
			continue // Never archive genes.
		}
		if f.UpdatedAt.Before(staleThreshold) {
			candidate := *f
			candidate.IsArchived = true
			if err := o.store.Update(ctx, &candidate); err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("hygiene archive %s: %v", f.ID, err))
				continue
			}
			archived++
			o.invalidateHygieneCache(ctx, result, f.ID)
		}
	}

	if expired > 0 || archived > 0 {
		log.Printf("orchestrator: hygiene — expired %d facts, archived %d stale facts", expired, archived)
	}
	return expired, archived
}

func (o *Orchestrator) invalidateHygieneCache(ctx context.Context, result *HeartbeatResult, id string) {
	if o.cache != nil {
		if err := o.cache.InvalidateFact(ctx, id); err != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("hygiene fact %s persisted but cache invalidation failed: %v", id, err))
		}
	}
}

// statePersistence writes a heartbeat snapshot every N cycles.
// This creates a persistent breadcrumb trail that survives restarts.
func (o *Orchestrator) statePersistence(ctx context.Context, result *HeartbeatResult) {
	// Snapshot every 50 cycles (avoids memory inflation in fast-heartbeat TUI mode).
	if result.Cycle%50 != 0 {
		return
	}

	snapshot := memory.NewFact(
		fmt.Sprintf("[HEARTBEAT_SNAPSHOT] cycle=%d genome=%v entropy=%.4f peers=%d synced=%d healed=%d",
			result.Cycle, result.GenomeIntact, result.EntropyLevel,
			result.PeersDiscovered, result.FactsSynced, result.GenesHealed),
		memory.LevelProject,
		"orchestrator",
		"heartbeat",
	)
	snapshot.Source = "heartbeat"
	// Derived: our own runtime state.
	snapshot.Origin = memory.OriginDerived
	if err := o.store.Add(ctx, snapshot); err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("snapshot: %v", err))
	}
}

// --- Helpers ---

func parsePeerSpec(spec string) (nodeName, hash string) {
	for i, c := range spec {
		if c == ':' {
			return spec[:i], spec[i+1:]
		}
	}
	return "unknown", spec
}

func genesToSyncFacts(genes []*memory.Fact) []peer.SyncFact {
	facts := make([]peer.SyncFact, 0, len(genes))
	for _, g := range genes {
		facts = append(facts, peer.SyncFact{
			ID:      g.ID,
			Content: g.Content,
			Level:   int(g.Level),
			Domain:  g.Domain,
			IsGene:  g.IsGene,
			Source:  g.Source,
		})
	}
	return facts
}

// SetSynapseStore enables Module 9 (Synapse Scanner) at runtime.
func (o *Orchestrator) SetSynapseStore(store synapse.SynapseStore) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.synapseStore = store
}

// synapseScanner is Module 9: automatic semantic link discovery.
// Scans active facts and proposes PENDING synapse connections based on
// domain overlap and keyword similarity. Threshold: 0.85.
func (o *Orchestrator) synapseScanner(ctx context.Context, result *HeartbeatResult) int {
	// Get all non-stale, non-archived facts.
	allFacts := make([]*memory.Fact, 0)
	for level := 0; level <= 3; level++ {
		hl, ok := memory.HierLevelFromInt(level)
		if !ok {
			continue
		}
		facts, err := o.store.ListByLevel(ctx, hl)
		if err != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("synapse_scan L%d: %v", level, err))
			continue
		}
		for _, f := range facts {
			if !f.IsGene && !f.IsStale && !f.IsArchived {
				allFacts = append(allFacts, f)
			}
		}
	}

	if len(allFacts) < 2 {
		return 0
	}

	created := 0
	// Compare pairs: O(n²) but fact count is small (typically <500).
	for i := 0; i < len(allFacts)-1 && i < 200; i++ {
		for j := i + 1; j < len(allFacts) && j < 200; j++ {
			a, b := allFacts[i], allFacts[j]
			confidence := synapseSimilarity(a, b)
			if confidence < 0.85 {
				continue
			}

			// Check if synapse already exists.
			exists, err := o.synapseStore.Exists(ctx, a.ID, b.ID)
			if err != nil || exists {
				continue
			}

			_, err = o.synapseStore.Create(ctx, a.ID, b.ID, confidence)
			if err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("synapse_create: %v", err))
				continue
			}
			created++
		}
	}

	if created > 0 && o.alertBus != nil {
		o.alertBus.Emit(alert.New(
			alert.SourceMemory,
			alert.SeverityInfo,
			fmt.Sprintf("Synapse Scanner: created %d new bridges", created),
			result.Cycle,
		))
	}

	return created
}

// synapseSimilarity computes a confidence score between two facts.
// Returns 0.0–1.0 based on domain match and keyword overlap.
func synapseSimilarity(a, b *memory.Fact) float64 {
	score := 0.0

	// Same domain → strong signal.
	if a.Domain != "" && a.Domain == b.Domain {
		score += 0.50
	}

	// Same module → additional signal.
	if a.Module != "" && a.Module == b.Module {
		score += 0.20
	}

	// Keyword overlap (words > 3 chars).
	wordsA := tokenize(a.Content)
	wordsB := tokenize(b.Content)

	if len(wordsA) > 0 && len(wordsB) > 0 {
		overlap := 0
		for w := range wordsA {
			if wordsB[w] {
				overlap++
			}
		}
		total := len(wordsA)
		if len(wordsB) < total {
			total = len(wordsB)
		}
		if total > 0 {
			score += 0.30 * float64(overlap) / float64(total)
		}
	}

	if score > 1.0 {
		score = 1.0
	}
	return score
}

// tokenize splits text into unique lowercase words (>3 chars).
func tokenize(text string) map[string]bool {
	words := make(map[string]bool)
	current := make([]byte, 0, 32)
	for i := 0; i < len(text); i++ {
		c := text[i]
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' {
			if c >= 'A' && c <= 'Z' {
				c += 32 // toLower
			}
			current = append(current, c)
		} else {
			if len(current) > 3 {
				words[string(current)] = true
			}
			current = current[:0]
		}
	}
	if len(current) > 3 {
		words[string(current)] = true
	}
	return words
}
