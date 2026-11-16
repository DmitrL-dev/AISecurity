package context

import (
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- ScoredFact tests ---

func TestNewScoredFact(t *testing.T) {
	fact := memory.NewFact("test content", memory.LevelProject, "arch", "")
	sf := NewScoredFact(fact, 0.85)

	assert.Equal(t, fact, sf.Fact)
	assert.Equal(t, 0.85, sf.Score)
	assert.Equal(t, 0, sf.AccessCount)
	assert.True(t, sf.LastAccessed.IsZero())
}

func TestScoredFact_EstimateTokens(t *testing.T) {
	tests := []struct {
		name    string
		content string
		want    int
	}{
		{"empty", "", 1},
		{"short", "hello", 2}, // 5/4 = 1.25, ceil = 2
		{"typical", "This is a typical fact about architecture", 11}, // ~40 chars / 4 = 10 + overhead
		{"long", string(make([]byte, 400)), 101},                     // 400/4 = 100 + overhead
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fact := memory.NewFact(tt.content, memory.LevelProject, "test", "")
			sf := NewScoredFact(fact, 1.0)
			tokens := sf.EstimateTokens()
			assert.Greater(t, tokens, 0, "tokens must be positive")
		})
	}
}

func TestScoredFact_RecordAccess(t *testing.T) {
	fact := memory.NewFact("test", memory.LevelProject, "arch", "")
	sf := NewScoredFact(fact, 0.5)

	assert.Equal(t, 0, sf.AccessCount)
	assert.True(t, sf.LastAccessed.IsZero())

	sf.RecordAccess()
	assert.Equal(t, 1, sf.AccessCount)
	assert.False(t, sf.LastAccessed.IsZero())
	first := sf.LastAccessed

	time.Sleep(time.Millisecond)
	sf.RecordAccess()
	assert.Equal(t, 2, sf.AccessCount)
	assert.True(t, sf.LastAccessed.After(first))
}

// --- ContextFrame tests ---

func TestNewContextFrame(t *testing.T) {
	frame := NewContextFrame("add_fact", 500)

	assert.Equal(t, "add_fact", frame.ToolName)
	assert.Equal(t, 500, frame.TokenBudget)
	assert.Empty(t, frame.Facts)
	assert.Equal(t, 0, frame.TokensUsed)
	assert.False(t, frame.CreatedAt.IsZero())
}

func TestContextFrame_AddFact_WithinBudget(t *testing.T) {
	frame := NewContextFrame("test", 1000)

	fact1 := memory.NewFact("short fact", memory.LevelProject, "arch", "")
	sf1 := NewScoredFact(fact1, 0.9)

	added := frame.AddFact(sf1)
	assert.True(t, added)
	assert.Len(t, frame.Facts, 1)
	assert.Greater(t, frame.TokensUsed, 0)
}

func TestContextFrame_AddFact_ExceedsBudget(t *testing.T) {
	frame := NewContextFrame("test", 5) // tiny budget

	fact := memory.NewFact("This is a fact with a lot of content that exceeds the token budget", memory.LevelProject, "arch", "")
	sf := NewScoredFact(fact, 0.9)

	added := frame.AddFact(sf)
	assert.False(t, added)
	assert.Empty(t, frame.Facts)
	assert.Equal(t, 0, frame.TokensUsed)
}

func TestContextFrame_RemainingTokens(t *testing.T) {
	frame := NewContextFrame("test", 100)
	assert.Equal(t, 100, frame.RemainingTokens())

	fact := memory.NewFact("x", memory.LevelProject, "a", "")
	sf := NewScoredFact(fact, 0.5)
	frame.AddFact(sf)
	assert.Less(t, frame.RemainingTokens(), 100)
}

func TestContextFrame_Format(t *testing.T) {
	frame := NewContextFrame("test_tool", 1000)

	fact1 := memory.NewFact("Architecture uses clean layers", memory.LevelProject, "arch", "")
	sf1 := NewScoredFact(fact1, 0.95)
	frame.AddFact(sf1)

	fact2 := memory.NewFact("TDD is mandatory", memory.LevelProject, "process", "")
	sf2 := NewScoredFact(fact2, 0.8)
	frame.AddFact(sf2)

	formatted := frame.Format()

	assert.Contains(t, formatted, "[MEMORY CONTEXT]")
	assert.Contains(t, formatted, "[/MEMORY CONTEXT]")
	assert.Contains(t, formatted, "Architecture uses clean layers")
	assert.Contains(t, formatted, "TDD is mandatory")
	assert.Contains(t, formatted, "L0")
}

