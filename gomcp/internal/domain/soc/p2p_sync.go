package soc

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// P2PSyncService implements §14 — SOC-to-SOC event synchronization over P2P mesh.
// Enables multi-site SOC deployments to share events, incidents, and IOCs.
type P2PSyncService struct {
	mu      sync.RWMutex
	peers   map[string]*SOCPeer
	outbox  []SyncMessage
	inbox   []SyncMessage
	maxBuf  int
	enabled bool
}

// SOCPeer represents a connected SOC peer node.
type SOCPeer struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Endpoint    string    `json:"endpoint"`
	Status      string    `json:"status"` // connected, disconnected, syncing
	LastSync    time.Time `json:"last_sync"`
	EventsSent  int       `json:"events_sent"`
	EventsRecv  int       `json:"events_recv"`
	TrustLevel  string    `json:"trust_level"` // full, partial, readonly
}

// SyncMessage is a SOC data unit exchanged between peers.
type SyncMessage struct {
	ID        string          `json:"id"`
	Type      SyncMessageType `json:"type"`
	PeerID    string          `json:"peer_id"`
	Payload   json.RawMessage `json:"payload"`
	Timestamp time.Time       `json:"timestamp"`
}

// SyncMessageType categorizes P2P messages.
type SyncMessageType string

const (
	SyncEvent    SyncMessageType = "EVENT"
	SyncIncident SyncMessageType = "INCIDENT"
	SyncIOC      SyncMessageType = "IOC"
	SyncRule     SyncMessageType = "RULE"
	SyncHeartbeat SyncMessageType = "HEARTBEAT"
)

// NewP2PSyncService creates the inter-SOC sync engine.
func NewP2PSyncService() *P2PSyncService {
	return &P2PSyncService{
		peers:  make(map[string]*SOCPeer),
		maxBuf: 1000,
	}
}

// Enable activates P2P sync.
func (p *P2PSyncService) Enable() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.enabled = true
}

// Disable deactivates P2P sync.
func (p *P2PSyncService) Disable() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.enabled = false
}

// IsEnabled returns whether P2P sync is active.
func (p *P2PSyncService) IsEnabled() bool {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.enabled
}

// AddPeer registers a SOC peer for synchronization.
func (p *P2PSyncService) AddPeer(id, name, endpoint, trustLevel string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.peers[id] = &SOCPeer{
		ID:         id,
		Name:       name,
		Endpoint:   endpoint,
		Status:     "disconnected",
		TrustLevel: trustLevel,
	}
}

// RemovePeer deregisters a SOC peer.
func (p *P2PSyncService) RemovePeer(id string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	delete(p.peers, id)
}

// ListPeers returns all known SOC peers.
func (p *P2PSyncService) ListPeers() []SOCPeer {
	p.mu.RLock()
	defer p.mu.RUnlock()
	result := make([]SOCPeer, 0, len(p.peers))
	for _, peer := range p.peers {
		result = append(result, *peer)
	}
	return result
}

// EnqueueOutbound adds a message to the outbound sync queue.
func (p *P2PSyncService) EnqueueOutbound(msgType SyncMessageType, payload any) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if !p.enabled {
		return nil
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("p2p: marshal failed: %w", err)
	}

	msg := SyncMessage{
		ID:        fmt.Sprintf("sync-%d", time.Now().UnixNano()),
		Type:      msgType,
		Payload:   data,
		Timestamp: time.Now(),
	}

	if len(p.outbox) >= p.maxBuf {
		p.outbox = p.outbox[1:] // drop oldest
	}
	p.outbox = append(p.outbox, msg)
	return nil
}

// ReceiveInbound processes an incoming sync message from a peer.
func (p *P2PSyncService) ReceiveInbound(peerID string, msg SyncMessage) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if !p.enabled {
		return fmt.Errorf("p2p sync disabled")
	}

	peer, ok := p.peers[peerID]
	if !ok {
		return fmt.Errorf("unknown peer: %s", peerID)
	}

	if peer.TrustLevel == "readonly" && msg.Type != SyncHeartbeat {
		return fmt.Errorf("peer %s is readonly, cannot receive %s", peerID, msg.Type)
	}

	msg.PeerID = peerID
	peer.EventsRecv++
	peer.LastSync = time.Now()
	peer.Status = "connected"

	if len(p.inbox) >= p.maxBuf {
		p.inbox = p.inbox[1:]
	}
	p.inbox = append(p.inbox, msg)
	return nil
}

// DrainOutbox returns and clears pending outbound messages.
func (p *P2PSyncService) DrainOutbox() []SyncMessage {
	p.mu.Lock()
	defer p.mu.Unlock()
	result := make([]SyncMessage, len(p.outbox))
	copy(result, p.outbox)
	p.outbox = p.outbox[:0]
	return result
}

// Stats returns P2P sync statistics.
func (p *P2PSyncService) Stats() map[string]any {
	p.mu.RLock()
	defer p.mu.RUnlock()

	totalSent := 0
	totalRecv := 0
	connected := 0
	for _, peer := range p.peers {
		totalSent += peer.EventsSent
		totalRecv += peer.EventsRecv
		if peer.Status == "connected" {
			connected++
		}
	}

	return map[string]any{
		"enabled":         p.enabled,
		"total_peers":     len(p.peers),
		"connected_peers": connected,
		"outbox_depth":    len(p.outbox),
		"inbox_depth":     len(p.inbox),
		"total_sent":      totalSent,
		"total_received":  totalRecv,
	}
}
