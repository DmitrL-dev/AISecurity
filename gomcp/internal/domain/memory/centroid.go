package memory

import (
	"context"
	"time"
)

// Centroid is the dense semantic summary of all live facts in a single domain.
// It is the L1-level abstraction in the Crystal hierarchy: one vector that
// stands in for many specific L2/L3 facts. Used for two-stage retrieval —
// query → nearest centroid(s) → drill down into that domain's facts.
type Centroid struct {
	Domain    string    `json:"domain"`
	Vector    []float64 `json:"vector"`
	FactCount int       `json:"fact_count"`
	UpdatedAt time.Time `json:"updated_at"`
}

// CentroidScore pairs a centroid with a similarity score.
type CentroidScore struct {
	Centroid   *Centroid `json:"centroid"`
	Similarity float64   `json:"similarity"`
}

// CentroidStore persists per-domain centroids. Implementations are expected
// to be append-on-recompute: a single Upsert replaces the previous centroid
// for a domain. Centroids are derived data — losing them is a recompute
// cost, never a data loss.
type CentroidStore interface {
	Get(ctx context.Context, domain string) (*Centroid, error)
	GetAll(ctx context.Context) ([]*Centroid, error)
	Upsert(ctx context.Context, c *Centroid) error
	Delete(ctx context.Context, domain string) error
	// RemoveAbsent deletes centroids for domains not in keep. Used after a
	// full recompute to prune centroids whose domain no longer has any
	// non-archived facts.
	RemoveAbsent(ctx context.Context, keep []string) error
}
