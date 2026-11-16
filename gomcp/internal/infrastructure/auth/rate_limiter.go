package auth

import (
	"net"
	"net/http"
	"sync"
	"time"
)

// RateLimiter tracks login attempts per IP using a sliding window.
type RateLimiter struct {
	mu       sync.Mutex
	attempts map[string]*ipBucket
	maxHits  int
	window   time.Duration
	cleanup  time.Duration
}

type ipBucket struct {
	timestamps []time.Time
}

// NewRateLimiter creates a rate limiter.
// maxHits: max attempts per window per IP.
// window: sliding window duration.
func NewRateLimiter(maxHits int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		attempts: make(map[string]*ipBucket),
		maxHits:  maxHits,
		window:   window,
		cleanup:  5 * time.Minute,
	}
	go rl.cleanupLoop()
	return rl
}

// Allow checks if the IP is within the rate limit.
// Returns true if allowed, false if rate-limited.
func (rl *RateLimiter) Allow(ip string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	bucket, ok := rl.attempts[ip]
	if !ok {
		bucket = &ipBucket{}
		rl.attempts[ip] = bucket
	}

	// Prune old timestamps outside the window.
	cutoff := now.Add(-rl.window)
	valid := bucket.timestamps[:0]
	for _, t := range bucket.timestamps {
		if t.After(cutoff) {
			valid = append(valid, t)
		}
	}
	bucket.timestamps = valid

	if len(bucket.timestamps) >= rl.maxHits {
		return false
	}

	bucket.timestamps = append(bucket.timestamps, now)
	return true
}

// Reset clears attempts for an IP (e.g., on successful login).
func (rl *RateLimiter) Reset(ip string) {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	delete(rl.attempts, ip)
}

func (rl *RateLimiter) cleanupLoop() {
	ticker := time.NewTicker(rl.cleanup)
	defer ticker.Stop()
	for range ticker.C {
		rl.mu.Lock()
		now := time.Now()
		cutoff := now.Add(-rl.window)
		for ip, bucket := range rl.attempts {
			valid := bucket.timestamps[:0]
			for _, t := range bucket.timestamps {
				if t.After(cutoff) {
					valid = append(valid, t)
				}
			}
			if len(valid) == 0 {
				delete(rl.attempts, ip)
			} else {
				bucket.timestamps = valid
			}
		}
		rl.mu.Unlock()
	}
}

// ExtractClientIP returns the rate-limit key for a request: the TCP peer host
// from r.RemoteAddr.
//
// It deliberately does NOT trust client-supplied X-Forwarded-For / X-Real-IP
// (Review 14.06 round-5). Those headers are attacker-controlled: a fresh forged
// XFF per request landed each attempt in a new bucket, defeating the
// login/register/demo brute-force caps entirely. This mirrors the global HTTP
// limiter ("T4-3 FIX: Use RemoteAddr directly to prevent X-Forwarded-For
// spoofing"). If a trusted reverse proxy is ever fronted, add an explicit
// trusted-proxy allowlist shared by both limiters rather than blindly trusting
// the header here.
func ExtractClientIP(r *http.Request) string {
	if host, _, err := net.SplitHostPort(r.RemoteAddr); err == nil {
		return host
	}
	return r.RemoteAddr
}

// RateLimitMiddleware wraps an http.HandlerFunc with rate limiting.
func RateLimitMiddleware(rl *RateLimiter, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := ExtractClientIP(r)

		if !rl.Allow(ip) {
			w.Header().Set("Retry-After", "60")
			writeAuthError(w, http.StatusTooManyRequests, "rate limit exceeded — try again later")
			return
		}
		next(w, r)
	}
}
