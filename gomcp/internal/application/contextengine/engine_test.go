package contextengine

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	ctxdomain "github.com/syntrex/gomcp/internal/domain/context"
)

// --- Mock FactProvider ---

type mockProvider struct {
	mu    sync.Mutex
	facts []*memory.Fact
	l0    []*memory.Fact
	// tracks RecordAccess calls
	accessed map[string]int
}

func newMockProvider(facts ...*memory.Fact) *mockProvider {
	l0 := make([]*memory.Fact, 0)
	for _, f := range facts {
		if f.Level == memory.LevelProject {
			l0 = append(l0, f)
		}
	}
	return &mockProvider{
		facts:    facts,
		l0:       l0,
		accessed: make(map[string]int),
	}
}

func (m *mockProvider) GetRelevantFacts(_ map[string]interface{}) ([]*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.facts, nil
}

func (m *mockProvider) GetL0Facts() ([]*memory.Fact, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.l0, nil
}

func (m *mockProvider) RecordAccess(factID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.accessed[factID]++
}

type mockBoostedProvider struct {
	*mockProvider
	boosts map[string]int
}

func (m *mockBoostedProvider) GetRelevantFactsWithBoost(_ context.Context, args map[string]interface{}) ([]*memory.Fact, map[string]int, error) {
	facts, err := m.mockProvider.GetRelevantFacts(args)
	return facts, m.boosts, err
}

// scopeCapturingProvider records the scope the engine threads into the boosted
// provider — locking the per-request-scope wiring (regression: the context
// engine previously ignored the request scope and used the pinned scope, so
// project-A facts leaked into a project-B response).
type scopeCapturingProvider struct {
	gotScope string
}

func (p *scopeCapturingProvider) GetRelevantFacts(_ map[string]interface{}) ([]*memory.Fact, error) {
	return nil, nil
}
func (p *scopeCapturingProvider) GetL0Facts() ([]*memory.Fact, error) { return nil, nil }
func (p *scopeCapturingProvider) RecordAccess(_ string)               {}
func (p *scopeCapturingProvider) GetRelevantFactsWithBoost(ctx context.Context, _ map[string]interface{}) ([]*memory.Fact, map[string]int, error) {
	p.gotScope = rlmscope.FromContext(ctx).String()
	return nil, nil, nil
}

// --- Engine tests ---

func TestEngine_BuildContextScoped_ThreadsRequestScope(t *testing.T) {
	// The proactive context must be built under the per-request scope (projB),
	// not the engine's pinned scope (projA) — otherwise cross-project bleed.
	prov := &scopeCapturingProvider{}
	engine := New(ctxdomain.DefaultEngineConfig(), prov)
	engine.WithScope(rlmscope.New("tenant-a", "project-alpha"))

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-beta"))
	engine.buildContextScoped(ctx, "search_facts", map[string]interface{}{"query": "x"})

	require.Equal(t, "tenant-a/project-beta", prov.gotScope)
}

func TestNewEngine(t *testing.T) {
	cfg := ctxdomain.DefaultEngineConfig()
	provider := newMockProvider()
	engine := New(cfg, provider)

	require.NotNil(t, engine)
	assert.True(t, engine.IsEnabled())
}

func TestNewEngine_Disabled(t *testing.T) {
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.Enabled = false
	engine := New(cfg, newMockProvider())

	assert.False(t, engine.IsEnabled())
}

func TestEngine_BuildContext_NoFacts(t *testing.T) {
	cfg := ctxdomain.DefaultEngineConfig()
	provider := newMockProvider()
	engine := New(cfg, provider)

	frame := engine.BuildContext("test_tool", map[string]interface{}{
		"content": "hello world",
	})

	assert.NotNil(t, frame)
	assert.Empty(t, frame.Facts)
	assert.Equal(t, "", frame.Format())
}

