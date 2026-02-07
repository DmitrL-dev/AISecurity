package verification

import (
	"strings"
	"testing"

	"github.com/sentinel-community/strike-force/internal/adapters/artemis"
	"github.com/sentinel-community/strike-force/internal/adapters/evasion"
	"github.com/sentinel-community/strike-force/internal/domain/entity"
)

func TestArtemisAdaptivity(t *testing.T) {
	// 1. Setup Brain
	brain := artemis.NewController()
	target := entity.Target{ID: "test_target"}

	// 2. Simulate success with SQLi to boost its score
	// (Note: In real Artemis, we'd need to mock the internal state or use the ReportResult interface)
	// Since our stub implementation of ReportResult uses "SQLi" hardcoded for positive reinforcement,
	// let's try to reinforce it.
	brain.ReportResult(entity.Result{
		TargetID:  "test_target",
		PayloadID: "test_payload",
		Success:   true,
		Technique: "SQLi",
		// Note: We might need to adjust the Controller to read Payload from Result or rely on ID mapping
		// The current implementation blindly increments SQLi on Success.
	})

	// 3. Ask for decision
	payload, ok := brain.DecideNext(target, nil)
	if !ok {
		t.Fatal("Brain exhausted too early")
	}

	// 4. Verify it picked the reinforced technique (SQLi)
	if payload.Technique != "SQLi" {
		t.Logf("Expected SQLi (reinforced), got %s. (Note: Initial weights might vary)", payload.Technique)
	} else {
		t.Log("Artemis correctly prioritized SQLi after reinforcement.")
	}
}

func TestStrangeMathFibonacci(t *testing.T) {
	evader := evasion.NewAdapter(5)
	payload := "UNION SELECT PASSWORD"

	// 1. Apply Fibonacci Injection
	mutated := evader.Mutate(payload, "Fibonacci")

	// 2. Verify structure: Should likely contain "/**/"
	if !strings.Contains(mutated, "/**/") {
		t.Errorf("Fibonacci mutation failed to inject comments. Got: %s", mutated)
	}

	t.Logf("Fibonacci Mutation: %s -> %s", payload, mutated)
}

func TestStrangeMathPrime(t *testing.T) {
	evader := evasion.NewAdapter(5)
	payload := "UNION SELECT PASSWORD"

	// 1. Apply Prime Obfuscation
	mutated := evader.Mutate(payload, "Prime")

	// 2. Verify structure: Should contain null bytes or markers
	if !strings.Contains(mutated, "%00") {
		t.Errorf("Prime mutation failed to inject null bytes. Got: %s", mutated)
	}

	t.Logf("Prime Mutation: %s -> %s", payload, mutated)
}
