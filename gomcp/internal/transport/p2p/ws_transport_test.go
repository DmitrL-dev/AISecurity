package transport

import (
	"bytes"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

func TestWSTransport_StartRequiresPeerVerifier(t *testing.T) {
	reg := peer.NewRegistry("test-node", 5*time.Minute)
	tr := NewWSTransport(WSConfig{Port: 0}, reg)
	require.ErrorIs(t, tr.Start(), ErrPeerVerifierUnavailable)
	assert.Empty(t, tr.Addr(), "no listener is created without a verifier")
}

// Preserve the existing input-boundary test without opening a TLS listener or
// generating credentials: a fake verifier and synthetic TLS state exercise
// only the handler's 16 MiB body bound.
func TestWSTransport_RejectsOversizedBody(t *testing.T) {
	reg := peer.NewRegistry("oversize-node", 5*time.Minute)
	tr := NewWSTransport(WSConfig{Port: 0}, reg)
	tr.verifyPeer = func(_ *tls.ConnectionState, _ string) error { return nil }
	oversized := `{"type":"sync","from":"x","payload":"` + strings.Repeat("A", int(maxP2PBodyBytes)+1024) + `"}`
	req := httptest.NewRequest(http.MethodPost, "/p2p", bytes.NewReader([]byte(oversized)))
	req.TLS = &tls.ConnectionState{PeerCertificates: []*x509.Certificate{{Subject: pkix.Name{CommonName: "x"}}}}
	recorder := httptest.NewRecorder()
	tr.handleP2P(recorder, req)
	assert.NotEqual(t, http.StatusOK, recorder.Code)
}

func TestFilterFactsSince(t *testing.T) {
	now := time.Now()
	facts := []peer.SyncFact{
		{ID: "old", Content: "old fact", CreatedAt: now.Add(-2 * time.Hour)},
		{ID: "new1", Content: "new fact 1", CreatedAt: now.Add(-30 * time.Minute)},
		{ID: "new2", Content: "new fact 2", CreatedAt: now.Add(-10 * time.Minute)},
	}

	// Filter since 1 hour ago.
	filtered, hasMore := peer.FilterFactsSince(facts, now.Add(-1*time.Hour), 100)
	assert.Len(t, filtered, 2)
	assert.False(t, hasMore)
	assert.Equal(t, "new1", filtered[0].ID)
	assert.Equal(t, "new2", filtered[1].ID)

	// Filter with small batch.
	filtered, hasMore = peer.FilterFactsSince(facts, now.Add(-1*time.Hour), 1)
	assert.Len(t, filtered, 1)
	assert.True(t, hasMore)
}

func TestMessage_JSON(t *testing.T) {
	msg := Message{
		Type:   "ping",
		From:   "node-1",
		SentAt: time.Now(),
	}
	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var decoded Message
	require.NoError(t, json.Unmarshal(data, &decoded))
	assert.Equal(t, "ping", decoded.Type)
	assert.Equal(t, "node-1", decoded.From)
}