func TestEngine_BuildContext_WithFacts(t *testing.T) {
	fact1 := memory.NewFact("Architecture uses clean layers", memory.LevelProject, "arch", "")
	fact2 := memory.NewFact("TDD is mandatory for all code", memory.LevelProject, "process", "")
	fact3 := memory.NewFact("Random snippet from old session", memory.LevelSnippet, "misc", "")
	fact3.CreatedAt = time.Now().Add(-90 * 24 * time.Hour) // very old

	provider := newMockProvider(fact1, fact2, fact3)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.TokenBudget = 500
	engine := New(cfg, provider)

	frame := engine.BuildContext("add_fact", map[string]interface{}{
		"content": "architecture decision",
	})

	require.NotNil(t, frame)
	assert.NotEmpty(t, frame.Facts)
	// L0 facts should be included and ranked higher
	assert.Equal(t, "add_fact", frame.ToolName)

	formatted := frame.Format()
	assert.Contains(t, formatted, "[MEMORY CONTEXT]")
	assert.Contains(t, formatted, "[/MEMORY CONTEXT]")
}

func TestEngine_BuildContext_RespectsTokenBudget(t *testing.T) {
	// Create many facts that exceed token budget
	facts := make([]*memory.Fact, 50)
	for i := 0; i < 50; i++ {
		facts[i] = memory.NewFact(
			fmt.Sprintf("Fact number %d with enough content to consume tokens in the budget allocation system", i),
			memory.LevelProject, "arch", "",
		)
	}

	provider := newMockProvider(facts...)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.TokenBudget = 100 // tight budget
	cfg.MaxFacts = 50
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"query": "test"})
	assert.LessOrEqual(t, frame.TokensUsed, cfg.TokenBudget)
}

func TestEngine_BuildContext_RespectsMaxFacts(t *testing.T) {
	facts := make([]*memory.Fact, 20)
	for i := 0; i < 20; i++ {
		facts[i] = memory.NewFact(fmt.Sprintf("Fact %d", i), memory.LevelProject, "arch", "")
	}

	provider := newMockProvider(facts...)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.MaxFacts = 5
	cfg.TokenBudget = 10000 // large budget so max_facts is the limiter
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"query": "fact"})
	assert.LessOrEqual(t, len(frame.Facts), cfg.MaxFacts)
}

func TestEngine_BuildContext_DisabledReturnsEmpty(t *testing.T) {
	fact := memory.NewFact("test", memory.LevelProject, "arch", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.Enabled = false
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"content": "test"})
	assert.Empty(t, frame.Facts)
	assert.Equal(t, "", frame.Format())
}

func TestEngine_RecordsAccess(t *testing.T) {
	fact1 := memory.NewFact("Architecture pattern", memory.LevelProject, "arch", "")
	provider := newMockProvider(fact1)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"content": "architecture"})
	require.NotEmpty(t, frame.Facts)

	// Check that RecordAccess was called on the provider
	provider.mu.Lock()
	count := provider.accessed[fact1.ID]
	provider.mu.Unlock()
	assert.Greater(t, count, 0, "RecordAccess should be called for injected facts")
}

