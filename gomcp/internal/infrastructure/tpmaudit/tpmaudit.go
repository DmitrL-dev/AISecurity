// Package tpmaudit implements SEC-006 TPM-Sealed Decision Logger.
//
// Provides hardware-backed integrity for the audit decision chain:
//   - Each decision entry is signed with a TPM-bound key
//   - PCR values extended with each entry hash
//   - Quotes can verify the entire chain hasn't been tampered
//
// When TPM is unavailable (dev/CI): falls back to software HMAC signing
// with a configurable secret key.
//
// Architecture:
//
//	Decision Entry → SHA-256 Hash → TPM Sign → PCR Extend → Sealed Entry
//	                                   ↓
//	                          Chain Verification via TPM Quote
package tpmaudit

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"
)

// SealMode defines the sealing backend.
type SealMode string

const (
	SealTPM      SealMode = "tpm"      // Hardware TPM 2.0
	SealSoftware SealMode = "software" // HMAC fallback for dev/CI
)

// DecisionEntry is a single audit decision record.
type DecisionEntry struct {
	ID            string    `json:"id"`
	Timestamp     time.Time `json:"timestamp"`
	Action        string    `json:"action"`         // ingest, correlate, respond, playbook
	Decision      string    `json:"decision"`        // allow, deny, escalate
	Reason        string    `json:"reason"`
	EventID       string    `json:"event_id,omitempty"`
	IncidentID    string    `json:"incident_id,omitempty"`
	Operator      string    `json:"operator,omitempty"`
	PreviousHash  string    `json:"previous_hash"`   // Chain link
}

// SealedEntry wraps a decision with cryptographic sealing.
type SealedEntry struct {
	Entry     DecisionEntry `json:"entry"`
	Hash      string        `json:"hash"`       // SHA-256 of entry
	Signature string        `json:"signature"`   // TPM or HMAC signature
	PCRValue  string        `json:"pcr_value"`   // Extended PCR (or simulated)
	SealMode  SealMode      `json:"seal_mode"`
	ChainIdx  int64         `json:"chain_idx"`
}

// ChainVerification holds the result of verifying an audit chain.
type ChainVerification struct {
	Valid          bool      `json:"valid"`
	TotalEntries   int       `json:"total_entries"`
	VerifiedCount  int       `json:"verified_count"`
	BrokenAtIndex  int       `json:"broken_at_index,omitempty"`
	BrokenReason   string    `json:"broken_reason,omitempty"`
	VerifiedAt     time.Time `json:"verified_at"`
	Mode           SealMode  `json:"mode"`
}

// SealedLogger provides TPM-sealed (or HMAC-fallback) audit logging.
type SealedLogger struct {
	mu          sync.Mutex
	mode        SealMode
	hmacKey     []byte        // Used in software mode
	chain       []SealedEntry // In-memory chain (also persisted)
	currentPCR  string        // Simulated PCR value
	logFile     *os.File
	logger      *slog.Logger
	stats       LoggerStats
}

// LoggerStats tracks audit logger metrics.
type LoggerStats struct {
	TotalEntries    int64     `json:"total_entries"`
	LastEntry       time.Time `json:"last_entry"`
	ChainIntegrity  bool      `json:"chain_integrity"`
	Mode            SealMode  `json:"mode"`
	StartedAt       time.Time `json:"started_at"`
}

// NewSealedLogger creates a TPM-sealed decision logger.
// Falls back to software HMAC if TPM is unavailable.
func NewSealedLogger(auditDir string, hmacSecret string) (*SealedLogger, error) {
	mode := SealTPM
	var hmacKey []byte

	// Try to open TPM device.
	if !tpmAvailable() {
		mode = SealSoftware
		if hmacSecret == "" {
			// SEC (pre-launch audit 18.06): no hardcoded fallback key — a known constant
			// would make software-mode audit signatures forgeable. Fail closed; the
			// operator must supply SOC_HMAC_SECRET (matches auth/secret.go + the keyed
			// decision chain). This package is currently unwired, but harden it now.
			return nil, fmt.Errorf("tpmaudit: software mode requires a non-empty HMAC secret (set SOC_HMAC_SECRET)")
		}
		hmacKey = []byte(hmacSecret)
	}

	// Open audit log file.
	logPath := auditDir + "/decisions_sealed.jsonl"
	f, err := os.OpenFile(logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		return nil, fmt.Errorf("tpmaudit: open %s: %w", logPath, err)
	}

	logger := &SealedLogger{
		mode:       mode,
		hmacKey:    hmacKey,
		currentPCR: "0000000000000000000000000000000000000000000000000000000000000000",
		logFile:    f,
		logger:     slog.Default().With("component", "sec-006-tpmaudit"),
		stats: LoggerStats{
			ChainIntegrity: true,
			Mode:           mode,
			StartedAt:      time.Now(),
		},
	}

	// Load existing chain from file.
	logger.loadExistingChain(logPath)

	logger.logger.Info("sealed decision logger initialized",
		"mode", mode,
		"chain_length", len(logger.chain),
		"log_path", logPath,
	)

	return logger, nil
}

