//go:build sentinel_native

package engines

import (
	"context"
	"math"
	"strings"
	"testing"
)

// Exercises the real CGo bridge and Rust exports. No HTTP service, customer
// data, external provider, model download or payment is used by this fixture.
func TestNativeSentinelABI(t *testing.T) {
	core, err := NewNativeSentinelCore()
	if err != nil {
		t.Fatalf("native initialization failed: %v", err)
	}
	t.Cleanup(func() { _ = core.Shutdown() })
	if core.Version() == "" || core.Version() == "unknown" || core.Status() != EngineHealthy {
		t.Fatal("native engine did not report version and healthy status")
	}
	var count uint64
	for _, tc := range []struct{ name, input string }{
		{"empty", ""}, {"ascii", "The meeting starts at ten."}, {"utf8", "Встреча начнётся в десять."},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got := core.analyze(tc.input)
			if got.Error != "" || got.InputLength != len(tc.input) || got.AnalyzeCount <= count {
				t.Fatalf("invalid native response or byte/count contract: error=%q length=%d count=%d", got.Error, got.InputLength, got.AnalyzeCount)
			}
			count = got.AnalyzeCount
			if got.IsThreat || math.IsNaN(got.Confidence) || math.IsInf(got.Confidence, 0) || got.Confidence < 0 || got.Confidence > 1 {
				t.Fatal("benign fixture rejected or invalid native confidence")
			}
			if len(got.EngineVector) == 0 || len(got.EngineVector) != len(got.EngineVectorOrder) {
				t.Fatal("native vector and order missing or inconsistent")
			}
			seen := map[string]bool{}
			for i, name := range got.EngineVectorOrder {
				v := got.EngineVector[i]
				if name == "" || seen[name] || math.IsNaN(v) || math.IsInf(v, 0) || v < 0 || v > 1 {
					t.Fatal("invalid vector coordinate or ambiguous engine identity")
				}
				seen[name] = true
			}
		})
	}
	t.Run("startup_canary", func(t *testing.T) {
		if err := StartupCanary(context.Background(), core); err != nil {
			t.Fatalf("native startup canary: %v", err)
		}
	})
	for _, tc := range []struct{ name, input string }{
		{"interior_nul", "synthetic-prefix\x00" + canaryPrompt},
		{"invalid_utf8", string([]byte{0xff, 0xfe})},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := core.ScanPrompt(context.Background(), tc.input)
			if err == nil || got != nil || strings.Contains(err.Error(), tc.input) {
				t.Fatal("invalid input did not fail closed without echoing input")
			}
		})
	}
	t.Run("response", func(t *testing.T) {
		got, err := core.ScanResponse(context.Background(), "The meeting starts at ten.")
		if err != nil || got == nil || got.ThreatFound || got.Engine != "sentinel-core" {
			t.Fatal("native response scan failed")
		}
	})
	t.Run("shutdown", func(t *testing.T) {
		if core.Shutdown() != nil || core.Shutdown() != nil || core.Status() != EngineOffline {
			t.Fatal("native shutdown was not idempotent or left the bridge online")
		}
		if got, err := core.ScanPrompt(context.Background(), "synthetic"); err == nil || got != nil {
			t.Fatal("closed native bridge admitted a scan")
		}
	})
}
