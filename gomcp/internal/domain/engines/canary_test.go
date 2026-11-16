package engines

import (
	"context"
	"errors"
	"testing"
)

type canaryFake struct {
	detect  bool
	scanErr error
}

func (f canaryFake) Name() string                 { return "canary-fake" }
func (f canaryFake) Status() EngineStatus          { return EngineHealthy }
func (f canaryFake) Version() string               { return "fake" }
func (f canaryFake) ScanResponse(context.Context, string) (*ScanResult, error) {
	return &ScanResult{}, nil
}
func (f canaryFake) ScanPrompt(context.Context, string) (*ScanResult, error) {
	if f.scanErr != nil {
		return nil, f.scanErr
	}
	return &ScanResult{Engine: "canary-fake", ThreatFound: f.detect}, nil
}

func TestStartupCanary(t *testing.T) {
	// A functioning engine flags the canary → nil.
	if err := StartupCanary(context.Background(), canaryFake{detect: true}); err != nil {
		t.Fatalf("detecting engine must pass canary, got %v", err)
	}

	// The stub / a non-detecting engine returns clean → error (fail closed).
	if err := StartupCanary(context.Background(), canaryFake{detect: false}); err == nil {
		t.Fatal("non-detecting engine must FAIL the canary")
	}

	// The real stub specifically must fail the canary.
	if err := StartupCanary(context.Background(), NewStubSentinelCore()); err == nil {
		t.Fatal("StubSentinelCore must FAIL the canary (it allows everything)")
	}

	// A scan error also fails closed.
	if err := StartupCanary(context.Background(), canaryFake{scanErr: errors.New("boom")}); err == nil {
		t.Fatal("a scan error must fail the canary")
	}
}