func TestEngine_AccessCountTracking(t *testing.T) {
	fact := memory.NewFact("Architecture decision", memory.LevelProject, "arch", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	// Build context 3 times
	for i := 0; i < 3; i++ {
		engine.BuildContext("test", map[string]interface{}{"content": "architecture"})
	}

	// Internal access count should be tracked
	count := engine.GetAccessCount(fact.ID)
	assert.Equal(t, 3, count)
}

func TestEngine_AccessCountInfluencesRanking(t *testing.T) {
	// Two similar facts but one has been accessed more
	fact1 := memory.NewFact("Architecture pattern A", memory.LevelDomain, "arch", "")
	fact2 := memory.NewFact("Architecture pattern B", memory.LevelDomain, "arch", "")

	provider := newMockProvider(fact1, fact2)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.FrequencyWeight = 0.9 // heavily weight frequency
	cfg.KeywordWeight = 0.01
	cfg.RecencyWeight = 0.01
	cfg.LevelWeight = 0.01
	engine := New(cfg, provider)

	// Simulate fact1 being accessed many times
	for i := 0; i < 20; i++ {
		engine.recordAccessInternal(fact1.ID)
	}

	frame := engine.BuildContext("test", map[string]interface{}{"content": "architecture pattern"})
	require.GreaterOrEqual(t, len(frame.Facts), 2)
	// fact1 should rank higher due to frequency
	assert.Equal(t, fact1.ID, frame.Facts[0].Fact.ID)
}

func TestEngine_RankingUsesTheDurableAccessCount(t *testing.T) {
	// A fresh process ranking facts with history.
	//
	// The engine's own counter map is created empty in New(), so before the durable counter was read
	// this test's expectation was unreachable: two facts, one used ninety times over months, scored
	// identically on frequency because the map knew nothing about either. `hit_count` was in the
	// database the whole time, written by TouchFact on every access and read by nobody.
	//
	// The frequency term is scaled against a ceiling of 100 accesses. A ceiling like that is a
	// statement about history; without a durable count it could only ever be approached inside a single
	// session, which is not how a memory server is used.
	used := memory.NewFact("Architecture pattern A", memory.LevelDomain, "arch", "")
	unused := memory.NewFact("Architecture pattern B", memory.LevelDomain, "arch", "")
	used.HitCount = 90

	provider := newMockProvider(used, unused)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.FrequencyWeight = 0.9
	cfg.KeywordWeight = 0.01
	cfg.RecencyWeight = 0.01
	cfg.LevelWeight = 0.01
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"content": "architecture pattern"})
	require.GreaterOrEqual(t, len(frame.Facts), 2)
	assert.Equal(t, used.ID, frame.Facts[0].Fact.ID,
		"a fact with 90 recorded accesses must outrank one with none in a freshly started process")
	assert.Equal(t, 90, frame.Facts[0].AccessCount,
		"the count reported alongside the fact is the durable one, not this session's zero")
}

func TestEngine_ThisSessionsAccessesAddToTheStoredOnes(t *testing.T) {
	// The two counters answer different questions and both matter: the stored one is history, the
	// in-memory one is reinforcement inside the current conversation. Summing is what keeps a fact
	// promoted by this session's use from being outranked by its own stale history — and what stops
	// the durable count from wiping out the reinforcement the engine performs on every injection.
	fact := memory.NewFact("Counted twice over", memory.LevelDomain, "arch", "")
	fact.HitCount = 4
	provider := newMockProvider(fact)
	engine := New(ctxdomain.DefaultEngineConfig(), provider)

	for i := 0; i < 3; i++ {
		engine.recordAccessInternal(fact.ID)
	}

	frame := engine.BuildContext("test", map[string]interface{}{"content": "counted"})
	require.NotEmpty(t, frame.Facts)
	assert.Equal(t, 7, frame.Facts[0].AccessCount,
		"four stored accesses plus three in this session is seven, not four and not three")
}

func TestEngine_BuildContext_UsesProviderBoosts(t *testing.T) {
	fact1 := memory.NewFact("plain unrelated A", memory.LevelSnippet, "misc", "")
	fact2 := memory.NewFact("plain unrelated B", memory.LevelSnippet, "misc", "")
	provider := &mockBoostedProvider{
		mockProvider: newMockProvider(fact1, fact2),
		boosts:       map[string]int{fact2.ID: 50},
	}

	cfg := ctxdomain.DefaultEngineConfig()
	cfg.KeywordWeight = 0
	cfg.RecencyWeight = 0
	cfg.LevelWeight = 0
	cfg.FrequencyWeight = 1
	engine := New(cfg, provider)

	frame := engine.BuildContext("test", map[string]interface{}{"content": "nomatch"})
	require.NotEmpty(t, frame.Facts)
	assert.Equal(t, fact2.ID, frame.Facts[0].Fact.ID)
}

