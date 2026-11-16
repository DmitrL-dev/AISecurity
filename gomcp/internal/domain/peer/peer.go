// Package peer defines domain entities for Peer-to-Peer Genome Verification
// and Distributed Fact Synchronization (DIP H1: Synapse).
//
// Trust model:
//  1. Two GoMCP instances exchange Merkle genome hashes
//  2. If hashes match → TrustedPair (genome-compatible nodes)
//  3. TrustedPairs can sync L0-L1 facts bidirectionally
//  4. If a peer goes offline → its last delta is preserved as GeneBackup
//  5. On reconnect → GeneBackup is restored to the recovered peer
//
// This is NOT a network protocol. Peer communication happens at the MCP tool
// level: one instance exports a handshake/fact payload as JSON, and the other
// imports it via the corresponding tool. The human operator transfers data.
package peer

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"sync"
	"time"
)

// TrustLevel represents the trust state between two peers.
type TrustLevel int

const (
	TrustUnknown  TrustLevel = iota // Never seen
	TrustPending                    // Handshake initiated, awaiting response
	TrustVerified                   // Genome hashes match → trusted pair
	TrustRejected                   // Genome hashes differ → untrusted
	TrustExpired                    // Peer timed out
)

// String returns human-readable trust level.
func (t TrustLevel) String() string {
	switch t {
	case TrustUnknown:
		return "UNKNOWN"
	case TrustPending:
		return "PENDING"
	case TrustVerified:
		return "VERIFIED"
	case TrustRejected:
		return "REJECTED"
	case TrustExpired:
		return "EXPIRED"
	default:
		return "INVALID"
	}
}

// PeerInfo represents a known peer node.
type PeerInfo struct {
	PeerID      string     `json:"peer_id"`      // Unique peer identifier
	NodeName    string     `json:"node_name"`    // Human-readable node name
	GenomeHash  string     `json:"genome_hash"`  // Peer's reported genome Merkle hash
	Trust       TrustLevel `json:"trust"`        // Current trust level
	LastSeen    time.Time  `json:"last_seen"`    // Last successful communication
	LastSyncAt  time.Time  `json:"last_sync_at"` // Last fact sync timestamp
	FactCount   int        `json:"fact_count"`   // Number of facts synced from this peer
	HandshakeAt time.Time  `json:"handshake_at"` // When handshake was completed
}

// IsAlive returns true if the peer was seen within the given timeout.
func (p *PeerInfo) IsAlive(timeout time.Duration) bool {
	return time.Since(p.LastSeen) < timeout
}

// HandshakeRequest is sent by the initiating peer.
type HandshakeRequest struct {
	FromPeerID string `json:"from_peer_id"` // Sender's peer ID
	FromNode   string `json:"from_node"`    // Sender's node name
	GenomeHash string `json:"genome_hash"`  // Sender's compiled genome hash
	Timestamp  int64  `json:"timestamp"`    // Unix timestamp
	Nonce      string `json:"nonce"`        // Random nonce for freshness
}

// HandshakeResponse is returned by the receiving peer.
type HandshakeResponse struct {
	ToPeerID   string     `json:"to_peer_id"`  // Receiver's peer ID
	ToNode     string     `json:"to_node"`     // Receiver's node name
	GenomeHash string     `json:"genome_hash"` // Receiver's compiled genome hash
	Match      bool       `json:"match"`       // Whether genome hashes matched
	Trust      TrustLevel `json:"trust"`       // Resulting trust level
	Timestamp  int64      `json:"timestamp"`
}

// SyncPayload carries facts and incidents between trusted peers.
// Version field enables backward-compatible schema evolution (§10 T-01).
type SyncPayload struct {
	Version    string         `json:"version,omitempty"` // Payload schema version (e.g., "1.0", "1.1")
	FromPeerID string         `json:"from_peer_id"`
	GenomeHash string         `json:"genome_hash"` // For verification at import
	Facts      []SyncFact     `json:"facts"`
	Incidents  []SyncIncident `json:"incidents,omitempty"` // §10 T-01: P2P incident sync
	SyncedAt   time.Time      `json:"synced_at"`
}

// SyncFact is a portable representation of a memory fact for peer sync.
type SyncFact struct {
	ID        string    `json:"id"`
	Content   string    `json:"content"`
	Level     int       `json:"level"`
	Domain    string    `json:"domain,omitempty"`
	Module    string    `json:"module,omitempty"`
	IsGene    bool      `json:"is_gene"`
	Source    string    `json:"source"`
	CreatedAt time.Time `json:"created_at"`
}

