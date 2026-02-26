package context

import (
	"math"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- RelevanceScorer tests ---

func TestNewRelevanceScorer(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)
	require.NotNil(t, scorer)
	assert.Equal(t, cfg.RecencyWeight, scorer.config.RecencyWeight)
}

func TestRelevanceScorer_ScoreKeywordMatch(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	fact := memory.NewFact("Architecture uses clean layers with dependency injection", memory.LevelProject, "arch", "")

	// Keywords that match
	score1 := scorer.scoreKeywordMatch(fact, []string{"architecture", "clean", "layers"})
	assert.Greater(t, score1, 0.0)

	// Keywords that don't match
	score2 := scorer.scoreKeywordMatch(fact, []string{"database", "migration", "schema"})
	assert.Equal(t, 0.0, score2)

	// Partial match scores less than full match
	score3 := scorer.scoreKeywordMatch(fact, []string{"architecture", "unrelated"})
	assert.Greater(t, score3, 0.0)
	assert.Less(t, score3, score1)
}

func TestRelevanceScorer_ScoreKeywordMatch_EmptyKeywords(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	fact := memory.NewFact("test content", memory.LevelProject, "test", "")
	score := scorer.scoreKeywordMatch(fact, nil)
	assert.Equal(t, 0.0, score)

	score2 := scorer.scoreKeywordMatch(fact, []string{})
	assert.Equal(t, 0.0, score2)
}

func TestRelevanceScorer_ScoreRecency(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	// Recent fact should score high
	recentFact := memory.NewFact("recent", memory.LevelProject, "test", "")
	recentFact.CreatedAt = time.Now().Add(-1 * time.Hour)
	scoreRecent := scorer.scoreRecency(recentFact)
	assert.Greater(t, scoreRecent, 0.5)

	// Old fact should score lower
	oldFact := memory.NewFact("old", memory.LevelProject, "test", "")
	oldFact.CreatedAt = time.Now().Add(-30 * 24 * time.Hour) // 30 days ago
	scoreOld := scorer.scoreRecency(oldFact)
	assert.Less(t, scoreOld, scoreRecent)

	// Very old fact should score very low
	veryOldFact := memory.NewFact("ancient", memory.LevelProject, "test", "")
	veryOldFact.CreatedAt = time.Now().Add(-365 * 24 * time.Hour)
	scoreVeryOld := scorer.scoreRecency(veryOldFact)
	assert.Less(t, scoreVeryOld, scoreOld)
}

func TestRelevanceScorer_ScoreLevel(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	tests := []struct {
		level    memory.HierLevel
		minScore float64
	}{
		{memory.LevelProject, 0.9}, // L0 scores highest
		{memory.LevelDomain, 0.6},  // L1
		{memory.LevelModule, 0.3},  // L2
		{memory.LevelSnippet, 0.1}, // L3 scores lowest
	}

	var prevScore float64 = 2.0
	for _, tt := range tests {
		fact := memory.NewFact("test", tt.level, "test", "")
		score := scorer.scoreLevel(fact)
		assert.Greater(t, score, 0.0, "level %d should have positive score", tt.level)
		assert.Less(t, score, prevScore, "level %d should score less than level %d", tt.level, tt.level-1)
		prevScore = score
	}
}

func TestRelevanceScorer_ScoreFrequency(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	// Zero access count
	score0 := scorer.scoreFrequency(0)
	assert.Equal(t, 0.0, score0)

	// Some accesses
	score5 := scorer.scoreFrequency(5)
	assert.Greater(t, score5, 0.0)

	// More accesses = higher score (but with diminishing returns)
	score50 := scorer.scoreFrequency(50)
	assert.Greater(t, score50, score5)

	// Score is bounded (shouldn't exceed 1.0)
	score1000 := scorer.scoreFrequency(1000)
	assert.LessOrEqual(t, score1000, 1.0)
}

func TestRelevanceScorer_ScoreFact(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	fact := memory.NewFact("Architecture uses clean layers", memory.LevelProject, "arch", "")
	keywords := []string{"architecture", "clean"}

	score := scorer.ScoreFact(fact, keywords, 3)
	assert.Greater(t, score, 0.0)
	assert.LessOrEqual(t, score, 1.0)
}

func TestRelevanceScorer_ScoreFact_StaleFact(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	fact := memory.NewFact("stale info", memory.LevelProject, "arch", "")
	fact.MarkStale()

	staleFact := scorer.ScoreFact(fact, []string{"info"}, 0)

	freshFact := memory.NewFact("fresh info", memory.LevelProject, "arch", "")
	freshScore := scorer.ScoreFact(freshFact, []string{"info"}, 0)

	// Stale facts should be penalized
	assert.Less(t, staleFact, freshScore)
}

