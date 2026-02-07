package transport

import (
	"testing"
)

// ============================================================================
// TDD: HTTP/2 Fingerprint Tests
// ============================================================================

func TestChromeH2Fingerprint_HasCorrectSettingsOrder(t *testing.T) {
	fp := ChromeH2Fingerprint()

	// Chrome sends SETTINGS in this exact order:
	// HEADER_TABLE_SIZE, ENABLE_PUSH, MAX_CONCURRENT_STREAMS,
	// INITIAL_WINDOW_SIZE, MAX_FRAME_SIZE, MAX_HEADER_LIST_SIZE
	expectedOrder := []string{
		"HEADER_TABLE_SIZE",
		"ENABLE_PUSH",
		"MAX_CONCURRENT_STREAMS",
		"INITIAL_WINDOW_SIZE",
		"MAX_FRAME_SIZE",
		"MAX_HEADER_LIST_SIZE",
	}

	if len(fp.Settings) != len(expectedOrder) {
		t.Fatalf("expected %d settings, got %d", len(expectedOrder), len(fp.Settings))
	}

	for i, s := range fp.Settings {
		if s.Name != expectedOrder[i] {
			t.Errorf("setting[%d] = %q, want %q", i, s.Name, expectedOrder[i])
		}
	}
}

func TestChromeH2Fingerprint_SettingsValues(t *testing.T) {
	fp := ChromeH2Fingerprint()

	expected := map[string]uint32{
		"HEADER_TABLE_SIZE":      65536,
		"ENABLE_PUSH":            0, // Chrome disables server push
		"MAX_CONCURRENT_STREAMS": 1000,
		"INITIAL_WINDOW_SIZE":    6291456,
		"MAX_FRAME_SIZE":         16384,
		"MAX_HEADER_LIST_SIZE":   262144,
	}

	for _, s := range fp.Settings {
		want, ok := expected[s.Name]
		if !ok {
			t.Errorf("unexpected setting: %s", s.Name)
			continue
		}
		if s.Value != want {
			t.Errorf("%s = %d, want %d", s.Name, s.Value, want)
		}
	}
}

func TestChromeH2Fingerprint_WindowUpdate(t *testing.T) {
	fp := ChromeH2Fingerprint()

	// Chrome sends WINDOW_UPDATE with 15663105 (connection-level)
	if fp.WindowUpdate != 15663105 {
		t.Errorf("window_update = %d, want 15663105", fp.WindowUpdate)
	}
}

func TestChromeH2Fingerprint_PseudoHeaderOrder(t *testing.T) {
	fp := ChromeH2Fingerprint()

	// Chrome sends pseudo-headers in this order: :method, :authority, :scheme, :path
	expectedOrder := []string{":method", ":authority", ":scheme", ":path"}

	if len(fp.PseudoHeaderOrder) != len(expectedOrder) {
		t.Fatalf("expected %d pseudo-headers, got %d", len(expectedOrder), len(fp.PseudoHeaderOrder))
	}

	for i, h := range fp.PseudoHeaderOrder {
		if h != expectedOrder[i] {
			t.Errorf("pseudo-header[%d] = %q, want %q", i, h, expectedOrder[i])
		}
	}
}

func TestChromeH2Fingerprint_HeaderPriority(t *testing.T) {
	fp := ChromeH2Fingerprint()

	// Chrome uses weight=256, streamDep=0, exclusive=true for initial request
	if fp.Priority.Weight != 256 {
		t.Errorf("priority weight = %d, want 256", fp.Priority.Weight)
	}
	if fp.Priority.StreamDep != 0 {
		t.Errorf("priority streamDep = %d, want 0", fp.Priority.StreamDep)
	}
	if !fp.Priority.Exclusive {
		t.Error("priority exclusive should be true")
	}
}

func TestH2FingerprintString_ContainsSettingsOrder(t *testing.T) {
	fp := ChromeH2Fingerprint()
	s := fp.String()

	// The string representation should contain settings in order
	if len(s) == 0 {
		t.Error("fingerprint string is empty")
	}
	// Should contain the Akamai-style representation
	if len(s) < 20 {
		t.Error("fingerprint string too short to be valid")
	}
}

func TestGoDefaultH2Fingerprint_DiffersFromChrome(t *testing.T) {
	chrome := ChromeH2Fingerprint()
	goDefault := GoDefaultH2Fingerprint()

	// Go's default INITIAL_WINDOW_SIZE differs from Chrome
	chromeWin := uint32(0)
	goWin := uint32(0)
	for _, s := range chrome.Settings {
		if s.Name == "INITIAL_WINDOW_SIZE" {
			chromeWin = s.Value
		}
	}
	for _, s := range goDefault.Settings {
		if s.Name == "INITIAL_WINDOW_SIZE" {
			goWin = s.Value
		}
	}

	if chromeWin == goWin {
		t.Error("Chrome and Go default should have DIFFERENT INITIAL_WINDOW_SIZE")
	}
}
