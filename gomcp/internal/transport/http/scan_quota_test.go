package httpserver

import "testing"

// Review 14.06 round-5: the anonymous (no-auth) scan path gets a small per-IP
// DEMO quota — configurable, with a safe default — instead of the removed
// unlimited Proof-of-Work bypass.
func TestAnonDemoScanLimit(t *testing.T) {
	t.Setenv("ANON_DEMO_SCAN_LIMIT", "")
	if got := anonDemoScanLimit(); got != 100 {
		t.Fatalf("default demo limit must be 100, got %d", got)
	}
	t.Setenv("ANON_DEMO_SCAN_LIMIT", "25")
	if got := anonDemoScanLimit(); got != 25 {
		t.Fatalf("override must be honored, got %d", got)
	}
	t.Setenv("ANON_DEMO_SCAN_LIMIT", "abc")
	if got := anonDemoScanLimit(); got != 100 {
		t.Fatalf("invalid override must fall back to 100, got %d", got)
	}
	t.Setenv("ANON_DEMO_SCAN_LIMIT", "0")
	if got := anonDemoScanLimit(); got != 100 {
		t.Fatalf("non-positive override must fall back to 100, got %d", got)
	}
}