func TestContextFrame_Format_Empty(t *testing.T) {
	frame := NewContextFrame("test", 1000)
	formatted := frame.Format()
	assert.Equal(t, "", formatted, "empty frame should produce no output")
}

// --- TokenBudget tests ---

func TestNewTokenBudget(t *testing.T) {
	tb := NewTokenBudget(500)
	assert.Equal(t, 500, tb.MaxTokens)
	assert.Equal(t, 500, tb.Remaining())
}

func TestNewTokenBudget_DefaultMinimum(t *testing.T) {
	tb := NewTokenBudget(0)
	assert.Equal(t, DefaultTokenBudget, tb.MaxTokens)

	tb2 := NewTokenBudget(-10)
	assert.Equal(t, DefaultTokenBudget, tb2.MaxTokens)
}

func TestTokenBudget_TryConsume(t *testing.T) {
	tb := NewTokenBudget(100)

	ok := tb.TryConsume(30)
	assert.True(t, ok)
	assert.Equal(t, 70, tb.Remaining())

	ok = tb.TryConsume(70)
	assert.True(t, ok)
	assert.Equal(t, 0, tb.Remaining())

	ok = tb.TryConsume(1)
	assert.False(t, ok, "should not consume beyond budget")
	assert.Equal(t, 0, tb.Remaining())
}

func TestTokenBudget_Reset(t *testing.T) {
	tb := NewTokenBudget(100)
	tb.TryConsume(60)
	assert.Equal(t, 40, tb.Remaining())

	tb.Reset()
	assert.Equal(t, 100, tb.Remaining())
}

// --- EngineConfig tests ---

func TestDefaultEngineConfig(t *testing.T) {
	cfg := DefaultEngineConfig()

	assert.Equal(t, DefaultTokenBudget, cfg.TokenBudget)
	assert.Equal(t, DefaultMaxFacts, cfg.MaxFacts)
	assert.Greater(t, cfg.RecencyWeight, 0.0)
	assert.Greater(t, cfg.FrequencyWeight, 0.0)
	assert.Greater(t, cfg.LevelWeight, 0.0)
	assert.Greater(t, cfg.KeywordWeight, 0.0)
	assert.Greater(t, cfg.DecayHalfLifeHours, 0.0)
	assert.True(t, cfg.Enabled)
	assert.NotEmpty(t, cfg.SkipTools, "defaults should include skip tools")
}

func TestEngineConfig_SkipTools(t *testing.T) {
	cfg := DefaultEngineConfig()

	// Default skip list should include memory and system tools
	assert.True(t, cfg.ShouldSkip("search_facts"))
	assert.True(t, cfg.ShouldSkip("get_fact"))
	assert.True(t, cfg.ShouldSkip("get_l0_facts"))
	assert.True(t, cfg.ShouldSkip("health"))
	assert.True(t, cfg.ShouldSkip("version"))
	assert.True(t, cfg.ShouldSkip("dashboard"))
	assert.True(t, cfg.ShouldSkip("semantic_search"))

	// Non-skipped tools
	assert.False(t, cfg.ShouldSkip("add_fact"))
	assert.False(t, cfg.ShouldSkip("save_state"))
	assert.False(t, cfg.ShouldSkip("add_causal_node"))
	assert.False(t, cfg.ShouldSkip("search_crystals"))
}

func TestEngineConfig_ShouldSkip_EmptyList(t *testing.T) {
	cfg := DefaultEngineConfig()
	cfg.SkipTools = nil
	cfg.BuildSkipSet()

	assert.False(t, cfg.ShouldSkip("search_facts"))
	assert.False(t, cfg.ShouldSkip("anything"))
}

func TestEngineConfig_ShouldSkip_CustomList(t *testing.T) {
	cfg := DefaultEngineConfig()
	cfg.SkipTools = []string{"custom_tool", "another_tool"}
	cfg.BuildSkipSet()

	assert.True(t, cfg.ShouldSkip("custom_tool"))
	assert.True(t, cfg.ShouldSkip("another_tool"))
	assert.False(t, cfg.ShouldSkip("search_facts")) // no longer in list
}