// --- Middleware tests ---

func TestMiddleware_InjectsContext(t *testing.T) {
	fact := memory.NewFact("Always remember: TDD first", memory.LevelProject, "process", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	// Create a simple handler
	handler := func(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "Original result"},
			},
		}, nil
	}

	// Wrap with middleware
	wrapped := engine.Middleware()(handler)

	req := mcp.CallToolRequest{}
	req.Params.Name = "test_tool"
	req.Params.Arguments = map[string]interface{}{
		"content": "TDD process",
	}

	result, err := wrapped(context.Background(), req)
	require.NoError(t, err)
	require.NotNil(t, result)
	require.Len(t, result.Content, 1)

	text := result.Content[0].(mcp.TextContent).Text
	assert.Contains(t, text, "Original result")
	assert.Contains(t, text, "[MEMORY CONTEXT]")
	assert.Contains(t, text, "TDD first")
}

func TestMiddleware_DisabledPassesThrough(t *testing.T) {
	fact := memory.NewFact("should not appear", memory.LevelProject, "test", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.Enabled = false
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "Original only"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	require.NoError(t, err)

	text := result.Content[0].(mcp.TextContent).Text
	assert.Equal(t, "Original only", text)
	assert.NotContains(t, text, "[MEMORY CONTEXT]")
}

func TestMiddleware_HandlerErrorPassedThrough(t *testing.T) {
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return nil, fmt.Errorf("handler error")
	}

	wrapped := engine.Middleware()(handler)
	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestMiddleware_ErrorResult_NoInjection(t *testing.T) {
	fact := memory.NewFact("should not appear on errors", memory.LevelProject, "test", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "Error: something failed"},
			},
			IsError: true,
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	require.NoError(t, err)

	text := result.Content[0].(mcp.TextContent).Text
	assert.NotContains(t, text, "[MEMORY CONTEXT]", "should not inject context on error results")
}

func TestMiddleware_EmptyContentSlice(t *testing.T) {
	provider := newMockProvider(memory.NewFact("test", memory.LevelProject, "a", ""))
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{},
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	require.NoError(t, err)
	// Should handle empty content gracefully
	assert.NotNil(t, result)
}

func TestMiddleware_NilResult(t *testing.T) {
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return nil, nil
	}

	wrapped := engine.Middleware()(handler)
	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	require.NoError(t, err)
	assert.Nil(t, result)
}

