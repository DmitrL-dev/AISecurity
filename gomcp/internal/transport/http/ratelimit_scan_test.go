package httpserver

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// Regression for the pre-launch audit 18.06 fail-open-under-degradation gap: the
// public /api/v1/scan endpoint must have a DEDICATED finite per-IP ceiling instead
// of a full rate-limiter exemption, so it keeps a floor independent of the
// DB-backed demo quota (which can fail open during a usage-DB outage). The truly
// internal control paths stay fully exempt.
func TestRateLimiter_ScanHasDedicatedFiniteCeiling(t *testing.T) {
	t.Setenv("SCAN_IP_HARD_LIMIT", "3") // tiny ceiling so the test hits it quickly
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	rl := NewRateLimiter(ctx, 100, time.Minute)
	h := rl.Middleware(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	do := func(path, ip string) int {
		r := httptest.NewRequest(http.MethodPost, path, nil)
		r.RemoteAddr = ip + ":40000"
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w.Code
	}

	// /api/v1/scan is NOT exempt and NOT unlimited: 3 pass, the 4th from the same IP
	// is throttled (429) — independent of any DB-backed quota.
	for i := 0; i < 3; i++ {
		if code := do("/api/v1/scan", "1.2.3.4"); code != http.StatusOK {
			t.Fatalf("scan request %d should pass under the ceiling, got %d", i+1, code)
		}
	}
	if code := do("/api/v1/scan", "1.2.3.4"); code != http.StatusTooManyRequests {
		t.Fatalf("scan over the per-IP ceiling must be 429, got %d", code)
	}

	// A different IP is unaffected (per-IP, not global).
	if code := do("/api/v1/scan", "5.6.7.8"); code != http.StatusOK {
		t.Fatalf("a different IP must still pass, got %d", code)
	}

	// The legacy /api/scan alias shares the same per-IP scan ceiling.
	for i := 0; i < 3; i++ {
		do("/api/scan", "9.9.9.9")
	}
	if code := do("/api/scan", "9.9.9.9"); code != http.StatusTooManyRequests {
		t.Fatalf("/api/scan must share the per-IP scan ceiling, got %d", code)
	}

	// A truly-exempt control path is NEVER limited — far beyond the global limit.
	for i := 0; i < 250; i++ {
		if code := do("/api/auth/login", "1.2.3.4"); code != http.StatusOK {
			t.Fatalf("fully-exempt path must never be rate limited, got %d at request %d", code, i+1)
		}
	}
}
