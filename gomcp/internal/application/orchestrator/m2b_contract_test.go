package orchestrator

import (
	"context"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

// An arbitrary configured string is not an authenticated remote handshake.
func TestM2DiscoveryDoesNotInventPeerAcknowledgement(t *testing.T) {
	cfg := DefaultConfig()
	cfg.KnownPeers = []string{"synthetic-node:" + memory.CompiledGenomeHash()}
	orch, _ := newTestOrchestrator(t, cfg)
	require.Zero(t, orch.autoDiscover(context.Background()))
	require.Zero(t, orch.peerReg.TrustedCount())
}

// Local payload preparation is not delivery. An edit that keeps the same count
// cannot be used as evidence that an earlier attempt was acknowledged.
func TestM2SyncDoesNotAdvanceWithoutRemoteAcknowledgement(t *testing.T) {
	orch, store := newTestOrchestrator(t, DefaultConfig())
	_, err := orch.peerReg.ProcessHandshake(peer.HandshakeRequest{
		FromPeerID: "fixture-peer", FromNode: "fixture", GenomeHash: memory.CompiledGenomeHash(),
	}, memory.CompiledGenomeHash())
	require.NoError(t, err)
	before, err := orch.peerReg.GetPeer("fixture-peer")
	require.NoError(t, err)
	fact := memory.NewFact("fixture", memory.LevelProject, "fixture", "test")
	require.NoError(t, store.Add(context.Background(), fact))
	first := HeartbeatResult{}
	require.Zero(t, orch.syncManager(context.Background(), &first))
	require.NotEmpty(t, first.Errors)
	require.True(t, orch.lastSync.IsZero())
	require.Zero(t, orch.lastFactCount)
	after, err := orch.peerReg.GetPeer("fixture-peer")
	require.NoError(t, err)
	require.Equal(t, before.LastSeen, after.LastSeen)
	require.Equal(t, before.LastSyncAt, after.LastSyncAt)
	require.Equal(t, before.FactCount, after.FactCount)
	fact.Content = "changed-in-place"
	require.NoError(t, store.Update(context.Background(), fact))
	second := HeartbeatResult{}
	require.Zero(t, orch.syncManager(context.Background(), &second))
	require.NotEmpty(t, second.Errors)
	require.True(t, orch.lastSync.IsZero())
	require.Zero(t, orch.lastFactCount)
}
