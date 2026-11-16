package engines

import (
	"context"
	"time"
)

// EngineStatus represents the health state of a security engine.
type EngineStatus string

const (
	EngineHealthy     EngineStatus = "HEALTHY"
	EngineDegraded    EngineStatus = "DEGRADED"
	EngineOffline     EngineStatus = "OFFLINE"
	EngineInitializing EngineStatus = "INITIALIZING"
)

// ScanResult is the unified output from any security engine.
type ScanResult struct {
	Engine      string        `json:"engine"`
	ThreatFound bool          `json:"threat_found"`
	ThreatType  string        `json:"threat_type,omitempty"`
	Severity    string        `json:"severity"`
	Confidence  float64       `json:"confidence"`
	Details     string        `json:"details,omitempty"`
	Indicators  []string      `json:"indicators,omitempty"`
	Duration    time.Duration `json:"duration_ns"`
	Timestamp   time.Time     `json:"timestamp"`

	// EngineVector is the DENSE per-engine confidence vector in the sentinel-core
	// fixed fan-out order (one slot per engine, 0.0 when an engine did not fire).
	// Populated only by the native sentinel-core bridge (sentinel_analyze emits
	// `engine_vector` + `engine_vector_order`); nil for the stub, the shield engine,
	// or an older sentinel binary that does not emit it. This is the real per-engine
	// feature the data-capture flywheel needs for combiner/router retraining.
	EngineVector      []float64 `json:"engine_vector,omitempty"`
	EngineVectorOrder []string  `json:"engine_vector_order,omitempty"`

	// Escalate is the sentinel Layer-2 ambiguity-band signal. NOTE: it is redundant
	// with gomcp's own band test and is false by default — carried for completeness
	// only; no detection/judge logic is built on it.
	Escalate       bool   `json:"escalate,omitempty"`
	EscalateReason string `json:"escalate_reason,omitempty"`
}

// SentinelCore defines the interface for the Rust-based detection engine (§3).
// Real implementation: FFI bridge to sentinel-core Rust binary.
// Stub implementation: used when sentinel-core is not deployed.
type SentinelCore interface {
	// Name returns the engine identifier.
	Name() string

	// Status returns current engine health.
	Status() EngineStatus

	// ScanPrompt analyzes an LLM prompt for injection/jailbreak patterns.
	ScanPrompt(ctx context.Context, prompt string) (*ScanResult, error)

	// ScanResponse analyzes an LLM response for data exfiltration or harmful content.
	ScanResponse(ctx context.Context, response string) (*ScanResult, error)

	// Version returns the engine version.
	Version() string
}

// Shield defines the interface for the C++ network protection engine (§4).
// Real implementation: FFI bridge to shield C++ shared library.
// Stub implementation: used when shield is not deployed.
type Shield interface {
	// Name returns the engine identifier.
	Name() string

	// Status returns current engine health.
	Status() EngineStatus

	// InspectTraffic analyzes network traffic for threats.
	InspectTraffic(ctx context.Context, payload []byte, metadata map[string]string) (*ScanResult, error)

	// BlockIP adds an IP to the block list.
	BlockIP(ctx context.Context, ip string, reason string, duration time.Duration) error

	// ListBlocked returns currently blocked IPs.
	ListBlocked(ctx context.Context) ([]BlockedIP, error)

	// Version returns the engine version.
	Version() string
}

// BlockedIP represents a blocked IP entry.
type BlockedIP struct {
	IP        string    `json:"ip"`
	Reason    string    `json:"reason"`
	BlockedAt time.Time `json:"blocked_at"`
	ExpiresAt time.Time `json:"expires_at"`
}

// --- Stub implementations for standalone Go deployment ---

// StubSentinelCore is a no-op sentinel-core when Rust engine is not deployed.
type StubSentinelCore struct{}

func NewStubSentinelCore() *StubSentinelCore { return &StubSentinelCore{} }
func (s *StubSentinelCore) Name() string     { return "sentinel-core-stub" }
func (s *StubSentinelCore) Status() EngineStatus { return EngineOffline }
func (s *StubSentinelCore) Version() string  { return "stub-1.0" }

func (s *StubSentinelCore) ScanPrompt(_ context.Context, _ string) (*ScanResult, error) {
	return &ScanResult{
		Engine:      "sentinel-core-stub",
		ThreatFound: false,
		Severity:    "NONE",
		Confidence:  0,
		Details:     "sentinel-core not deployed, stub mode",
		Timestamp:   time.Now(),
	}, nil
}

func (s *StubSentinelCore) ScanResponse(_ context.Context, _ string) (*ScanResult, error) {
	return &ScanResult{
		Engine:      "sentinel-core-stub",
		ThreatFound: false,
		Severity:    "NONE",
		Confidence:  0,
		Details:     "sentinel-core not deployed, stub mode",
		Timestamp:   time.Now(),
	}, nil
}

// StubShield is a no-op shield when C++ engine is not deployed.
type StubShield struct{}

func NewStubShield() *StubShield         { return &StubShield{} }
func (s *StubShield) Name() string       { return "shield-stub" }
func (s *StubShield) Status() EngineStatus { return EngineOffline }
func (s *StubShield) Version() string    { return "stub-1.0" }

func (s *StubShield) InspectTraffic(_ context.Context, _ []byte, _ map[string]string) (*ScanResult, error) {
	return &ScanResult{
		Engine:      "shield-stub",
		ThreatFound: false,
		Severity:    "NONE",
		Details:     "shield not deployed, stub mode",
		Timestamp:   time.Now(),
	}, nil
}

func (s *StubShield) BlockIP(_ context.Context, _ string, _ string, _ time.Duration) error {
	return nil
}

func (s *StubShield) ListBlocked(_ context.Context) ([]BlockedIP, error) {
	return nil, nil
}