func TestRelevanceScorer_ScoreFact_ArchivedFact(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	fact := memory.NewFact("archived info", memory.LevelProject, "arch", "")
	fact.Archive()

	score := scorer.ScoreFact(fact, []string{"info"}, 0)
	assert.Equal(t, 0.0, score, "archived facts should score 0")
}

func TestRelevanceScorer_RankFacts(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	facts := []*memory.Fact{
		memory.NewFact("Low relevance snippet", memory.LevelSnippet, "misc", ""),
		memory.NewFact("Architecture uses clean dependency injection", memory.LevelProject, "arch", ""),
		memory.NewFact("Domain boundary for auth module", memory.LevelDomain, "auth", ""),
	}

	keywords := []string{"architecture", "clean"}
	accessCounts := map[string]int{
		facts[1].ID: 10, // architecture fact accessed often
	}

	ranked := scorer.RankFacts(facts, keywords, accessCounts)

	require.Len(t, ranked, 3)
	// Architecture fact should rank highest (L0 + keyword match + access count)
	assert.Equal(t, facts[1].ID, ranked[0].Fact.ID)
	// Scores should be descending
	for i := 1; i < len(ranked); i++ {
		assert.GreaterOrEqual(t, ranked[i-1].Score, ranked[i].Score,
			"facts should be sorted by score descending")
	}
}

func TestRelevanceScorer_RankFacts_Empty(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	ranked := scorer.RankFacts(nil, []string{"test"}, nil)
	assert.Empty(t, ranked)
}

func TestRelevanceScorer_RankFacts_FiltersArchived(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	active := memory.NewFact("active fact", memory.LevelProject, "arch", "")
	archived := memory.NewFact("archived fact", memory.LevelProject, "arch", "")
	archived.Archive()

	ranked := scorer.RankFacts([]*memory.Fact{active, archived}, []string{"fact"}, nil)
	require.Len(t, ranked, 1)
	assert.Equal(t, active.ID, ranked[0].Fact.ID)
}

func TestRelevanceScorer_DecayFunction(t *testing.T) {
	cfg := DefaultEngineConfig()
	cfg.DecayHalfLifeHours = 24.0 // 1 day half-life
	scorer := NewRelevanceScorer(cfg)

	// At t=0, decay should be 1.0
	decay0 := scorer.decayFactor(0)
	assert.InDelta(t, 1.0, decay0, 0.01)

	// At t=half-life, decay should be ~0.5
	decayHalf := scorer.decayFactor(24.0)
	assert.InDelta(t, 0.5, decayHalf, 0.05)

	// At t=2*half-life, decay should be ~0.25
	decayDouble := scorer.decayFactor(48.0)
	assert.InDelta(t, 0.25, decayDouble, 0.05)
}

func TestRelevanceScorer_DomainMatch(t *testing.T) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	factArch := memory.NewFact("architecture pattern", memory.LevelDomain, "architecture", "")
	factAuth := memory.NewFact("auth module pattern", memory.LevelDomain, "auth", "")

	// Keywords mentioning "architecture" should boost the arch fact
	keywords := []string{"architecture", "pattern"}
	scoreArch := scorer.ScoreFact(factArch, keywords, 0)
	scoreAuth := scorer.ScoreFact(factAuth, keywords, 0)

	// Both match "pattern" but only arch fact matches "architecture" in content+domain
	assert.Greater(t, scoreArch, scoreAuth)
}

// --- Benchmark ---

func BenchmarkScoreFact(b *testing.B) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)
	fact := memory.NewFact("Architecture uses clean layers with dependency injection", memory.LevelProject, "arch", "core")
	keywords := []string{"architecture", "clean", "layers", "dependency"}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scorer.ScoreFact(fact, keywords, 5)
	}
}

func BenchmarkRankFacts(b *testing.B) {
	cfg := DefaultEngineConfig()
	scorer := NewRelevanceScorer(cfg)

	facts := make([]*memory.Fact, 100)
	for i := 0; i < 100; i++ {
		facts[i] = memory.NewFact(
			"fact content with various keywords for testing relevance scoring",
			memory.HierLevel(i%4), "domain", "module",
		)
	}
	keywords := []string{"content", "testing", "scoring"}
	_ = math.Abs(0) // use math import

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scorer.RankFacts(facts, keywords, nil)
	}
}
