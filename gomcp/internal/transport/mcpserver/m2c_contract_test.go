package mcpserver

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

type m2FaultStore struct {
	memory.FactStore
	lookupID string
	writeID  string
	writes   int
}

func (f *m2FaultStore) Get(ctx context.Context, id string) (*memory.Fact, error) {
	if id == f.lookupID {
		return nil, errors.New("PRIVATE_BACKEND_DETAIL")
	}
	return f.FactStore.Get(ctx, id)
}
func (f *m2FaultStore) Add(ctx context.Context, fact *memory.Fact) error {
	f.writes++
	if fact.ID == f.writeID {
		return errors.New("PRIVATE_BACKEND_DETAIL")
	}
	return f.FactStore.Add(ctx, fact)
}
func m2Import(t *testing.T, srv *Server, peerID string, facts []peer.SyncFact, incidents []peer.SyncIncident) (*mcp.CallToolResult, string) {
	t.Helper()
	payload := peer.SyncPayload{FromPeerID: peerID, GenomeHash: memory.CompiledGenomeHash(), Facts: facts, Incidents: incidents}
	data, err := json.Marshal(payload)
	require.NoError(t, err)
	res, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": peerID, "payload_json": string(data)}))
	require.NoError(t, err)
	return res, extractText(t, res)
}
func m2Statuses(t *testing.T, output string) []interface{} {
	t.Helper()
	var body map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(output), &body))
	statuses, ok := body["fact_results"].([]interface{})
	require.True(t, ok)
	return statuses
}
func TestM2cLookupFailureIsNotMissingOrAcknowledged(t *testing.T) {
	srv := newTestServer(t)
	const id = "m2c-lookup-peer"
	trustPeer(t, srv, id)
	before, err := srv.peerReg.GetPeer(id)
	require.NoError(t, err)
	fault := &m2FaultStore{FactStore: srv.facts.Store(), lookupID: "lookup-fail"}
	srv.facts = tools.NewFactService(fault, nil)
	res, out := m2Import(t, srv, id, []peer.SyncFact{{ID: "lookup-fail", Content: "fixture", Level: 0}}, nil)
	require.True(t, res.IsError)
	require.NotContains(t, out, "PRIVATE_BACKEND_DETAIL")
	statuses := m2Statuses(t, out)
	require.Equal(t, "lookup_failed", statuses[0].(map[string]interface{})["status"])
	require.Zero(t, fault.writes)
	after, err := srv.peerReg.GetPeer(id)
	require.NoError(t, err)
	require.Equal(t, before.LastSeen, after.LastSeen)
	require.Equal(t, before.LastSyncAt, after.LastSyncAt)
}
func TestM2cPartialWriteIsUnconfirmedNotDuplicate(t *testing.T) {
	srv := newTestServer(t)
	const id = "m2c-write-peer"
	trustPeer(t, srv, id)
	fault := &m2FaultStore{FactStore: srv.facts.Store(), writeID: "write-fail"}
	srv.facts = tools.NewFactService(fault, nil)
	res, out := m2Import(t, srv, id, []peer.SyncFact{{ID: "written", Content: "one", Level: 0}, {ID: "write-fail", Content: "two", Level: 0}}, nil)
	require.True(t, res.IsError)
	require.NotContains(t, out, "PRIVATE_BACKEND_DETAIL")
	statuses := m2Statuses(t, out)
	require.Equal(t, "imported", statuses[0].(map[string]interface{})["status"])
	require.Equal(t, "write_unconfirmed", statuses[1].(map[string]interface{})["status"])
	actual, err := fault.FactStore.Get(context.Background(), "written")
	require.NoError(t, err)
	require.Equal(t, "one", actual.Content)
}
func TestM2cConflictingIdentityAndInvalidFactsAreNotAcknowledged(t *testing.T) {
	srv := newTestServer(t)
	const id = "m2c-conflict-peer"
	trustPeer(t, srv, id)
	existing := memory.NewFact("original", memory.LevelProject, "", "")
	existing.ID = "same-id"
	require.NoError(t, srv.facts.Store().Add(context.Background(), existing))
	res, out := m2Import(t, srv, id, []peer.SyncFact{{ID: "same-id", Content: "changed", Level: 0}, {ID: "", Content: "invalid", Level: 0}, {ID: "bad-level", Content: "invalid", Level: 99}}, nil)
	require.True(t, res.IsError)
	statuses := m2Statuses(t, out)
	require.Equal(t, "conflict", statuses[0].(map[string]interface{})["status"])
	require.Equal(t, "invalid", statuses[1].(map[string]interface{})["status"])
	require.Equal(t, "invalid", statuses[2].(map[string]interface{})["status"])
}
func TestM2cIncidentPayloadRejectedBeforeFactWrites(t *testing.T) {
	srv := newTestServer(t)
	const id = "m2c-incident-peer"
	trustPeer(t, srv, id)
	fault := &m2FaultStore{FactStore: srv.facts.Store()}
	srv.facts = tools.NewFactService(fault, nil)
	res, _ := m2Import(t, srv, id, []peer.SyncFact{{ID: "must-not-write", Content: "fixture", Level: 0}}, []peer.SyncIncident{{ID: "fixture"}})
	require.True(t, res.IsError)
	require.Zero(t, fault.writes)
}

