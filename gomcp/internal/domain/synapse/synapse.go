// Package synapse defines domain entities for semantic fact connections.
package synapse

import (
	"context"
	"time"
)

// Status represents the state of a synapse link.
type Status string

const (
	StatusPending  Status = "PENDING"
	StatusVerified Status = "VERIFIED"
	StatusRejected Status = "REJECTED"
)

// Synapse represents a semantic connection between two facts.
type Synapse struct {
	ID         int64     `json:"id"`
	TenantID   string    `json:"tenant_id,omitempty"`
	ProjectID  string    `json:"project_id,omitempty"`
	FactIDA    string    `json:"fact_id_a"`
	FactIDB    string    `json:"fact_id_b"`
	Confidence float64   `json:"confidence"`
	Status     Status    `json:"status"`
	CreatedAt  time.Time `json:"created_at"`
}

// SynapseStore defines the interface for synapse persistence.
type SynapseStore interface {
	// Create inserts a new synapse.
	Create(ctx context.Context, factIDA, factIDB string, confidence float64) (int64, error)

	// ListPending returns all PENDING synapses.
	ListPending(ctx context.Context, limit int) ([]*Synapse, error)

	// Accept transitions a synapse to VERIFIED.
	Accept(ctx context.Context, id int64) error

	// Reject transitions a synapse to REJECTED.
	Reject(ctx context.Context, id int64) error

	// ListVerified returns all VERIFIED synapses.
	ListVerified(ctx context.Context) ([]*Synapse, error)

	// Count returns total synapse counts by status.
	Count(ctx context.Context) (pending, verified, rejected int, err error)

	// Exists checks if a synapse already exists between two facts (any direction).
	Exists(ctx context.Context, factIDA, factIDB string) (bool, error)
}
