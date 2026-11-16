package peer

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testGenomeHash = "f1cf104ff9cfd71c6d3a2e5b8e7f9d0a4b6c8e1f3a5b7d9e2c4f6a8b0d2e4f6"

func TestNewRegistry(t *testing.T) {
	r := NewRegistry("node-alpha", 0)
	assert.NotEmpty(t, r.SelfID())
	assert.Equal(t, "node-alpha", r.NodeName())
	assert.Equal(t, 0, r.PeerCount())
}

func TestTrustLevel_String(t *testing.T) {
	tests := []struct {
		level TrustLevel
		want  string
	}{
		{TrustUnknown, "UNKNOWN"},
		{TrustPending, "PENDING"},
		{TrustVerified, "VERIFIED"},
		{TrustRejected, "REJECTED"},
		{TrustExpired, "EXPIRED"},
		{TrustLevel(99), "INVALID"},
	}
	for _, tt := range tests {
		assert.Equal(t, tt.want, tt.level.String())
	}
}

func TestHandshake_MatchingGenomes(t *testing.T) {
	alpha := NewRegistry("alpha", 30*time.Minute)
	beta := NewRegistry("beta", 30*time.Minute)

	// Alpha initiates handshake.
	req := HandshakeRequest{
		FromPeerID: alpha.SelfID(),
		FromNode:   alpha.NodeName(),
		GenomeHash: testGenomeHash,
		Timestamp:  time.Now().Unix(),
		Nonce:      "nonce123",
	}

	// Beta processes it.
	resp, err := beta.ProcessHandshake(req, testGenomeHash)
	require.NoError(t, err)
	assert.True(t, resp.Match, "Same hash must match")
	assert.Equal(t, TrustVerified, resp.Trust)
	assert.True(t, beta.IsTrusted(alpha.SelfID()))
	assert.Equal(t, 1, beta.PeerCount())

	// Alpha completes handshake with response.
	err = alpha.CompleteHandshake(*resp, testGenomeHash)
	require.NoError(t, err)
	assert.True(t, alpha.IsTrusted(beta.SelfID()))
	assert.Equal(t, 1, alpha.PeerCount())
}

func TestHandshake_MismatchedGenomes(t *testing.T) {
	alpha := NewRegistry("alpha", 30*time.Minute)
	beta := NewRegistry("beta", 30*time.Minute)

	req := HandshakeRequest{
		FromPeerID: alpha.SelfID(),
		FromNode:   alpha.NodeName(),
		GenomeHash: "deadbeef_bad_hash",
		Timestamp:  time.Now().Unix(),
	}

	resp, err := beta.ProcessHandshake(req, testGenomeHash)
	require.NoError(t, err)
	assert.False(t, resp.Match, "Different hashes must not match")
	assert.Equal(t, TrustRejected, resp.Trust)
	assert.False(t, beta.IsTrusted(alpha.SelfID()))
}

func TestHandshake_SelfHandshake_Blocked(t *testing.T) {
	r := NewRegistry("self-node", 30*time.Minute)
	req := HandshakeRequest{
		FromPeerID: r.SelfID(),
		FromNode:   r.NodeName(),
		GenomeHash: testGenomeHash,
	}
	_, err := r.ProcessHandshake(req, testGenomeHash)
	assert.ErrorIs(t, err, ErrSelfHandshake)
}

func TestGetPeer_NotFound(t *testing.T) {
	r := NewRegistry("node", 30*time.Minute)
	_, err := r.GetPeer("nonexistent")
	assert.ErrorIs(t, err, ErrPeerNotFound)
}

func TestListPeers_Empty(t *testing.T) {
	r := NewRegistry("node", 30*time.Minute)
	peers := r.ListPeers()
	assert.Empty(t, peers)
}

func TestRecordSync(t *testing.T) {
	alpha := NewRegistry("alpha", 30*time.Minute)
	beta := NewRegistry("beta", 30*time.Minute)

	// Establish trust.
	req := HandshakeRequest{
		FromPeerID: beta.SelfID(),
		FromNode:   beta.NodeName(),
		GenomeHash: testGenomeHash,
	}
	_, err := alpha.ProcessHandshake(req, testGenomeHash)
	require.NoError(t, err)

	// Record sync.
	err = alpha.RecordSync(beta.SelfID(), 5)
	require.NoError(t, err)

	peer, err := alpha.GetPeer(beta.SelfID())
	require.NoError(t, err)
	assert.Equal(t, 5, peer.FactCount)
	assert.False(t, peer.LastSyncAt.IsZero())
}

