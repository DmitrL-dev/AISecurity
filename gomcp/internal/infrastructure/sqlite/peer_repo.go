package sqlite

import (
	"context"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/peer"
)

// PeerRepo implements peer.PeerStore using SQLite.
type PeerRepo struct {
	db *DB
}

// NewPeerRepo creates a PeerRepo and ensures the peers table exists.
func NewPeerRepo(db *DB) (*PeerRepo, error) {
	repo := &PeerRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("peer repo migrate: %w", err)
	}
	return repo, nil
}

func (r *PeerRepo) migrate() error {
	stmt := `CREATE TABLE IF NOT EXISTS peers (
		peer_id TEXT PRIMARY KEY,
		node_name TEXT NOT NULL,
		genome_hash TEXT NOT NULL,
		trust_level INTEGER DEFAULT 0,
		last_seen TEXT NOT NULL,
		fact_count INTEGER DEFAULT 0,
		handshake_at TEXT,
		created_at TEXT DEFAULT CURRENT_TIMESTAMP
	)`
	if _, err := r.db.Exec(stmt); err != nil {
		return fmt.Errorf("create peers table: %w", err)
	}
	_, _ = r.db.Exec(`CREATE INDEX IF NOT EXISTS idx_peers_trust ON peers(trust_level)`)
	_, _ = r.db.Exec(`CREATE INDEX IF NOT EXISTS idx_peers_last_seen ON peers(last_seen)`)
	return nil
}

// SavePeer upserts a peer record.
func (r *PeerRepo) SavePeer(_ context.Context, p *peer.PeerInfo) error {
	stmt := `INSERT OR REPLACE INTO peers (peer_id, node_name, genome_hash, trust_level, last_seen, fact_count, handshake_at)
	         VALUES (?, ?, ?, ?, ?, ?, ?)`
	hsAt := ""
	if !p.HandshakeAt.IsZero() {
		hsAt = p.HandshakeAt.Format(timeFormat)
	}
	_, err := r.db.Exec(stmt,
		p.PeerID, p.NodeName, p.GenomeHash, int(p.Trust),
		p.LastSeen.Format(timeFormat), p.FactCount, hsAt,
	)
	return err
}

// LoadPeers returns all stored peers.
func (r *PeerRepo) LoadPeers(_ context.Context) ([]*peer.PeerInfo, error) {
	rows, err := r.db.Query(`SELECT peer_id, node_name, genome_hash, trust_level, last_seen, fact_count, handshake_at FROM peers`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var peers []*peer.PeerInfo
	for rows.Next() {
		var p peer.PeerInfo
		var trustInt int
		var lastSeenStr, handshakeStr string
		if err := rows.Scan(&p.PeerID, &p.NodeName, &p.GenomeHash, &trustInt, &lastSeenStr, &p.FactCount, &handshakeStr); err != nil {
			return nil, err
		}
		p.Trust = peer.TrustLevel(trustInt)
		p.LastSeen, _ = time.Parse(timeFormat, lastSeenStr)
		if handshakeStr != "" {
			p.HandshakeAt, _ = time.Parse(timeFormat, handshakeStr)
		}
		peers = append(peers, &p)
	}
	return peers, rows.Err()
}

// DeleteExpired removes peers not seen within the given duration.
func (r *PeerRepo) DeleteExpired(_ context.Context, olderThan time.Duration) (int, error) {
	cutoff := time.Now().Add(-olderThan).Format(timeFormat)
	result, err := r.db.Exec(`DELETE FROM peers WHERE last_seen < ?`, cutoff)
	if err != nil {
		return 0, err
	}
	n, _ := result.RowsAffected()
	return int(n), nil
}
