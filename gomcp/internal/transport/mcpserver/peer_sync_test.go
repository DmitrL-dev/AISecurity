package mcpserver

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

// trustPeer establishes a VERIFIED trust pair for peerID by driving a handshake
// whose genome hash matches the node's local compiled genome. This is the only
// way IsTrusted(peerID) becomes true, so the sync trust-gate tests below mirror
// the real path an attacker would have to clear.
func trustPeer(t *testing.T, srv *Server, peerID string) {
	t.Helper()
	local := memory.CompiledGenomeHash()
	_, err := srv.peerReg.ProcessHandshake(peer.HandshakeRequest{
		FromPeerID: peerID,
		FromNode:   "trusted-node",
		GenomeHash: local, // matching hash → TrustVerified
	}, local)
	require.NoError(t, err)
	require.True(t, srv.peerReg.IsTrusted(peerID), "handshake must establish trust")
}

// --- sync_facts: trust gate (security invariant) ---

// Export to a NON-trusted peer must be refused. Otherwise any caller could
// exfiltrate the node's L0-L1 memory simply by naming an unknown peer.
func TestHandleSyncFacts_Export_UntrustedPeerRejected(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	// Seed a fact so a successful export would be observable.
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "secret L0 memory", "level": float64(0),
	}))

	result, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
		"mode":    "export",
		"peer_id": "attacker-unknown-peer",
	}))
	require.NoError(t, err)
	require.True(t, result.IsError, "export to untrusted peer must be rejected")
	out := extractText(t, result)
	assert.Contains(t, out, "not trusted")
	assert.NotContains(t, out, "secret L0 memory", "no facts may leak to an untrusted peer")
}

// Import from a NON-trusted peer must be refused before any fact is written.
func TestHandleSyncFacts_Import_UntrustedPeerRejected(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	payload := peer.SyncPayload{
		Version:    "1.1",
		FromPeerID: "attacker-unknown-peer",
		GenomeHash: memory.CompiledGenomeHash(),
		Facts: []peer.SyncFact{
			{ID: "evil-1", Content: "poisoned fact", Level: 0},
		},
	}
	data, err := json.Marshal(payload)
	require.NoError(t, err)

	result, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
		"mode":         "import",
		"peer_id":      "attacker-unknown-peer",
		"payload_json": string(data),
	}))
	require.NoError(t, err)
	require.True(t, result.IsError, "import from untrusted peer must be rejected")
	assert.Contains(t, extractText(t, result), "not trusted")

	// The poisoned fact must not have been persisted.
	getRes, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{"id": "evil-1"}))
	require.NoError(t, err)
	assert.True(t, getRes.IsError, "rejected import must not write any fact")
}

// A trusted peer whose payload carries the WRONG genome hash must still be
// rejected — genome-hash equality is the integrity check that prevents a
// trusted-but-divergent node from poisoning local memory. This also exercises
// the mismatch error path (shortHashN on the payload hash) without panicking.
func TestHandleSyncFacts_Import_GenomeMismatchRejected(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	const peerID = "trusted-but-divergent"
	trustPeer(t, srv, peerID)

	payload := peer.SyncPayload{
		Version:    "1.1",
		FromPeerID: peerID,
		GenomeHash: "deadbeef", // short + non-matching → mismatch path
		Facts: []peer.SyncFact{
			{ID: "mismatch-1", Content: "fact from a different genome", Level: 0},
		},
	}
	data, err := json.Marshal(payload)
	require.NoError(t, err)

	require.NotPanics(t, func() {
		result, e := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
			"mode":         "import",
			"peer_id":      peerID,
			"payload_json": string(data),
		}))
		require.NoError(t, e)
		require.True(t, result.IsError, "genome hash mismatch must be rejected")
		assert.Contains(t, extractText(t, result), "genome hash mismatch")
	}, "genome-mismatch error path must not panic on a short payload hash")

	getRes, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{"id": "mismatch-1"}))
	require.NoError(t, err)
	assert.True(t, getRes.IsError, "mismatched-genome import must not write any fact")
}

