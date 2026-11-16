package mcpserver

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

type budgetProbeStore struct {
	memory.FactStore
	writes int
}

func (s *budgetProbeStore) Get(context.Context, string) (*memory.Fact, error) {
	return nil, memory.ErrFactNotFound
}
func (s *budgetProbeStore) Add(context.Context, *memory.Fact) error {
	s.writes++
	return errors.New("synthetic-write-unconfirmed")
}
func budgetServer(t *testing.T, peerID string) (*Server, *budgetProbeStore) {
	t.Helper()
	srv := newTestServer(t)
	trustPeer(t, srv, peerID)
	store := &budgetProbeStore{FactStore: srv.facts.Store()}
	srv.facts = tools.NewFactService(store, nil)
	return srv, store
}
func requireBudgetError(t *testing.T, out string, kind string) {
	t.Helper()
	var body map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(out), &body))
	require.Equal(t, "sync_import_limit_exceeded", body["code"])
	require.Equal(t, kind, body["limit_kind"])
	require.Equal(t, float64(0), body["imported"])
	require.Equal(t, false, body["facts_import_complete"])
}
func TestM2BudgetRejectsCountBeforeAnyWrites(t *testing.T) {
	const peerID = "budget-count"
	srv, store := budgetServer(t, peerID)
	facts := make([]peer.SyncFact, 101)
	for i := range facts {
		facts[i] = peer.SyncFact{ID: fmt.Sprintf("fact-%d", i), Content: "fixture", Level: 0}
	}
	res, out := m2Import(t, srv, peerID, facts, nil)
	require.True(t, res.IsError)
	requireBudgetError(t, out, "fact_count")
	require.Zero(t, store.writes)
}
func TestM2BudgetRejectsOversizedFactBeforeEarlierWrites(t *testing.T) {
	const peerID = "budget-fact"
	srv, store := budgetServer(t, peerID)
	facts := []peer.SyncFact{{ID: "first", Content: "small", Level: 0}, {ID: "large", Content: strings.Repeat("a", 64*1024), Level: 0}}
	res, out := m2Import(t, srv, peerID, facts, nil)
	require.True(t, res.IsError)
	requireBudgetError(t, out, "fact_bytes")
	require.Zero(t, store.writes)
}
func TestM2BudgetRejectsLargePayloadBeforeWrites(t *testing.T) {
	const peerID = "budget-payload"
	srv, store := budgetServer(t, peerID)
	facts := []peer.SyncFact{{ID: "large", Content: strings.Repeat("a", 512*1024), Level: 0}}
	res, out := m2Import(t, srv, peerID, facts, nil)
	require.True(t, res.IsError)
	requireBudgetError(t, out, "payload_bytes")
	require.Zero(t, store.writes)
}
func TestM2BudgetAllowsCallerSplitBatches(t *testing.T) {
	const peerID = "budget-split"
	srv := newTestServer(t)
	trustPeer(t, srv, peerID)
	facts := []peer.SyncFact{{ID: "split-1", Content: "one", Level: 0}, {ID: "split-2", Content: "two", Level: 0}, {ID: "split-3", Content: "three", Level: 0}}
	for _, batch := range [][]peer.SyncFact{facts[:2], facts[2:]} {
		res, out := m2Import(t, srv, peerID, batch, nil)
		require.False(t, res.IsError, out)
		var body map[string]interface{}
		require.NoError(t, json.Unmarshal([]byte(out), &body))
		require.Equal(t, true, body["facts_import_complete"])
	}
}
func TestM2BudgetResultIsBoundedAtMaximumCount(t *testing.T) {
	const peerID = "budget-result"
	srv, store := budgetServer(t, peerID)
	facts := make([]peer.SyncFact, 100)
	for i := range facts {
		facts[i] = peer.SyncFact{ID: fmt.Sprintf("fact-%d", i), Content: "fixture", Level: 0}
	}
	res, out := m2Import(t, srv, peerID, facts, nil)
	require.True(t, res.IsError)
	require.Equal(t, 100, store.writes)
	require.Len(t, m2Statuses(t, out), 100)
	require.Less(t, len(out), 64*1024)
	envelope, err := json.Marshal(res)
	require.NoError(t, err)
	require.Less(t, len(envelope), 1024*1024)
}

func TestM2BudgetRejectsLongPeerReferenceBeforeWrites(t *testing.T) {
	peerID := strings.Repeat("p", 257)
	srv, store := budgetServer(t, peerID)
	res, out := m2Import(t, srv, peerID, []peer.SyncFact{{ID: "fixture", Content: "fixture", Level: 0}}, nil)
	require.True(t, res.IsError)
	requireBudgetError(t, out, "peer_id_bytes")
	require.Zero(t, store.writes)
	require.NotContains(t, out, peerID)
	var body map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(out), &body))
	require.Equal(t, "peer_reference_exceeds_limit", body["continuation"])
}

func TestM2BudgetCountsRawUnknownFieldsBeforeWrites(t *testing.T) {
	const peerID = "budget-raw"
	srv, store := budgetServer(t, peerID)
	payload := fmt.Sprintf(`{"from_peer_id":%q,"genome_hash":%q,"facts":[{"id":"first","content":"small","level":0},{"id":"second","content":"small","level":0,"unknown_padding":%q}]}`, peerID, memory.CompiledGenomeHash(), strings.Repeat("z", 64*1024))
	res, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": peerID, "payload_json": payload}))
	require.NoError(t, err)
	require.True(t, res.IsError)
	out := extractText(t, res)
	requireBudgetError(t, out, "fact_bytes")
	require.Zero(t, store.writes)
	var body map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(out), &body))
	require.Equal(t, float64(1), body["fact_index"])
}
func TestM2BudgetRejectsFactListCaseAliasBeforeWrites(t *testing.T) {
	const peerID = "budget-alias"
	srv, store := budgetServer(t, peerID)
	payload := fmt.Sprintf(`{"from_peer_id":%q,"genome_hash":%q,"facts":[],"Facts":[{"id":"evil","content":"fixture","level":0}]}`, peerID, memory.CompiledGenomeHash())
	res, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": peerID, "payload_json": payload}))
	require.NoError(t, err)
	require.True(t, res.IsError)
	require.Zero(t, store.writes)
}
