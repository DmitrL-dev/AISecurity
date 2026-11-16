package httpserver

import (
	"net/http"
	"sync"
	"testing"
)

// resetTrustedProxies forces a re-parse of SOC_TRUSTED_PROXIES (the production
// loader is sync.Once; tests need to vary the env).
func resetTrustedProxies() {
	trustedProxiesOnce = sync.Once{}
	trustedProxyNets = nil
}

func reqWith(remote, xff, xreal string) *http.Request {
	r := &http.Request{RemoteAddr: remote, Header: http.Header{}}
	if xff != "" {
		r.Header.Set("X-Forwarded-For", xff)
	}
	if xreal != "" {
		r.Header.Set("X-Real-IP", xreal)
	}
	return r
}

func TestClientIP_NoAllowlist_IgnoresForwardedHeaders(t *testing.T) {
	t.Setenv("SOC_TRUSTED_PROXIES", "")
	resetTrustedProxies()
	defer resetTrustedProxies()

	// Default (no trusted proxy): a direct client CANNOT spoof its key via XFF /
	// X-Real-IP — the TCP peer wins (the T4-3 guarantee).
	got := clientIP(reqWith("203.0.113.7:5555", "1.2.3.4", "5.6.7.8"))
	if got != "203.0.113.7" {
		t.Fatalf("expected TCP peer 203.0.113.7, got %q", got)
	}
}

func TestClientIP_TrustedProxy_UsesForwardedClient(t *testing.T) {
	t.Setenv("SOC_TRUSTED_PROXIES", "10.0.0.0/8,172.16.0.0/12")
	resetTrustedProxies()
	defer resetTrustedProxies()

	// Peer is the trusted proxy (172.18.x docker net) → trust the forwarded client.
	got := clientIP(reqWith("172.18.0.5:443", "198.51.100.23", ""))
	if got != "198.51.100.23" {
		t.Fatalf("expected forwarded client 198.51.100.23, got %q", got)
	}

	// Right-most NON-proxy hop wins (proxy chain: client, then internal proxies).
	got = clientIP(reqWith("172.18.0.5:443", "198.51.100.23, 10.1.2.3", ""))
	if got != "198.51.100.23" {
		t.Fatalf("expected right-most non-proxy hop 198.51.100.23, got %q", got)
	}

	// XFF absent → fall back to X-Real-IP.
	got = clientIP(reqWith("172.18.0.5:443", "", "198.51.100.99"))
	if got != "198.51.100.99" {
		t.Fatalf("expected X-Real-IP 198.51.100.99, got %q", got)
	}
}

func TestClientIP_UntrustedPeer_IgnoresForwardedEvenWithAllowlist(t *testing.T) {
	t.Setenv("SOC_TRUSTED_PROXIES", "10.0.0.0/8")
	resetTrustedProxies()
	defer resetTrustedProxies()

	// Peer is NOT in the allowlist (a direct internet client) → its forged XFF is
	// ignored; the TCP peer is the key. No spoofing even with an allowlist set.
	got := clientIP(reqWith("203.0.113.7:5555", "10.0.0.1", "10.0.0.2"))
	if got != "203.0.113.7" {
		t.Fatalf("expected TCP peer 203.0.113.7 (forged headers ignored), got %q", got)
	}
}
