package httpserver

import (
	"context"
	"testing"
	"time"
)

func TestRateLimiter_Allow(t *testing.T) {
	// limit=10 → burst=max(10/5,5)=5 → hard_limit=15
	rl := NewRateLimiter(context.Background(), 10, time.Second)

	// First 15 (hard_limit) should pass
	for i := 0; i < 15; i++ {
		if !rl.Allow("1.2.3.4") {
			t.Fatalf("request %d should be allowed (hard_limit=15)", i+1)
		}
	}

	// 16th should be denied
	if rl.Allow("1.2.3.4") {
		t.Fatal("request 16 should be rate-limited (exceeds hard_limit=15)")
	}

	// Different IP should be fine
	if !rl.Allow("5.6.7.8") {
		t.Fatal("different IP should be allowed")
	}
}

func TestRateLimiter_Disabled(t *testing.T) {
	rl := NewRateLimiter(context.Background(), 0, time.Second)

	for i := 0; i < 100; i++ {
		if !rl.Allow("1.2.3.4") {
			t.Fatal("disabled rate limiter should allow all")
		}
	}
}

func TestRateLimiter_WindowExpiry(t *testing.T) {
	// limit=10 → burst=5 → hard_limit=15
	rl := NewRateLimiter(context.Background(), 10, 50*time.Millisecond)

	// Exhaust hard limit
	for i := 0; i < 15; i++ {
		rl.Allow("1.2.3.4")
	}

	if rl.Allow("1.2.3.4") {
		t.Fatal("should be rate-limited at hard_limit=15")
	}

	// Wait for window to expire
	time.Sleep(60 * time.Millisecond)

	if !rl.Allow("1.2.3.4") {
		t.Fatal("should be allowed after window expires")
	}
}

func TestRateLimiter_BurstTolerance(t *testing.T) {
	// limit=20 → burst=max(20/5,5)=5 → hard_limit=25
	rl := NewRateLimiter(context.Background(), 20, time.Second)

	// Verify burst field
	stats := rl.Stats()
	if stats["burst"].(int) != 5 {
		t.Fatalf("expected burst=5, got %v", stats["burst"])
	}
	if stats["hard_limit"].(int) != 25 {
		t.Fatalf("expected hard_limit=25, got %v", stats["hard_limit"])
	}

	// Requests 1-20 (within soft limit) — all allowed
	for i := 0; i < 20; i++ {
		if !rl.Allow("10.0.0.1") {
			t.Fatalf("request %d should be within soft limit", i+1)
		}
	}

	// Requests 21-25 (burst zone) — still allowed
	for i := 20; i < 25; i++ {
		if !rl.Allow("10.0.0.1") {
			t.Fatalf("request %d should be within burst zone", i+1)
		}
	}

	// Request 26 (exceeds hard limit) — denied
	if rl.Allow("10.0.0.1") {
		t.Fatal("request 26 should exceed hard limit")
	}
}

func TestRateLimiter_RemainingAndReset(t *testing.T) {
	rl := NewRateLimiter(context.Background(), 10, time.Minute)

	// Fresh IP: remaining = limit
	remaining, resetAt := rl.RemainingAndReset("fresh-ip")
	if remaining != 10 {
		t.Fatalf("expected remaining=10 for fresh IP, got %d", remaining)
	}
	_ = resetAt // reset not meaningful for zero-count IP

	// Use 3 requests
	rl.Allow("test-ip")
	rl.Allow("test-ip")
	rl.Allow("test-ip")

	remaining, resetAt = rl.RemainingAndReset("test-ip")
	if remaining != 7 {
		t.Fatalf("expected remaining=7 after 3 uses, got %d", remaining)
	}
	if resetAt.Before(time.Now()) {
		t.Fatal("reset time should be in the future")
	}

	// Exhaust soft limit
	for i := 0; i < 7; i++ {
		rl.Allow("test-ip")
	}

	remaining, _ = rl.RemainingAndReset("test-ip")
	if remaining != 0 {
		t.Fatalf("expected remaining=0 after exhausting soft limit, got %d", remaining)
	}
}

func TestRateLimiter_Stats(t *testing.T) {
	rl := NewRateLimiter(context.Background(), 10, time.Minute)
	rl.Allow("1.1.1.1")
	rl.Allow("2.2.2.2")

	stats := rl.Stats()
	if stats["enabled"] != true {
		t.Fatal("should be enabled")
	}
	if stats["tracked_ips"].(int) != 2 {
		t.Fatal("should track 2 IPs")
	}
}

func TestMetrics_Counters(t *testing.T) {
	m := NewMetrics()
	m.IncRequests()
	m.IncRequests()
	m.IncErrors()
	m.IncEvents()
	m.IncIncidents()
	m.IncRateLimited()

	if m.requestsTotal.Load() != 2 {
		t.Fatalf("expected 2 requests, got %d", m.requestsTotal.Load())
	}
	if m.requestErrors.Load() != 1 {
		t.Fatalf("expected 1 error, got %d", m.requestErrors.Load())
	}
	if m.eventsIngested.Load() != 1 {
		t.Fatalf("expected 1 event, got %d", m.eventsIngested.Load())
	}
}