// LogDecision seals and persists a decision entry.
func (sl *SealedLogger) LogDecision(entry DecisionEntry) (*SealedEntry, error) {
	sl.mu.Lock()
	defer sl.mu.Unlock()

	// Set chain link.
	if len(sl.chain) > 0 {
		entry.PreviousHash = sl.chain[len(sl.chain)-1].Hash
	} else {
		entry.PreviousHash = "genesis"
	}

	entry.Timestamp = time.Now()
	if entry.ID == "" {
		entry.ID = fmt.Sprintf("DEC-%d", time.Now().UnixNano())
	}

	// Hash the entry.
	entryBytes, err := json.Marshal(entry)
	if err != nil {
		return nil, fmt.Errorf("tpmaudit: marshal entry: %w", err)
	}
	hash := sha256.Sum256(entryBytes)
	hashHex := hex.EncodeToString(hash[:])

	// Sign with TPM or HMAC.
	var signature string
	switch sl.mode {
	case SealTPM:
		signature, err = sl.tpmSign(hash[:])
		if err != nil {
			// Fallback to software if TPM fails at runtime.
			sl.logger.Warn("TPM sign failed, falling back to HMAC", "error", err)
			signature = sl.hmacSign(hash[:])
			sl.mode = SealSoftware
		}
	case SealSoftware:
		signature = sl.hmacSign(hash[:])
	}

	// Extend PCR (simulated in software mode).
	sl.extendPCR(hash[:])

	sealed := SealedEntry{
		Entry:     entry,
		Hash:      hashHex,
		Signature: signature,
		PCRValue:  sl.currentPCR,
		SealMode:  sl.mode,
		ChainIdx:  int64(len(sl.chain)),
	}

	// Persist to file.
	line, _ := json.Marshal(sealed)
	line = append(line, '\n')
	if _, err := sl.logFile.Write(line); err != nil {
		return nil, fmt.Errorf("tpmaudit: write log: %w", err)
	}

	sl.chain = append(sl.chain, sealed)
	sl.stats.TotalEntries++
	sl.stats.LastEntry = time.Now()

	sl.logger.Info("decision sealed",
		"id", entry.ID,
		"action", entry.Action,
		"decision", entry.Decision,
		"chain_idx", sealed.ChainIdx,
		"mode", sl.mode,
	)

	return &sealed, nil
}

// VerifyChain validates the entire decision chain integrity.
func (sl *SealedLogger) VerifyChain() ChainVerification {
	sl.mu.Lock()
	defer sl.mu.Unlock()

	result := ChainVerification{
		Valid:        true,
		TotalEntries: len(sl.chain),
		VerifiedAt:   time.Now(),
		Mode:         sl.mode,
	}

	runningPCR := "0000000000000000000000000000000000000000000000000000000000000000"

	for i, sealed := range sl.chain {
		// Verify hash.
		entryBytes, _ := json.Marshal(sealed.Entry)
		hash := sha256.Sum256(entryBytes)
		hashHex := hex.EncodeToString(hash[:])

		if hashHex != sealed.Hash {
			result.Valid = false
			result.BrokenAtIndex = i
			result.BrokenReason = fmt.Sprintf("hash mismatch at index %d", i)
			sl.stats.ChainIntegrity = false
			return result
		}

		// Verify chain link.
		if i > 0 {
			if sealed.Entry.PreviousHash != sl.chain[i-1].Hash {
				result.Valid = false
				result.BrokenAtIndex = i
				result.BrokenReason = fmt.Sprintf("chain break at index %d: previous_hash mismatch", i)
				sl.stats.ChainIntegrity = false
				return result
			}
		} else {
			if sealed.Entry.PreviousHash != "genesis" {
				result.Valid = false
				result.BrokenAtIndex = 0
				result.BrokenReason = "genesis entry has wrong previous_hash"
				sl.stats.ChainIntegrity = false
				return result
			}
		}

		// Verify signature.
		if sealed.SealMode == SealSoftware {
			expectedSig := sl.hmacSign(hash[:])
			if expectedSig != sealed.Signature {
				result.Valid = false
				result.BrokenAtIndex = i
				result.BrokenReason = fmt.Sprintf("signature invalid at index %d", i)
				sl.stats.ChainIntegrity = false
				return result
			}
		} else if sealed.SealMode == SealTPM {
			// Fail-Closed: TPM signature verification is not yet implemented
			result.Valid = false
			result.BrokenAtIndex = i
			result.BrokenReason = fmt.Sprintf("TPM hardware verification not implemented (fail-closed) at index %d", i)
			sl.stats.ChainIntegrity = false
			return result
		} else {
			result.Valid = false
			result.BrokenAtIndex = i
			result.BrokenReason = fmt.Sprintf("unknown seal mode at index %d: %s", i, sealed.SealMode)
			sl.stats.ChainIntegrity = false
			return result		
		}

		// Verify PCR Continuity.
		oldPCRBytes, _ := hex.DecodeString(runningPCR)
		combined := append(oldPCRBytes, hash[:]...)
		newPCR := sha256.Sum256(combined)
		runningPCR = hex.EncodeToString(newPCR[:])

		if sealed.PCRValue != runningPCR {
			result.Valid = false
			result.BrokenAtIndex = i
			result.BrokenReason = fmt.Sprintf("PCR continuity mismatch at index %d", i)
			sl.stats.ChainIntegrity = false
			return result
		}

		result.VerifiedCount++
	}

	return result
}

