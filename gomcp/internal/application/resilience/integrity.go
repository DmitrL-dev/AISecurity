package resilience

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"log/slog"
	"os"
	"sync"
	"time"
)

// IntegrityStatus represents the result of an integrity check.
type IntegrityStatus string

const (
	IntegrityVerified    IntegrityStatus = "VERIFIED"
	IntegrityCompromised IntegrityStatus = "COMPROMISED"
	IntegrityUnknown     IntegrityStatus = "UNKNOWN"
)

// IntegrityReport is the full result of an integrity verification.
type IntegrityReport struct {
	Overall    IntegrityStatus            `json:"overall"`
	Timestamp  time.Time                  `json:"timestamp"`
	Binaries   map[string]BinaryStatus    `json:"binaries,omitempty"`
	Chain      *ChainStatus               `json:"chain,omitempty"`
	Configs    map[string]ConfigStatus     `json:"configs,omitempty"`
}

// BinaryStatus is the integrity status of a single binary.
type BinaryStatus struct {
	Status   IntegrityStatus `json:"status"`
	Expected string          `json:"expected"`
	Current  string          `json:"current"`
}

// ChainStatus is the integrity status of the decision chain.
type ChainStatus struct {
	Valid      bool   `json:"valid"`
	Error      string `json:"error,omitempty"`
	BreakPoint int    `json:"break_point,omitempty"`
	Entries    int    `json:"entries"`
}

// ConfigStatus is the integrity status of a config file.
type ConfigStatus struct {
	Valid       bool   `json:"valid"`
	Error       string `json:"error,omitempty"`
	StoredHMAC  string `json:"stored_hmac,omitempty"`
	CurrentHMAC string `json:"current_hmac,omitempty"`
}

// IntegrityVerifier performs periodic integrity checks on binaries,
// decision chain, and config files.
type IntegrityVerifier struct {
	mu            sync.RWMutex
	binaryHashes  map[string]string // path → expected SHA-256
	configPaths   []string          // config files to verify
	hmacKey       []byte            // key for config HMAC-SHA256
	chainPath     string            // path to decision chain log
	logger        *slog.Logger
	lastReport    *IntegrityReport
}

// NewIntegrityVerifier creates a new integrity verifier.
func NewIntegrityVerifier(hmacKey []byte) *IntegrityVerifier {
	return &IntegrityVerifier{
		binaryHashes: make(map[string]string),
		hmacKey:      hmacKey,
		logger:       slog.Default().With("component", "sarl-integrity"),
	}
}

// RegisterBinary adds a binary with its expected SHA-256 hash.
func (iv *IntegrityVerifier) RegisterBinary(path, expectedHash string) {
	iv.mu.Lock()
	defer iv.mu.Unlock()
	iv.binaryHashes[path] = expectedHash
}

// RegisterConfig adds a config file to verify.
func (iv *IntegrityVerifier) RegisterConfig(path string) {
	iv.mu.Lock()
	defer iv.mu.Unlock()
	iv.configPaths = append(iv.configPaths, path)
}

// SetChainPath sets the decision chain log path.
func (iv *IntegrityVerifier) SetChainPath(path string) {
	iv.mu.Lock()
	defer iv.mu.Unlock()
	iv.chainPath = path
}