func TestMiddleware_SkipListTools(t *testing.T) {
	fact := memory.NewFact("Should not appear for skipped tools", memory.LevelProject, "test", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "Facts result"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	// Tools in default skip list should NOT get context injected
	skipTools := []string{"search_facts", "get_fact", "get_l0_facts", "health", "version", "dashboard"}
	for _, tool := range skipTools {
		t.Run(tool, func(t *testing.T) {
			req := mcp.CallToolRequest{}
			req.Params.Name = tool
			req.Params.Arguments = map[string]interface{}{"query": "test"}

			result, err := wrapped(context.Background(), req)
			require.NoError(t, err)
			text := result.Content[0].(mcp.TextContent).Text
			assert.NotContains(t, text, "[MEMORY CONTEXT]",
				"tool %s is in skip list, should not get context injected", tool)
		})
	}
}

func TestMiddleware_NonSkipToolGetsContext(t *testing.T) {
	fact := memory.NewFact("Important architecture fact", memory.LevelProject, "arch", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "Tool result"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	req := mcp.CallToolRequest{}
	req.Params.Name = "add_causal_node"
	req.Params.Arguments = map[string]interface{}{"content": "architecture decision"}

	result, err := wrapped(context.Background(), req)
	require.NoError(t, err)
	text := result.Content[0].(mcp.TextContent).Text
	assert.Contains(t, text, "[MEMORY CONTEXT]")
}

func TestMiddlewareExactProtocolToolsBypassLoggingAndInjectionUnconditionally(t *testing.T) {
	fact := memory.NewFact("legacy context must not enter exact JSON", memory.LevelProject, "legacy", "")
	provider := newMockProvider(fact)
	cfg := ctxdomain.DefaultEngineConfig()
	cfg.SkipTools = []string{} // A local config must not be able to remove this isolation boundary.
	cfg.BuildSkipSet()
	engine := New(cfg, provider)
	logger := &mockInteractionLogger{}
	engine.SetInteractionLogger(logger)

	const exactJSON = `{"memory_scope":{"version":1},"facts":[]}`
	handlerCalls := 0
	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		handlerCalls++
		return &mcp.CallToolResult{Content: []mcp.Content{
			mcp.TextContent{Type: "text", Text: exactJSON},
		}}, nil
	}
	wrapped := engine.Middleware()(handler)

	for _, toolName := range memory.ExactProtocolToolNames() {
		req := mcp.CallToolRequest{}
		req.Params.Name = toolName
		req.Params.Arguments = map[string]interface{}{
			"session_id": "session-one",
			"content":    "private conversation content",
		}
		result, err := wrapped(context.Background(), req)
		require.NoError(t, err)
		require.Len(t, result.Content, 1)
		require.Equal(t, exactJSON, result.Content[0].(mcp.TextContent).Text,
			"exact protocol response must remain byte-for-byte JSON")
	}

	require.Equal(t, len(memory.ExactProtocolToolNames()), handlerCalls)
	require.Zero(t, logger.count(), "exact tool arguments must not enter the legacy interaction log")
}

// --- Concurrency test ---

func TestEngine_ConcurrentAccess(t *testing.T) {
	facts := make([]*memory.Fact, 10)
	for i := 0; i < 10; i++ {
		facts[i] = memory.NewFact(fmt.Sprintf("Concurrent fact %d", i), memory.LevelProject, "arch", "")
	}

	provider := newMockProvider(facts...)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			engine.BuildContext("tool", map[string]interface{}{
				"content": fmt.Sprintf("query %d", n),
			})
		}(i)
	}
	wg.Wait()

	// Just verify no panics or races (run with -race)
	for _, f := range facts {
		count := engine.GetAccessCount(f.ID)
		assert.GreaterOrEqual(t, count, 0)
	}
}

// --- Benchmark ---

func BenchmarkEngine_BuildContext(b *testing.B) {
	facts := make([]*memory.Fact, 100)
	for i := 0; i < 100; i++ {
		facts[i] = memory.NewFact(
			"Architecture uses clean layers with dependency injection for modularity",
			memory.HierLevel(i%4), "arch", "core",
		)
	}

	provider := newMockProvider(facts...)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	args := map[string]interface{}{
		"content": "architecture clean layers dependency",
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		engine.BuildContext("test_tool", args)
	}
}

func BenchmarkMiddleware(b *testing.B) {
	facts := make([]*memory.Fact, 50)
	for i := 0; i < 50; i++ {
		facts[i] = memory.NewFact("test fact content", memory.LevelProject, "arch", "")
	}

	provider := newMockProvider(facts...)
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "result"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	req := mcp.CallToolRequest{}
	req.Params.Arguments = map[string]interface{}{"content": "test"}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = wrapped(context.Background(), req)
	}
}

// --- Mock InteractionLogger ---

type mockInteractionLogger struct {
	mu      sync.Mutex
	entries []logEntry
	failErr error // if set, Record returns this error
}

type logEntry struct {
	toolName string
	args     map[string]interface{}
}

func (m *mockInteractionLogger) Record(_ context.Context, toolName string, args map[string]interface{}) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.failErr != nil {
		return m.failErr
	}
	m.entries = append(m.entries, logEntry{toolName: toolName, args: args})
	return nil
}

