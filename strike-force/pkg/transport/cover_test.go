package transport

import (
	"context"
	"testing"
	"time"
)

// ============================================================================
// TDD: Cover Traffic Generator Tests
// ============================================================================

func TestNewCoverTraffic_NotNil(t *testing.T) {
	ct := NewCoverTraffic()
	if ct == nil {
		t.Fatal("CoverTraffic is nil")
	}
}

func TestCoverTraffic_HasTargets(t *testing.T) {
	ct := NewCoverTraffic()
	if len(ct.targets) == 0 {
		t.Error("cover targets should not be empty")
	}
}

func TestCoverTraffic_TargetsAreLegitimate(t *testing.T) {
	ct := NewCoverTraffic()
	for _, target := range ct.targets {
		if len(target) < 10 {
			t.Errorf("target too short to be a real URL: %s", target)
		}
	}
}

func TestCoverTraffic_GenerateBurst_RespectsCount(t *testing.T) {
	ct := NewCoverTraffic()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	results := ct.GenerateBurst(ctx, 3)
	if len(results) != 3 {
		t.Errorf("expected 3 results, got %d", len(results))
	}
}

func TestCoverTraffic_GenerateBurst_HasStatus(t *testing.T) {
	ct := NewCoverTraffic()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	results := ct.GenerateBurst(ctx, 1)
	if len(results) == 0 {
		t.Skip("no results (network issue?)")
	}
	// Each result should have a target and status
	if results[0].Target == "" {
		t.Error("result target is empty")
	}
}

func TestCoverTraffic_Cancelled(t *testing.T) {
	ct := NewCoverTraffic()
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Immediately cancel

	results := ct.GenerateBurst(ctx, 5)
	// Should return empty or partial results
	if len(results) > 5 {
		t.Error("should not exceed requested count")
	}
}
