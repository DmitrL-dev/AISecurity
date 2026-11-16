// Package resources provides MCP resource implementations.
package resources

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/session"
)

// Provider serves MCP resources (rlm://state, rlm://facts, rlm://stats).
type Provider struct {
	factStore  memory.FactStore
	stateStore session.StateStore
	scope      rlmscope.Scope
}

// NewProvider creates a new resource Provider.
func NewProvider(factStore memory.FactStore, stateStore session.StateStore) *Provider {
	return &Provider{
		factStore:  factStore,
		stateStore: stateStore,
		scope:      rlmscope.Default(),
	}
}

// WithScope binds resource reads to a tenant/project memory boundary.
func (p *Provider) WithScope(sc rlmscope.Scope) *Provider {
	p.scope = sc.Normalize()
	return p
}

func (p *Provider) scopedContext(ctx context.Context) context.Context {
	if sc, ok := rlmscope.Lookup(ctx); ok {
		return rlmscope.WithScope(ctx, sc)
	}
	return rlmscope.WithScope(ctx, p.scope)
}

// GetState returns the current cognitive state for a session as JSON.
func (p *Provider) GetState(ctx context.Context, sessionID string) (string, error) {
	ctx = p.scopedContext(ctx)
	state, _, err := p.stateStore.Load(ctx, sessionID, nil)
	if err != nil {
		return "", fmt.Errorf("load state: %w", err)
	}
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return "", fmt.Errorf("marshal state: %w", err)
	}
	return string(data), nil
}

// GetFacts returns L0 facts as JSON.
func (p *Provider) GetFacts(ctx context.Context) (string, error) {
	ctx = p.scopedContext(ctx)
	facts, err := p.factStore.ListByLevel(ctx, memory.LevelProject)
	if err != nil {
		return "", fmt.Errorf("list L0 facts: %w", err)
	}
	data, err := json.MarshalIndent(facts, "", "  ")
	if err != nil {
		return "", fmt.Errorf("marshal facts: %w", err)
	}
	return string(data), nil
}

// GetStats returns fact store statistics as JSON.
func (p *Provider) GetStats(ctx context.Context) (string, error) {
	ctx = p.scopedContext(ctx)
	stats, err := p.factStore.Stats(ctx)
	if err != nil {
		return "", fmt.Errorf("get stats: %w", err)
	}
	data, err := json.MarshalIndent(stats, "", "  ")
	if err != nil {
		return "", fmt.Errorf("marshal stats: %w", err)
	}
	return string(data), nil
}
