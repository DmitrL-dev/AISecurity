package transport

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"sync"
	"time"
)

// DiscoveryConfig configures UDP peer auto-discovery (v3.6).
type DiscoveryConfig struct {
	Port     int           `json:"port"`     // Broadcast port (default: 9742)
	Interval time.Duration `json:"interval"` // Broadcast interval (default: 30s)
	Enabled  bool          `json:"enabled"`  // Enable discovery
}

// DiscoveryAnnounce is broadcast via UDP to discover peers.
type DiscoveryAnnounce struct {
	PeerID     string `json:"peer_id"`
	NodeName   string `json:"node_name"`
	GenomeHash string `json:"genome_hash"`
	WSPort     int    `json:"ws_port"` // Port where WSTransport listens
	Timestamp  int64  `json:"timestamp"`
}

// Discovery manages UDP broadcast-based peer auto-discovery.
type Discovery struct {
	mu       sync.RWMutex
	config   DiscoveryConfig
	selfID   string
	nodeName string
	wsPort   int
	genHash  string
	conn     *net.UDPConn
	running  bool
	onFound  func(DiscoveryAnnounce) // Callback when new peer found
	seen     map[string]time.Time    // peerID → last seen
}

// NewDiscovery creates a new UDP auto-discovery service.
func NewDiscovery(cfg DiscoveryConfig, selfID, nodeName, genomeHash string, wsPort int) *Discovery {
	if cfg.Port <= 0 {
		cfg.Port = 9742
	}
	if cfg.Interval <= 0 {
		cfg.Interval = 30 * time.Second
	}
	return &Discovery{
		config:   cfg,
		selfID:   selfID,
		nodeName: nodeName,
		wsPort:   wsPort,
		genHash:  genomeHash,
		seen:     make(map[string]time.Time),
	}
}

// OnPeerFound registers a callback for discovered peers.
func (d *Discovery) OnPeerFound(fn func(DiscoveryAnnounce)) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.onFound = fn
}

// Start begins broadcasting and listening for peer announcements.
func (d *Discovery) Start() error {
	addr := &net.UDPAddr{IP: net.IPv4(255, 255, 255, 255), Port: d.config.Port}

	// Listen for broadcasts.
	listenAddr := &net.UDPAddr{IP: net.IPv4zero, Port: d.config.Port}
	conn, err := net.ListenUDP("udp4", listenAddr)
	if err != nil {
		return fmt.Errorf("discovery listen: %w", err)
	}

	d.mu.Lock()
	d.conn = conn
	d.running = true
	d.mu.Unlock()

	log.Printf("discovery: listening on UDP :%d (peer=%s)", d.config.Port, d.selfID)

	// Listener goroutine.
	go d.listen()

	// Announcer goroutine.
	go func() {
		ticker := time.NewTicker(d.config.Interval)
		defer ticker.Stop()
		for {
			if !d.isRunning() {
				return
			}
			d.broadcast(addr)
			<-ticker.C
		}
	}()

	return nil
}

func (d *Discovery) listen() {
	buf := make([]byte, 4096)
	for d.isRunning() {
		d.conn.SetReadDeadline(time.Now().Add(5 * time.Second))
		n, _, err := d.conn.ReadFromUDP(buf)
		if err != nil {
			continue // Timeout or error — retry.
		}

		var ann DiscoveryAnnounce
		if err := json.Unmarshal(buf[:n], &ann); err != nil {
			continue
		}

		// Ignore self.
		if ann.PeerID == d.selfID {
			continue
		}

		d.mu.Lock()
		_, seen := d.seen[ann.PeerID]
		d.seen[ann.PeerID] = time.Now()
		handler := d.onFound
		d.mu.Unlock()

		if !seen && handler != nil {
			handler(ann)
			log.Printf("discovery: new peer found — %s (%s) at port %d", shortID(ann.PeerID), ann.NodeName, ann.WSPort)
		}
	}
}

func (d *Discovery) broadcast(addr *net.UDPAddr) {
	ann := DiscoveryAnnounce{
		PeerID:     d.selfID,
		NodeName:   d.nodeName,
		GenomeHash: d.genHash,
		WSPort:     d.wsPort,
		Timestamp:  time.Now().Unix(),
	}
	data, err := json.Marshal(ann)
	if err != nil {
		return
	}

	conn, err := net.DialUDP("udp4", nil, addr)
	if err != nil {
		return
	}
	defer conn.Close()
	conn.Write(data)
}

// Stop shuts down discovery.
func (d *Discovery) Stop() error {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.running = false
	if d.conn != nil {
		return d.conn.Close()
	}
	return nil
}

// KnownPeers returns all seen peer IDs.
func (d *Discovery) KnownPeers() []string {
	d.mu.RLock()
	defer d.mu.RUnlock()
	peers := make([]string, 0, len(d.seen))
	for id := range d.seen {
		peers = append(peers, id)
	}
	return peers
}

func (d *Discovery) isRunning() bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.running
}

// shortID truncates a peer ID to at most 8 characters for log output without
// panicking on short, attacker-controlled IDs (announcements arrive as
// untrusted UDP broadcasts; a sub-8-char peer_id would otherwise slice-panic
// in this recovery-less goroutine and crash the process).
func shortID(id string) string {
	if len(id) > 8 {
		return id[:8]
	}
	return id
}