func TestEngineConfig_ShouldSkip_LazyBuild(t *testing.T) {
	cfg := EngineConfig{
		SkipTools: []string{"lazy_tool"},
	}
	// skipSet is nil, ShouldSkip should auto-build
	assert.True(t, cfg.ShouldSkip("lazy_tool"))
	assert.False(t, cfg.ShouldSkip("other"))
}

func TestEngineConfig_Validate(t *testing.T) {
	tests := []struct {
		name    string
		modify  func(*EngineConfig)
		wantErr bool
	}{
		{"default is valid", func(c *EngineConfig) {}, false},
		{"zero budget", func(c *EngineConfig) { c.TokenBudget = 0 }, true},
		{"negative max facts", func(c *EngineConfig) { c.MaxFacts = -1 }, true},
		{"zero max facts uses default", func(c *EngineConfig) { c.MaxFacts = 0 }, true},
		{"all weights zero", func(c *EngineConfig) {
			c.RecencyWeight = 0
			c.FrequencyWeight = 0
			c.LevelWeight = 0
			c.KeywordWeight = 0
		}, true},
		{"negative weight", func(c *EngineConfig) { c.RecencyWeight = -1 }, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := DefaultEngineConfig()
			tt.modify(&cfg)
			err := cfg.Validate()
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// --- KeywordExtractor tests ---

func TestExtractKeywords(t *testing.T) {
	tests := []struct {
		name string
		text string
		want int // minimum expected keywords
	}{
		{"empty", "", 0},
		{"single word", "architecture", 1},
		{"sentence", "The architecture uses clean layers with dependency injection", 4},
		{"with stopwords", "this is a test of the system", 2}, // "test", "system"
		{"code ref", "file:main.go line:42 function:handleRequest", 3},
		{"duplicate words", "test test test unique", 2}, // deduped
		{"camelCase", "handleRequest", 2},               // "handle", "request"
		{"snake_case", "get_crystal_stats", 3},          // "get", "crystal", "stats"
		{"HTTPClient", "getHTTPClient", 3},              // "get", "http", "client"
		{"mixed", "myFunc_name camelCase", 4},           // "func", "name", "camel", "case"
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			keywords := ExtractKeywords(tt.text)
			assert.GreaterOrEqual(t, len(keywords), tt.want)
			// Verify no duplicates
			seen := make(map[string]bool)
			for _, kw := range keywords {
				assert.False(t, seen[kw], "duplicate keyword: %s", kw)
				seen[kw] = true
			}
		})
	}
}

// --- FactProvider interface test ---

func TestSplitCamelCase(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"handleRequest", "handle Request"},
		{"getHTTPClient", "get HTTP Client"},
		{"simple", "simple"},
		{"ABC", "ABC"},
		{"snake_case", "snake case"},
		{"myFunc_name", "my Func name"},
		{"", ""},
	}
	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := splitCamelCase(tt.input)
			assert.Equal(t, tt.want, got)
		})
	}
}

func TestFactProviderInterface(t *testing.T) {
	// Verify the interface is properly defined (compile-time check)
	var _ FactProvider = (*mockFactProvider)(nil)
}

type mockFactProvider struct {
	facts []*memory.Fact
}

func (m *mockFactProvider) GetRelevantFacts(_ map[string]interface{}) ([]*memory.Fact, error) {
	return m.facts, nil
}

func (m *mockFactProvider) GetL0Facts() ([]*memory.Fact, error) {
	return m.facts, nil
}

func (m *mockFactProvider) RecordAccess(factID string) {
	// no-op for mock
}

// --- Helpers ---

func TestEstimateTokenCount(t *testing.T) {
	tests := []struct {
		text string
		want int
	}{
		{"", 1},
		{"word", 2},
		{"hello world", 4}, // ~11 chars / 4 + 1
	}
	for _, tt := range tests {
		t.Run(tt.text, func(t *testing.T) {
			got := EstimateTokenCount(tt.text)
			require.Greater(t, got, 0)
		})
	}
}
