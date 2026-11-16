package soc

import (
	"testing"
)

func TestZeroGMode_Disabled(t *testing.T) {
	zg := NewZeroGMode()

	id := zg.RequestApproval("evt-1", "", "block_ip", "HIGH", "Block attacker IP")
	if id != "" {
		t.Fatal("disabled Zero-G should return empty ID")
	}
}

func TestZeroGMode_EnableAndRequest(t *testing.T) {
	zg := NewZeroGMode()
	zg.Enable()

	if !zg.IsEnabled() {
		t.Fatal("should be enabled")
	}

	id := zg.RequestApproval("evt-1", "inc-1", "block_ip", "CRITICAL", "Block attacker 1.2.3.4")
	if id == "" {
		t.Fatal("enabled Zero-G should return request ID")
	}

	pending := zg.PendingRequests()
	if len(pending) != 1 {
		t.Fatalf("expected 1 pending, got %d", len(pending))
	}
	if pending[0].EventID != "evt-1" {
		t.Fatalf("expected evt-1, got %s", pending[0].EventID)
	}
}

func TestZeroGMode_Approve(t *testing.T) {
	zg := NewZeroGMode()
	zg.Enable()

	id := zg.RequestApproval("evt-1", "", "quarantine", "HIGH", "Quarantine host")

	err := zg.Resolve(id, ZGVerdictApprove, "analyst-1")
	if err != nil {
		t.Fatalf("resolve failed: %v", err)
	}

	pending := zg.PendingRequests()
	if len(pending) != 0 {
		t.Fatal("should have 0 pending after resolve")
	}

	stats := zg.Stats()
	if stats["approved"].(int) != 1 {
		t.Fatal("should have 1 approved")
	}
}

func TestZeroGMode_Deny(t *testing.T) {
	zg := NewZeroGMode()
	zg.Enable()

	id := zg.RequestApproval("evt-2", "", "kill_process", "MEDIUM", "Kill suspicious proc")

	err := zg.Resolve(id, ZGVerdictDeny, "analyst-2")
	if err != nil {
		t.Fatalf("resolve failed: %v", err)
	}

	stats := zg.Stats()
	if stats["denied"].(int) != 1 {
		t.Fatal("should have 1 denied")
	}
}

func TestZeroGMode_ResolveNotFound(t *testing.T) {
	zg := NewZeroGMode()
	zg.Enable()

	err := zg.Resolve("zg-nonexistent", ZGVerdictApprove, "analyst")
	if err == nil {
		t.Fatal("should error on non-existent request")
	}
}

func TestZeroGMode_QueueOverflow(t *testing.T) {
	zg := NewZeroGMode()
	zg.Enable()

	// Fill queue past max (200)
	for i := 0; i < 201; i++ {
		zg.RequestApproval("evt", "", "action", "LOW", "test")
	}

	pending := zg.PendingRequests()
	if len(pending) != 200 {
		t.Fatalf("expected 200 pending (capped), got %d", len(pending))
	}

	stats := zg.Stats()
	if stats["expired"].(int) != 1 {
		t.Fatalf("expected 1 expired, got %d", stats["expired"])
	}
}

func TestZeroGMode_Toggle(t *testing.T) {
	zg := NewZeroGMode()

	if zg.IsEnabled() {
		t.Fatal("should start disabled")
	}

	zg.Enable()
	if !zg.IsEnabled() {
		t.Fatal("should be enabled")
	}

	zg.Disable()
	if zg.IsEnabled() {
		t.Fatal("should be disabled again")
	}
}
