//go:build sentinel_native

package engines

/*
#cgo LDFLAGS: -L${SRCDIR}/../../../../sentinel-core/target/release -lsentinel_core -ldl -lm -lpthread
#cgo CFLAGS: -I${SRCDIR}/../../../../sentinel-core/include

#include <sentinel_core.h>
#include <stdlib.h>
*/
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"
	"unsafe"
)

// NativeSentinelCore wraps the Rust sentinel-core via CGo FFI.
// Build tag: sentinel_native
type NativeSentinelCore struct {
	mu          sync.RWMutex
	initialized bool
	version     string
	lastCheck   time.Time
}

// NewNativeSentinelCore creates the FFI bridge and initializes the Rust engine.
func NewNativeSentinelCore() (*NativeSentinelCore, error) {
	result := C.sentinel_init()
	if result != 0 {
		return nil, fmt.Errorf("sentinel_init failed with code %d", int(result))
	}

	// Get version from Rust
	cVer := C.sentinel_version()
	version := "unknown"
	if cVer != nil {
		version = C.GoString(cVer)
		C.sentinel_free(cVer)
	}

	return &NativeSentinelCore{
		initialized: true,
		version:     version,
		lastCheck:   time.Now(),
	}, nil
}

// analyze sends text through the Rust sentinel-core analysis pipeline.
func (n *NativeSentinelCore) analyze(text string) sentinelAnalyzeResult {
	n.mu.RLock()
	defer n.mu.RUnlock()

	if !n.initialized {
		return sentinelAnalyzeResult{Error: "engine not initialized"}
	}

	// Reject interior NUL bytes (defense-in-depth, Review 14.06 round-4): C.CString
	// copies the whole Go string incl. NULs, but the Rust side reads via
	// CStr::from_ptr which stops at the FIRST NUL — so a prompt like
	// "hello\x00<malicious tail>" would be analyzed as only "hello", silently
	// bypassing detection. Fail CLOSED (error → caller denies) for any caller,
	// not just the HTTP scan handler.
	if !validSentinelInput(text) {
		return sentinelAnalyzeResult{Error: "input contains NUL byte"}
	}

	cText := C.CString(text)
	defer C.free(unsafe.Pointer(cText))

	cResult := C.sentinel_analyze(cText)
	if cResult == nil {
		return sentinelAnalyzeResult{Error: "sentinel_analyze returned null"}
	}
	defer C.sentinel_free(cResult)

	jsonStr := C.GoString(cResult)
	result, err := decodeSentinelAnalyze([]byte(jsonStr), len(text))
	if err != nil {
		return sentinelAnalyzeResult{Error: "invalid native analysis response"}
	}
	return result
}

// ScanPrompt analyzes an LLM prompt for injection/jailbreak patterns.
func (n *NativeSentinelCore) ScanPrompt(_ context.Context, prompt string) (*ScanResult, error) {
	start := time.Now()
	res := n.analyze(prompt)

	if res.Error != "" {
		return nil, fmt.Errorf("sentinel-core: %s", res.Error)
	}

	severity := "NONE"
	threatType := ""
	if res.IsThreat {
		severity = "HIGH"
		if len(res.Categories) > 0 {
			threatType = res.Categories[0]
		}
	}

	return &ScanResult{
		Engine:      "sentinel-core",
		ThreatFound: res.IsThreat,
		ThreatType:  threatType,
		Severity:    severity,
		Confidence:  res.Confidence,
		Details:     fmt.Sprintf("engines=%d categories=%v", res.EnginesTriggered, res.Categories),
		Indicators:  res.Indicators,
		Duration:    time.Since(start),
		Timestamp:   time.Now(),
		// Surface the dense per-engine vector (+ its self-describing order) and the
		// Layer-2 escalate signal for the flywheel. nil/false when an older sentinel
		// binary omits them — backward-compatible.
		EngineVector:      res.EngineVector,
		EngineVectorOrder: res.EngineVectorOrder,
		Escalate:          res.Escalate,
		EscalateReason:    res.EscalateReason,
	}, nil
}

// ScanResponse analyzes an LLM response for data exfiltration or harmful content.
func (n *NativeSentinelCore) ScanResponse(ctx context.Context, response string) (*ScanResult, error) {
	return n.ScanPrompt(ctx, response)
}

// Status returns the engine health via FFI.
func (n *NativeSentinelCore) Status() EngineStatus {
	n.mu.RLock()
	defer n.mu.RUnlock()

	if !n.initialized {
		return EngineOffline
	}

	cStatus := C.sentinel_status()
	if cStatus == nil {
		return EngineDegraded
	}
	defer C.sentinel_free(cStatus)

	var statusObj struct {
		Status string `json:"status"`
	}
	if err := json.Unmarshal([]byte(C.GoString(cStatus)), &statusObj); err != nil {
		return EngineDegraded
	}

	switch statusObj.Status {
	case "HEALTHY":
		return EngineHealthy
	case "OFFLINE":
		return EngineOffline
	default:
		return EngineDegraded
	}
}

// Name returns the engine identifier.
func (n *NativeSentinelCore) Name() string {
	return "sentinel-core"
}

// Version returns the native library version.
func (n *NativeSentinelCore) Version() string {
	return n.version
}

// Shutdown gracefully closes the FFI bridge.
func (n *NativeSentinelCore) Shutdown() error {
	n.mu.Lock()
	defer n.mu.Unlock()

	if !n.initialized {
		return nil
	}

	result := C.sentinel_shutdown()
	n.initialized = false
	if result != 0 {
		return fmt.Errorf("sentinel_shutdown failed with code %d", int(result))
	}
	return nil
}