// ChainLength returns the current chain length.
func (sl *SealedLogger) ChainLength() int {
	sl.mu.Lock()
	defer sl.mu.Unlock()
	return len(sl.chain)
}

// Stats returns logger metrics.
func (sl *SealedLogger) Stats() LoggerStats {
	sl.mu.Lock()
	defer sl.mu.Unlock()
	return sl.stats
}

// Close flushes and closes the logger.
func (sl *SealedLogger) Close() error {
	if sl.logFile != nil {
		return sl.logFile.Close()
	}
	return nil
}

// --- Internal ---

func (sl *SealedLogger) hmacSign(data []byte) string {
	mac := hmac.New(sha256.New, sl.hmacKey)
	mac.Write(data)
	return hex.EncodeToString(mac.Sum(nil))
}

func (sl *SealedLogger) tpmSign(data []byte) (string, error) {
	// TODO: Real TPM integration with github.com/google/go-tpm/tpm2.
	// For now, return error to trigger fallback.
	return "", fmt.Errorf("TPM not implemented — use software mode")
}

func (sl *SealedLogger) extendPCR(hash []byte) {
	// Simulate PCR extend: new_pcr = SHA-256(old_pcr || hash).
	oldPCR, _ := hex.DecodeString(sl.currentPCR)
	combined := append(oldPCR, hash...)
	newPCR := sha256.Sum256(combined)
	sl.currentPCR = hex.EncodeToString(newPCR[:])
}

func (sl *SealedLogger) loadExistingChain(path string) {
	data, err := os.ReadFile(path)
	if err != nil || len(data) == 0 {
		return
	}

	// Parse JSONL.
	for _, line := range splitLines(data) {
		if len(line) == 0 {
			continue
		}
		var sealed SealedEntry
		if err := json.Unmarshal(line, &sealed); err == nil {
			sl.chain = append(sl.chain, sealed)
		}
	}

	// Restore the running PCR to the last entry's value. Without this the PCR
	// stays at the zero seed after a restart, so the next extendPCR() chains
	// from zero instead of the accumulated value — making VerifyChain() report
	// a false "PCR continuity mismatch" for any entry appended post-restart.
	if n := len(sl.chain); n > 0 {
		sl.currentPCR = sl.chain[n-1].PCRValue
	}
}

func splitLines(data []byte) [][]byte {
	var lines [][]byte
	start := 0
	for i, b := range data {
		if b == '\n' {
			if i > start {
				lines = append(lines, data[start:i])
			}
			start = i + 1
		}
	}
	if start < len(data) {
		lines = append(lines, data[start:])
	}
	return lines
}

func tpmAvailable() bool {
	// Check for TPM device.
	// Linux: /dev/tpm0 or /dev/tpmrm0
	// Windows: TBS (TPM Base Services)
	for _, path := range []string{"/dev/tpm0", "/dev/tpmrm0"} {
		if _, err := os.Stat(path); err == nil {
			return true
		}
	}
	return false
}
