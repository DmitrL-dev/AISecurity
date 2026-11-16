// Package ipc provides localhost IPC transport for Virtual Swarm peer
// synchronization using Named Pipes (Windows) or Unix Domain Sockets.
// Zero external dependencies — uses Go standard `net` package.
package ipc

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"hash/fnv"
	"log"
	"net"
	"os"
	"runtime"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/domain/alert"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// pipePath returns the platform-specific IPC socket path.
func pipePath(rlmDir string) string {
	if runtime.GOOS == "windows" {
		return "sentinel_swarm_" + shortHash(rlmDir)
	}
	return rlmDir + "/swarm.sock"
}

func shortHash(s string) string {
	h := fnv.New32a()
	_, _ = h.Write([]byte(s))
	return fmt.Sprintf("%08x", h.Sum32())
}

// Message types for the IPC protocol.
const (
	MsgHandshake    = "handshake"
	MsgHandshakeAck = "handshake_ack"
	MsgSyncRequest  = "sync_request"
	MsgSyncPayload  = "sync_payload"
)

// Message is the wire format for IPC communication.
type Message struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
}

// SwarmTransport manages localhost IPC for peer synchronization.
type SwarmTransport struct {
	mu       sync.RWMutex
	rlmDir   string
	peerReg  *peer.Registry
	store    memory.FactStore
	alertBus *alert.Bus
	scope    rlmscope.Scope
	listener net.Listener
	active   bool
}

// NewSwarmTransport creates a new IPC transport.
func NewSwarmTransport(rlmDir string, reg *peer.Registry, store memory.FactStore, bus *alert.Bus) *SwarmTransport {
	return &SwarmTransport{
		rlmDir:   rlmDir,
		peerReg:  reg,
		store:    store,
		alertBus: bus,
		scope:    rlmscope.Default(),
	}
}

// WithScope binds swarm fact export/import to a tenant/project boundary.
func (t *SwarmTransport) WithScope(sc rlmscope.Scope) *SwarmTransport {
	t.scope = sc.Normalize()
	return t
}

// Listen starts the IPC server. Blocks until context is cancelled.
// Only one instance can listen at a time — the first one wins.
func (t *SwarmTransport) Listen(ctx context.Context) error {
	path := pipePath(t.rlmDir)

	// On Unix, remove stale socket file.
	if runtime.GOOS != "windows" {
		os.Remove(path)
	}

	ln, err := listen(path)
	if err != nil {
		// Another instance is already listening — that's OK.
		log.Printf("swarm: listen failed (another instance active?): %v", err)
		return nil
	}

	t.mu.Lock()
	t.listener = ln
	t.active = true
	t.mu.Unlock()

	t.emit(alert.SeverityInfo, fmt.Sprintf("Swarm IPC listening on %s", path))
	log.Printf("swarm: listening on %s", path)

	// Accept loop.
	go func() {
		<-ctx.Done()
		ln.Close()
	}()

	for {
		conn, err := ln.Accept()
		if err != nil {
			if ctx.Err() != nil {
				return nil // Context cancelled.
			}
			continue
		}
		go t.handleIncoming(ctx, conn)
	}
}

// Dial connects to a listening peer and performs handshake + sync.
// Returns true if sync was successful.
func (t *SwarmTransport) Dial(ctx context.Context) (bool, error) {
	path := pipePath(t.rlmDir)

	conn, err := dial(path)
	if err != nil {
		return false, nil // No peer listening — normal.
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(5 * time.Second))

	// Step 1: Send handshake.
	selfID := t.peerReg.SelfID()
	selfNode := t.peerReg.NodeName()
	genomeHash := memory.CompiledGenomeHash()

	req := peer.HandshakeRequest{
		FromPeerID: selfID,
		FromNode:   selfNode,
		GenomeHash: genomeHash,
		Timestamp:  time.Now().Unix(),
	}
	if err := t.sendMsg(conn, MsgHandshake, req); err != nil {
		return false, fmt.Errorf("swarm: send handshake: %w", err)
	}

	// Step 2: Read handshake response.
	msg, err := t.readMsg(conn)
	if err != nil {
		return false, fmt.Errorf("swarm: read handshake ack: %w", err)
	}
	if msg.Type != MsgHandshakeAck {
		return false, fmt.Errorf("swarm: unexpected message type: %s", msg.Type)
	}

	var resp peer.HandshakeResponse
	if err := json.Unmarshal(msg.Payload, &resp); err != nil {
		return false, fmt.Errorf("swarm: parse handshake ack: %w", err)
	}

	if !resp.Match {
		t.emit(alert.SeverityWarning,
			fmt.Sprintf("Swarm peer %s genome MISMATCH — rejected", resp.ToNode))
		return false, nil
	}

	// Step 3: Register peer via CompleteHandshake.
	t.peerReg.CompleteHandshake(resp, genomeHash)

	t.emit(alert.SeverityInfo,
		fmt.Sprintf("Swarm peer %s VERIFIED — syncing facts", resp.ToNode))

	// Step 4: Export our facts and send.
	facts, err := t.exportFacts(ctx)
	if err != nil {
		return false, fmt.Errorf("swarm: export facts: %w", err)
	}

	payload := peer.SyncPayload{
		FromPeerID: selfID,
		GenomeHash: genomeHash,
		Facts:      facts,
		SyncedAt:   time.Now(),
	}
	if err := t.sendMsg(conn, MsgSyncPayload, payload); err != nil {
		return false, fmt.Errorf("swarm: send sync: %w", err)
	}

	t.emit(alert.SeverityInfo,
		fmt.Sprintf("Swarm sync complete — sent %d facts to %s", len(facts), resp.ToNode))
	return true, nil
}

