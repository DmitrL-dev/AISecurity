package transport

import (
	"context"
	"net"
	"strings"
	"testing"
	"time"
)

// ============================================================================
// TDD: DNS-over-HTTPS Resolver Tests
// ============================================================================

func TestNewDoHResolver_NotNil(t *testing.T) {
	r := NewDoHResolver("")
	if r == nil {
		t.Fatal("DoHResolver is nil")
	}
}

func TestDoHResolver_DefaultProvider(t *testing.T) {
	r := NewDoHResolver("")
	if r.provider == "" {
		t.Error("default provider should not be empty")
	}
	// Should be Cloudflare or Google by default
	if !strings.Contains(r.provider, "cloudflare") && !strings.Contains(r.provider, "google") {
		t.Errorf("unexpected default provider: %s", r.provider)
	}
}

func TestDoHResolver_CustomProvider(t *testing.T) {
	r := NewDoHResolver("https://custom.dns/resolve")
	if r.provider != "https://custom.dns/resolve" {
		t.Errorf("provider = %q, want custom", r.provider)
	}
}

func TestDoHResolver_ResolvesGoogle(t *testing.T) {
	r := NewDoHResolver("")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	ips, err := r.Resolve(ctx, "google.com")
	if err != nil {
		t.Skipf("DoH resolve failed (network?): %v", err)
	}
	if len(ips) == 0 {
		t.Error("expected at least one IP for google.com")
	}
	// Validate it's an actual IP
	for _, ip := range ips {
		if net.ParseIP(ip) == nil {
			t.Errorf("invalid IP: %s", ip)
		}
	}
}

func TestDoHResolver_InvalidDomain(t *testing.T) {
	r := NewDoHResolver("")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	ips, err := r.Resolve(ctx, "this-domain-definitely-does-not-exist-7f3k9x.invalid")
	if err == nil && len(ips) > 0 {
		t.Error("expected error or empty for nonexistent domain")
	}
}

func TestDoHResolver_TimeoutRespected(t *testing.T) {
	r := NewDoHResolver("")
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Nanosecond)
	defer cancel()

	// Should fail fast with timeout
	_, err := r.Resolve(ctx, "google.com")
	if err == nil {
		t.Error("expected timeout error")
	}
}
