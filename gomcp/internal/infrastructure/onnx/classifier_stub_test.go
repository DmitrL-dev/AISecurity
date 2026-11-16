//go:build !onnx

package onnx

import (
	"context"
	"testing"
)

// These tests run in the DEFAULT (CGO=0, no -tags onnx) build and pin the
// honest fail-open contract: without the onnx build tag the classifier is
// simply unavailable — the constructor returns (nil, nil) so the SOC server
// leaves s.safetyClassifier nil and reports ml_status:"offline". It must never
// claim to be active.
func TestStubNewSafetyClassifier_ReturnsNil(t *testing.T) {
	cls, err := NewSafetyClassifier(ClassifierConfig{ModelPath: "ignored", MaxSeqLen: 256})
	if err != nil {
		t.Fatalf("stub constructor should not error, got %v", err)
	}
	if cls != nil {
		t.Fatalf("stub constructor must return nil classifier (so ML stays offline), got %v", cls)
	}
}

func TestStubClassify_ReturnsSafe(t *testing.T) {
	// The stub Classify is only reachable if someone holds a non-nil stub value;
	// it must return a benign, non-threat result (additive signal, never blocks).
	var sc SafetyClassifier
	res, err := sc.Classify(context.Background(), "any text")
	if err != nil {
		t.Fatalf("stub classify error: %v", err)
	}
	if res == nil || res.IsThreat || res.Category != ThreatSafe {
		t.Fatalf("stub classify must be safe/non-threat, got %+v", res)
	}
}
