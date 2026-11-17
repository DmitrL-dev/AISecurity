package sqlite

import (
	"math"
	"sort"
	"strings"
	"unicode"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// BM25 parameters, the usual defaults.
const (
	bm25K1 = 1.2
	bm25B  = 0.75
)

// rankKeywordMatches orders the facts of one scope that match the query.
//
// A fact containing the whole query as a phrase ranks above every other fact,
// as before. Below that the order is BM25 over the query terms: a term found in
// few facts weighs more than one found in most, so «PYO3_PYTHON» outranks «the»
// even when both match. Matching stays substring-based, which is what lets
// «релиз» find «релиза»; term frequency counts substring occurrences and
// document frequency is taken over the candidates, the scope's whole fact set.
//
// Callers pass every candidate of the scope (the bounded paths have already
// proved that set's size), so the statistics need no separate index. Equal
// scores go to the newer fact when newestFirstOnTie is set (session recall,
// where the latest turns matter), then to the lower ID.
func rankKeywordMatches(candidates []*memory.Fact, query string, limit int, newestFirstOnTie bool) []*memory.Fact {
	if limit <= 0 {
		limit = 50
	}
	phrase := strings.ToLower(strings.TrimSpace(query))
	if phrase == "" {
		return nil
	}
	terms := searchTerms(query)

	lowered := make([]string, len(candidates))
	lengths := make([]float64, len(candidates))
	var totalLength float64
	docFreq := make([]int, len(terms))
	for i, fact := range candidates {
		lowered[i] = strings.ToLower(fact.Content)
		lengths[i] = float64(wordCount(lowered[i]))
		totalLength += lengths[i]
		for t, term := range terms {
			if strings.Contains(lowered[i], term) {
				docFreq[t]++
			}
		}
	}
	n := float64(len(candidates))
	avgLength := 1.0
	if n > 0 && totalLength > 0 {
		avgLength = totalLength / n
	}
	idf := make([]float64, len(terms))
	for t := range terms {
		df := float64(docFreq[t])
		idf[t] = math.Log(1 + (n-df+0.5)/(df+0.5))
	}

	type scored struct {
		fact   *memory.Fact
		phrase bool
		score  float64
	}
	ranked := make([]scored, 0, len(candidates))
	for i, fact := range candidates {
		isPhrase := strings.Contains(lowered[i], phrase)
		score := 0.0
		for t, term := range terms {
			tf := float64(strings.Count(lowered[i], term))
			if tf == 0 {
				continue
			}
			norm := bm25K1 * (1 - bm25B + bm25B*lengths[i]/avgLength)
			score += idf[t] * tf * (bm25K1 + 1) / (tf + norm)
		}
		if isPhrase || score > 0 {
			ranked = append(ranked, scored{fact: fact, phrase: isPhrase, score: score})
		}
	}
	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].phrase != ranked[j].phrase {
			return ranked[i].phrase
		}
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		if newestFirstOnTie && !ranked[i].fact.CreatedAt.Equal(ranked[j].fact.CreatedAt) {
			return ranked[i].fact.CreatedAt.After(ranked[j].fact.CreatedAt)
		}
		return ranked[i].fact.ID < ranked[j].fact.ID
	})
	if limit > len(ranked) {
		limit = len(ranked)
	}
	out := make([]*memory.Fact, limit)
	for i := range out {
		out[i] = ranked[i].fact
	}
	return out
}

func wordCount(s string) int {
	return len(strings.FieldsFunc(s, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	}))
}
