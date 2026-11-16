// Package eval implements the CLASP Evaluation Framework (SDD-005).
//
// Provides structured capability scoring for SOC agents across 6 dimensions
// with 5 maturity levels each. Supports automated scoring via LLM-as-judge
// and trend analysis via stored results.
package eval

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Dimension represents a capability axis for agent evaluation.
type Dimension string

const (
	DimPlanning   Dimension = "planning"
	DimToolUse    Dimension = "tool_use"
	DimMemory     Dimension = "memory"
	DimReasoning  Dimension = "reasoning"
	DimReflection Dimension = "reflection"
	DimPerception Dimension = "perception"
)

// AllDimensions returns the 6 CLASP dimensions.
func AllDimensions() []Dimension {
	return []Dimension{
		DimPlanning, DimToolUse, DimMemory,
		DimReasoning, DimReflection, DimPerception,
	}
}

// Stage represents the security lifecycle stage of an eval scenario.
type Stage string

const (
	StageFind      Stage = "find"
	StageConfirm   Stage = "confirm"
	StageRootCause Stage = "root_cause"
	StageValidate  Stage = "validate"
)

// Score represents a capability score for one dimension.
type Score struct {
	Level      int     `json:"level"`      // 1-5 maturity
	Confidence float64 `json:"confidence"` // 0.0-1.0
	Evidence   string  `json:"evidence"`   // Justification
}

// EvalScenario defines a test scenario for agent evaluation.
type EvalScenario struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Stage       Stage    `json:"stage"`
	Description string   `json:"description"`
	Inputs      []string `json:"inputs"`
	Expected    string   `json:"expected"`
	Dimensions  []Dimension `json:"dimensions"` // Which dimensions this tests
}

// EvalResult represents the outcome of evaluating an agent on a scenario.
type EvalResult struct {
	AgentID     string              `json:"agent_id"`
	Timestamp   time.Time           `json:"timestamp"`
	ScenarioID  string              `json:"scenario_id"`
	Scores      map[Dimension]Score `json:"scores"`
	OverallL    int                 `json:"overall_l"` // 1-5 aggregate
	JudgeModel  string              `json:"judge_model,omitempty"`
}

// ComputeOverall calculates the aggregate maturity level (average, rounded down).
func (r *EvalResult) ComputeOverall() int {
	if len(r.Scores) == 0 {
		return 0
	}
	total := 0
	for _, s := range r.Scores {
		total += s.Level
	}
	r.OverallL = total / len(r.Scores)
	return r.OverallL
}

// AgentProfile aggregates multiple EvalResults into a capability profile.
type AgentProfile struct {
	AgentID    string              `json:"agent_id"`
	Results    []EvalResult        `json:"results"`
	Averages   map[Dimension]float64 `json:"averages"`
	OverallL   int                 `json:"overall_l"`
	EvalCount  int                 `json:"eval_count"`
	LastEvalAt time.Time           `json:"last_eval_at"`
}

// ComputeAverages calculates per-dimension average scores across all results.
func (p *AgentProfile) ComputeAverages() {
	if len(p.Results) == 0 {
		return
	}

	dimSums := make(map[Dimension]float64)
	dimCounts := make(map[Dimension]int)

	for _, r := range p.Results {
		for dim, score := range r.Scores {
			dimSums[dim] += float64(score.Level)
			dimCounts[dim]++
		}
	}

	p.Averages = make(map[Dimension]float64)
	totalAvg := 0.0
	for _, dim := range AllDimensions() {
		if count, ok := dimCounts[dim]; ok && count > 0 {
			avg := dimSums[dim] / float64(count)
			p.Averages[dim] = avg
			totalAvg += avg
		}
	}

	if len(p.Averages) > 0 {
		p.OverallL = int(totalAvg / float64(len(p.Averages)))
	}
	p.EvalCount = len(p.Results)
	if len(p.Results) > 0 {
		p.LastEvalAt = p.Results[len(p.Results)-1].Timestamp
	}
}

// DetectRegression compares current profile to a previous one.
// Returns dimensions where the score dropped.
type Regression struct {
	Dimension Dimension `json:"dimension"`
	Previous  float64   `json:"previous"`
	Current   float64   `json:"current"`
	Delta     float64   `json:"delta"`
}

func DetectRegressions(previous, current *AgentProfile) []Regression {
	var regressions []Regression
	for _, dim := range AllDimensions() {
		prev, hasPrev := previous.Averages[dim]
		curr, hasCurr := current.Averages[dim]
		if hasPrev && hasCurr && curr < prev {
			regressions = append(regressions, Regression{
				Dimension: dim,
				Previous:  prev,
				Current:   curr,
				Delta:     curr - prev,
			})
		}
	}
	return regressions
}

// LoadScenarios loads eval scenarios from a JSON file.
func LoadScenarios(path string) ([]EvalScenario, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("load scenarios: %w", err)
	}
	var scenarios []EvalScenario
	if err := json.Unmarshal(data, &scenarios); err != nil {
		return nil, fmt.Errorf("parse scenarios: %w", err)
	}
	return scenarios, nil
}

// SaveResult saves an eval result to the results directory.
func SaveResult(dir string, result *EvalResult) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	filename := fmt.Sprintf("%s_%s_%d.json",
		result.AgentID, result.ScenarioID, result.Timestamp.Unix())
	path := filepath.Join(dir, filename)

	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}
