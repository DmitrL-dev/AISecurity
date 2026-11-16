package transport

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/syntrex/gomcp/internal/domain/peer"
)

// WSTransport provides WebSocket-based P2P communication (v3.5).
// Enables real-time fact sync between GoMCP instances.
type WSTransport struct {
	mu       sync.RWMutex
	registry *peer.Registry
	listener net.Listener
	port     int
	running  bool
	onSync   func(payload peer.SyncPayload) error // Callback for incoming syncs
	tlsCfg   *tls.Config                          // SEC-V7-2: Cached mTLS config
	// No production configuration supplies these: the legacy certificate CN
	// is not a trust anchor. Internal synthetic tests may provide fakes.
	verifyPeer     func(*tls.ConnectionState, string) error
	expectedPeerID string
	roundTripper   http.RoundTripper
}

var ErrPeerVerifierUnavailable = errors.New("authenticated peer verifier unavailable")

// WSConfig holds WebSocket transport configuration.
type WSConfig struct {
	Port    int    `json:"port"`    // Listen port (default: 9741)
	Host    string `json:"host"`    // Bind address (default: localhost)
	Enabled bool   `json:"enabled"` // Enable WebSocket transport
}

// NewWSTransport creates a new WebSocket transport.
func NewWSTransport(cfg WSConfig, reg *peer.Registry) *WSTransport {
	if cfg.Port < 0 {
		cfg.Port = 9741
	}
	if cfg.Host == "" {
		cfg.Host = "localhost"
	}
	return &WSTransport{
		registry: reg,
		port:     cfg.Port,
	}
}

// OnSync registers a callback for incoming sync payloads.
func (t *WSTransport) OnSync(fn func(peer.SyncPayload) error) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.onSync = fn
}

// Message is the wire protocol for P2P communication.
type Message struct {
	Type    string          `json:"type"`    // "handshake", "sync", "delta_sync_req", "delta_sync_res", "ping", "pong"
	Payload json.RawMessage `json:"payload"` // Type-specific data
	From    string          `json:"from"`    // Sender peer ID
	SentAt  time.Time       `json:"sent_at"`
}

// maxP2PBodyBytes caps the request body handleP2P will buffer when decoding an
// inbound peer Message. mTLS here is RequireAnyClientCert + InsecureSkipVerify,
// so any peer presenting a (trivially self-signed) cert can reach the decoder;
// an unbounded json.Decode on r.Body is therefore a remote memory-DoS vector.
// 16 MiB comfortably fits a full L0-L1 fact sync while bounding allocation.
const maxP2PBodyBytes int64 = 16 << 20

// Start begins listening for WebSocket connections.
func (t *WSTransport) Start() error {
	t.mu.RLock()
	verify := t.verifyPeer
	t.mu.RUnlock()
	if verify == nil {
		return ErrPeerVerifierUnavailable
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/p2p", t.handleP2P)
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status":"ok","peer_id":"%s","node":"%s"}`, t.registry.SelfID(), t.registry.NodeName())
	})

	addr := fmt.Sprintf("localhost:%d", t.port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("ws listen %s: %w", addr, err)
	}

	// SEC-V7-1: Upgrade P2P TCP socket to Mutual TLS to protect AI memory synced between peers.
	cert, err := GenerateSelfSignedCert(t.registry.SelfID())
	if err != nil {
		return fmt.Errorf("generate mtls cert: %w", err)
	}
	tlsConfig := NewMutualTLSConfig(cert)
	tlsListener := tls.NewListener(listener, tlsConfig)

	t.mu.Lock()
	t.listener = tlsListener
	t.tlsCfg = tlsConfig
	t.running = true
	t.mu.Unlock()

	log.Printf("ws-transport: listening on %s (peer=%s)", addr, t.registry.SelfID())

	go func() {
		srv := &http.Server{Handler: mux}
		if err := srv.Serve(tlsListener); err != nil && t.isRunning() {
			log.Printf("ws-transport: serve error: %v", err)
		}
	}()

	return nil
}

