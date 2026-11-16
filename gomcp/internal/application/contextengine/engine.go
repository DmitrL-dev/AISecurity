// Package contextengine implements the Proactive Context Engine.
// It automatically injects relevant memory facts into every MCP tool response
// via ToolHandlerMiddleware, so the LLM always has context without asking.
package contextengine

import (
	"context"
	"log"
	"strings"
	"sync"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	ctxdomain "github.com/syntrex/gomcp/internal/domain/context"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// InteractionLogger records tool calls for crash-safe memory.
// Implementations must be safe for concurrent use.
type InteractionLogger interface {
	Record(ctx context.Context, toolName string, args map[string]interface{}) error
}

type boostedFactProvider interface {
	GetRelevantFactsWithBoost(ctx context.Context, args map[string]interface{}) ([]*memory.Fact, map[string]int, error)
}

// Engine is the Proactive Context Engine. It scores facts by relevance,
// selects the top ones within a token budget, and injects them into
// every tool response as a [MEMORY CONTEXT] block.
type Engine struct {
	config   ctxdomain.EngineConfig
	scorer   *ctxdomain.RelevanceScorer
	provider ctxdomain.FactProvider
	logger   InteractionLogger // optional, nil = no logging
	scope    rlmscope.Scope

	mu           sync.RWMutex
	accessCounts map[string]int // in-memory access counters per fact ID
}

// New creates a new Proactive Context Engine.
func New(cfg ctxdomain.EngineConfig, provider ctxdomain.FactProvider) *Engine {
	return &Engine{
		config:       cfg,
		scorer:       ctxdomain.NewRelevanceScorer(cfg),
		provider:     provider,
		scope:        rlmscope.Default(),
		accessCounts: make(map[string]int),
	}
}

// WithScope binds engine-side logging to a tenant/project memory boundary.
func (e *Engine) WithScope(sc rlmscope.Scope) *Engine {
	e.scope = sc.Normalize()
	return e
}

// SetInteractionLogger attaches an optional interaction logger for crash-safe
// tool call recording. If set, every tool call passing through the middleware
// will be recorded fire-and-forget (errors logged, never propagated).
func (e *Engine) SetInteractionLogger(l InteractionLogger) {
	e.logger = l
}

// IsEnabled returns whether the engine is active.
func (e *Engine) IsEnabled() bool {
	return e.config.Enabled
}

// BuildContext scores and selects relevant facts for the given tool call,
// returning a ContextFrame ready for formatting and injection. It uses the
// engine's pinned scope (back-compat for direct/test callers); the middleware
// path uses buildContextScoped to honor the per-request tenant/project scope.
func (e *Engine) BuildContext(toolName string, args map[string]interface{}) *ctxdomain.ContextFrame {
	return e.buildContextScoped(context.Background(), toolName, args)
}

// requestScope returns the per-request scope resolved by the scope middleware,
// falling back to the engine's pinned scope when the context carries none.
func (e *Engine) requestScope(ctx context.Context) context.Context {
	if _, ok := rlmscope.Lookup(ctx); ok {
		return ctx
	}
	return rlmscope.WithScope(ctx, e.scope)
}

func (e *Engine) buildContextScoped(ctx context.Context, toolName string, args map[string]interface{}) *ctxdomain.ContextFrame {
	frame := ctxdomain.NewContextFrame(toolName, e.config.TokenBudget)

	if !e.config.Enabled {
		return frame
	}

	// Extract keywords from all string arguments
	keywords := e.extractKeywordsFromArgs(args)

	// Get candidate facts from provider. Newer providers may also return
	// per-request boosts for facts reached through verified memory links.
	var boosts map[string]int
	var facts []*memory.Fact
	var err error
	if provider, ok := e.provider.(boostedFactProvider); ok {
		facts, boosts, err = provider.GetRelevantFactsWithBoost(ctx, args)
	} else {
		facts, err = e.provider.GetRelevantFacts(args)
	}
	if err != nil || len(facts) == 0 {
		return frame
	}

	// Access counts: what the database remembers, plus what this process has seen.
	//
	// The in-memory map alone is what ranking used to get, and it is created empty in New() — so the
	// frequency term (weight 0.15, scaled against a ceiling of 100 accesses) was zero for every fact
	// at the start of every session, and a ceiling of 100 is unreachable inside one. The durable
	// counter `hit_count` was being written by TouchFact all along and read by nobody. Summing the two
	// keeps this session's reinforcement immediate while giving the term the history it was scaled for.
	e.mu.RLock()
	countsCopy := make(map[string]int, len(e.accessCounts)+len(facts))
	for _, f := range facts {
		if f != nil && f.HitCount > 0 {
			countsCopy[f.ID] = f.HitCount
		}
	}
	for k, v := range e.accessCounts {
		countsCopy[k] += v
	}
	e.mu.RUnlock()
	for id, boost := range boosts {
		countsCopy[id] += boost
	}

	// Score and rank facts
	ranked := e.scorer.RankFacts(facts, keywords, countsCopy)

	// Fill frame within token budget and max facts
	added := 0
	for _, sf := range ranked {
		if added >= e.config.MaxFacts {
			break
		}
		if frame.AddFact(sf) {
			added++
			// Record access for reinforcement
			e.recordAccessInternal(sf.Fact.ID)
			e.provider.RecordAccess(sf.Fact.ID)
		}
	}

	return frame
}

// GetAccessCount returns the internal access count for a fact.
func (e *Engine) GetAccessCount(factID string) int {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.accessCounts[factID]
}

// recordAccessInternal increments the in-memory access counter.
func (e *Engine) recordAccessInternal(factID string) {
	e.mu.Lock()
	e.accessCounts[factID]++
	e.mu.Unlock()
}

// bypassExactProtocolTool is deliberately not configurable. These tools carry
// strict JSON envelopes and explicit memory authority; logging their arguments
// would copy session content into the legacy interaction log, and appending a
// context block would corrupt the protocol response. A user-supplied skip list
// must not be able to re-enable either side effect.
func bypassExactProtocolTool(toolName string) bool {
	return memory.IsExactProtocolTool(toolName)
}

// Middleware returns a ToolHandlerMiddleware that wraps every tool handler
// to inject relevant memory context into the response and optionally
// record tool calls to the interaction log for crash-safe memory.
func (e *Engine) Middleware() server.ToolHandlerMiddleware {
	return func(next server.ToolHandlerFunc) server.ToolHandlerFunc {
		return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			if bypassExactProtocolTool(req.Params.Name) {
				return next(ctx, req)
			}

			// Fire-and-forget: record this tool call in the interaction log.
			// This runs BEFORE the handler so the record is persisted even if
			// the process is killed mid-handler.
			if e.logger != nil {
				if logErr := e.logger.Record(e.requestScope(ctx), req.Params.Name, req.GetArguments()); logErr != nil {
					log.Printf("contextengine: interaction log error: %v", logErr)
				}
			}

			// Call the original handler
			result, err := next(ctx, req)
			if err != nil {
				return result, err
			}

			// Don't inject on nil result, error results, or empty content
			if result == nil || result.IsError || len(result.Content) == 0 {
				return result, nil
			}

			// Don't inject if engine is disabled
			if !e.IsEnabled() {
				return result, nil
			}

			// Don't inject for tools in the skip list
			if e.config.ShouldSkip(req.Params.Name) {
				return result, nil
			}

			// Build context frame (honors the per-request scope carried by ctx)
			frame := e.buildContextScoped(ctx, req.Params.Name, req.GetArguments())
			contextText := frame.Format()
			if contextText == "" {
				return result, nil
			}

			// Append context to the last text content block
			e.appendContextToResult(result, contextText)

			return result, nil
		}
	}
}

// appendContextToResult appends the context text to the last TextContent in the result.
func (e *Engine) appendContextToResult(result *mcp.CallToolResult, contextText string) {
	for i := len(result.Content) - 1; i >= 0; i-- {
		if tc, ok := result.Content[i].(mcp.TextContent); ok {
			tc.Text += contextText
			result.Content[i] = tc
			return
		}
	}

	// No text content found — add a new one
	result.Content = append(result.Content, mcp.TextContent{
		Type: "text",
		Text: contextText,
	})
}

// extractKeywordsFromArgs extracts keywords from all string values in the arguments map.
func (e *Engine) extractKeywordsFromArgs(args map[string]interface{}) []string {
	if len(args) == 0 {
		return nil
	}

	var allText strings.Builder
	for _, v := range args {
		switch val := v.(type) {
		case string:
			allText.WriteString(val)
			allText.WriteString(" ")
		}
	}

	return ctxdomain.ExtractKeywords(allText.String())
}
