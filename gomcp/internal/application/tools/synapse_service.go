package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/synapse"
)

// SynapseService implements MCP tool logic for synapse operations.
type SynapseService struct {
	store    synapse.SynapseStore
	recorder DecisionRecorder // v3.7: tamper-evident trace
}

// NewSynapseService creates a new SynapseService.
func NewSynapseService(store synapse.SynapseStore) *SynapseService {
	return &SynapseService{store: store}
}

// SuggestSynapsesResult contains a pending synapse for architect review.
type SuggestSynapsesResult struct {
	ID         int64   `json:"id"`
	FactIDA    string  `json:"fact_id_a"`
	FactIDB    string  `json:"fact_id_b"`
	Confidence float64 `json:"confidence"`
}

// SuggestSynapses returns pending synapses for architect approval.
func (s *SynapseService) SuggestSynapses(ctx context.Context, limit int) ([]SuggestSynapsesResult, error) {
	if limit <= 0 {
		limit = 20
	}
	pending, err := s.store.ListPending(ctx, limit)
	if err != nil {
		return nil, fmt.Errorf("list pending: %w", err)
	}

	results := make([]SuggestSynapsesResult, len(pending))
	for i, syn := range pending {
		results[i] = SuggestSynapsesResult{
			ID:         syn.ID,
			FactIDA:    syn.FactIDA,
			FactIDB:    syn.FactIDB,
			Confidence: syn.Confidence,
		}
	}
	return results, nil
}

// AcceptSynapse transitions a synapse from PENDING to VERIFIED.
// Only VERIFIED synapses influence context ranking.
func (s *SynapseService) AcceptSynapse(ctx context.Context, id int64) error {
	err := s.store.Accept(ctx, id)
	if err == nil && s.recorder != nil {
		s.recorder.RecordDecision("SYNAPSE", "ACCEPT_SYNAPSE", fmt.Sprintf("synapse_id=%d", id))
	}
	return err
}

// RejectSynapse transitions a synapse from PENDING to REJECTED.
func (s *SynapseService) RejectSynapse(ctx context.Context, id int64) error {
	err := s.store.Reject(ctx, id)
	if err == nil && s.recorder != nil {
		s.recorder.RecordDecision("SYNAPSE", "REJECT_SYNAPSE", fmt.Sprintf("synapse_id=%d", id))
	}
	return err
}

// SynapseStats returns counts by status.
type SynapseStats struct {
	Pending  int `json:"pending"`
	Verified int `json:"verified"`
	Rejected int `json:"rejected"`
}

// GetStats returns synapse counts.
func (s *SynapseService) GetStats(ctx context.Context) (*SynapseStats, error) {
	p, v, r, err := s.store.Count(ctx)
	if err != nil {
		return nil, err
	}
	return &SynapseStats{Pending: p, Verified: v, Rejected: r}, nil
}