// handleIncoming processes an incoming peer connection.
func (t *SwarmTransport) handleIncoming(ctx context.Context, conn net.Conn) {
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(5 * time.Second))

	// Step 1: Read handshake.
	msg, err := t.readMsg(conn)
	if err != nil {
		return
	}
	if msg.Type != MsgHandshake {
		return
	}

	var req peer.HandshakeRequest
	if err := json.Unmarshal(msg.Payload, &req); err != nil {
		return
	}

	// Step 2: Verify genome.
	ourHash := memory.CompiledGenomeHash()
	match := req.GenomeHash == ourHash

	resp := peer.HandshakeResponse{
		ToPeerID:   req.FromPeerID,
		ToNode:     t.peerReg.NodeName(),
		GenomeHash: ourHash,
		Match:      match,
		Trust:      peer.TrustVerified,
		Timestamp:  time.Now().Unix(),
	}
	if !match {
		resp.Trust = peer.TrustRejected
	}

	t.sendMsg(conn, MsgHandshakeAck, resp)

	if !match {
		t.emit(alert.SeverityWarning,
			fmt.Sprintf("Swarm: rejected peer %s (genome mismatch)", req.FromNode))
		return
	}

	// Register peer.
	t.peerReg.ProcessHandshake(req, ourHash)

	t.emit(alert.SeverityInfo,
		fmt.Sprintf("Swarm: accepted peer %s (VERIFIED)", req.FromNode))

	// Step 3: Read sync payload.
	msg, err = t.readMsg(conn)
	if err != nil {
		return
	}
	if msg.Type != MsgSyncPayload {
		return
	}

	var payload peer.SyncPayload
	if err := json.Unmarshal(msg.Payload, &payload); err != nil {
		return
	}

	// Step 4: Import facts.
	imported := t.importFacts(ctx, payload.Facts)
	t.emit(alert.SeverityInfo,
		fmt.Sprintf("Swarm: imported %d facts from %s", imported, req.FromNode))
}

// IsListening returns true if this transport is the active listener.
func (t *SwarmTransport) IsListening() bool {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.active
}

// --- Wire protocol helpers ---

func (t *SwarmTransport) sendMsg(conn net.Conn, msgType string, payload interface{}) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	msg := Message{Type: msgType, Payload: data}
	line, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	line = append(line, '\n')
	_, err = conn.Write(line)
	return err
}

func (t *SwarmTransport) readMsg(conn net.Conn) (*Message, error) {
	scanner := bufio.NewScanner(conn)
	if !scanner.Scan() {
		if err := scanner.Err(); err != nil {
			return nil, err
		}
		return nil, fmt.Errorf("connection closed")
	}
	var msg Message
	if err := json.Unmarshal(scanner.Bytes(), &msg); err != nil {
		return nil, err
	}
	return &msg, nil
}

// --- Fact export/import ---

func (t *SwarmTransport) exportFacts(ctx context.Context) ([]peer.SyncFact, error) {
	ctx = rlmscope.WithScope(ctx, t.scope)
	facts, err := t.store.ListByLevel(ctx, memory.LevelProject)
	if err != nil {
		return nil, err
	}

	var syncFacts []peer.SyncFact
	for _, f := range facts {
		syncFacts = append(syncFacts, peer.SyncFact{
			ID:        f.ID,
			Content:   f.Content,
			Level:     int(f.Level),
			Domain:    f.Domain,
			Module:    f.Module,
			IsGene:    f.IsGene,
			Source:    f.Source,
			CreatedAt: f.CreatedAt,
		})
	}
	return syncFacts, nil
}

func (t *SwarmTransport) importFacts(ctx context.Context, facts []peer.SyncFact) int {
	ctx = rlmscope.WithScope(ctx, t.scope)
	imported := 0
	for _, sf := range facts {
		// Skip if fact already exists.
		if _, err := t.store.Get(ctx, sf.ID); err == nil {
			continue
		}
		fact := memory.NewFact(sf.Content, memory.HierLevel(sf.Level), sf.Domain, sf.Module)
		fact.ID = sf.ID
		fact.Source = "swarm:" + sf.Source
		// External unconditionally: same reasoning as the peer-sync importer in mcpserver. What
		// the sending node says about its own fact is not evidence about that fact.
		fact.Origin = memory.OriginExternal
		fact.IsGene = sf.IsGene
		if err := t.store.Add(ctx, fact); err == nil {
			imported++
		}
	}
	return imported
}

func (t *SwarmTransport) emit(severity alert.Severity, message string) {
	if t.alertBus != nil {
		t.alertBus.Emit(alert.New(alert.SourceSystem, severity, message, 0))
	}
}
