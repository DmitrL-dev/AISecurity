package tools

import (
	"context"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// DecayService is the cold-decay pass — Crystal Эшелон 1 #4. Old, never-hit
// facts that the system has demonstrably ignored are collapsed: those that
// already feed into a parent (and thus into a centroid) get archived; those
// without a parent are marked stale for later human review. Genome facts
// are immune (FactRepo.GetColdFacts skips source='genome'), and archived
// facts are skipped to avoid double-action.
//
// "Decay" not "delete" — content is never destroyed by this service. Raw
// rows remain in SQLite; archive flips a flag, stale flips a flag. The
// raw bytes can be recovered. Compaction of long-archived rows is a
// separate housekeeping concern.
type DecayService struct {
	facts     memory.FactStore
	centroids *CentroidService // optional — when set, affected domains are recomputed
}

// NewDecayService wires the pass.
func NewDecayService(facts memory.FactStore) *DecayService {
	return &DecayService{facts: facts}
}

// SetCentroidService enables auto-recompute of centroids for domains whose
// fact set changed during the decay pass. Without it, decay still runs but
// centroids drift until something else recomputes them.
func (s *DecayService) SetCentroidService(c *CentroidService) {
	s.centroids = c
}

// DecayPlan is the structured outcome of analysing a set of cold facts. It
// is returned by Plan() and consumed by Apply(); separating the two enables
// dry-run reporting without touching the store.
type DecayPlan struct {
	Archive []*memory.Fact `json:"-"`
	Stale   []*memory.Fact `json:"-"`
	Domains []string       `json:"domains"`
}

// DecayResult summarises a decay pass.
type DecayResult struct {
	Considered    int      `json:"considered"`
	Archived      int      `json:"archived"`
	Staled        int      `json:"staled"`
	Domains       []string `json:"domains"`
	CentroidsKept int      `json:"centroids_kept,omitempty"`
	DryRun        bool     `json:"dry_run"`
}

// Plan classifies each cold fact as archivable (has a live parent in the
// store, so its content is already represented at L2/L1) or stale-only
// (no parent — flag for review rather than silently archive).
func (s *DecayService) Plan(ctx context.Context, cold []*memory.Fact) DecayPlan {
	plan := DecayPlan{}
	if len(cold) == 0 {
		return plan
	}

	// Resolve which parent IDs actually exist. A single Get per unique
	// parent_id keeps this O(parents), not O(facts²).
	parents := map[string]bool{}
	for _, f := range cold {
		if f != nil && f.ParentID != "" {
			parents[f.ParentID] = false
		}
	}
	for pid := range parents {
		got, err := s.facts.Get(ctx, pid)
		parents[pid] = err == nil && got != nil
	}

	domainSet := map[string]struct{}{}
	for _, f := range cold {
		if f == nil {
			continue
		}
		if f.ParentID != "" && parents[f.ParentID] {
			plan.Archive = append(plan.Archive, f)
		} else {
			plan.Stale = append(plan.Stale, f)
		}
		if f.Domain != "" {
			domainSet[f.Domain] = struct{}{}
		}
	}
	for d := range domainSet {
		plan.Domains = append(plan.Domains, d)
	}
	return plan
}

// Apply executes a plan: archives the archive set, marks stale the stale
// set, optionally recomputes centroids for affected domains.
func (s *DecayService) Apply(ctx context.Context, plan DecayPlan) (DecayResult, error) {
	res := DecayResult{
		Considered: len(plan.Archive) + len(plan.Stale),
		Domains:    plan.Domains,
	}

	for _, f := range plan.Archive {
		f.Archive()
		if err := s.facts.Update(ctx, f); err != nil {
			return res, fmt.Errorf("archive fact %s: %w", f.ID, err)
		}
		res.Archived++
	}
	for _, f := range plan.Stale {
		f.MarkStale()
		if err := s.facts.Update(ctx, f); err != nil {
			return res, fmt.Errorf("stale fact %s: %w", f.ID, err)
		}
		res.Staled++
	}

	if s.centroids != nil {
		kept := 0
		for _, d := range plan.Domains {
			c, err := s.centroids.Recompute(ctx, d)
			if err != nil {
				return res, fmt.Errorf("recompute centroid %q: %w", d, err)
			}
			if c != nil {
				kept++
			}
		}
		res.CentroidsKept = kept
	}
	return res, nil
}

// Decay is the convenience entry point: pull cold facts older than `olderThan`,
// build a plan, optionally execute it. olderThan must be ≥ 30 days because
// the underlying GetColdFacts has a 30-day floor; smaller values silently
// behave as 30 days.
func (s *DecayService) Decay(ctx context.Context, olderThan time.Duration, dryRun bool) (DecayResult, error) {
	cold, err := s.facts.GetColdFacts(ctx, 10000)
	if err != nil {
		return DecayResult{}, fmt.Errorf("get cold facts: %w", err)
	}
	cutoff := time.Now().Add(-olderThan)
	filtered := make([]*memory.Fact, 0, len(cold))
	for _, f := range cold {
		if f != nil && f.CreatedAt.Before(cutoff) {
			filtered = append(filtered, f)
		}
	}
	plan := s.Plan(ctx, filtered)

	if dryRun {
		return DecayResult{
			Considered: len(plan.Archive) + len(plan.Stale),
			Archived:   len(plan.Archive),
			Staled:     len(plan.Stale),
			Domains:    plan.Domains,
			DryRun:     true,
		}, nil
	}
	return s.Apply(ctx, plan)
}
