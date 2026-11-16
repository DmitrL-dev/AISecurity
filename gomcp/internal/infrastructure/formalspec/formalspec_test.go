package formalspec

import (
	"testing"
)

func TestVerifyPipeline_ValidTrace(t *testing.T) {
	v := NewSpecVerifier()

	history := []Transition{
		{From: StateInit, To: StateScanning, Guard: "event_received"},
		{From: StateScanning, To: StateDedup, Guard: "no_secrets_found"},
		{From: StateDedup, To: StateCorrelate, Guard: "not_duplicate"},
		{From: StateCorrelate, To: StatePersist, Guard: "correlation_done"},
		{From: StatePersist, To: StateDecisionLog, Guard: "persisted"},
		{From: StateDecisionLog, To: StateComplete, Guard: "logged"},
	}

	results := v.VerifyPipeline(StateComplete, history)
	for _, r := range results {
		if !r.Passed {
			t.Errorf("invariant %s failed: %s", r.Name, r.Details)
		}
	}
}

func TestVerifyPipeline_SecretDetected(t *testing.T) {
	v := NewSpecVerifier()

	history := []Transition{
		{From: StateInit, To: StateScanning, Guard: "event_received"},
		{From: StateScanning, To: StateError, Guard: "secret_detected"},
	}

	results := v.VerifyPipeline(StateError, history)
	for _, r := range results {
		if !r.Passed {
			t.Errorf("invariant %s failed for secret path", r.Name)
		}
	}
}

func TestVerifyPipeline_DedupSkip(t *testing.T) {
	v := NewSpecVerifier()

	history := []Transition{
		{From: StateInit, To: StateScanning, Guard: "event_received"},
		{From: StateScanning, To: StateDedup, Guard: "no_secrets_found"},
		{From: StateDedup, To: StateComplete, Guard: "is_duplicate"},
	}

	results := v.VerifyPipeline(StateComplete, history)
	for _, r := range results {
		if !r.Passed {
			t.Errorf("invariant %s failed for dedup skip", r.Name)
		}
	}
}

func TestVerifyPipeline_SkipScanner_Violation(t *testing.T) {
	v := NewSpecVerifier()

	// Invalid: skips secret scanner.
	history := []Transition{
		{From: StateInit, To: StateDedup, Guard: "event_received"},
	}

	results := v.VerifyPipeline(StateDedup, history)
	scannerInvariant := results[0] // SecretScannerAlwaysFirst
	if scannerInvariant.Passed {
		t.Error("should fail when scanner is skipped")
	}
}

func TestVerifyChain_Valid(t *testing.T) {
	v := NewSpecVerifier()

	chain := []ChainEntry{
		{Index: 0, Hash: "aaa", PreviousHash: "genesis"},
		{Index: 1, Hash: "bbb", PreviousHash: "aaa"},
		{Index: 2, Hash: "ccc", PreviousHash: "bbb"},
	}

	results := v.VerifyChain(chain)
	for _, r := range results {
		if !r.Passed {
			t.Errorf("chain invariant %s failed: %s", r.Name, r.Details)
		}
	}
}

func TestVerifyChain_BrokenLink(t *testing.T) {
	v := NewSpecVerifier()

	chain := []ChainEntry{
		{Index: 0, Hash: "aaa", PreviousHash: "genesis"},
		{Index: 1, Hash: "bbb", PreviousHash: "WRONG"},
	}

	results := v.VerifyChain(chain)
	continuity := results[1] // ChainContinuity
	if continuity.Passed {
		t.Error("should fail on broken chain link")
	}
}

func TestVerifyChain_BadGenesis(t *testing.T) {
	v := NewSpecVerifier()

	chain := []ChainEntry{
		{Index: 0, Hash: "aaa", PreviousHash: "not-genesis"},
	}

	results := v.VerifyChain(chain)
	genesis := results[0]
	if genesis.Passed {
		t.Error("should fail on bad genesis")
	}
}

func TestStats(t *testing.T) {
	v := NewSpecVerifier()

	v.VerifyPipeline(StateComplete, []Transition{
		{From: StateInit, To: StateScanning, Guard: "event_received"},
	})
	v.VerifyChain([]ChainEntry{
		{Index: 0, Hash: "a", PreviousHash: "genesis"},
	})

	stats := v.Stats()
	if stats.TotalChecks != 7 { // 3 pipeline + 4 chain
		t.Errorf("total = %d, want 7", stats.TotalChecks)
	}
}
