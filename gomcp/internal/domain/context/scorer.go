package context

import (
	"math"
	"sort"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// RelevanceScorer computes relevance scores for facts based on multiple signals:
// keyword match, recency decay, access frequency, and hierarchy level.
type RelevanceScorer struct {
	config EngineConfig
}

// NewRelevanceScorer creates a scorer with the given configuration.
func NewRelevanceScorer(cfg EngineConfig) *RelevanceScorer {
	return &RelevanceScorer{config: cfg}
}

// ScoreFact computes a composite relevance score for a single fact.
// Score is in [0.0, 1.0]. Archived facts always return 0.
func (rs *RelevanceScorer) ScoreFact(fact *memory.Fact, keywords []string, accessCount int) float64 {
	if fact.IsArchived {
		return 0.0
	}

	totalWeight := rs.config.KeywordWeight + rs.config.RecencyWeight +
		rs.config.FrequencyWeight + rs.config.LevelWeight
	if totalWeight == 0 {
		return 0.0
	}

	score := 0.0
	score += rs.config.KeywordWeight * rs.scoreKeywordMatch(fact, keywords)
	score += rs.config.RecencyWeight * rs.scoreRecency(fact)
	score += rs.config.FrequencyWeight * rs.scoreFrequency(accessCount)
	score += rs.config.LevelWeight * rs.scoreLevel(fact)

	// Normalize to [0, 1]
	score /= totalWeight

	// Penalize stale facts
	if fact.IsStale {
		score *= 0.5
	}

	return math.Min(score, 1.0)
}

// RankFacts scores and sorts all facts by relevance, filtering out archived ones.
//
// Facts that match at least one query keyword rank above facts that match none, whatever the
// composite scores say. The composite is a weighted sum, so topical relevance is one term out of
// four and can be outvoted — with the shipped weights (level 0.30, keyword 0.30, recency 0.25,
// frequency 0.15) a brand-new L0 fact matching NOTHING scores 0.55, while a week-old L2 fact
// matching every keyword scores 0.47. The unrelated fact wins, and it wins by default
// configuration rather than in some corner case.
//
// Relevance to the query is not one signal among four. It is the precondition; recency, level and
// frequency are how you choose among facts that are already relevant. Ordering by the pair
// (matches anything, score) says exactly that.
//
// Nothing is discarded, which matters: with no keywords — context injected without a query — every
// fact is in the no-match group and the composite ordering applies unchanged, so L0 invariants are
// still injected. The rule only forbids an unrelated fact from taking a slot from a related one.
func (rs *RelevanceScorer) RankFacts(facts []*memory.Fact, keywords []string, accessCounts map[string]int) []*ScoredFact {
	if len(facts) == 0 {
		return nil
	}

	// The match flag travels beside the fact rather than in a map keyed by ID: an empty or repeated
	// ID would silently make two facts share one entry, and the symptom would be a ranking that is
	// wrong only for some inputs.
	type candidate struct {
		scored   *ScoredFact
		hasMatch bool
	}

	candidates := make([]candidate, 0, len(facts))
	for _, f := range facts {
		ac := 0
		if accessCounts != nil {
			ac = accessCounts[f.ID]
		}
		s := rs.ScoreFact(f, keywords, ac)
		if s <= 0 {
			continue // skip archived / zero-score facts
		}
		sf := NewScoredFact(f, s)
		sf.AccessCount = ac
		candidates = append(candidates, candidate{scored: sf, hasMatch: rs.scoreKeywordMatch(f, keywords) > 0})
	}

	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].hasMatch != candidates[j].hasMatch {
			return candidates[i].hasMatch
		}
		return candidates[i].scored.Score > candidates[j].scored.Score
	})

	scored := make([]*ScoredFact, 0, len(candidates))
	for _, c := range candidates {
		scored = append(scored, c.scored)
	}
	return scored
}

// scoreKeywordMatch computes keyword overlap between query keywords and fact content.
// Returns [0.0, 1.0] — fraction of query keywords found in fact text.
func (rs *RelevanceScorer) scoreKeywordMatch(fact *memory.Fact, keywords []string) float64 {
	if len(keywords) == 0 {
		return 0.0
	}

	// Build searchable text from all fact fields
	searchText := strings.ToLower(fact.Content + " " + fact.Domain + " " + fact.Module)

	matches := 0
	for _, kw := range keywords {
		if strings.Contains(searchText, kw) {
			matches++
		}
	}

	return float64(matches) / float64(len(keywords))
}

// scoreRecency computes time-based recency score using exponential decay.
// Recent facts score close to 1.0, older facts decay towards 0.
func (rs *RelevanceScorer) scoreRecency(fact *memory.Fact) float64 {
	hoursAgo := timeSinceHours(fact.CreatedAt)
	return rs.decayFactor(hoursAgo)
}

// scoreLevel returns a score based on hierarchy level.
// L0 (project) is most valuable, L3 (snippet) is least.
func (rs *RelevanceScorer) scoreLevel(fact *memory.Fact) float64 {
	switch fact.Level {
	case memory.LevelProject:
		return 1.0
	case memory.LevelDomain:
		return 0.7
	case memory.LevelModule:
		return 0.4
	case memory.LevelSnippet:
		return 0.15
	default:
		return 0.1
	}
}

// scoreFrequency computes an access-frequency score with diminishing returns.
// Uses log(1 + count) / log(1 + ceiling) to bound in [0, 1].
func (rs *RelevanceScorer) scoreFrequency(accessCount int) float64 {
	if accessCount <= 0 {
		return 0.0
	}
	// Logarithmic scaling with ceiling of 100 accesses = score 1.0
	const ceiling = 100.0
	score := math.Log1p(float64(accessCount)) / math.Log1p(ceiling)
	if score > 1.0 {
		return 1.0
	}
	return score
}

// decayFactor computes exponential decay: 2^(-hoursAgo / halfLife).
func (rs *RelevanceScorer) decayFactor(hoursAgo float64) float64 {
	halfLife := rs.config.DecayHalfLifeHours
	if halfLife <= 0 {
		halfLife = DefaultDecayHalfLife
	}
	return math.Pow(2, -hoursAgo/halfLife)
}
