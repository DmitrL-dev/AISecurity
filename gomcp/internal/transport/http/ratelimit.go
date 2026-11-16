package httpserver

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

// RateLimiter provides per-IP sliding window rate limiting (§17.3).
// Supports burst tolerance (soft/hard limits) and standard X-RateLimit headers.
type RateLimiter struct {
	mu      sync.RWMutex
	windows map[string][]time.Time
	limit   int           // max requests per window (soft limit)
	burst   int           // burst tolerance (hard limit = limit + burst)
	window  time.Duration // window size
	// scanLimit is the DEDICATED hard per-IP ceiling for the public scan endpoints
	// (audit 18.06). The scanner is too high-volume for the global limit, but a full
	// exemption left it with NO rate floor — so during a usage-DB outage (when the
	// DB-backed demo quota fails open) a single IP could saturate the heavy-scan
	// concurrency slots. This is a generous-but-finite floor, keyed separately
	// ("scan:<ip>") so scan volume doesn't consume the global bucket. Tunable via
	// SCAN_IP_HARD_LIMIT.
	scanLimit int
	enabled   bool
}

// defaultScanHardLimit is the per-window per-IP ceiling for /api/v1/scan when
// SCAN_IP_HARD_LIMIT is unset — generous for legitimate dashboard/battle/proxy
// scan volume, but finite so abuse can't be unbounded.
const defaultScanHardLimit = 600

// NewRateLimiter creates a rate limiter. Set limit=0 to disable.
// Burst is set to 20% of limit (allows short spikes before hard-dropping).
// The cleanup goroutine stops when ctx is cancelled (T4-6).
func NewRateLimiter(ctx context.Context, limit int, window time.Duration) *RateLimiter {
	burst := limit / 5 // 20% burst tolerance
	if burst < 5 {
		burst = 5
	}
	scanLimit := defaultScanHardLimit
	if v := os.Getenv("SCAN_IP_HARD_LIMIT"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			scanLimit = n
		}
	}
	rl := &RateLimiter{
		windows:   make(map[string][]time.Time),
		limit:     limit,
		burst:     burst,
		window:    window,
		scanLimit: scanLimit,
		enabled:   limit > 0,
	}
	// Background cleanup every 60s — stops on ctx cancellation
	go rl.cleanup(ctx)
	return rl
}

// allowKey is the shared sliding-window admission check for an arbitrary bucket
// key against a hard limit. Returns true if allowed (and records the hit).
func (rl *RateLimiter) allowKey(key string, hardLimit int) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	cutoff := now.Add(-rl.window)

	// Slide window: keep only timestamps within the window
	timestamps := rl.windows[key]
	valid := timestamps[:0]
	for _, ts := range timestamps {
		if ts.After(cutoff) {
			valid = append(valid, ts)
		}
	}

	if len(valid) >= hardLimit {
		rl.windows[key] = valid
		return false
	}

	rl.windows[key] = append(valid, now)
	return true
}

// Allow checks if the IP is within the hard limit (limit + burst).
// Returns true if allowed.
func (rl *RateLimiter) Allow(ip string) bool {
	if !rl.enabled {
		return true
	}
	return rl.allowKey(ip, rl.limit+rl.burst)
}

// AllowScan applies the DEDICATED per-IP ceiling for the public scan endpoints —
// higher than the global limit (so legitimate dashboard/battle/proxy scan volume
// isn't throttled) but FINITE, so the public scanner keeps a per-IP floor that
// survives a usage-DB outage (audit 18.06). Keyed separately from the global bucket.
func (rl *RateLimiter) AllowScan(ip string) bool {
	if !rl.enabled {
		return true
	}
	return rl.allowKey("scan:"+ip, rl.scanLimit)
}

// remainingAndResetKey returns the remaining requests (against `limit`) and the
// window-reset time for an arbitrary bucket key.
func (rl *RateLimiter) remainingAndResetKey(key string, limit int) (remaining int, resetAt time.Time) {
	rl.mu.RLock()
	defer rl.mu.RUnlock()

	now := time.Now()
	cutoff := now.Add(-rl.window)
	count := 0
	earliestInWindow := now

	for _, ts := range rl.windows[key] {
		if ts.After(cutoff) {
			count++
			if ts.Before(earliestInWindow) {
				earliestInWindow = ts
			}
		}
	}

	remaining = limit - count
	if remaining < 0 {
		remaining = 0
	}
	resetAt = earliestInWindow.Add(rl.window)
	return
}

