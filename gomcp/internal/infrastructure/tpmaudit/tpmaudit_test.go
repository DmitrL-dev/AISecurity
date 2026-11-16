package tpmaudit

import (
	"os"
	"testing"
)

func TestNewSealedLogger(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	if logger.ChainLength() != 0 {
		t.Errorf("chain length = %d, want 0", logger.ChainLength())
	}

	stats := logger.Stats()
	if stats.Mode != SealSoftware {
		t.Errorf("mode = %s, want software (no TPM in CI)", stats.Mode)
	}
}

func TestLogDecision(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	sealed, err := logger.LogDecision(DecisionEntry{
		Action:   "ingest",
		Decision: "allow",
		Reason:   "event passed secret scanner",
		EventID:  "EVT-001",
	})
	if err != nil {
		t.Fatalf("LogDecision: %v", err)
	}

	if sealed.Hash == "" {
		t.Error("hash is empty")
	}
	if sealed.Signature == "" {
		t.Error("signature is empty")
	}
	if sealed.Entry.PreviousHash != "genesis" {
		t.Errorf("first entry previous_hash = %s, want genesis", sealed.Entry.PreviousHash)
	}
	if sealed.ChainIdx != 0 {
		t.Errorf("chain_idx = %d, want 0", sealed.ChainIdx)
	}
}

func TestChainLinking(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	s1, _ := logger.LogDecision(DecisionEntry{Action: "ingest", Decision: "allow", Reason: "ok"})
	s2, _ := logger.LogDecision(DecisionEntry{Action: "correlate", Decision: "escalate", Reason: "high severity"})
	s3, _ := logger.LogDecision(DecisionEntry{Action: "respond", Decision: "allow", Reason: "playbook matched"})

	// Verify chain links.
	if s2.Entry.PreviousHash != s1.Hash {
		t.Error("entry 2 not linked to entry 1")
	}
	if s3.Entry.PreviousHash != s2.Hash {
		t.Error("entry 3 not linked to entry 2")
	}

	if logger.ChainLength() != 3 {
		t.Errorf("chain length = %d, want 3", logger.ChainLength())
	}
}

func TestVerifyChain_Valid(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	logger.LogDecision(DecisionEntry{Action: "ingest", Decision: "allow", Reason: "ok"})
	logger.LogDecision(DecisionEntry{Action: "correlate", Decision: "allow", Reason: "ok"})
	logger.LogDecision(DecisionEntry{Action: "respond", Decision: "allow", Reason: "ok"})

	result := logger.VerifyChain()
	if !result.Valid {
		t.Errorf("chain invalid: %s at index %d", result.BrokenReason, result.BrokenAtIndex)
	}
	if result.VerifiedCount != 3 {
		t.Errorf("verified = %d, want 3", result.VerifiedCount)
	}
}

func TestVerifyChain_Tampered(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	logger.LogDecision(DecisionEntry{Action: "ingest", Decision: "allow", Reason: "ok"})
	logger.LogDecision(DecisionEntry{Action: "correlate", Decision: "allow", Reason: "ok"})

	// Tamper with chain.
	logger.chain[1].Hash = "tampered-hash"

	result := logger.VerifyChain()
	if result.Valid {
		t.Error("expected chain to be invalid after tampering")
	}
	if result.BrokenAtIndex != 1 {
		t.Errorf("broken at = %d, want 1", result.BrokenAtIndex)
	}
}

func TestPCRExtension(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	s1, _ := logger.LogDecision(DecisionEntry{Action: "a", Decision: "allow", Reason: "ok"})
	s2, _ := logger.LogDecision(DecisionEntry{Action: "b", Decision: "allow", Reason: "ok"})

	// PCR values should be different (extended with each entry).
	if s1.PCRValue == s2.PCRValue {
		t.Error("PCR values should differ after extension")
	}
	// PCR should not be the initial zero value.
	if s1.PCRValue == "0000000000000000000000000000000000000000000000000000000000000000" {
		t.Error("PCR should have been extended from zero")
	}
}

func TestPersistence(t *testing.T) {
	dir := t.TempDir()

	// Write entries.
	{
		logger, err := NewSealedLogger(dir, "test-secret")
		if err != nil {
			t.Fatalf("NewSealedLogger: %v", err)
		}
		logger.LogDecision(DecisionEntry{Action: "ingest", Decision: "allow", Reason: "ok"})
		logger.LogDecision(DecisionEntry{Action: "correlate", Decision: "deny", Reason: "blocked"})
		logger.Close()
	}

	// Reopen and verify chain was loaded.
	{
		logger, err := NewSealedLogger(dir, "test-secret")
		if err != nil {
			t.Fatalf("NewSealedLogger reopen: %v", err)
		}
		defer logger.Close()

		if logger.ChainLength() != 2 {
			t.Errorf("chain length after reopen = %d, want 2", logger.ChainLength())
		}
	}

	// Verify file exists.
	if _, err := os.Stat(dir + "/decisions_sealed.jsonl"); err != nil {
		t.Errorf("log file not found: %v", err)
	}
}

func TestStats(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewSealedLogger(dir, "test-secret")
	if err != nil {
		t.Fatalf("NewSealedLogger: %v", err)
	}
	defer logger.Close()

	logger.LogDecision(DecisionEntry{Action: "a", Decision: "allow", Reason: "ok"})
	logger.LogDecision(DecisionEntry{Action: "b", Decision: "deny", Reason: "blocked"})

	stats := logger.Stats()
	if stats.TotalEntries != 2 {
		t.Errorf("total_entries = %d, want 2", stats.TotalEntries)
	}
	if !stats.ChainIntegrity {
		t.Error("chain integrity should be true")
	}
}
