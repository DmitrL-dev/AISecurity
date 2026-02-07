package transport

import (
	"context"
	"math"
	"testing"
	"time"
)

// ============================================================================
// TDD: Ghost Dialer + Jitter Tests
// ============================================================================

func TestNewGhostDialer_NotNil(t *testing.T) {
	gd := NewGhostDialer("https://sourcecraft.dev")
	if gd == nil {
		t.Fatal("GhostDialer is nil")
	}
}

func TestGhostDialer_HasCookieJar(t *testing.T) {
	gd := NewGhostDialer("https://example.com")
	if gd.jar == nil {
		t.Error("cookie jar is nil")
	}
}

func TestGhostDialer_HasUserAgent(t *testing.T) {
	gd := NewGhostDialer("https://example.com")
	if gd.userAgent == "" {
		t.Error("user agent is empty")
	}
	// Must be Chrome 131+
	if len(gd.userAgent) < 50 {
		t.Error("user agent too short to be realistic")
	}
}

func TestGhostDialer_HasOrigin(t *testing.T) {
	gd := NewGhostDialer("https://target.dev")
	if gd.origin != "https://target.dev" {
		t.Errorf("origin = %q, want 'https://target.dev'", gd.origin)
	}
}

func TestHumanDelay_ReturnsPositive(t *testing.T) {
	for i := 0; i < 100; i++ {
		d := HumanDelay(3500, 1500)
		if d <= 0 {
			t.Fatalf("delay must be positive, got %v", d)
		}
	}
}

func TestHumanDelay_HasVariance(t *testing.T) {
	seen := map[time.Duration]bool{}
	for i := 0; i < 50; i++ {
		seen[HumanDelay(3500, 1500)] = true
	}
	if len(seen) < 10 {
		t.Errorf("expected variance in delays, only got %d unique values", len(seen))
	}
}

func TestHumanDelay_BoundedRange(t *testing.T) {
	center := 3500
	for i := 0; i < 200; i++ {
		d := HumanDelay(center, 1500)
		ms := float64(d.Milliseconds())
		// Floor has 1ms tolerance for integer truncation (3500/3 = 1166.67)
		floor := float64(center)/3 - 1
		cap := float64(center) * 3

		if ms < floor || ms > cap {
			t.Errorf("delay %v out of bounds [%.0f, %.0f]", d, floor, cap)
		}
	}
}

func TestHumanDelay_CenteredApproximately(t *testing.T) {
	sum := 0.0
	n := 1000
	for i := 0; i < n; i++ {
		sum += float64(HumanDelay(3500, 500).Milliseconds())
	}
	avg := sum / float64(n)
	// With spread=500, average should be close to 3500 (±300ms)
	if math.Abs(avg-3500) > 300 {
		t.Errorf("average delay = %.0fms, expected ~3500ms", avg)
	}
}

func TestSleepLikeHuman_RespectsContext(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()

	err := SleepLikeHuman(ctx, 10000, 1000) // 10 second sleep
	if err == nil {
		t.Error("expected context cancellation error")
	}
}

func TestDialUTLS_ConnectionRefused(t *testing.T) {
	ctx := context.Background()
	_, err := dialUTLS(ctx, "tcp", "127.0.0.1:1")
	if err == nil {
		t.Error("expected connection error to port 1")
	}
}
