package eval

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestAllDimensionsCount(t *testing.T) {
	dims := AllDimensions()
	if len(dims) != 6 {
		t.Errorf("expected 6 dimensions, got %d", len(dims))
	}
}

func TestComputeOverall(t *testing.T) {
	result := &EvalResult{
		Scores: map[Dimension]Score{
			DimPlanning:   {Level: 3},
			DimToolUse:    {Level: 4},
			DimMemory:     {Level: 2},
			DimReasoning:  {Level: 5},
			DimReflection: {Level: 3},
			DimPerception: {Level: 1},
		},
	}
	overall := result.ComputeOverall()
	// (3+4+2+5+3+1)/6 = 18/6 = 3
	if overall != 3 {
		t.Errorf("expected overall 3, got %d", overall)
	}
}

func TestAgentProfileAverages(t *testing.T) {
	profile := &AgentProfile{
		AgentID: "test-agent",
		Results: []EvalResult{
			{
				Scores: map[Dimension]Score{
					DimPlanning: {Level: 2},
					DimToolUse:  {Level: 4},
				},
				Timestamp: time.Now(),
			},
			{
				Scores: map[Dimension]Score{
					DimPlanning: {Level: 4},
					DimToolUse:  {Level: 4},
				},
				Timestamp: time.Now(),
			},
		},
	}
	profile.ComputeAverages()

	if profile.Averages[DimPlanning] != 3.0 {
		t.Errorf("planning avg should be 3.0, got %.1f", profile.Averages[DimPlanning])
	}
	if profile.Averages[DimToolUse] != 4.0 {
		t.Errorf("tool_use avg should be 4.0, got %.1f", profile.Averages[DimToolUse])
	}
	if profile.EvalCount != 2 {
		t.Errorf("expected 2 evals, got %d", profile.EvalCount)
	}
}

func TestDetectRegressions(t *testing.T) {
	prev := &AgentProfile{
		Averages: map[Dimension]float64{
			DimPlanning: 4.0,
			DimToolUse:  3.0,
			DimMemory:   2.0,
		},
	}
	curr := &AgentProfile{
		Averages: map[Dimension]float64{
			DimPlanning: 3.0, // regression
			DimToolUse:  4.0, // improvement
			DimMemory:   2.0, // same
		},
	}

	regressions := DetectRegressions(prev, curr)
	if len(regressions) != 1 {
		t.Fatalf("expected 1 regression, got %d", len(regressions))
	}
	if regressions[0].Dimension != DimPlanning {
		t.Errorf("expected regression in planning, got %s", regressions[0].Dimension)
	}
	if regressions[0].Delta != -1.0 {
		t.Errorf("expected delta -1.0, got %.1f", regressions[0].Delta)
	}
}

func TestSaveAndLoadResult(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "results")

	result := &EvalResult{
		AgentID:    "test-agent",
		Timestamp:  time.Now(),
		ScenarioID: "scenario-001",
		Scores: map[Dimension]Score{
			DimPlanning: {Level: 3, Confidence: 0.9, Evidence: "good planning"},
		},
		OverallL: 3,
	}

	if err := SaveResult(dir, result); err != nil {
		t.Fatalf("SaveResult error: %v", err)
	}

	// Verify file was created
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("ReadDir error: %v", err)
	}
	if len(entries) != 1 {
		t.Errorf("expected 1 result file, got %d", len(entries))
	}
}

func TestScoreValidLevels(t *testing.T) {
	for level := 1; level <= 5; level++ {
		s := Score{Level: level, Confidence: 0.8}
		if s.Level < 1 || s.Level > 5 {
			t.Errorf("level %d out of range", s.Level)
		}
	}
}