func TestM2cContentFoldDoesNotAcknowledgeDifferentID(t *testing.T) {
	srv := newTestServer(t)
	const peerID = "m2c-fold-peer"
	trustPeer(t, srv, peerID)
	existing := memory.NewFact("folded-content", memory.LevelProject, "", "")
	existing.ID = "canonical-existing"
	require.NoError(t, srv.facts.Store().Add(context.Background(), existing))
	res, out := m2Import(t, srv, peerID, []peer.SyncFact{{ID: "different-peer-id", Content: "folded-content", Level: 0}}, nil)
	require.True(t, res.IsError)
	statuses := m2Statuses(t, out)
	require.Equal(t, "write_unconfirmed", statuses[0].(map[string]interface{})["status"])
}

func TestM2cPayloadPeerReferenceMismatchIsRejectedBeforeWrites(t *testing.T) {
	srv := newTestServer(t)
	const peerID = "m2c-reference-peer"
	trustPeer(t, srv, peerID)
	fault := &m2FaultStore{FactStore: srv.facts.Store()}
	srv.facts = tools.NewFactService(fault, nil)
	payload := peer.SyncPayload{FromPeerID: "different-peer", GenomeHash: memory.CompiledGenomeHash(), Facts: []peer.SyncFact{{ID: "do-not-write", Content: "fixture", Level: 0}}}
	data, err := json.Marshal(payload)
	require.NoError(t, err)
	res, err := srv.handleSyncFacts(context.Background(), callToolReq("sync_facts", map[string]interface{}{"mode": "import", "peer_id": peerID, "payload_json": string(data)}))
	require.NoError(t, err)
	require.True(t, res.IsError)
	require.Zero(t, fault.writes)
}

func TestM2cPeerGeneIsNotPersistedAsTrustedGenome(t *testing.T) {
	srv := newTestServer(t)
	const peerID = "m2c-gene-peer"
	trustPeer(t, srv, peerID)
	fault := &m2FaultStore{FactStore: srv.facts.Store()}
	srv.facts = tools.NewFactService(fault, nil)
	res, out := m2Import(t, srv, peerID, []peer.SyncFact{{ID: "external-gene", Content: "fixture", Level: 0, IsGene: true}}, nil)
	require.True(t, res.IsError)
	require.Zero(t, fault.writes)
	statuses := m2Statuses(t, out)
	require.Equal(t, "unsupported_gene", statuses[0].(map[string]interface{})["status"])
}

func TestM2cFactOnlyDoesNotClaimSOCSnapshot(t *testing.T) {
	srv := newTestServer(t)
	const peerID = "m2c-fact-only-peer"
	trustPeer(t, srv, peerID)
	res, out := m2Import(t, srv, peerID, []peer.SyncFact{{ID: "fact-only", Content: "fixture", Level: 0}}, nil)
	require.False(t, res.IsError)
	var body map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(out), &body))
	require.Equal(t, false, body["incidents_import_complete"])
	require.Equal(t, "not_included", body["incidents_import_status"])
	require.Equal(t, false, body["peer_identity_verified"])
}
