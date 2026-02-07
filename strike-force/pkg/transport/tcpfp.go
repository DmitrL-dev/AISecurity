package transport

import (
	"fmt"
	"runtime"
	"strings"
)

// ============================================================================
// TCP FINGERPRINT — Passive OS Fingerprinting Evasion
// ============================================================================
// Tools like p0f and Nmap can identify the OS/application by:
//   - Initial TTL value (Windows=128, Linux=64, Go=???)
//   - TCP Window Size
//   - Maximum Segment Size (MSS)
//   - Window Scale factor
//   - TCP Option order (MSS, NOP, WScale, NOP, NOP, Timestamps, SACK, EOL)
//
// Go's net.Dial uses platform defaults which often differ from Chrome.
// This module provides the correct values for Chrome on each OS.
// Fixes GAP-4: TCP Fingerprint.
// ============================================================================

// TCPProfile describes a TCP fingerprint for mimicry.
type TCPProfile struct {
	TTL         int
	WindowSize  int
	MSS         int
	WindowScale int
	Options     []string // TCP option order
	DF          bool     // Don't Fragment bit
}

// String returns the p0f-style fingerprint string.
func (p *TCPProfile) String() string {
	df := "0"
	if p.DF {
		df = "1"
	}
	return fmt.Sprintf("TTL:%d|WS:%d|MSS:%d|WSCALE:%d|DF:%s|OPTS:[%s]",
		p.TTL, p.WindowSize, p.MSS, p.WindowScale, df,
		strings.Join(p.Options, ","))
}

// ChromeTCPProfile returns Chrome's TCP fingerprint for the current OS.
// Values extracted from real Chrome traffic captures.
func ChromeTCPProfile() *TCPProfile {
	p := &TCPProfile{
		WindowSize:  65535,
		MSS:         1460, // Standard Ethernet
		WindowScale: 8,    // Chrome's default
		DF:          true, // Chrome sets Don't Fragment
		Options: []string{
			"MSS",
			"NOP",
			"WindowScale",
			"NOP",
			"NOP",
			"Timestamps",
			"SACK_Permitted",
			"EOL",
		},
	}

	// TTL is OS-dependent
	switch runtime.GOOS {
	case "windows":
		p.TTL = 128
	case "darwin":
		p.TTL = 64
	default: // linux, freebsd, etc.
		p.TTL = 64
	}

	return p
}

// GoDefaultTCPProfile returns Go's default TCP fingerprint.
// This is what we look like WITHOUT mimicry — detectable by p0f.
func GoDefaultTCPProfile() *TCPProfile {
	p := &TCPProfile{
		WindowSize:  65535,
		MSS:         1460,
		WindowScale: 7, // Go's default differs from Chrome's 8
		DF:          true,
		Options: []string{
			"MSS",
			"NOP",
			"NOP",
			"SACK_Permitted",
			"NOP",
			"WindowScale",
		},
	}

	switch runtime.GOOS {
	case "windows":
		p.TTL = 128
	default:
		p.TTL = 64
	}

	return p
}

// ApplyToDialer returns syscall-level TCP options for net.Dialer.
// Usage: set these on the raw socket after net.Dial returns.
//
//	conn, _ := net.Dial("tcp", addr)
//	raw, _ := conn.(*net.TCPConn).SyscallConn()
//	raw.Control(func(fd uintptr) {
//	    // Apply TTL, window size, etc. via setsockopt
//	})
func (p *TCPProfile) SyscallOptions() map[string]int {
	return map[string]int{
		"IP_TTL":          p.TTL,
		"TCP_WINDOW":      p.WindowSize,
		"TCP_MAXSEG":      p.MSS,
		"TCP_WINDOWSCALE": p.WindowScale,
	}
}
