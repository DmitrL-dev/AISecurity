package httpserver

import (
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
)

// Trusted-proxy-aware client-IP resolution (Review 14.06 round-6).
//
// Background: a prior fix (T4-3) keyed rate-limits and quotas on r.RemoteAddr and
// deliberately IGNORED X-Forwarded-For, because a direct client can forge that
// header to dodge per-IP limits. Correct against a directly-exposed server — but
// behind a reverse proxy (the production topology: nginx → soc_api), RemoteAddr is
// the PROXY's address, so every client collapses into ONE bucket: the anonymous
// demo cap becomes a single global counter and the rate-limiter throttles everyone
// together.
//
// Resolution: trust the proxy's forwarded client IP ONLY when the immediate TCP
// peer is itself a CONFIGURED trusted proxy (SOC_TRUSTED_PROXIES). With no
// allowlist (the default) clientIP returns the TCP peer exactly as before — so a
// directly-exposed deploy keeps the T4-3 anti-spoof guarantee, and a proxied deploy
// opts in by naming its proxy network.

var (
	trustedProxiesOnce sync.Once
	trustedProxyNets   []*net.IPNet
)

// loadTrustedProxies parses SOC_TRUSTED_PROXIES: a comma-separated list of CIDRs or
// bare IPs (IPv4/IPv6). Bare IPs become /32 or /128. Parsed once. Empty ⇒ nil ⇒ no
// proxy is trusted.
func loadTrustedProxies() []*net.IPNet {
	trustedProxiesOnce.Do(func() {
		for _, p := range strings.Split(os.Getenv("SOC_TRUSTED_PROXIES"), ",") {
			p = strings.TrimSpace(p)
			if p == "" {
				continue
			}
			if !strings.Contains(p, "/") {
				if strings.Contains(p, ":") {
					p += "/128"
				} else {
					p += "/32"
				}
			}
			if _, n, err := net.ParseCIDR(p); err == nil {
				trustedProxyNets = append(trustedProxyNets, n)
			}
		}
	})
	return trustedProxyNets
}

func isTrustedProxy(nets []*net.IPNet, ip net.IP) bool {
	if ip == nil {
		return false
	}
	for _, n := range nets {
		if n.Contains(ip) {
			return true
		}
	}
	return false
}

// clientIP returns the best-effort real client IP to key rate-limits / quotas on.
// It honours X-Forwarded-For / X-Real-IP ONLY when the TCP peer is a trusted proxy;
// otherwise it returns the TCP peer so a direct client cannot spoof its key. When
// trusted, it returns the right-most XFF hop that is NOT itself a trusted proxy
// (the closest client-controlled address the proxy chain saw), falling back to
// X-Real-IP, then the peer.
func clientIP(r *http.Request) string {
	peer := r.RemoteAddr
	if host, _, err := net.SplitHostPort(peer); err == nil {
		peer = host
	}
	nets := loadTrustedProxies()
	if len(nets) == 0 || !isTrustedProxy(nets, net.ParseIP(peer)) {
		return peer
	}
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		for i := len(parts) - 1; i >= 0; i-- {
			cand := strings.TrimSpace(parts[i])
			cip := net.ParseIP(cand)
			if cip != nil && !isTrustedProxy(nets, cip) {
				return cand
			}
		}
	}
	if xr := strings.TrimSpace(r.Header.Get("X-Real-IP")); xr != "" && net.ParseIP(xr) != nil {
		return xr
	}
	return peer
}
