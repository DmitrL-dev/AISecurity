package sqlite

import (
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

func rankFacts(contents ...string) []*memory.Fact {
	out := make([]*memory.Fact, len(contents))
	for i, c := range contents {
		out[i] = &memory.Fact{ID: string(rune('a' + i)), Content: c}
	}
	return out
}

func rankedContents(facts []*memory.Fact) []string {
	out := make([]string, len(facts))
	for i, f := range facts {
		out[i] = f.Content
	}
	return out
}

// A term found in one fact weighs more than one found in all of them: the
// fact carrying the rare term ranks first even though another fact repeats
// the common term.
func TestRankKeyword_RareTermOutweighsCommonTerm(t *testing.T) {
	facts := rankFacts(
		"deploy deploy deploy notes",
		"deploy notes about PYO3_PYTHON",
		"deploy checklist",
		"deploy rollback",
	)
	got := rankKeywordMatches(facts, "deploy pyo3_python", 4, false)
	assert.Equal(t, "deploy notes about PYO3_PYTHON", got[0].Content)
}

func TestRankKeyword_WholePhraseRanksFirst(t *testing.T) {
	facts := rankFacts(
		"bash script edits and reads; the script reads by offset many times bash bash",
		"bash reads the file by offset",
	)
	got := rankKeywordMatches(facts, "reads the file by offset", 2, false)
	assert.Equal(t, "bash reads the file by offset", got[0].Content)
}

// Matching stays substring-based, so an inflected Russian form still matches.
func TestRankKeyword_SubstringMatchesInflection(t *testing.T) {
	facts := rankFacts("откат релиза на прошлый", "погода")
	got := rankKeywordMatches(facts, "релиз", 5, false)
	assert.Equal(t, []string{"откат релиза на прошлый"}, rankedContents(got))
}

func TestRankKeyword_NoMatchAndEmptyQuery(t *testing.T) {
	facts := rankFacts("alpha", "beta")
	assert.Empty(t, rankKeywordMatches(facts, "gamma", 5, false))
	assert.Nil(t, rankKeywordMatches(facts, "   ", 5, false))
	assert.Len(t, rankKeywordMatches(facts, "alpha", 0, false), 1, "non-positive limit means the default")
}
