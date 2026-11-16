package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// In-memory synthetic tenants only. No external peers or transport.
func TestSOCUnsourcedPeerSyncFailsClosed(t *testing.T) {
	srv := newTestServer(t)
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { _ = db.Close() })
	repo, err := sqlite.NewSOCRepo(db)
	require.NoError(t, err)
	for _, tenant := range []string{"synthetic-a", "synthetic-b"} {
		inc := domsoc.NewIncident("synthetic-incident-"+tenant, domsoc.SeverityHigh, "synthetic")
		inc.TenantID = tenant
		require.NoError(t, repo.InsertIncident(inc))
	}
	srv.socSvc = appsoc.NewService(repo, nil)
	trustPeer(t, srv, "synthetic-trusted-peer")
	ctx := context.Background()
	result, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{"mode": "export", "peer_id": "synthetic-trusted-peer"}))
	require.NoError(t, err)
	require.True(t, result.IsError, "unscoped SOC export must not succeed")
	text := extractText(t, result)
	require.NotContains(t, text, "synthetic-incident-synthetic-a")
	require.NotContains(t, text, "synthetic-incident-synthetic-b")
	handshake, err := srv.handleForceResonanceHandshake(ctx, callToolReq("force_resonance_handshake", map[string]interface{}{"peer_genome_hash": memory.CompiledGenomeHash(), "peer_id": "synthetic-trusted-peer"}))
	require.NoError(t, err)
	require.True(t, handshake.IsError, "auto-sync must not export unscoped SOC")
	payload := peer.SyncPayload{FromPeerID: "synthetic-trusted-peer", GenomeHash: memory.CompiledGenomeHash(), Facts: []peer.SyncFact{{ID: "synthetic-fact", Content: "synthetic", Level: 0}}, Incidents: []peer.SyncIncident{{ID: "synthetic-remote"}}}
	body, err := json.Marshal(payload)
	require.NoError(t, err)
	result, err = srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": "synthetic-trusted-peer", "payload_json": string(body)}))
	require.NoError(t, err)
	require.True(t, result.IsError, "tenantless incident import must fail")
	// Empty or omitted incidents is not a verified complete SOC sync.
	payload.Incidents = nil
	body, err = json.Marshal(payload)
	require.NoError(t, err)
	result, err = srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": "synthetic-trusted-peer", "payload_json": string(body)}))
	require.NoError(t, err)
	require.True(t, result.IsError, "wired SOC must not falsely acknowledge an absent incident set")
	fact, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{"id": "synthetic-fact"}))
	require.NoError(t, err)
	require.True(t, fact.IsError, "incident refusal must precede fact writes")
	for _, tenant := range []string{"synthetic-a", "synthetic-b"} {
		rows, err := repo.ListIncidents(tenant, "", 100)
		require.NoError(t, err)
		require.Len(t, rows, 1)
	}
}

func TestSOCIncidentDuplicatesOrAliasesFailBeforeFactMutation(t *testing.T) {
	srv := newTestServer(t)
	trustPeer(t, srv, "synthetic-trusted-peer")
	ctx := context.Background()
	for _, field := range []string{`"incidents":[{"id":"x"}],"incidents":[]`, `"INCIDENTS":[]`} {
		payload := fmt.Sprintf(`{"genome_hash":%q,"facts":[{"id":"synthetic-fact","content":"synthetic","level":0}],%s}`, memory.CompiledGenomeHash(), field)
		result, err := srv.handleSyncFacts(ctx, callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": "synthetic-trusted-peer", "payload_json": payload}))
		require.NoError(t, err)
		require.True(t, result.IsError)
		fact, err := srv.handleGetFact(ctx, callToolReq("get_fact", map[string]interface{}{"id": "synthetic-fact"}))
		require.NoError(t, err)
		require.True(t, fact.IsError)
	}
}

func TestFactOnlyPeerSyncWithoutSOCRemainsAvailable(t *testing.T) {
	srv := newTestServer(t)
	trustPeer(t, srv, "synthetic-trusted-peer")
	result, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "export", "peer_id": "synthetic-trusted-peer"}))
	require.NoError(t, err)
	require.False(t, result.IsError)
}
