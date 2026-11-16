package transport

import (
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

type m2eRoundTrip func(*http.Request) (*http.Response, error)

func (f m2eRoundTrip) RoundTrip(req *http.Request) (*http.Response, error) { return f(req) }
func m2eFakeTransport(t *testing.T, rt m2eRoundTrip) (*WSTransport, peer.SyncPayload, string) {
	t.Helper()
	reg := peer.NewRegistry("sender-fixture", time.Minute)
	tr := NewWSTransport(WSConfig{}, reg)
	// Synthetic test callback only. There is no production verifier or setter.
	tr.verifyPeer = func(state *tls.ConnectionState, expected string) error {
		if state == nil || expected != "receiver-fixture" {
			return errors.New("unverified synthetic peer")
		}
		return nil
	}
	tr.expectedPeerID = "receiver-fixture"
	tr.roundTripper = rt
	payload := peer.SyncPayload{FromPeerID: reg.SelfID(), Facts: []peer.SyncFact{{ID: "one", Content: "fixture", Level: 0}}}
	data, err := json.Marshal(payload)
	require.NoError(t, err)
	digest := fmt.Sprintf("%x", sha256.Sum256(data))
	return tr, payload, digest
}
func m2eFakeResponse(body string) *http.Response {
	return &http.Response{StatusCode: http.StatusOK, Header: make(http.Header), Body: io.NopCloser(strings.NewReader(body)), TLS: &tls.ConnectionState{}}
}
func TestM2eVerifiedHandlerRequiresDurableReceipt(t *testing.T) {
	reg := peer.NewRegistry("receiver-fixture", time.Minute)
	tr := NewWSTransport(WSConfig{}, reg)
	tr.verifyPeer = func(state *tls.ConnectionState, expected string) error {
		if state == nil || expected != "sender-fixture" {
			return errors.New("bad peer")
		}
		return nil
	}
	payload, _ := json.Marshal(peer.SyncPayload{FromPeerID: "sender-fixture", Facts: []peer.SyncFact{{ID: "one", Content: "fixture", Level: 0}}})
	msg := Message{Type: "sync", From: "sender-fixture", Payload: payload}
	rr := m2eRequest(t, tr, msg)
	require.Equal(t, http.StatusServiceUnavailable, rr.Code)
	require.NotContains(t, rr.Body.String(), "accepted")
	invoked := false
	tr.OnSync(func(peer.SyncPayload) error { invoked = true; return nil })
	rr = m2eRequest(t, tr, msg)
	require.Equal(t, http.StatusServiceUnavailable, rr.Code)
	require.False(t, invoked)
	require.NotContains(t, rr.Body.String(), "accepted")
	payload, _ = json.Marshal(peer.DeltaSyncRequest{FromPeerID: "sender-fixture", MaxBatch: 1})
	rr = m2eRequest(t, tr, Message{Type: "delta_sync_req", From: "sender-fixture", Payload: payload})
	require.Equal(t, http.StatusServiceUnavailable, rr.Code)
	require.NotContains(t, rr.Body.String(), "has_more")
}
func TestM2eSyncRequiresBoundPeerTypeCountAndRequestDigest(t *testing.T) {
	tr, payload, digest := m2eFakeTransport(t, nil)
	cases := []struct {
		name, body string
		ok         bool
	}{
		{"complete", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":1,"request_sha256":"%s"}}`, digest), true},
		{"type", fmt.Sprintf(`{"type":"pong","from":"receiver-fixture","payload":{"accepted":1,"request_sha256":"%s"}}`, digest), false},
		{"peer", fmt.Sprintf(`{"type":"sync","from":"other","payload":{"accepted":1,"request_sha256":"%s"}}`, digest), false},
		{"count", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":0,"request_sha256":"%s"}}`, digest), false},
		{"missing_count", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"request_sha256":"%s"}}`, digest), false},
		{"null_count", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":null,"request_sha256":"%s"}}`, digest), false},
		{"digest", `{"type":"sync","from":"receiver-fixture","payload":{"accepted":1,"request_sha256":"wrong"}}`, false},
		{"duplicate_count", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":0,"accepted":1,"request_sha256":"%s"}}`, digest), false},
		{"duplicate_type", fmt.Sprintf(`{"type":"bad","type":"sync","from":"receiver-fixture","payload":{"accepted":1,"request_sha256":"%s"}}`, digest), false},
		{"case_alias", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","From":"receiver-fixture","payload":{"accepted":1,"request_sha256":"%s"}}`, digest), false},
		{"invalid_utf8", string([]byte{'{', '"', 't', 'y', 'p', 'e', '"', ':', '"', 0xff, '"', '}'}), false},
		{"extra_failure", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":1,"request_sha256":"%s","failed":1}}`, digest), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			tr.roundTripper = m2eRoundTrip(func(*http.Request) (*http.Response, error) { return m2eFakeResponse(tc.body), nil })
			err := tr.SendSync(context.Background(), "fixture.invalid", payload)
			if tc.ok {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
}

func TestM2eRedirectNeverDispatchesSecondRequest(t *testing.T) {
	calls := 0
	tr, payload, _ := m2eFakeTransport(t, m2eRoundTrip(func(*http.Request) (*http.Response, error) {
		calls++
		response := m2eFakeResponse("")
		response.StatusCode = http.StatusFound
		response.Header.Set("Location", "https://redirect.invalid/p2p")
		return response, nil
	}))
	require.Error(t, tr.SendSync(context.Background(), "fixture.invalid", payload))
	require.Equal(t, 1, calls)
}

func TestM2eIncomingFieldAliasesAndInvalidUTF8Rejected(t *testing.T) {
	_, err := uniqueObject([]byte(`{"from":"a","From":"a"}`))
	require.Error(t, err)
	_, err = uniqueObject([]byte{'{', '"', 'x', '"', ':', '"', 0xff, '"', '}'})
	require.Error(t, err)
}

type m2eBlockingBody struct {
	ctx     context.Context
	started chan struct{}
}

func (body *m2eBlockingBody) Read(_ []byte) (int, error) {
	close(body.started)
	<-body.ctx.Done()
	return 0, body.ctx.Err()
}
func (body *m2eBlockingBody) Close() error { return nil }

func TestM2eCancellationWhileReadingResponse(t *testing.T) {
	started := make(chan struct{})
	tr, payload, _ := m2eFakeTransport(t, m2eRoundTrip(func(req *http.Request) (*http.Response, error) {
		response := m2eFakeResponse("")
		response.Body = &m2eBlockingBody{ctx: req.Context(), started: started}
		return response, nil
	}))
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	defer cancel()
	go func() { done <- tr.SendSync(ctx, "fixture.invalid", payload) }()
	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("response reader did not start")
	}
	cancel()
	select {
	case err := <-done:
		require.ErrorIs(t, err, context.Canceled)
	case <-time.After(time.Second):
		t.Fatal("response read ignored cancellation")
	}
}
func TestM2eCancellationWhileRequestInFlight(t *testing.T) {
	started := make(chan struct{})
	tr, payload, _ := m2eFakeTransport(t, m2eRoundTrip(func(req *http.Request) (*http.Response, error) {
		close(started)
		<-req.Context().Done()
		return nil, req.Context().Err()
	}))
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- tr.SendSync(ctx, "fixture.invalid", payload) }()
	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("request did not start")
	}
	cancel()
	select {
	case err := <-done:
		require.ErrorIs(t, err, context.Canceled)
	case <-time.After(time.Second):
		t.Fatal("cancellation did not reach request")
	}
}
func TestM2eUnverifiedResponseAndPayloadMismatchFailClosed(t *testing.T) {
	tr, payload, _ := m2eFakeTransport(t, m2eRoundTrip(func(*http.Request) (*http.Response, error) {
		r := m2eFakeResponse(`{"type":"sync","from":"receiver-fixture","payload":{"accepted":0}}`)
		r.TLS = nil
		return r, nil
	}))
	require.Error(t, tr.SendSync(context.Background(), "fixture.invalid", payload))
	payload.FromPeerID = "other"
	require.Error(t, tr.SendSync(context.Background(), "fixture.invalid", payload))
}

func TestM2eDeltaRequiresExplicitBoundCompleteResponse(t *testing.T) {
	tr, _, _ := m2eFakeTransport(t, nil)
	request := peer.DeltaSyncRequest{FromPeerID: tr.registry.SelfID(), GenomeHash: "fixture-hash", MaxBatch: 1}
	data, err := json.Marshal(request)
	require.NoError(t, err)
	digest := fmt.Sprintf("%x", sha256.Sum256(data))
	cases := []struct {
		name, body string
		ok         bool
	}{
		{"complete", fmt.Sprintf(`{"type":"delta_sync_res","from":"receiver-fixture","payload":{"from_peer_id":"receiver-fixture","genome_hash":"fixture-hash","facts":[],"synced_at":"2026-01-01T00:00:00Z","has_more":false,"request_sha256":"%s"}}`, digest), true},
		{"missing_has_more", fmt.Sprintf(`{"type":"delta_sync_res","from":"receiver-fixture","payload":{"from_peer_id":"receiver-fixture","genome_hash":"fixture-hash","facts":[],"synced_at":"2026-01-01T00:00:00Z","request_sha256":"%s"}}`, digest), false},
		{"wrong_peer", fmt.Sprintf(`{"type":"delta_sync_res","from":"receiver-fixture","payload":{"from_peer_id":"other","genome_hash":"fixture-hash","facts":[],"synced_at":"2026-01-01T00:00:00Z","has_more":false,"request_sha256":"%s"}}`, digest), false},
		{"wrong_type", fmt.Sprintf(`{"type":"sync","from":"receiver-fixture","payload":{"from_peer_id":"receiver-fixture","genome_hash":"fixture-hash","facts":[],"synced_at":"2026-01-01T00:00:00Z","has_more":false,"request_sha256":"%s"}}`, digest), false},
		{"over_count", fmt.Sprintf(`{"type":"delta_sync_res","from":"receiver-fixture","payload":{"from_peer_id":"receiver-fixture","genome_hash":"fixture-hash","facts":[{},{}],"synced_at":"2026-01-01T00:00:00Z","has_more":false,"request_sha256":"%s"}}`, digest), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			tr.roundTripper = m2eRoundTrip(func(*http.Request) (*http.Response, error) { return m2eFakeResponse(tc.body), nil })
			_, err := tr.SendDeltaSync(context.Background(), "fixture.invalid", request)
			if tc.ok {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
}

func TestM2eOversizedResponseIsRejected(t *testing.T) {
	tr, payload, _ := m2eFakeTransport(t, m2eRoundTrip(func(*http.Request) (*http.Response, error) {
		return m2eFakeResponse(strings.Repeat("a", 64*1024+1)), nil
	}))
	require.Error(t, tr.SendSync(context.Background(), "fixture.invalid", payload))
}

func TestM2eSyntheticPingRequiresPeerAndPong(t *testing.T) {
	cases := []struct {
		name, body string
		ok         bool
	}{
		{"pong", `{"type":"pong","from":"receiver-fixture","payload":null}`, true},
		{"wrong_type", `{"type":"sync","from":"receiver-fixture","payload":null}`, false},
		{"wrong_peer", `{"type":"pong","from":"other","payload":null}`, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			tr, _, _ := m2eFakeTransport(t, m2eRoundTrip(func(*http.Request) (*http.Response, error) { return m2eFakeResponse(tc.body), nil }))
			id, err := tr.Ping(context.Background(), "fixture.invalid")
			if tc.ok {
				require.NoError(t, err)
				require.Equal(t, "receiver-fixture", id)
			} else {
				require.Error(t, err)
			}
		})
	}
}
