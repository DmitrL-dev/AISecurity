package tools

import (
	"context"
	"fmt"
	"math"
	"sort"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// CentroidService computes per-domain centroids — the L1 dense summary of
// every domain's live facts. Crystal Principle in action: many specific
// L2/L3 facts collapse into one vector that stands in for them at the
// abstract level.
type CentroidService struct {
	facts     memory.FactStore
	centroids memory.CentroidStore
}

// NewCentroidService wires up the centroid pipeline.
func NewCentroidService(facts memory.FactStore, centroids memory.CentroidStore) *CentroidService {
	return &CentroidService{facts: facts, centroids: centroids}
}

// Recompute rebuilds the centroid for a single domain from its live
// (non-archived, non-stale) facts that carry an embedding. Returns the new
// centroid, or nil if the domain has no embed-able facts (in which case
// any existing centroid for that domain is deleted).
func (s *CentroidService) Recompute(ctx context.Context, domain string) (*memory.Centroid, error) {
	if domain == "" {
		return nil, fmt.Errorf("domain is required")
	}
	facts, err := s.facts.ListByDomain(ctx, domain, false)
	if err != nil {
		return nil, fmt.Errorf("list domain %q: %w", domain, err)
	}

	mean, count, err := MeanEmbedding(facts)
	if err != nil {
		return nil, err
	}
	if count == 0 {
		// No usable embeddings — drop any stale centroid.
		_ = s.centroids.Delete(ctx, domain)
		return nil, nil
	}

	c := &memory.Centroid{
		Domain:    domain,
		Vector:    mean,
		FactCount: count,
		UpdatedAt: time.Now().UTC(),
	}
	if err := s.centroids.Upsert(ctx, c); err != nil {
		return nil, err
	}
	return c, nil
}

// RecomputeAll recomputes centroids for every domain that has at least one
// live fact, and removes centroids for domains that have none. Returns the
// number of centroids written (not deleted).
func (s *CentroidService) RecomputeAll(ctx context.Context) (int, error) {
	domains, err := s.facts.ListDomains(ctx)
	if err != nil {
		return 0, fmt.Errorf("list domains: %w", err)
	}

	written := 0
	kept := make([]string, 0, len(domains))
	for _, d := range domains {
		c, err := s.Recompute(ctx, d)
		if err != nil {
			return written, err
		}
		if c != nil {
			written++
			kept = append(kept, d)
		}
	}
	if err := s.centroids.RemoveAbsent(ctx, kept); err != nil {
		return written, err
	}
	return written, nil
}

// List returns every stored centroid, sorted by domain.
func (s *CentroidService) List(ctx context.Context) ([]*memory.Centroid, error) {
	return s.centroids.GetAll(ctx)
}

// SearchDomainsByVector returns top-K domains whose centroid is closest to
// queryVec by cosine similarity. This is the abstract-first half of two-stage
// retrieval: pick the right neighbourhood, then drill down.
func (s *CentroidService) SearchDomainsByVector(ctx context.Context, queryVec []float64, limit int) ([]memory.CentroidScore, error) {
	if len(queryVec) == 0 {
		return nil, nil
	}
	if limit <= 0 {
		limit = 10
	}
	all, err := s.centroids.GetAll(ctx)
	if err != nil {
		return nil, err
	}

	scored := make([]memory.CentroidScore, 0, len(all))
	for _, c := range all {
		if len(c.Vector) != len(queryVec) {
			continue
		}
		sim := vectorstore.CosineSimilarity(queryVec, c.Vector)
		scored = append(scored, memory.CentroidScore{Centroid: c, Similarity: sim})
	}
	sort.Slice(scored, func(i, j int) bool { return scored[i].Similarity > scored[j].Similarity })
	if limit > len(scored) {
		limit = len(scored)
	}
	return scored[:limit], nil
}

// MeanEmbedding computes the unit-normalised mean of every embed-bearing
// fact's embedding. Mismatched-dimensionality and archived facts are
// skipped. Returns the centroid vector and the count of contributing facts;
// (nil, 0, nil) when there are no usable embeddings.
//
// Exported so tests and the future cold-decay pass can reuse the same
// reduction without going through the service.
func MeanEmbedding(facts []*memory.Fact) ([]float64, int, error) {
	// First pass: discover the dominant embedding dimensionality.
	dimCount := map[int]int{}
	for _, f := range facts {
		if f == nil || f.IsArchived || f.IsStale || len(f.Embedding) == 0 {
			continue
		}
		dimCount[len(f.Embedding)]++
	}
	if len(dimCount) == 0 {
		return nil, 0, nil
	}
	dim, max := 0, -1
	for d, n := range dimCount {
		if n > max {
			dim, max = d, n
		}
	}

	// Second pass: sum embeddings of the dominant dimensionality.
	sum := make([]float64, dim)
	count := 0
	for _, f := range facts {
		if f == nil || f.IsArchived || f.IsStale || len(f.Embedding) != dim {
			continue
		}
		for i, v := range f.Embedding {
			sum[i] += v
		}
		count++
	}
	if count == 0 {
		return nil, 0, nil
	}
	// Mean.
	for i := range sum {
		sum[i] /= float64(count)
	}
	// L2-normalise so cosine against unit-query is just dot product.
	var norm float64
	for _, v := range sum {
		norm += v * v
	}
	norm = math.Sqrt(norm)
	if norm > 0 {
		for i := range sum {
			sum[i] /= norm
		}
	}
	return sum, count, nil
}