// handleP2P handles incoming WebSocket-like HTTP connections.
// Uses simple HTTP POST for compatibility (true WebSocket upgrade optional in v3.6).
func (t *WSTransport) handleP2P(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	t.mu.RLock()
	verify := t.verifyPeer
	t.mu.RUnlock()
	if verify == nil {
		http.Error(w, "authenticated peer verifier unavailable", http.StatusServiceUnavailable)
		return
	}

	// Bound the inbound body before decoding — an untrusted peer must not be
	// able to force an unbounded allocation (memory-DoS) via a huge POST body.
	r.Body = http.MaxBytesReader(w, r.Body, maxP2PBodyBytes)

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "invalid message", http.StatusBadRequest)
		return
	}
	if _, err := uniqueObject(body); err != nil {
		http.Error(w, "invalid message", http.StatusBadRequest)
		return
	}
	var msg Message
	if err := json.Unmarshal(body, &msg); err != nil {
		http.Error(w, "invalid message", http.StatusBadRequest)
		return
	}

	// A certificate CN alone is not an authenticated peer identity.
	if r.TLS == nil || len(r.TLS.PeerCertificates) == 0 {
		http.Error(w, "missing p2p mtls certificate", http.StatusUnauthorized)
		return
	}
	verifiedPeerID := r.TLS.PeerCertificates[0].Subject.CommonName
	if msg.From != verifiedPeerID {
		log.Printf("SEC-V7 CRITICAL: P2P spoofing detected! Claimed: %s, Verified TLS: %s", msg.From, verifiedPeerID)
		http.Error(w, "spoofed identity", http.StatusUnauthorized)
		return
	}
	if err := verify(r.TLS, msg.From); err != nil {
		http.Error(w, "peer identity unverified", http.StatusUnauthorized)
		return
	}

	w.Header().Set("Content-Type", "application/json")

	switch msg.Type {
	case "ping":
		resp := Message{Type: "pong", From: t.registry.SelfID(), SentAt: time.Now()}
		json.NewEncoder(w).Encode(resp)

	case "handshake":
		if _, err := uniqueObject(msg.Payload); err != nil {
			http.Error(w, "invalid handshake payload", http.StatusBadRequest)
			return
		}
		var req peer.HandshakeRequest
		if err := json.Unmarshal(msg.Payload, &req); err != nil || req.FromPeerID != msg.From {
			http.Error(w, "invalid handshake peer reference", http.StatusBadRequest)
			return
		}
		// This only reports receipt; it does not promote a peer or complete trust.
		respData, _ := json.Marshal(map[string]string{"status": "received", "peer_id": t.registry.SelfID()})
		resp := Message{Type: "handshake", From: t.registry.SelfID(), Payload: respData, SentAt: time.Now()}
		json.NewEncoder(w).Encode(resp)

	case "sync":
		if _, err := uniqueObject(msg.Payload); err != nil {
			http.Error(w, "invalid sync payload", http.StatusBadRequest)
			return
		}
		var payload peer.SyncPayload
		if err := json.Unmarshal(msg.Payload, &payload); err != nil {
			http.Error(w, "invalid sync payload", http.StatusBadRequest)
			return
		}
		if payload.FromPeerID != msg.From {
			http.Error(w, "peer reference mismatch", http.StatusBadRequest)
			return
		}
		t.mu.RLock()
		handler := t.onSync
		t.mu.RUnlock()
		if handler == nil {
			http.Error(w, "sync handler unavailable", http.StatusServiceUnavailable)
			return
		}
		// The legacy callback returns only error and cannot attest per-fact
		// persistence or an exact accepted count. Do not call it or forge an ACK.
		http.Error(w, "verified sync receipt unavailable", http.StatusServiceUnavailable)

	case "delta_sync_req":
		if _, err := uniqueObject(msg.Payload); err != nil {
			http.Error(w, "invalid delta sync request", http.StatusBadRequest)
			return
		}
		var req peer.DeltaSyncRequest
		if err := json.Unmarshal(msg.Payload, &req); err != nil {
			http.Error(w, "invalid delta sync request", http.StatusBadRequest)
			return
		}
		if req.FromPeerID != msg.From {
			http.Error(w, "delta peer reference mismatch", http.StatusBadRequest)
			return
		}
		http.Error(w, "delta sync handler unavailable", http.StatusServiceUnavailable)

	default:
		http.Error(w, "unknown message type", http.StatusBadRequest)
	}
}

