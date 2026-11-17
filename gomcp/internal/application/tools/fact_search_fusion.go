package tools

import (
	"sort"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// Hybrid search fuses the keyword and the semantic ranking with weighted
// Reciprocal Rank Fusion. It replaces «semantic first, keyword after», which
// let the semantic list fill the whole page: the pure-Go fallback embedder
// gives almost every fact a non-zero cosine, so keyword matches never reached
// the result. TestRetrievalBench measured it on 193 facts: hybrid hit@5 was
// 144 against 187 for keyword alone, and 192 after this change.

// rrfK is the usual RRF constant: a fact's contribution from one list is
// weight / (rrfK + rank).
const rrfK = 60.0

// degradedSemanticWeight is the weight of the semantic list when the embedder
// reports OracleModeDegraded (character trigrams, not a language model). On the
// retrieval bench every positive weight ranked worse than keyword alone, so it is
// zero: the trigram list then only orders the facts the keyword list did not
// find, after all of those it did. A variable only so that bench can sweep it.
var degradedSemanticWeight = 0.0

// hybridDepth is how many results each list contributes before fusion. Reading
// deeper than the page lets a fact ranked moderately by both lists overtake a
// fact ranked first by only one of them.
func hybridDepth(limit int) int {
	depth := limit * 3
	if depth < 30 {
		depth = 30
	}
	return depth
}

func (s *FactService) semanticFusionWeight() float64 {
	if s.embedder != nil && s.embedder.Mode() == vectorstore.OracleModeDegraded {
		return degradedSemanticWeight
	}
	return 1
}

// fuseHybridResults merges two rankings of the same fact store. A fact present
// in both lists sums both contributions. Ties go to the fact with a keyword
// rank, then to the better semantic rank, then to the lower ID, so the order is
// deterministic and a zero semantic weight still keeps the semantic order for
// the facts only it found.
func fuseHybridResults(semantic, keyword []*memory.Fact, limit int, semanticWeight float64) []*memory.Fact {
	type entry struct {
		fact         *memory.Fact
		score        float64
		keywordRank  int
		semanticRank int
	}
	entries := make(map[string]*entry, len(semantic)+len(keyword))
	order := make([]*entry, 0, len(semantic)+len(keyword))
	add := func(facts []*memory.Fact, weight float64, isKeyword bool) {
		inList := make(map[string]struct{}, len(facts))
		for rank, fact := range facts {
			if fact == nil {
				continue
			}
			if _, repeated := inList[fact.ID]; repeated {
				continue // a list repeating a fact counts it once, at its best rank
			}
			inList[fact.ID] = struct{}{}
			e, ok := entries[fact.ID]
			if !ok {
				e = &entry{fact: fact, keywordRank: -1, semanticRank: -1}
				entries[fact.ID] = e
				order = append(order, e)
			}
			e.score += weight / (rrfK + float64(rank+1))
			if isKeyword {
				e.keywordRank = rank
			} else {
				e.semanticRank = rank
			}
		}
	}
	add(keyword, 1, true)
	add(semantic, semanticWeight, false)

	sort.SliceStable(order, func(i, j int) bool {
		a, b := order[i], order[j]
		if a.score != b.score {
			return a.score > b.score
		}
		if (a.keywordRank >= 0) != (b.keywordRank >= 0) {
			return a.keywordRank >= 0
		}
		if (a.semanticRank >= 0) != (b.semanticRank >= 0) {
			return a.semanticRank >= 0
		}
		if a.semanticRank != b.semanticRank {
			return a.semanticRank < b.semanticRank
		}
		return a.fact.ID < b.fact.ID
	})
	if limit > len(order) {
		limit = len(order)
	}
	out := make([]*memory.Fact, limit)
	for i := range out {
		out[i] = order[i].fact
	}
	return out
}
