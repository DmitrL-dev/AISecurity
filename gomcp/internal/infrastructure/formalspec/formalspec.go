// Package formalspec implements SEC-012 TLA+ Formal Verification.
//
// Provides a Go representation of the Event Bus pipeline and
// Decision Logger chain specifications for formal verification.
//
// The TLA+ specifications can be model-checked with the TLC checker:
//   tlc EventBusPipeline.tla
//   tlc DecisionLoggerChain.tla
//
// This package provides:
//   - Go types mirroring the TLA+ state machine
//   - Invariant checking functions
//   - Trace generation for debugging
package formalspec

import (
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// --- Event Bus Pipeline Specification ---

// PipelineState represents the Event Bus pipeline state machine.
type PipelineState string

const (
	StateInit       PipelineState = "INIT"
	StateScanning   PipelineState = "SCANNING"    // Secret Scanner (Step 0)
	StateDedup      PipelineState = "DEDUP"       // Deduplication
	StateCorrelate  PipelineState = "CORRELATE"   // Correlation Engine
	StatePersist    PipelineState = "PERSIST"      // SQLite Persist
	StateDecisionLog PipelineState = "DECISION_LOG" // Audit Decision Logger
	StateComplete   PipelineState = "COMPLETE"
	StateError      PipelineState = "ERROR"
)

// Transition represents a state transition in the pipeline.
type Transition struct {
	From      PipelineState `json:"from"`
	To        PipelineState `json:"to"`
	Guard     string        `json:"guard"`     // Condition for transition
	Action    string        `json:"action"`    // Side effect
	Timestamp time.Time     `json:"timestamp"`
}

// PipelineSpec defines all valid transitions in the Event Bus pipeline.
var PipelineSpec = []Transition{
	{From: StateInit, To: StateScanning, Guard: "event_received", Action: "run_secret_scanner"},
	{From: StateScanning, To: StateDedup, Guard: "no_secrets_found", Action: "dedup_check"},
	{From: StateScanning, To: StateError, Guard: "secret_detected", Action: "reject_event"},
	{From: StateDedup, To: StateCorrelate, Guard: "not_duplicate", Action: "run_correlation"},
	{From: StateDedup, To: StateComplete, Guard: "is_duplicate", Action: "skip"},
	{From: StateCorrelate, To: StatePersist, Guard: "correlation_done", Action: "persist_event"},
	{From: StatePersist, To: StateDecisionLog, Guard: "persisted", Action: "log_decision"},
	{From: StateDecisionLog, To: StateComplete, Guard: "logged", Action: "emit_complete"},
}

// PipelineInvariant defines a safety property that must always hold.
type PipelineInvariant struct {
	Name        string
	Description string
	Check       func(state PipelineState, history []Transition) bool
}

// PipelineInvariants are the safety properties of the Event Bus.
var PipelineInvariants = []PipelineInvariant{
	{
		Name:        "SecretScannerAlwaysFirst",
		Description: "Secret Scanner (Step 0) MUST execute before any other processing",
		Check: func(state PipelineState, history []Transition) bool {
			if len(history) == 0 {
				return true
			}
			return history[0].From == StateInit && history[0].To == StateScanning
		},
	},
	{
		Name:        "DecisionLoggerAlwaysFires",
		Description: "Every successfully processed event MUST have a decision log entry",
		Check: func(state PipelineState, history []Transition) bool {
			if state != StateComplete {
				return true // Only check on completion.
			}
			for _, t := range history {
				if t.To == StateDecisionLog {
					return true
				}
			}
			// Allow completion from dedup (skip path).
			for _, t := range history {
				if t.Guard == "is_duplicate" {
					return true
				}
			}
			return false
		},
	},
	{
		Name:        "NoSkipToComplete",
		Description: "Cannot jump directly from INIT to COMPLETE",
		Check: func(state PipelineState, history []Transition) bool {
			for _, t := range history {
				if t.From == StateInit && t.To == StateComplete {
					return false
				}
			}
			return true
		},
	},
}

// --- Decision Logger Chain Specification ---

// ChainInvariant defines a safety property for the Decision Logger chain.
type ChainInvariant struct {
	Name        string
	Description string
	Check       func(chain []ChainEntry) bool
}

// ChainEntry is a simplified chain entry for verification.
type ChainEntry struct {
	Index        int    `json:"index"`
	Hash         string `json:"hash"`
	PreviousHash string `json:"previous_hash"`
	Signature    string `json:"signature"`
}

// ChainInvariants are the safety properties of the Decision Logger.
var ChainInvariants = []ChainInvariant{
	{
		Name:        "GenesisBlockValid",
		Description: "First entry MUST have PreviousHash='genesis'",
		Check: func(chain []ChainEntry) bool {
			if len(chain) == 0 {
				return true
			}
			return chain[0].PreviousHash == "genesis"
		},
	},
	{
		Name:        "ChainContinuity",
		Description: "Each entry[i].PreviousHash MUST equal entry[i-1].Hash",
		Check: func(chain []ChainEntry) bool {
			for i := 1; i < len(chain); i++ {
				if chain[i].PreviousHash != chain[i-1].Hash {
					return false
				}
			}
			return true
		},
	},
	{
		Name:        "NoEmptyHashes",
		Description: "No entry may have an empty hash",
		Check: func(chain []ChainEntry) bool {
			for _, e := range chain {
				if e.Hash == "" {
					return false
				}
			}
			return true
		},
	},
	{
		Name:        "MonotonicIndices",
		Description: "Chain indices MUST be strictly monotonically increasing",
		Check: func(chain []ChainEntry) bool {
			for i := 1; i < len(chain); i++ {
				if chain[i].Index != chain[i-1].Index+1 {
					return false
				}
			}
			return true
		},
	},
}

// --- Verifier ---

// SpecVerifier runs formal invariant checks.
type SpecVerifier struct {
	mu     sync.Mutex
	logger *slog.Logger
	stats  VerifierStats
}

// VerifierStats tracks verification results.
type VerifierStats struct {
	TotalChecks int64 `json:"total_checks"`
	Passed      int64 `json:"passed"`
	Failed      int64 `json:"failed"`
}

// InvariantResult is the outcome of an invariant check.
type InvariantResult struct {
	Name    string `json:"name"`
	Passed  bool   `json:"passed"`
	Details string `json:"details,omitempty"`
}

// NewSpecVerifier creates a new formal spec verifier.
func NewSpecVerifier() *SpecVerifier {
	return &SpecVerifier{
		logger: slog.Default().With("component", "sec-012-formalspec"),
	}
}

// VerifyPipeline checks all Event Bus pipeline invariants.
func (v *SpecVerifier) VerifyPipeline(state PipelineState, history []Transition) []InvariantResult {
	var results []InvariantResult
	for _, inv := range PipelineInvariants {
		v.mu.Lock()
		v.stats.TotalChecks++
		passed := inv.Check(state, history)
		if passed {
			v.stats.Passed++
		} else {
			v.stats.Failed++
		}
		v.mu.Unlock()

		results = append(results, InvariantResult{
			Name:   inv.Name,
			Passed: passed,
			Details: fmt.Sprintf("%s: %v", inv.Description, passed),
		})
	}
	return results
}

// VerifyChain checks all Decision Logger chain invariants.
func (v *SpecVerifier) VerifyChain(chain []ChainEntry) []InvariantResult {
	var results []InvariantResult
	for _, inv := range ChainInvariants {
		v.mu.Lock()
		v.stats.TotalChecks++
		passed := inv.Check(chain)
		if passed {
			v.stats.Passed++
		} else {
			v.stats.Failed++
		}
		v.mu.Unlock()

		results = append(results, InvariantResult{
			Name:   inv.Name,
			Passed: passed,
			Details: fmt.Sprintf("%s: %v", inv.Description, passed),
		})
	}
	return results
}

// Stats returns verification metrics.
func (v *SpecVerifier) Stats() VerifierStats {
	v.mu.Lock()
	defer v.mu.Unlock()
	return v.stats
}