// SendSync sends a sync payload to a remote peer via HTTP POST.
func (t *WSTransport) SendSync(ctx context.Context, addr string, payload peer.SyncPayload) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	msg := Message{
		Type:    "sync",
		From:    t.registry.SelfID(),
		Payload: data,
		SentAt:  time.Now(),
	}
	if payload.FromPeerID != t.registry.SelfID() {
		return fmt.Errorf("payload peer reference does not match local sender")
	}
	response, err := t.sendAndReceive(ctx, addr, msg)
	if err != nil {
		return err
	}
	if response.Type != "sync" {
		return fmt.Errorf("unexpected sync response type")
	}
	fields, err := uniqueObject(response.Payload)
	if err != nil {
		return fmt.Errorf("invalid sync acknowledgement")
	}
	if len(fields) != 2 {
		return fmt.Errorf("unexpected sync acknowledgement fields")
	}
	raw, ok := fields["accepted"]
	if !ok || string(raw) == "null" {
		return fmt.Errorf("missing accepted count")
	}
	var accepted int
	if json.Unmarshal(raw, &accepted) != nil || accepted != len(payload.Facts) {
		return fmt.Errorf("sync acknowledgement count mismatch")
	}
	rawDigest, ok := fields["request_sha256"]
	if !ok {
		return fmt.Errorf("missing sync request binding")
	}
	var receivedDigest string
	if json.Unmarshal(rawDigest, &receivedDigest) != nil || receivedDigest != fmt.Sprintf("%x", sha256.Sum256(data)) {
		return fmt.Errorf("sync request binding mismatch")
	}
	return nil
}

// SendDeltaSync sends a delta sync request to a remote peer.
func (t *WSTransport) SendDeltaSync(ctx context.Context, addr string, req peer.DeltaSyncRequest) (*peer.DeltaSyncResponse, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if req.FromPeerID != t.registry.SelfID() {
		return nil, fmt.Errorf("payload peer reference does not match local sender")
	}
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	msg := Message{
		Type:    "delta_sync_req",
		From:    t.registry.SelfID(),
		Payload: data,
		SentAt:  time.Now(),
	}

	respMsg, err := t.sendAndReceive(ctx, addr, msg)
	if err != nil {
		return nil, err
	}

	if respMsg.Type != "delta_sync_res" {
		return nil, fmt.Errorf("unexpected delta response type")
	}
	fields, err := uniqueObject(respMsg.Payload)
	if err != nil {
		return nil, fmt.Errorf("invalid delta response")
	}
	for _, name := range []string{"from_peer_id", "genome_hash", "facts", "synced_at", "has_more", "request_sha256"} {
		raw, ok := fields[name]
		if !ok || string(raw) == "null" {
			return nil, fmt.Errorf("incomplete delta response")
		}
	}
	if len(fields) != 6 {
		return nil, fmt.Errorf("unexpected delta response fields")
	}
	var responseDigest string
	if json.Unmarshal(fields["request_sha256"], &responseDigest) != nil || responseDigest != fmt.Sprintf("%x", sha256.Sum256(data)) {
		return nil, fmt.Errorf("delta request binding mismatch")
	}
	var resp peer.DeltaSyncResponse
	if err := json.Unmarshal(respMsg.Payload, &resp); err != nil {
		return nil, fmt.Errorf("decode delta response: %w", err)
	}
	t.mu.RLock()
	expected := t.expectedPeerID
	t.mu.RUnlock()
	if resp.FromPeerID != expected {
		return nil, fmt.Errorf("delta peer reference mismatch")
	}
	if resp.GenomeHash != req.GenomeHash {
		return nil, fmt.Errorf("delta genome mismatch")
	}
	maxBatch := req.MaxBatch
	if maxBatch <= 0 {
		maxBatch = 100
	}
	if len(resp.Facts) > maxBatch {
		return nil, fmt.Errorf("delta response exceeds requested batch")
	}
	return &resp, nil
}

// Ping checks if a remote peer is alive.
func (t *WSTransport) Ping(ctx context.Context, addr string) (peerID string, err error) {
	if err := ctx.Err(); err != nil {
		return "", err
	}
	msg := Message{Type: "ping", From: t.registry.SelfID(), SentAt: time.Now()}
	resp, err := t.sendAndReceive(ctx, addr, msg)
	if err != nil {
		return "", err
	}
	if resp.Type != "pong" {
		return "", fmt.Errorf("unexpected ping response type")
	}
	return resp.From, nil
}

// Stop shuts down the transport.
func (t *WSTransport) Stop() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.running = false
	if t.listener != nil {
		return t.listener.Close()
	}
	return nil
}

