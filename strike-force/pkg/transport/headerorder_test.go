package transport

import (
	"strings"
	"testing"
)

// ============================================================================
// TDD: Chrome Header Order Tests
// ============================================================================

func TestChromeHeaderOrder_NotEmpty(t *testing.T) {
	order := ChromeHeaderOrder()
	if len(order) == 0 {
		t.Fatal("Chrome header order is empty")
	}
}

func TestChromeHeaderOrder_StartsWithHost(t *testing.T) {
	// Chrome always sends Host first (after pseudo-headers in h2)
	order := ChromeHeaderOrder()
	found := false
	for i, h := range order {
		if strings.EqualFold(h, "Host") {
			if i > 2 { // Should be in first 3
				t.Errorf("Host at position %d, expected < 3", i)
			}
			found = true
			break
		}
	}
	if !found {
		t.Error("Host not found in Chrome header order")
	}
}

func TestChromeHeaderOrder_UABeforeAccept(t *testing.T) {
	order := ChromeHeaderOrder()
	uaIdx := -1
	acceptIdx := -1
	for i, h := range order {
		if strings.EqualFold(h, "User-Agent") {
			uaIdx = i
		}
		if strings.EqualFold(h, "Accept") {
			acceptIdx = i
		}
	}
	if uaIdx == -1 || acceptIdx == -1 {
		t.Fatal("User-Agent or Accept missing")
	}
	if uaIdx > acceptIdx {
		t.Errorf("User-Agent (pos %d) should come before Accept (pos %d)", uaIdx, acceptIdx)
	}
}

func TestBuildOrderedHeaders_PreservesOrder(t *testing.T) {
	headers := map[string]string{
		"Accept":          "text/html",
		"User-Agent":      "Chrome/133",
		"Accept-Language": "en-US",
		"Host":            "example.com",
	}

	raw := BuildOrderedHeaders(headers)

	// Host must appear before User-Agent in raw output
	hostIdx := strings.Index(raw, "Host:")
	uaIdx := strings.Index(raw, "User-Agent:")

	if hostIdx == -1 || uaIdx == -1 {
		t.Fatalf("missing headers in output: %s", raw)
	}
	if hostIdx > uaIdx {
		t.Errorf("Host should come before User-Agent in Chrome order")
	}
}

func TestBuildOrderedHeaders_IncludesAllHeaders(t *testing.T) {
	headers := map[string]string{
		"Accept":     "text/html",
		"User-Agent": "Chrome/133",
		"X-Custom":   "value",
	}

	raw := BuildOrderedHeaders(headers)

	for k, v := range headers {
		if !strings.Contains(raw, k+": "+v) {
			t.Errorf("missing header %s: %s", k, v)
		}
	}
}

func TestBuildOrderedHeaders_UnknownHeadersAtEnd(t *testing.T) {
	headers := map[string]string{
		"Host":         "example.com",
		"X-Weird":      "something",
		"User-Agent":   "Chrome/133",
		"Z-Custom-Foo": "bar",
	}

	raw := BuildOrderedHeaders(headers)

	// Known headers should come before unknown
	uaIdx := strings.Index(raw, "User-Agent:")
	xIdx := strings.Index(raw, "X-Weird:")
	zIdx := strings.Index(raw, "Z-Custom-Foo:")

	if uaIdx > xIdx || uaIdx > zIdx {
		t.Error("known headers should come before unknown custom headers")
	}
}
