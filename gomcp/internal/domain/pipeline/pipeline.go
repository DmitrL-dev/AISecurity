// Package pipeline implements the Intent Pipeline — the end-to-end chain
// that processes signals through DIP components (H1.3).
//
// Flow: Input → Entropy Check → Distill → Oracle Verify → Output
//
//	       ↕
//	Circuit Breaker
//
// Each stage can halt the pipeline. The Circuit Breaker monitors
// overall pipeline health across invocations.
package pipeline

import (
	"context"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/circuitbreaker"
	"github.com/syntrex/gomcp/internal/domain/entropy"
	"github.com/syntrex/gomcp/internal/domain/intent"
	"github.com/syntrex/gomcp/internal/domain/oracle"
)

// Stage represents a processing stage.
type Stage string

const (
	StageEntropy  Stage = "entropy_check"
	StageDistill  Stage = "distill_intent"
	StageOracle   Stage = "oracle_verify"
	StageComplete Stage = "complete"
	StageBlocked  Stage = "blocked"
)

// Result holds the complete pipeline processing result.
type Result struct {
	// Pipeline status
	Stage       Stage  `json:"stage"`      // Last completed stage
	IsAllowed   bool   `json:"is_allowed"` // Pipeline passed all checks
	IsBlocked   bool   `json:"is_blocked"` // Pipeline was halted
	BlockReason string `json:"block_reason,omitempty"`
	BlockStage  Stage  `json:"block_stage,omitempty"` // Which stage blocked

	// Stage outputs
	EntropyResult *entropy.GateResult   `json:"entropy,omitempty"`
	DistillResult *intent.DistillResult `json:"distill,omitempty"`
	OracleResult  *oracle.Result        `json:"oracle,omitempty"`
	CircuitState  string                `json:"circuit_state"`

	// Timing
	DurationMs int64 `json:"duration_ms"`
}

// Config configures the pipeline.
type Config struct {
	// SkipDistill disables the distillation stage (if no PyBridge).
	SkipDistill bool

	// SkipOracle disables the Oracle verification stage.
	SkipOracle bool
}

// Pipeline chains DIP components into a single processing flow.
type Pipeline struct {
	cfg     Config
	gate    *entropy.Gate
	distill *intent.Distiller // nil if no PyBridge
	oracle  *oracle.Oracle
	breaker *circuitbreaker.Breaker
}

// New creates a new Intent Pipeline.
func New(
	gate *entropy.Gate,
	distill *intent.Distiller,
	oracleInst *oracle.Oracle,
	breaker *circuitbreaker.Breaker,
	cfg *Config,
) *Pipeline {
	p := &Pipeline{
		gate:    gate,
		distill: distill,
		oracle:  oracleInst,
		breaker: breaker,
	}
	if cfg != nil {
		p.cfg = *cfg
	}
	if p.distill == nil {
		p.cfg.SkipDistill = true
	}
	return p
}

// Process runs the full pipeline on input text.
func (p *Pipeline) Process(ctx context.Context, text string) *Result {
	start := time.Now()

	result := &Result{
		IsAllowed:    true,
		CircuitState: p.breaker.CurrentState().String(),
	}

	// Pre-check: Circuit Breaker.
	if !p.breaker.IsAllowed() {
		result.IsAllowed = false
		result.IsBlocked = true
		result.Stage = StageBlocked
		result.BlockStage = StageBlocked
		result.BlockReason = "circuit breaker is OPEN"
		result.DurationMs = time.Since(start).Milliseconds()
		return result
	}

	// Stage 1: Entropy Check.
	if p.gate != nil {
		er := p.gate.Check(text)
		result.EntropyResult = er
		if er.IsBlocked {
			p.breaker.RecordAnomaly(fmt.Sprintf("entropy: %s", er.BlockReason))
			result.IsAllowed = false
			result.IsBlocked = true
			result.Stage = StageEntropy
			result.BlockStage = StageEntropy
			result.BlockReason = er.BlockReason
			result.CircuitState = p.breaker.CurrentState().String()
			result.DurationMs = time.Since(start).Milliseconds()
			return result
		}
	}

	// Stage 2: Intent Distillation.
	if !p.cfg.SkipDistill {
		dr, err := p.distill.Distill(ctx, text)
		if err != nil {
			// Distillation error is an anomaly but not a block.
			p.breaker.RecordAnomaly(fmt.Sprintf("distill error: %v", err))
			// Continue without distillation.
		} else {
			result.DistillResult = dr

			// Check sincerity.
			if dr.IsManipulation {
				p.breaker.RecordAnomaly("manipulation detected")
				result.IsAllowed = false
				result.IsBlocked = true
				result.Stage = StageDistill
				result.BlockStage = StageDistill
				result.BlockReason = fmt.Sprintf(
					"manipulation detected (sincerity=%.3f)",
					dr.SincerityScore)
				result.CircuitState = p.breaker.CurrentState().String()
				result.DurationMs = time.Since(start).Milliseconds()
				return result
			}

			// Use compressed text for Oracle if distillation succeeded.
			text = dr.CompressedText
		}
	}

	// Stage 3: Oracle Verification.
	if !p.cfg.SkipOracle && p.oracle != nil {
		or := p.oracle.Verify(text)
		result.OracleResult = or

		if or.Verdict == "DENY" {
			p.breaker.RecordAnomaly(fmt.Sprintf("oracle denied: %s", or.Reason))
			result.IsAllowed = false
			result.IsBlocked = true
			result.Stage = StageOracle
			result.BlockStage = StageOracle
			result.BlockReason = fmt.Sprintf("action denied: %s", or.Reason)
			result.CircuitState = p.breaker.CurrentState().String()
			result.DurationMs = time.Since(start).Milliseconds()
			return result
		}
	}

	// All stages passed.
	p.breaker.RecordClean()
	result.Stage = StageComplete
	result.CircuitState = p.breaker.CurrentState().String()
	result.DurationMs = time.Since(start).Milliseconds()
	return result
}
