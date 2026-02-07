package transport

import (
	"runtime"
	"testing"
)

// ============================================================================
// TDD: TCP Fingerprint Obfuscation Tests
// ============================================================================

func TestChromeTCPProfile_NotNil(t *testing.T) {
	p := ChromeTCPProfile()
	if p == nil {
		t.Fatal("TCP profile is nil")
	}
}

func TestChromeTCPProfile_TTL(t *testing.T) {
	p := ChromeTCPProfile()
	// Chrome on Windows uses TTL=128, Linux/Mac=64
	if runtime.GOOS == "windows" {
		if p.TTL != 128 {
			t.Errorf("TTL = %d, want 128 (Windows)", p.TTL)
		}
	} else {
		if p.TTL != 64 {
			t.Errorf("TTL = %d, want 64 (Unix)", p.TTL)
		}
	}
}

func TestChromeTCPProfile_WindowSize(t *testing.T) {
	p := ChromeTCPProfile()
	// Chrome's TCP window size: 65535 (standard)
	if p.WindowSize != 65535 {
		t.Errorf("WindowSize = %d, want 65535", p.WindowSize)
	}
}

func TestChromeTCPProfile_MSS(t *testing.T) {
	p := ChromeTCPProfile()
	// Standard MSS for Ethernet: 1460
	if p.MSS != 1460 {
		t.Errorf("MSS = %d, want 1460", p.MSS)
	}
}

func TestChromeTCPProfile_WindowScale(t *testing.T) {
	p := ChromeTCPProfile()
	// Chrome uses window scale factor 8
	if p.WindowScale != 8 {
		t.Errorf("WindowScale = %d, want 8", p.WindowScale)
	}
}

func TestChromeTCPProfile_Options(t *testing.T) {
	p := ChromeTCPProfile()
	// Chrome's TCP option order: MSS, NOP, WindowScale, NOP, NOP, Timestamps, SACK_Permitted, EOL
	if len(p.Options) == 0 {
		t.Error("TCP options should not be empty")
	}
	// First option must be MSS
	if p.Options[0] != "MSS" {
		t.Errorf("first TCP option should be MSS, got %s", p.Options[0])
	}
}

func TestGoDefaultTCPProfile_DiffersFromChrome(t *testing.T) {
	chrome := ChromeTCPProfile()
	goDefault := GoDefaultTCPProfile()

	// Go's default window size differs from Chrome
	if chrome.WindowSize == goDefault.WindowSize && chrome.WindowScale == goDefault.WindowScale {
		t.Error("Chrome and Go TCP profiles should differ in at least window params")
	}
}

func TestTCPFingerprintString_NotEmpty(t *testing.T) {
	p := ChromeTCPProfile()
	s := p.String()
	if len(s) < 10 {
		t.Errorf("fingerprint string too short: %q", s)
	}
}