// RemainingAndReset returns the remaining requests within the soft limit
// and the time when the window resets for this IP.
func (rl *RateLimiter) RemainingAndReset(ip string) (remaining int, resetAt time.Time) {
	return rl.remainingAndResetKey(ip, rl.limit)
}

// write429 emits the standard rate-limit headers + a 429 for a throttled key.
func (rl *RateLimiter) write429(w http.ResponseWriter, key string, limit int) {
	_, resetAt := rl.remainingAndResetKey(key, limit)
	retryAfter := int(time.Until(resetAt).Seconds())
	if retryAfter < 1 {
		retryAfter = 1
	}
	w.Header().Set("Retry-After", fmt.Sprintf("%d", retryAfter))
	w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", limit))
	w.Header().Set("X-RateLimit-Remaining", "0")
	w.Header().Set("X-RateLimit-Reset", fmt.Sprintf("%d", resetAt.Unix()))
	writeError(w, http.StatusTooManyRequests, "rate limit exceeded")
}

// writeRateHeaders emits the X-RateLimit-* headers for an admitted request.
func (rl *RateLimiter) writeRateHeaders(w http.ResponseWriter, key string, limit int) {
	remaining, resetAt := rl.remainingAndResetKey(key, limit)
	w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", limit))
	w.Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))
	w.Header().Set("X-RateLimit-Reset", fmt.Sprintf("%d", resetAt.Unix()))
}

// Middleware wraps an HTTP handler with rate limiting.
// Internal/dashboard control paths (auth, SSE stream, event ingestion, signed
// webhooks) are fully exempt to avoid throttling legitimate operations. The PUBLIC
// scan endpoints are NOT fully exempt — they get a dedicated higher-but-finite
// per-IP ceiling (audit 18.06) so they keep a floor independent of the DB-backed
// demo quota. Emits standard X-RateLimit-* headers on every response.
func (rl *RateLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !rl.enabled {
			next.ServeHTTP(w, r)
			return
		}

		p := r.URL.Path
		switch {
		case p == "/api/auth/login",
			p == "/api/auth/refresh",
			p == "/api/soc/stream",
			p == "/api/v1/soc/events",
			p == "/api/soc/events",
			p == "/api/billing/webhook",
			p == "/api/soc/webhooks",
			p == "/api/soc/webhooks/test":
			// Fully exempt: internal/dashboard control + event-ingest streams.
			next.ServeHTTP(w, r)
			return
		}

		// Key on the real client IP: the TCP peer (so a direct client cannot spoof
		// via X-Forwarded-For, the T4-3 guarantee), OR — when the peer is a
		// configured trusted proxy (SOC_TRUSTED_PROXIES) — the client the proxy
		// forwarded, so behind nginx clients aren't all collapsed into the proxy's IP.
		ip := clientIP(r)

		// Public scanner: dedicated finite per-IP ceiling instead of a full exemption
		// (audit 18.06) — a hard floor independent of the DB-backed demo quota so a
		// single IP can't saturate the heavy-scan slots during a usage-DB outage.
		if p == "/api/v1/scan" || p == "/api/scan" {
			scanKey := "scan:" + ip
			if !rl.AllowScan(ip) {
				rl.write429(w, scanKey, rl.scanLimit)
				return
			}
			rl.writeRateHeaders(w, scanKey, rl.scanLimit)
			next.ServeHTTP(w, r)
			return
		}

		if !rl.Allow(ip) {
			rl.write429(w, ip, rl.limit)
			return
		}
		rl.writeRateHeaders(w, ip, rl.limit)
		next.ServeHTTP(w, r)
	})
}

// Stats returns rate limiter statistics.
func (rl *RateLimiter) Stats() map[string]any {
	rl.mu.RLock()
	defer rl.mu.RUnlock()
	return map[string]any{
		"enabled":     rl.enabled,
		"limit":       rl.limit,
		"burst":       rl.burst,
		"hard_limit":  rl.limit + rl.burst,
		"scan_limit":  rl.scanLimit,
		"window_sec":  rl.window.Seconds(),
		"tracked_ips": len(rl.windows),
	}
}

// cleanup removes expired entries periodically. Stops on ctx cancellation.
func (rl *RateLimiter) cleanup(ctx context.Context) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			rl.mu.Lock()
			cutoff := time.Now().Add(-rl.window)
			for ip, timestamps := range rl.windows {
				valid := timestamps[:0]
				for _, ts := range timestamps {
					if ts.After(cutoff) {
						valid = append(valid, ts)
					}
				}
				if len(valid) == 0 {
					delete(rl.windows, ip)
				} else {
					rl.windows[ip] = valid
				}
			}
			rl.mu.Unlock()
		}
	}
}