// Happy path: a trusted peer with a matching genome hash imports new facts; the
// import is idempotent (re-importing the same payload adds nothing).
func TestHandleSyncFacts_Import_TrustedHappyPathAndIdempotent(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	const peerID = "trusted-peer-ok"
	trustPeer(t, srv, peerID)

	payload := peer.SyncPayload{
		Version:    "1.1",
		FromPeerID: peerID,
		GenomeHash: memory.CompiledGenomeHash(),
		Facts: []peer.SyncFact{
			{ID: "import-ok-1", Content: "domain fact from peer", Level: 1, Domain: "shared"},
		},
	}
	data, err := json.Marshal(payload)
	require.NoError(t, err)

	// First import: 1 new fact.
	res1, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
		"mode": "import", "peer_id": peerID, "payload_json": string(data),
	}))
	require.NoError(t, err)
	require.False(t, res1.IsError, "trusted matching-genome import must succeed: %s", extractText(t, res1))
	var imp1 map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, res1)), &imp1))
	assert.Equal(t, float64(1), imp1["imported"], "first import must add the new fact")

	// The fact must now be retrievable and tagged with the peer source.
	getRes, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{"id": "import-ok-1"}))
	require.NoError(t, err)
	require.False(t, getRes.IsError)
	assert.Contains(t, extractText(t, getRes), "peer_sync:"+peerID)

	// Second import of the same payload: idempotent, nothing new.
	res2, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
		"mode": "import", "peer_id": peerID, "payload_json": string(data),
	}))
	require.NoError(t, err)
	require.False(t, res2.IsError)
	var imp2 map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, res2)), &imp2))
	assert.Equal(t, float64(0), imp2["imported"], "re-importing the same fact must add nothing (skip-existing)")
}

// Export to a trusted peer returns L0 AND L1 facts but never stale/archived ones
// — the documented L0-L1 sync contract that delta_sync was fixed to match.
func TestHandleSyncFacts_Export_IncludesL0L1_ExcludesStale(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	const peerID = "trusted-exporter"
	trustPeer(t, srv, peerID)

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "project-level-export", "level": float64(0),
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "domain-level-export", "level": float64(1), "domain": "d",
	}))
	staleAdd, _ := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "stale-should-not-export", "level": float64(0),
	}))
	var staleFact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, staleAdd)), &staleFact))
	_, _ = srv.handleUpdateFact(ctx, callToolReq("update_fact", map[string]interface{}{
		"id": staleFact["id"].(string), "is_stale": true,
	}))

	result, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{
		"mode": "export", "peer_id": peerID,
	}))
	require.NoError(t, err)
	require.False(t, result.IsError)
	out := extractText(t, result)

	assert.Contains(t, out, "project-level-export", "L0 facts must be exported")
	assert.Contains(t, out, "domain-level-export", "L1 facts must be exported")
	assert.NotContains(t, out, "stale-should-not-export", "stale facts must be excluded from export")
}

// --- delta_sync: trust + genome wiring (mirrors sync_facts export tiers) ---