// SyncIncident is a portable representation of an SOC incident for P2P sync (§10 T-01).
type SyncIncident struct {
	ID              string    `json:"id"`
	Status          string    `json:"status"`
	Severity        string    `json:"severity"`
	Title           string    `json:"title"`
	Description     string    `json:"description"`
	EventCount      int       `json:"event_count"`
	CorrelationRule string    `json:"correlation_rule"`
	KillChainPhase  string    `json:"kill_chain_phase"`
	MITREMapping    []string  `json:"mitre_mapping,omitempty"`
	CreatedAt       time.Time `json:"created_at"`
	SourcePeerID    string    `json:"source_peer_id"` // Which peer created it
}

// GeneBackup stores the last known state of a fallen peer for recovery.
type GeneBackup struct {
	PeerID     string     `json:"peer_id"`
	GenomeHash string     `json:"genome_hash"`
	Facts      []SyncFact `json:"facts"`
	BackedUpAt time.Time  `json:"backed_up_at"`
	Reason     string     `json:"reason"` // "timeout", "explicit", etc.
}

// PeerStore is a persistence interface for peer data (v3.4).
type PeerStore interface {
	SavePeer(ctx context.Context, p *PeerInfo) error
	LoadPeers(ctx context.Context) ([]*PeerInfo, error)
	DeleteExpired(ctx context.Context, olderThan time.Duration) (int, error)
}

// Registry manages known peers and their trust states.
type Registry struct {
	mu      sync.RWMutex
	selfID  string
	node    string
	peers   map[string]*PeerInfo
	backups map[string]*GeneBackup // peerID → backup
	timeout time.Duration
	store   PeerStore // v3.4: optional persistent store
}

// NewRegistry creates a new peer registry.
func NewRegistry(nodeName string, peerTimeout time.Duration) *Registry {
	if peerTimeout <= 0 {
		peerTimeout = 30 * time.Minute
	}
	return &Registry{
		selfID:  generatePeerID(),
		node:    nodeName,
		peers:   make(map[string]*PeerInfo),
		backups: make(map[string]*GeneBackup),
		timeout: peerTimeout,
	}
}

// SelfID returns this node's peer ID.
func (r *Registry) SelfID() string {
	return r.selfID
}

// NodeName returns this node's name.
func (r *Registry) NodeName() string {
	return r.node
}

// SetStore enables persistent peer storage (v3.4).
func (r *Registry) SetStore(s PeerStore) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store = s
}

// LoadFromStore hydrates in-memory peer map from persistent storage.
func (r *Registry) LoadFromStore(ctx context.Context) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.store == nil {
		return nil
	}
	peers, err := r.store.LoadPeers(ctx)
	if err != nil {
		return err
	}
	for _, p := range peers {
		r.peers[p.PeerID] = p
	}
	return nil
}

// PersistPeer saves a single peer to the store (if available).
func (r *Registry) PersistPeer(ctx context.Context, peerID string) {
	r.mu.RLock()
	p, ok := r.peers[peerID]
	store := r.store
	r.mu.RUnlock()
	if !ok || store == nil {
		return
	}
	_ = store.SavePeer(ctx, p)
}

// CleanExpiredPeers removes peers not seen within TTL from store.
func (r *Registry) CleanExpiredPeers(ctx context.Context, ttl time.Duration) int {
	r.mu.Lock()
	store := r.store
	r.mu.Unlock()
	if store == nil {
		return 0
	}
	n, _ := store.DeleteExpired(ctx, ttl)
	return n
}

// Errors.
var (
	ErrPeerNotFound  = errors.New("peer not found")
	ErrNotTrusted    = errors.New("peer not trusted (genome hash mismatch)")
	ErrSelfHandshake = errors.New("cannot handshake with self")
	ErrHashMismatch  = errors.New("genome hash mismatch on import")
)

