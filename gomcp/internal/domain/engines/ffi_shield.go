//go:build shield_native

package engines

/*
#cgo LDFLAGS: -L${SRCDIR}/../../../../shield/build -lshield -lstdc++ -lm -lpthread
#cgo CFLAGS: -I${SRCDIR}/../../../../shield/include

#include <stdlib.h>

// Shield C FFI exports
extern int shield_init(void);
extern char* shield_inspect(const char* payload, int payload_len);
extern char* shield_status(void);
extern int shield_shutdown(void);
extern void shield_free(char* ptr);
*/
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// NativeShield wraps the C Shield engine via CGo FFI.
// Build tag: shield_native
type NativeShield struct {
	mu          sync.RWMutex
	initialized bool
	version     string
	lastCheck   time.Time
	blocked     []BlockedIP // In-memory block list
}

// NewNativeShield creates the FFI bridge to the C Shield engine.
func NewNativeShield() (*NativeShield, error) {
	result := C.shield_init()
	if result != 0 {
		return nil, fmt.Errorf("shield_init failed with code %d", int(result))
	}

	// Get version from status
	version := "0.1.0"
	cStatus := C.shield_status()
	if cStatus != nil {
		var statusObj struct {
			Version string `json:"version"`
		}
		if err := json.Unmarshal([]byte(C.GoString(cStatus)), &statusObj); err == nil && statusObj.Version != "" {
			version = statusObj.Version
		}
		C.shield_free(cStatus)
	}

	return &NativeShield{
		initialized: true,
		version:     version,
		lastCheck:   time.Now(),
		blocked:     make([]BlockedIP, 0),
	}, nil
}

// shieldInspectResult matches the JSON returned by shield_inspect().
type shieldInspectResult struct {
	Blocked      bool    `json:"blocked"`
	Reason       string  `json:"reason"`
	Confidence   float64 `json:"confidence"`
	InspectCount string  `json:"inspect_count,omitempty"`
	Error        string  `json:"error,omitempty"`
}

// inspect sends payload through the C Shield inspection pipeline.
func (n *NativeShield) inspect(payload []byte) shieldInspectResult {
	n.mu.RLock()
	defer n.mu.RUnlock()

	if !n.initialized {
		return shieldInspectResult{Error: "engine not initialized"}
	}

	cPayload := C.CBytes(payload)
	defer C.free(cPayload)

	cResult := C.shield_inspect((*C.char)(cPayload), C.int(len(payload)))
	if cResult == nil {
		return shieldInspectResult{Error: "shield_inspect returned null"}
	}
	defer C.shield_free(cResult)

	jsonStr := C.GoString(cResult)
	var result shieldInspectResult
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return shieldInspectResult{Error: fmt.Sprintf("json parse error: %v", err)}
	}

	return result
}

// InspectTraffic analyzes network traffic / payload for threats.
func (n *NativeShield) InspectTraffic(_ context.Context, payload []byte, metadata map[string]string) (*ScanResult, error) {
	start := time.Now()
	res := n.inspect(payload)

	if res.Error != "" {
		return nil, fmt.Errorf("shield: %s", res.Error)
	}

	severity := "NONE"
	threatType := ""
	if res.Blocked {
		severity = "CRITICAL"
		threatType = "network_threat"
	}

	details := res.Reason
	if src, ok := metadata["source_ip"]; ok {
		details += fmt.Sprintf(" (from %s)", src)
	}

	return &ScanResult{
		Engine:      "shield",
		ThreatFound: res.Blocked,
		ThreatType:  threatType,
		Severity:    severity,
		Confidence:  res.Confidence,
		Details:     details,
		Duration:    time.Since(start),
		Timestamp:   time.Now(),
	}, nil
}

// BlockIP adds an IP to the in-memory block list.
func (n *NativeShield) BlockIP(_ context.Context, ip string, reason string, duration time.Duration) error {
	n.mu.Lock()
	defer n.mu.Unlock()

	n.blocked = append(n.blocked, BlockedIP{
		IP:        ip,
		Reason:    reason,
		BlockedAt: time.Now(),
		ExpiresAt: time.Now().Add(duration),
	})
	return nil
}

// ListBlocked returns currently blocked IPs (filters expired).
func (n *NativeShield) ListBlocked(_ context.Context) ([]BlockedIP, error) {
	n.mu.RLock()
	defer n.mu.RUnlock()

	now := time.Now()
	active := make([]BlockedIP, 0, len(n.blocked))
	for _, b := range n.blocked {
		if b.ExpiresAt.After(now) {
			active = append(active, b)
		}
	}
	return active, nil
}

// Status returns the engine health via FFI.
func (n *NativeShield) Status() EngineStatus {
	n.mu.RLock()
	defer n.mu.RUnlock()

	if !n.initialized {
		return EngineOffline
	}

	cStatus := C.shield_status()
	if cStatus == nil {
		return EngineDegraded
	}
	defer C.shield_free(cStatus)

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
func (n *NativeShield) Name() string {
	return "shield"
}

// Version returns the native library version.
func (n *NativeShield) Version() string {
	return n.version
}

// Shutdown gracefully closes the FFI bridge.
func (n *NativeShield) Shutdown() error {
	n.mu.Lock()
	defer n.mu.Unlock()

	if !n.initialized {
		return nil
	}

	result := C.shield_shutdown()
	n.initialized = false
	if result != 0 {
		return fmt.Errorf("shield_shutdown failed with code %d", int(result))
	}
	return nil
}