// delta_sync must export L0 AND L1 facts created after `since`, while excluding
// stale facts — the contract Pass 6 fixed (it previously dropped all L1 facts).
func TestHandleDeltaSync_IncludesL0L1_ExcludesStale(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "delta-l0-fact", "level": float64(0),
	}))
	_, _ = srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "delta-l1-fact", "level": float64(1), "domain": "d",
	}))
	staleAdd, _ := srv.handleAddFact(ctx, callToolReq("add_fact", map[string]interface{}{
		"content": "delta-stale-fact", "level": float64(1), "domain": "d",
	}))
	var staleFact map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, staleAdd)), &staleFact))
	_, _ = srv.handleUpdateFact(ctx, callToolReq("update_fact", map[string]interface{}{
		"id": staleFact["id"].(string), "is_stale": true,
	}))

	// since well in the past → all live facts qualify.
	result, err := srv.handleDeltaSync(ctx, callToolReq("delta_sync", map[string]interface{}{
		"since": "2000-01-01T00:00:00Z",
	}))
	require.NoError(t, err)
	require.False(t, result.IsError, "delta_sync should succeed: %s", extractText(t, result))
	out := extractText(t, result)

	assert.Contains(t, out, "delta-l0-fact", "delta_sync must include L0 facts")
	assert.Contains(t, out, "delta-l1-fact", "delta_sync must include L1 (domain) facts")
	assert.NotContains(t, out, "delta-stale-fact", "delta_sync must exclude stale facts")
}

// delta_sync requires the `since` timestamp and rejects malformed ones.
func TestHandleDeltaSync_RejectsBadSince(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	missing, err := srv.handleDeltaSync(ctx, callToolReq("delta_sync", map[string]interface{}{}))
	require.NoError(t, err)
	assert.True(t, missing.IsError, "missing 'since' must error")
	assert.Contains(t, extractText(t, missing), "since")

	bad, err := srv.handleDeltaSync(ctx, callToolReq("delta_sync", map[string]interface{}{
		"since": "not-a-timestamp",
	}))
	require.NoError(t, err)
	assert.True(t, bad.IsError, "malformed 'since' must error")
	assert.Contains(t, extractText(t, bad), "RFC3339")
}

// --- Genome layer: add_gene / list_genes / verify_genome ---

// A gene round-trips through add_gene → list_genes, and verify_genome reports a
// non-empty Merkle hash with a gene count that reflects the added gene.
func TestHandleGeneLifecycle(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	addRes, err := srv.handleAddGene(ctx, callToolReq("add_gene", map[string]interface{}{
		"content": "survival invariant: never fail open", "domain": "security",
	}))
	require.NoError(t, err)
	require.False(t, addRes.IsError, "add_gene should succeed: %s", extractText(t, addRes))

	listRes, err := srv.handleListGenes(ctx, callToolReq("list_genes", nil))
	require.NoError(t, err)
	require.False(t, listRes.IsError)
	assert.Contains(t, extractText(t, listRes), "never fail open")

	verRes, err := srv.handleVerifyGenome(ctx, callToolReq("verify_genome", nil))
	require.NoError(t, err)
	require.False(t, verRes.IsError)
	var ver map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, verRes)), &ver))
	assert.Equal(t, "verified", ver["status"])
	assert.NotEmpty(t, ver["genome_hash"], "verify_genome must return a Merkle hash")
	assert.GreaterOrEqual(t, ver["gene_count"], float64(1), "gene_count must include the added gene")
}

// --- peer_status / peer_backup smoke (untested handlers) ---

func TestHandlePeerStatus_ReportsGenomeHash(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handlePeerStatus(ctx, callToolReq("peer_status", nil))
	require.NoError(t, err)
	require.False(t, result.IsError)
	var stats map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(extractText(t, result)), &stats))
	assert.Equal(t, memory.CompiledGenomeHash(), stats["genome_hash"],
		"peer_status must surface the local compiled genome hash")
}

func TestHandlePeerBackup_NoBackupForUnknownPeer(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()

	result, err := srv.handlePeerBackup(ctx, callToolReq("peer_backup", map[string]interface{}{
		"peer_id": "ghost-peer",
	}))
	require.NoError(t, err)
	require.False(t, result.IsError)
	assert.Contains(t, extractText(t, result), "no backup found")
}

func TestAuditExportRequiresExplicitTrustedPeer(t *testing.T) {
	srv := newTestServer(t)
	for _, peerID := range []string{"", "not-trusted"} {
		result, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "export", "peer_id": peerID}))
		require.NoError(t, err)
		require.True(t, result.IsError)
	}
}
