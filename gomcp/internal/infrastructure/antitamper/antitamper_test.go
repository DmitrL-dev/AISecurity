package antitamper

import (
	"os"
	"testing"
)

func TestNewShield(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	if shield.BinaryHash() == "" {
		t.Error("binary hash is empty")
	}
	if len(shield.BinaryHash()) != 64 { // SHA-256 = 64 hex chars
		t.Errorf("hash length = %d, want 64", len(shield.BinaryHash()))
	}
}

func TestCheckBinaryIntegrity_Clean(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	event := shield.CheckBinaryIntegrity()
	if event != nil {
		t.Errorf("expected no tamper event, got: %+v", event)
	}
}

func TestCheckBinaryIntegrity_Tampered(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	// Simulate tamper by changing stored hash.
	shield.binaryHash = "0000000000000000000000000000000000000000000000000000000000000000"

	event := shield.CheckBinaryIntegrity()
	if event == nil {
		t.Fatal("expected tamper event for modified hash")
	}
	if event.Type != TamperBinaryMod {
		t.Errorf("type = %s, want binary_modified", event.Type)
	}
	if event.Severity != "CRITICAL" {
		t.Errorf("severity = %s, want CRITICAL", event.Severity)
	}
}

func TestCheckEnvIntegrity_Clean(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	event := shield.CheckEnvIntegrity()
	if event != nil {
		t.Errorf("expected no tamper event, got: %+v", event)
	}
}

func TestCheckEnvIntegrity_Tampered(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	// Set a monitored env var after snapshot.
	original := os.Getenv("SOC_DB_PATH")
	os.Setenv("SOC_DB_PATH", "/malicious/path")
	defer os.Setenv("SOC_DB_PATH", original)

	event := shield.CheckEnvIntegrity()
	if event == nil {
		t.Fatal("expected tamper event for env change")
	}
	if event.Type != TamperEnvTamper {
		t.Errorf("type = %s, want env_tampering", event.Type)
	}
}

func TestCheckDebugger(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	// In a normal test environment, no debugger should be attached.
	event := shield.CheckDebugger()
	if event != nil {
		t.Logf("debugger detected (expected if running under debugger): %+v", event)
	}
}

func TestRunAllChecks(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	events := shield.RunAllChecks()
	// In clean environment, no events expected.
	if len(events) > 0 {
		t.Logf("tamper events detected (may be expected in CI): %d", len(events))
		for _, e := range events {
			t.Logf("  %s: %s", e.Type, e.Detail)
		}
	}
}

func TestStats(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	shield.CheckBinaryIntegrity()
	shield.CheckEnvIntegrity()
	shield.CheckDebugger()

	stats := shield.Stats()
	if stats.TotalChecks != 3 {
		t.Errorf("total_checks = %d, want 3", stats.TotalChecks)
	}
	if !stats.BinaryIntegrity {
		t.Error("binary_integrity should be true for clean binary")
	}
}

func TestTamperHandler(t *testing.T) {
	shield, err := NewShield()
	if err != nil {
		t.Fatalf("NewShield: %v", err)
	}

	var received []TamperEvent
	shield.OnTamper(func(e TamperEvent) {
		received = append(received, e)
	})

	// Force a tamper detection.
	shield.binaryHash = "fake"
	shield.CheckBinaryIntegrity()

	if len(received) != 1 {
		t.Fatalf("handler received %d events, want 1", len(received))
	}
	if received[0].Type != TamperBinaryMod {
		t.Errorf("type = %s, want binary_modified", received[0].Type)
	}
}