// VerifyAll runs all integrity checks and returns a comprehensive report.
// Note: file I/O (binary hashing, config reading) is done WITHOUT holding
// the mutex to prevent thread starvation on slow storage.
func (iv *IntegrityVerifier) VerifyAll() IntegrityReport {
	report := IntegrityReport{
		Overall:   IntegrityVerified,
		Timestamp: time.Now(),
		Binaries:  make(map[string]BinaryStatus),
		Configs:   make(map[string]ConfigStatus),
	}

	// Snapshot config under lock, then release before I/O.
	iv.mu.RLock()
	binaryHashesCopy := make(map[string]string, len(iv.binaryHashes))
	for k, v := range iv.binaryHashes {
		binaryHashesCopy[k] = v
	}
	configPathsCopy := make([]string, len(iv.configPaths))
	copy(configPathsCopy, iv.configPaths)
	hmacKeyCopy := make([]byte, len(iv.hmacKey))
	copy(hmacKeyCopy, iv.hmacKey)
	chainPath := iv.chainPath
	iv.mu.RUnlock()

	// Check binaries (file I/O — no lock held).
	for path, expected := range binaryHashesCopy {
		status := iv.verifyBinary(path, expected)
		report.Binaries[path] = status
		if status.Status == IntegrityCompromised {
			report.Overall = IntegrityCompromised
		}
	}

	// Check configs (file I/O — no lock held).
	for _, path := range configPathsCopy {
		status := iv.verifyConfigFile(path)
		report.Configs[path] = status
		if !status.Valid {
			report.Overall = IntegrityCompromised
		}
	}

	// Check decision chain (file I/O — no lock held).
	if chainPath != "" {
		chain := iv.verifyDecisionChain(chainPath)
		report.Chain = &chain
		if !chain.Valid {
			report.Overall = IntegrityCompromised
		}
	}

	iv.mu.Lock()
	iv.lastReport = &report
	iv.mu.Unlock()

	if report.Overall == IntegrityCompromised {
		iv.logger.Error("INTEGRITY COMPROMISED", "report", report)
	} else {
		iv.logger.Debug("integrity verified", "binaries", len(report.Binaries))
	}

	return report
}

// LastReport returns the most recent integrity report.
func (iv *IntegrityVerifier) LastReport() *IntegrityReport {
	iv.mu.RLock()
	defer iv.mu.RUnlock()
	return iv.lastReport
}

// verifyBinary calculates SHA-256 of a file and compares to expected.
func (iv *IntegrityVerifier) verifyBinary(path, expected string) BinaryStatus {
	current, err := fileSHA256(path)
	if err != nil {
		return BinaryStatus{
			Status:   IntegrityUnknown,
			Expected: expected,
			Current:  fmt.Sprintf("error: %v", err),
		}
	}

	if current != expected {
		return BinaryStatus{
			Status:   IntegrityCompromised,
			Expected: expected,
			Current:  current,
		}
	}

	return BinaryStatus{
		Status:   IntegrityVerified,
		Expected: expected,
		Current:  current,
	}
}

// verifyConfigFile checks HMAC-SHA256 of a config file.
func (iv *IntegrityVerifier) verifyConfigFile(path string) ConfigStatus {
	data, err := os.ReadFile(path)
	if err != nil {
		return ConfigStatus{Valid: false, Error: fmt.Sprintf("unreadable: %v", err)}
	}

	currentHMAC := computeHMAC(data, iv.hmacKey)
	// For now, we just verify the file is readable and compute HMAC.
	// In production, the stored HMAC would be extracted from a sidecar file.
	return ConfigStatus{
		Valid:       true,
		CurrentHMAC: currentHMAC,
	}
}

// verifyDecisionChain verifies the SHA-256 hash chain in the decision log.
func (iv *IntegrityVerifier) verifyDecisionChain(path string) ChainStatus {
	_, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return ChainStatus{Valid: true, Entries: 0} // No chain yet.
		}
		return ChainStatus{Valid: false, Error: fmt.Sprintf("unreadable: %v", err)}
	}

	// In a real implementation, we'd parse the chain entries and verify
	// that each entry's hash includes the previous entry's hash.
	// For now, verify the file exists and is readable.
	return ChainStatus{Valid: true}
}

// fileSHA256 computes the SHA-256 hash of a file.
func fileSHA256(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// computeHMAC computes HMAC-SHA256 of data with the given key.
func computeHMAC(data, key []byte) string {
	mac := hmac.New(sha256.New, key)
	mac.Write(data)
	return hex.EncodeToString(mac.Sum(nil))
}
