// Package resources provides MCP resource implementations.
package resources

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/sentinel-community/gomcp/internal/domain/session"
)

// Provider serves MCP resources (rlm://state, rlm://facts, rlm://stats).
type Provider struct {
	factStore  memory.FactStore
	stateStore session.StateStore
}

// NewProvider creates a new resource Provider.
func NewProvider(factStore memory.FactStore, stateStore session.StateStore) *Provider {
	return &Provider{
		factStore:  factStore,
		stateStore: stateStore,
	}
}

// GetState returns the current cognitive state for a session as JSON.
func (p *Provider) GetState(ctx context.Context, sessionID string) (string, error) {
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
