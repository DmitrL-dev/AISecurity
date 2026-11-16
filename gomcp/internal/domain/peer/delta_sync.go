package peer

import "time"

// DeltaSyncRequest asks a peer for facts created after a given timestamp (v3.5).
type DeltaSyncRequest struct {
	FromPeerID string    `json:"from_peer_id"`
	GenomeHash string    `json:"genome_hash"`
	Since      time.Time `json:"since"` // Only return facts created after this time
	MaxBatch   int       `json:"max_batch,omitempty"`
}

// DeltaSyncResponse carries only facts newer than the requested timestamp.
type DeltaSyncResponse struct {
	FromPeerID string     `json:"from_peer_id"`
	GenomeHash string     `json:"genome_hash"`
	Facts      []SyncFact `json:"facts"`
	SyncedAt   time.Time  `json:"synced_at"`
	HasMore    bool       `json:"has_more"` // True if more facts exist (pagination)
}

// FilterFactsSince returns facts with CreatedAt after the given time.
// Used by both MCP and WebSocket transports for delta-sync.
func FilterFactsSince(facts []SyncFact, since time.Time, maxBatch int) (filtered []SyncFact, hasMore bool) {
	if maxBatch <= 0 {
		maxBatch = 100
	}
	for _, f := range facts {
		if f.CreatedAt.After(since) {
			filtered = append(filtered, f)
			if len(filtered) >= maxBatch {
				return filtered, true
			}
		}
	}
	return filtered, false
}