func (m *mockInteractionLogger) count() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return len(m.entries)
}

func (m *mockInteractionLogger) lastToolName() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.entries) == 0 {
		return ""
	}
	return m.entries[len(m.entries)-1].toolName
}

// --- Interaction Logger Tests ---

func TestMiddleware_InteractionLogger_RecordsToolCalls(t *testing.T) {
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	logger := &mockInteractionLogger{}
	engine.SetInteractionLogger(logger)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "ok"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	req := mcp.CallToolRequest{}
	req.Params.Name = "add_fact"
	req.Params.Arguments = map[string]interface{}{"content": "test fact"}

	_, err := wrapped(context.Background(), req)
	require.NoError(t, err)

	assert.Equal(t, 1, logger.count())
	assert.Equal(t, "add_fact", logger.lastToolName())
}

func TestMiddleware_InteractionLogger_RecordsSkippedTools(t *testing.T) {
	// Even skip-list tools should be recorded in the interaction log
	// (skip-list only controls context injection, not logging)
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	logger := &mockInteractionLogger{}
	engine.SetInteractionLogger(logger)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "ok"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	// "health" is in the skip list
	req := mcp.CallToolRequest{}
	req.Params.Name = "health"

	_, err := wrapped(context.Background(), req)
	require.NoError(t, err)

	assert.Equal(t, 1, logger.count(), "skip-list tools should still be logged")
	assert.Equal(t, "health", logger.lastToolName())
}

func TestMiddleware_InteractionLogger_ErrorDoesNotBreakHandler(t *testing.T) {
	// Logger errors must be swallowed — never break the tool call
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	logger := &mockInteractionLogger{failErr: fmt.Errorf("disk full")}
	engine.SetInteractionLogger(logger)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "handler succeeded"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	req := mcp.CallToolRequest{}
	req.Params.Name = "add_fact"

	result, err := wrapped(context.Background(), req)
	require.NoError(t, err, "logger error must not propagate")
	require.NotNil(t, result)
	text := result.Content[0].(mcp.TextContent).Text
	assert.Contains(t, text, "handler succeeded")
}

func TestMiddleware_NoLogger_StillWorks(t *testing.T) {
	// Without a logger set, middleware should work normally
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)
	// engine.logger is nil — no SetInteractionLogger call

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "no logger ok"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)
	req := mcp.CallToolRequest{}
	req.Params.Name = "add_fact"

	result, err := wrapped(context.Background(), req)
	require.NoError(t, err)
	require.NotNil(t, result)
}

func TestMiddleware_InteractionLogger_MultipleToolCalls(t *testing.T) {
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	logger := &mockInteractionLogger{}
	engine.SetInteractionLogger(logger)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "ok"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	toolNames := []string{"add_fact", "search_facts", "health", "add_causal_node", "version"}
	for _, name := range toolNames {
		req := mcp.CallToolRequest{}
		req.Params.Name = name
		_, _ = wrapped(context.Background(), req)
	}

	assert.Equal(t, 5, logger.count(), "all 5 tool calls should be logged")
}

func TestMiddleware_InteractionLogger_ConcurrentCalls(t *testing.T) {
	provider := newMockProvider()
	cfg := ctxdomain.DefaultEngineConfig()
	engine := New(cfg, provider)

	logger := &mockInteractionLogger{}
	engine.SetInteractionLogger(logger)

	handler := func(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				mcp.TextContent{Type: "text", Text: "ok"},
			},
		}, nil
	}

	wrapped := engine.Middleware()(handler)

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			req := mcp.CallToolRequest{}
			req.Params.Name = fmt.Sprintf("tool_%d", n)
			_, _ = wrapped(context.Background(), req)
		}(i)
	}
	wg.Wait()

	assert.Equal(t, 20, logger.count(), "all 20 concurrent calls should be logged")
}
