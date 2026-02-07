package transport

import (
	"fmt"
	"strings"
)

// ============================================================================
// HTTP/2 FINGERPRINT — Akamai/Cloudflare Detection Evasion
// ============================================================================
// Cloudflare and Akamai fingerprint HTTP/2 clients by:
//   1. SETTINGS frame order and values
//   2. WINDOW_UPDATE value
//   3. Pseudo-header order (:method, :authority, :scheme, :path)
//   4. PRIORITY frame (weight, stream dependency, exclusive bit)
//
// Go's default HTTP/2 stack has a DIFFERENT fingerprint than Chrome.
// This module provides Chrome's exact HTTP/2 fingerprint for mimicry.
//
// Reference: https://www.blackhat.com/us-19/briefings/schedule/#http2-the-sequel-is-always-worse-15265
// ============================================================================

// H2Setting represents a single HTTP/2 SETTINGS parameter.
type H2Setting struct {
	Name  string
	ID    uint16
	Value uint32
}

// H2Priority represents HTTP/2 PRIORITY frame parameters.
type H2Priority struct {
	Weight    int
	StreamDep int
	Exclusive bool
}

// H2Fingerprint represents a complete HTTP/2 fingerprint.
type H2Fingerprint struct {
	Settings          []H2Setting
	WindowUpdate      uint32
	PseudoHeaderOrder []string
	Priority          H2Priority
}

// String returns the Akamai-style fingerprint string.
// Format: S[settings]|WU[window_update]|P[pseudo_headers]
func (h *H2Fingerprint) String() string {
	var parts []string

	// Settings: ID:VALUE
	var settings []string
	for _, s := range h.Settings {
		settings = append(settings, fmt.Sprintf("%d:%d", s.ID, s.Value))
	}
	parts = append(parts, "S["+strings.Join(settings, ",")+"]")

	// Window Update
	parts = append(parts, fmt.Sprintf("WU[%d]", h.WindowUpdate))

	// Pseudo-header order
	parts = append(parts, "P["+strings.Join(h.PseudoHeaderOrder, ",")+"]")

	// Priority
	excl := 0
	if h.Priority.Exclusive {
		excl = 1
	}
	parts = append(parts, fmt.Sprintf("PR[w:%d,d:%d,e:%d]", h.Priority.Weight, h.Priority.StreamDep, excl))

	return strings.Join(parts, "|")
}

// ChromeH2Fingerprint returns Chrome 131-133's HTTP/2 fingerprint.
// These values are extracted from real Chrome traffic captures.
func ChromeH2Fingerprint() H2Fingerprint {
	return H2Fingerprint{
		Settings: []H2Setting{
			{Name: "HEADER_TABLE_SIZE", ID: 0x1, Value: 65536},
			{Name: "ENABLE_PUSH", ID: 0x2, Value: 0}, // Chrome disables push
			{Name: "MAX_CONCURRENT_STREAMS", ID: 0x3, Value: 1000},
			{Name: "INITIAL_WINDOW_SIZE", ID: 0x4, Value: 6291456}, // 6MB — Chrome's signature
			{Name: "MAX_FRAME_SIZE", ID: 0x5, Value: 16384},
			{Name: "MAX_HEADER_LIST_SIZE", ID: 0x6, Value: 262144},
		},
		// Chrome sends WINDOW_UPDATE = 15663105 on connection stream (0)
		WindowUpdate: 15663105,
		// Chrome's pseudo-header order differs from curl and Go
		PseudoHeaderOrder: []string{":method", ":authority", ":scheme", ":path"},
		// Chrome uses weight=256, streamDep=0, exclusive=true
		Priority: H2Priority{
			Weight:    256,
			StreamDep: 0,
			Exclusive: true,
		},
	}
}

// GoDefaultH2Fingerprint returns Go's default HTTP/2 fingerprint for comparison.
// This is what we look like WITHOUT fingerprint mimicry — easily detectable.
func GoDefaultH2Fingerprint() H2Fingerprint {
	return H2Fingerprint{
		Settings: []H2Setting{
			// Go sends in different order with different values
			{Name: "MAX_FRAME_SIZE", ID: 0x5, Value: 16384},
			{Name: "MAX_CONCURRENT_STREAMS", ID: 0x3, Value: 250},    // Go default: 250
			{Name: "MAX_HEADER_LIST_SIZE", ID: 0x6, Value: 10485760}, // Go: 10MB
			{Name: "INITIAL_WINDOW_SIZE", ID: 0x4, Value: 1048576},   // Go: 1MB (Chrome: 6MB!)
			{Name: "HEADER_TABLE_SIZE", ID: 0x1, Value: 4096},        // Go: 4KB (Chrome: 64KB)
		},
		WindowUpdate:      983041,                                                // Go default
		PseudoHeaderOrder: []string{":method", ":path", ":scheme", ":authority"}, // Different order!
		Priority: H2Priority{
			Weight:    16, // Go default
			StreamDep: 0,
			Exclusive: false,
		},
	}
}

// SettingsMap returns settings as a map for use with HTTP/2 transport configuration.
func (h *H2Fingerprint) SettingsMap() map[uint16]uint32 {
	m := make(map[uint16]uint32)
	for _, s := range h.Settings {
		m[s.ID] = s.Value
	}
	return m
}
