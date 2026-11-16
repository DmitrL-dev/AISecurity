// Package tools provides application-level tool services.
// This file adds the Intent Distiller MCP tool integration (DIP H0.2).
package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/intent"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// IntentService provides MCP tool logic for intent distillation.
type IntentService struct {
	distiller *intent.Distiller
	embedder  vectorstore.Embedder
}

// NewIntentService creates a new IntentService.
// If embedder is nil, the service will be unavailable.
func NewIntentService(embedder vectorstore.Embedder) *IntentService {
	if embedder == nil {
		return &IntentService{}
	}

	embedFn := func(ctx context.Context, text string) ([]float64, error) {
		return embedder.Embed(ctx, text)
	}

	return &IntentService{
		distiller: intent.NewDistiller(embedFn, nil),
		embedder:  embedder,
	}
}

// IsAvailable returns true if the intent distiller is ready.
func (s *IntentService) IsAvailable() bool {
	return s.distiller != nil && s.embedder != nil
}

// DistillIntentParams holds parameters for the distill_intent tool.
type DistillIntentParams struct {
	Text string `json:"text"`
}

// DistillIntent performs recursive intent distillation on user text.
func (s *IntentService) DistillIntent(ctx context.Context, params DistillIntentParams) (*intent.DistillResult, error) {
	if !s.IsAvailable() {
		return nil, fmt.Errorf("intent distiller not available (no embedder configured)")
	}
	return s.distiller.Distill(ctx, params.Text)
}
