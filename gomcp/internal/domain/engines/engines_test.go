package engines

import (
	"context"
	"testing"
)

func TestStubSentinelCore(t *testing.T) {
	core := NewStubSentinelCore()

	if core.Name() != "sentinel-core-stub" {
		t.Fatalf("expected stub name, got %s", core.Name())
	}
	if core.Status() != EngineOffline {
		t.Fatal("stub should be offline")
	}

	result, err := core.ScanPrompt(context.Background(), "test prompt injection")
	if err != nil {
		t.Fatalf("scan should not error: %v", err)
	}
	if result.ThreatFound {
		t.Fatal("stub should never find threats")
	}
	if result.Engine != "sentinel-core-stub" {
		t.Fatalf("wrong engine: %s", result.Engine)
	}

	result2, err := core.ScanResponse(context.Background(), "response data")
	if err != nil {
		t.Fatalf("response scan should not error: %v", err)
	}
	if result2.ThreatFound {
		t.Fatal("stub response scan should not find threats")
	}
}

func TestStubShield(t *testing.T) {
	shield := NewStubShield()

	if shield.Name() != "shield-stub" {
		t.Fatalf("expected stub name, got %s", shield.Name())
	}
	if shield.Status() != EngineOffline {
		t.Fatal("stub should be offline")
	}

	result, err := shield.InspectTraffic(context.Background(), []byte("data"), nil)
	if err != nil {
		t.Fatalf("inspect should not error: %v", err)
	}
	if result.ThreatFound {
		t.Fatal("stub should never find threats")
	}

	err = shield.BlockIP(context.Background(), "1.2.3.4", "test", 0)
	if err != nil {
		t.Fatalf("block should not error: %v", err)
	}

	blocked, err := shield.ListBlocked(context.Background())
	if err != nil || len(blocked) != 0 {
		t.Fatal("stub should return empty blocked list")
	}
}

// Verify interfaces are satisfied at compile time
var _ SentinelCore = (*StubSentinelCore)(nil)
var _ Shield = (*StubShield)(nil)
