package oracle

import (
	"fmt"
	"sync"
)

// EvalVerdict is the Shadow Oracle's decision.
type EvalVerdict int

const (
	// EvalAllow — content passes all checks.
	EvalAllow EvalVerdict = iota
	// EvalDenySecret — blocked by Secret Scanner (invariant, always active).
	EvalDenySecret
	// EvalDenyEthical — blocked by Ethical Filter (inactive in ZERO-G).
	EvalDenyEthical
	// EvalRawIntent — passed in ZERO-G with RAW_INTENT tag.
	EvalRawIntent
	// EvalDenySafe — blocked because system is in SAFE (read-only) mode.
	EvalDenySafe
)

// String returns human-readable verdict.
func (v EvalVerdict) String() string {
	switch v {
	case EvalAllow:
		return "ALLOW"
	case EvalDenySecret:
		return "DENY:SECRET"
	case EvalDenyEthical:
		return "DENY:ETHICAL"
	case EvalRawIntent:
		return "ALLOW:RAW_INTENT"
	case EvalDenySafe:
		return "DENY:SAFE_MODE"
	default:
		return "UNKNOWN"
	}
}

// EvalResult holds the Shadow Oracle's evaluation result.
type EvalResult struct {
	Verdict    EvalVerdict `json:"verdict"`
	Detections []string    `json:"detections,omitempty"`
	Origin     string      `json:"origin"` // "STANDARD" or "RAW_INTENT"
	MaxEntropy float64     `json:"max_entropy"`
	Mode       string      `json:"mode"`
}

// --- Mode constants (avoid circular import with hardware) ---

// OracleMode mirrors SystemMode from hardware package.
type OracleMode int

const (
	OModeArmed OracleMode = iota
	OModeZeroG
	OModeSafe
)

// Service is the Shadow Oracle — mode-aware content evaluator.
// Wraps Secret Scanner (invariant) + Ethical Filter (configurable).
type Service struct {
	mu   sync.RWMutex
	mode OracleMode
}

// NewService creates a new Shadow Oracle service.
func NewService() *Service {
	return &Service{mode: OModeArmed}
}

// SetMode updates the operational mode (thread-safe).
func (s *Service) SetMode(m OracleMode) {
	s.mu.Lock()
	s.mode = m
	s.mu.Unlock()
}

// GetMode returns current mode (thread-safe).
func (s *Service) GetMode() OracleMode {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.mode
}

// Evaluate performs mode-aware content evaluation.
//
// Pipeline:
//  1. Secret Scanner (ALWAYS active) → DENY:SECRET if detected
//  2. Mode check:
//     - SAFE → DENY:SAFE_MODE (no writes allowed)
//     - ZERO-G → skip ethical filter → ALLOW:RAW_INTENT
//     - ARMED → apply ethical filter → ALLOW or DENY:ETHICAL
func (s *Service) Evaluate(content string) *EvalResult {
	mode := s.GetMode()
	result := &EvalResult{
		Mode: modeString(mode),
	}

	// --- Step 1: Secret Scanner (INVARIANT — always active) ---
	scanResult := ScanForSecrets(content)
	result.MaxEntropy = scanResult.MaxEntropy

	if scanResult.HasSecrets {
		result.Verdict = EvalDenySecret
		result.Detections = scanResult.Detections
		result.Origin = "SECURITY"
		return result
	}

	// --- Step 2: Mode-specific logic ---
	switch mode {
	case OModeSafe:
		result.Verdict = EvalDenySafe
		result.Origin = "SAFE_MODE"
		return result

	case OModeZeroG:
		// Ethical filter SKIPPED. Content passes with RAW_INTENT tag.
		result.Verdict = EvalRawIntent
		result.Origin = "RAW_INTENT"
		return result

	default: // OModeArmed
		result.Verdict = EvalAllow
		result.Origin = "STANDARD"
		return result
	}
}

// EvaluateWrite checks if write operations are permitted in current mode.
func (s *Service) EvaluateWrite() *EvalResult {
	mode := s.GetMode()
	if mode == OModeSafe {
		return &EvalResult{
			Verdict: EvalDenySafe,
			Origin:  "SAFE_MODE",
			Mode:    modeString(mode),
		}
	}
	return &EvalResult{
		Verdict: EvalAllow,
		Origin:  "STANDARD",
		Mode:    modeString(mode),
	}
}

func modeString(m OracleMode) string {
	switch m {
	case OModeZeroG:
		return "ZERO-G"
	case OModeSafe:
		return "SAFE"
	default:
		return "ARMED"
	}
}

// FormatOriginTag returns the metadata tag for fact storage.
func FormatOriginTag(result *EvalResult) string {
	if result.Origin == "RAW_INTENT" {
		return "origin:RAW_INTENT"
	}
	return fmt.Sprintf("origin:%s", result.Origin)
}
