package transport

import (
	"strings"
	"testing"
)

// ============================================================================
// TDD: Transport Client Tests
// ============================================================================

func TestNewStealthClient_NotNil(t *testing.T) {
	c := NewStealthClient(0)
	if c == nil {
		t.Fatal("NewStealthClient returned nil")
	}
}

func TestUserAgentPool_NotEmpty(t *testing.T) {
	pool := UserAgentPool()
	if len(pool) == 0 {
		t.Fatal("UA pool is empty")
	}
}

func TestUserAgentPool_AllModern(t *testing.T) {
	pool := UserAgentPool()
	for _, ua := range pool {
		// All UAs must be Chrome 131+ (current era)
		if !strings.Contains(ua, "Chrome/13") {
			t.Errorf("outdated UA detected: %s", ua)
		}
		// Must contain Windows NT 10.0
		if !strings.Contains(ua, "Windows NT 10.0") {
			t.Errorf("UA missing Windows NT 10.0: %s", ua)
		}
	}
}

func TestRandomUA_ReturnsDifferentValues(t *testing.T) {
	c := NewStealthClient(0)
	seen := make(map[string]bool)

	for i := 0; i < 50; i++ {
		ua := c.RandomUA()
		seen[ua] = true
	}

	// With a pool of 5+, we expect at least 2 different values in 50 tries
	if len(seen) < 2 {
		t.Errorf("expected UA rotation, but got only %d unique values", len(seen))
	}
}

func TestStealthClient_HeadersSet(t *testing.T) {
	c := NewStealthClient(0)
	headers := c.DefaultHeaders()

	// Must have realistic browser headers
	required := []string{"User-Agent", "Accept", "Accept-Language", "Accept-Encoding"}
	for _, h := range required {
		if headers[h] == "" {
			t.Errorf("missing required header: %s", h)
		}
	}
}