// Addr returns the listen address.
func (t *WSTransport) Addr() string {
	t.mu.RLock()
	defer t.mu.RUnlock()
	if t.listener != nil {
		return t.listener.Addr().String()
	}
	return ""
}

func (t *WSTransport) isRunning() bool {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.running
}

// uniqueObject rejects duplicate fields and trailing JSON on wire responses.
func uniqueObject(data []byte) (map[string]json.RawMessage, error) {
	if !utf8.Valid(data) {
		return nil, fmt.Errorf("invalid UTF-8")
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	first, err := decoder.Token()
	if err != nil || first != json.Delim('{') {
		return nil, fmt.Errorf("expected JSON object")
	}
	fields := make(map[string]json.RawMessage)
	for decoder.More() {
		token, err := decoder.Token()
		if err != nil {
			return nil, err
		}
		name, ok := token.(string)
		if !ok {
			return nil, fmt.Errorf("invalid field")
		}
		for _, ch := range name {
			if !(ch >= 'a' && ch <= 'z') && !(ch >= '0' && ch <= '9') && ch != '_' {
				return nil, fmt.Errorf("invalid field name")
			}
		}
		if _, exists := fields[name]; exists {
			return nil, fmt.Errorf("duplicate field")
		}
		var raw json.RawMessage
		if err := decoder.Decode(&raw); err != nil {
			return nil, err
		}
		fields[name] = raw
	}
	last, err := decoder.Token()
	if err != nil || last != json.Delim('}') {
		return nil, fmt.Errorf("invalid object end")
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); err != io.EOF {
		return nil, fmt.Errorf("trailing JSON")
	}
	return fields, nil
}

const maxP2PResponseBytes = 64 * 1024

func (t *WSTransport) sendAndReceive(ctx context.Context, addr string, msg Message) (*Message, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	t.mu.RLock()
	verify, expected, config, transport := t.verifyPeer, t.expectedPeerID, t.tlsCfg, t.roundTripper
	t.mu.RUnlock()
	if verify == nil || expected == "" {
		return nil, ErrPeerVerifierUnavailable
	}
	if addr == "" || strings.ContainsAny(addr, "/@?# \t\r\n") {
		return nil, fmt.Errorf("invalid peer address")
	}
	data, err := json.Marshal(msg)
	if err != nil {
		return nil, err
	}
	if transport == nil {
		if config == nil {
			config = &tls.Config{MinVersion: tls.VersionTLS13}
		} else {
			config = config.Clone()
		}
		previous := config.VerifyConnection
		config.VerifyConnection = func(state tls.ConnectionState) error {
			if previous != nil {
				if err := previous(state); err != nil {
					return err
				}
			}
			return verify(&state, expected)
		}
		transport = &http.Transport{TLSClientConfig: config}
	}
	client := &http.Client{
		Timeout:       10 * time.Second,
		Transport:     transport,
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
	}
	defer client.CloseIdleConnections()
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, fmt.Sprintf("https://%s/p2p", addr), jsonReader(data))
	if err != nil {
		return nil, fmt.Errorf("build peer request: %w", err)
	}
	request.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("peer request failed: %w", err)
	}
	defer resp.Body.Close()
	if err := verify(resp.TLS, expected); err != nil {
		return nil, fmt.Errorf("peer identity unverified")
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("peer request returned HTTP %d", resp.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, maxP2PResponseBytes+1))
	if err != nil {
		return nil, fmt.Errorf("read peer response: %w", err)
	}
	if len(body) > maxP2PResponseBytes {
		return nil, fmt.Errorf("peer response exceeds limit")
	}
	fields, err := uniqueObject(body)
	if err != nil {
		return nil, fmt.Errorf("invalid peer response")
	}
	for name := range fields {
		if name != "type" && name != "from" && name != "payload" && name != "sent_at" {
			return nil, fmt.Errorf("unexpected peer response field")
		}
	}
	var response Message
	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("invalid peer response")
	}
	if response.From != expected {
		return nil, fmt.Errorf("peer response identity mismatch")
	}
	return &response, nil
}

func jsonReader(data []byte) *jsonBody { return &jsonBody{data: data} }

type jsonBody struct {
	data []byte
	off  int
}

func (j *jsonBody) Read(p []byte) (n int, err error) {
	if j.off >= len(j.data) {
		return 0, io.EOF
	}
	n = copy(p, j.data[j.off:])
	j.off += n
	return n, nil
}
