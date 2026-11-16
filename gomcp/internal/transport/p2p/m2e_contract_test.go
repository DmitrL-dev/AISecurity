package transport

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

func m2eRequest(t *testing.T, tr *WSTransport, msg Message) *httptest.ResponseRecorder {
	t.Helper()
	data, err := json.Marshal(msg)
	require.NoError(t, err)
	req := httptest.NewRequest(http.MethodPost, "/p2p", bytes.NewReader(data))
	// Synthetic certificate struct only: no private key or TLS handshake.
	req.TLS = &tls.ConnectionState{PeerCertificates: []*x509.Certificate{{Subject: pkix.Name{CommonName: msg.From}}}}
	rr := httptest.NewRecorder()
	tr.handleP2P(rr, req)
	return rr
}
func TestM2eNilSyncDoesNotAcknowledge(t *testing.T) {
	reg := peer.NewRegistry("local-fixture", time.Minute)
	tr := NewWSTransport(WSConfig{}, reg)
	payload, _ := json.Marshal(peer.SyncPayload{FromPeerID: "remote-fixture", Facts: []peer.SyncFact{{ID: "one", Content: "fixture", Level: 0}}})
	rr := m2eRequest(t, tr, Message{Type: "sync", From: "remote-fixture", Payload: payload})
	require.NotEqual(t, http.StatusOK, rr.Code)
	require.NotContains(t, rr.Body.String(), "accepted")
}
func TestM2eMissingDeltaHandlerDoesNotClaimComplete(t *testing.T) {
	reg := peer.NewRegistry("local-fixture", time.Minute)
	tr := NewWSTransport(WSConfig{}, reg)
	payload, _ := json.Marshal(peer.DeltaSyncRequest{FromPeerID: "remote-fixture", MaxBatch: 1})
	rr := m2eRequest(t, tr, Message{Type: "delta_sync_req", From: "remote-fixture", Payload: payload})
	require.NotEqual(t, http.StatusOK, rr.Code)
	require.NotContains(t, rr.Body.String(), "has_more")
}
func TestM2eCancelledSendPropagatesContext(t *testing.T) {
	reg := peer.NewRegistry("local-fixture", time.Minute)
	tr := NewWSTransport(WSConfig{}, reg)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	err := tr.SendSync(ctx, "127.0.0.1:1", peer.SyncPayload{FromPeerID: reg.SelfID()})
	require.True(t, errors.Is(err, context.Canceled), "cancelled context must be returned, got %v", err)
}