func TestRecordSync_UnknownPeer(t *testing.T) {
	r := NewRegistry("node", 30*time.Minute)
	err := r.RecordSync("unknown_peer", 1)
	assert.ErrorIs(t, err, ErrPeerNotFound)
}

func TestCheckTimeouts_ExpiresOldPeers(t *testing.T) {
	r := NewRegistry("node", 1*time.Millisecond) // Ultra-short timeout

	// Add a peer via handshake.
	req := HandshakeRequest{
		FromPeerID: "peer_old",
		FromNode:   "old-node",
		GenomeHash: testGenomeHash,
	}
	_, err := r.ProcessHandshake(req, testGenomeHash)
	require.NoError(t, err)
	assert.True(t, r.IsTrusted("peer_old"))

	// Wait for timeout.
	time.Sleep(5 * time.Millisecond)

	// Check timeouts — should expire and create backup.
	facts := []SyncFact{
		{ID: "f1", Content: "test fact", Level: 0, Source: "test"},
	}
	backups := r.CheckTimeouts(facts)
	assert.Len(t, backups, 1)
	assert.Equal(t, "peer_old", backups[0].PeerID)
	assert.Equal(t, "timeout", backups[0].Reason)

	// Peer should now be expired.
	assert.False(t, r.IsTrusted("peer_old"))
}

func TestGeneBackup_SaveAndRetrieve(t *testing.T) {
	r := NewRegistry("node", 1*time.Millisecond)

	req := HandshakeRequest{
		FromPeerID: "peer_backup_test",
		FromNode:   "backup-node",
		GenomeHash: testGenomeHash,
	}
	_, err := r.ProcessHandshake(req, testGenomeHash)
	require.NoError(t, err)

	time.Sleep(5 * time.Millisecond)

	facts := []SyncFact{
		{ID: "gene1", Content: "survival invariant", Level: 0, IsGene: true, Source: "genome"},
	}
	r.CheckTimeouts(facts)

	// Retrieve backup.
	backup, ok := r.GetBackup("peer_backup_test")
	require.True(t, ok)
	assert.Equal(t, "peer_backup_test", backup.PeerID)
	assert.Len(t, backup.Facts, 1)
	assert.Equal(t, "gene1", backup.Facts[0].ID)

	// Clear backup after recovery.
	r.ClearBackup("peer_backup_test")
	_, ok = r.GetBackup("peer_backup_test")
	assert.False(t, ok)
}

func TestStats(t *testing.T) {
	r := NewRegistry("stats-node", 30*time.Minute)

	// Add two peers.
	r.ProcessHandshake(HandshakeRequest{FromPeerID: "p1", FromNode: "n1", GenomeHash: testGenomeHash}, testGenomeHash) //nolint
	r.ProcessHandshake(HandshakeRequest{FromPeerID: "p2", FromNode: "n2", GenomeHash: "bad_hash"}, testGenomeHash)     //nolint

	stats := r.Stats()
	assert.Equal(t, 2, stats["total_peers"])
	byTrust := stats["by_trust"].(map[string]int)
	assert.Equal(t, 1, byTrust["VERIFIED"])
	assert.Equal(t, 1, byTrust["REJECTED"])
}

func TestTrustedCount(t *testing.T) {
	r := NewRegistry("node", 30*time.Minute)
	assert.Equal(t, 0, r.TrustedCount())

	r.ProcessHandshake(HandshakeRequest{FromPeerID: "p1", FromNode: "n1", GenomeHash: testGenomeHash}, testGenomeHash) //nolint
	r.ProcessHandshake(HandshakeRequest{FromPeerID: "p2", FromNode: "n2", GenomeHash: testGenomeHash}, testGenomeHash) //nolint
	r.ProcessHandshake(HandshakeRequest{FromPeerID: "p3", FromNode: "n3", GenomeHash: "wrong"}, testGenomeHash)        //nolint

	assert.Equal(t, 2, r.TrustedCount())
}

func TestPeerInfo_IsAlive(t *testing.T) {
	p := &PeerInfo{LastSeen: time.Now()}
	assert.True(t, p.IsAlive(1*time.Hour))

	p.LastSeen = time.Now().Add(-2 * time.Hour)
	assert.False(t, p.IsAlive(1*time.Hour))
}