// ProcessHandshake handles an incoming handshake request.
// Returns a response indicating whether the peer is trusted.
func (r *Registry) ProcessHandshake(req HandshakeRequest, localHash string) (*HandshakeResponse, error) {
	if req.FromPeerID == r.selfID {
		return nil, ErrSelfHandshake
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	match := req.GenomeHash == localHash
	trust := TrustRejected
	if match {
		trust = TrustVerified
	}

	now := time.Now()
	r.peers[req.FromPeerID] = &PeerInfo{
		PeerID:      req.FromPeerID,
		NodeName:    req.FromNode,
		GenomeHash:  req.GenomeHash,
		Trust:       trust,
		LastSeen:    now,
		HandshakeAt: now,
	}

	return &HandshakeResponse{
		ToPeerID:   r.selfID,
		ToNode:     r.node,
		GenomeHash: localHash,
		Match:      match,
		Trust:      trust,
		Timestamp:  now.Unix(),
	}, nil
}

// CompleteHandshake processes a handshake response (initiator side).
func (r *Registry) CompleteHandshake(resp HandshakeResponse, localHash string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	match := resp.GenomeHash == localHash
	trust := TrustRejected
	if match {
		trust = TrustVerified
	}

	now := time.Now()
	r.peers[resp.ToPeerID] = &PeerInfo{
		PeerID:      resp.ToPeerID,
		NodeName:    resp.ToNode,
		GenomeHash:  resp.GenomeHash,
		Trust:       trust,
		LastSeen:    now,
		HandshakeAt: now,
	}
	return nil
}

// IsTrusted checks if a peer is a verified trusted pair.
func (r *Registry) IsTrusted(peerID string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()

	p, ok := r.peers[peerID]
	if !ok {
		return false
	}
	return p.Trust == TrustVerified
}

// GetPeer returns info about a known peer.
func (r *Registry) GetPeer(peerID string) (*PeerInfo, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	p, ok := r.peers[peerID]
	if !ok {
		return nil, ErrPeerNotFound
	}
	cp := *p
	return &cp, nil
}

// ListPeers returns all known peers.
func (r *Registry) ListPeers() []*PeerInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]*PeerInfo, 0, len(r.peers))
	for _, p := range r.peers {
		cp := *p
		result = append(result, &cp)
	}
	return result
}

// RecordSync updates the sync timestamp for a peer.
func (r *Registry) RecordSync(peerID string, factCount int) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	p, ok := r.peers[peerID]
	if !ok {
		return ErrPeerNotFound
	}
	p.LastSyncAt = time.Now()
	p.LastSeen = p.LastSyncAt
	p.FactCount += factCount
	return nil
}

// TouchPeer updates the LastSeen timestamp.
func (r *Registry) TouchPeer(peerID string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if p, ok := r.peers[peerID]; ok {
		p.LastSeen = time.Now()
	}
}

// CheckTimeouts marks timed-out peers as expired and creates backups.
func (r *Registry) CheckTimeouts(facts []SyncFact) []GeneBackup {
	r.mu.Lock()
	defer r.mu.Unlock()

	var newBackups []GeneBackup
	for _, p := range r.peers {
		if p.Trust == TrustVerified && !p.IsAlive(r.timeout) {
			p.Trust = TrustExpired

			backup := GeneBackup{
				PeerID:     p.PeerID,
				GenomeHash: p.GenomeHash,
				Facts:      facts, // Current node's facts as recovery data
				BackedUpAt: time.Now(),
				Reason:     "timeout",
			}
			r.backups[p.PeerID] = &backup
			newBackups = append(newBackups, backup)
		}
	}
	return newBackups
}

// GetBackup returns the gene backup for a peer, if any.
func (r *Registry) GetBackup(peerID string) (*GeneBackup, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	b, ok := r.backups[peerID]
	if !ok {
		return nil, false
	}
	cp := *b
	return &cp, true
}

// ClearBackup removes a backup after successful recovery.
func (r *Registry) ClearBackup(peerID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.backups, peerID)
}

// PeerCount returns the number of known peers.
func (r *Registry) PeerCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.peers)
}

// TrustedCount returns the number of verified trusted peers.
func (r *Registry) TrustedCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	count := 0
	for _, p := range r.peers {
		if p.Trust == TrustVerified {
			count++
		}
	}
	return count
}

// Stats returns aggregate peer statistics.
func (r *Registry) Stats() map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	byTrust := make(map[string]int)
	for _, p := range r.peers {
		byTrust[p.Trust.String()]++
	}

	return map[string]interface{}{
		"self_id":       r.selfID,
		"node_name":     r.node,
		"total_peers":   len(r.peers),
		"by_trust":      byTrust,
		"total_backups": len(r.backups),
	}
}

func generatePeerID() string {
	b := make([]byte, 12)
	_, _ = rand.Read(b)
	return fmt.Sprintf("peer_%s", hex.EncodeToString(b))
}
