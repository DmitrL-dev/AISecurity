package httpserver

import (
	"context"
	"log/slog"
	"time"

	"github.com/syntrex/gomcp/internal/application/judge"
	"github.com/syntrex/gomcp/internal/domain/oracle"
)

// LAYER 3 — gated LLM-judge escalation seam for the scan path.
//
// maybeEscalateToJudge is the ONLY integration point between handlePublicScan
// and the judge tier. It is a strict no-op unless BOTH hold:
//   1. an escalation judge is wired (s.escalationJudge != nil), AND
//   2. the engine risk lands in the operator's ambiguity band.
// In every other case it returns the engine decision unchanged — so when the
// tier is OFF (the default) the scan path is byte-identical to the no-judge path.
//
// On a judge error it FAILS HONEST: logs and returns the ENGINE verdict verbatim
// (never a fabricated judge result). Only on a successful, strictly-parsed judge
// verdict does it apply the conservative merge policy.

// judgeDecision is the result the handler applies after (optionally) consulting
// the judge.
type judgeDecision struct {
	// Blocked is the final block decision (engine, or merged with the judge).
	Blocked bool
	// Consulted is true iff the judge was actually called (in-band + wired).
	Consulted bool
	// Action is the merge action label when Consulted ("escalated_block",
	// "downgraded_allow", "concur", "no_change"); empty when not consulted.
	Action string
	// Vendor is the judge vendor when Consulted; empty otherwise.
	Vendor string
	// Confidence is the judge's confidence when Consulted.
	Confidence float64
	// Reason is the judge's short reason when Consulted.
	Reason string
	// Err is set when the judge was in-band but failed (honest-degrade). The
	// engine verdict is kept; this is surfaced for transparency, not as a 5xx.
	Err error
}

// maybeEscalateToJudge consults the judge iff wired AND the engine risk is in the
// ambiguity band, then applies the merge policy. `prompt` is the raw user prompt;
// it is redacted before being sent to the (operator-configured, BYO-key) vendor.
func (s *Server) maybeEscalateToJudge(ctx context.Context, prompt string, engineBlocked bool, risk float64, threatType string, indicators []string) judgeDecision {
	dec := judgeDecision{Blocked: engineBlocked}

	// Gate 1: tier wired?
	if s.escalationJudge == nil {
		return dec
	}
	// Gate 2: engine risk in the ambiguity band? Out-of-band → no escalation.
	if !s.judgeCfg.InBand(risk) {
		return dec
	}

	dec.Consulted = true

	// PRIVACY TRADEOFF (documented): the judge needs text to classify, so within
	// the ambiguity band we send the MINIMAL needed prompt — but first run it
	// through the same secret scanner used by the SOC seam and strip any matched
	// secret span, so credentials/keys are never shipped to the vendor even
	// in-band. The endpoint is operator-configured and BYO-key/on-prem, so an
	// operator who must not egress prompt text at all simply leaves the tier OFF
	// (default) or points BaseURL at a local model. We also bound the length.
	redacted := redactForJudge(prompt)

	engineView := judge.EngineVerdict{
		Blocked:    engineBlocked,
		Risk:       risk,
		ThreatType: threatType,
		Indicators: indicators,
	}

	// Bound the judge call independently of the outer 30s scan budget so a slow
	// vendor cannot stretch scan latency; the adapter also applies its own timeout.
	jctx, cancel := context.WithTimeout(ctx, judgeCallBudget(s.judgeCfg))
	defer cancel()

	verdict, err := s.escalationJudge.Evaluate(jctx, redacted, engineView)
	if err != nil {
		// FAIL HONEST: keep the engine verdict, do not fabricate. Log without the
		// prompt or key.
		slog.Warn("escalation judge failed — keeping engine verdict (honest-degrade)",
			"vendor", s.escalationJudge.Name(), "error", err)
		dec.Err = err
		return dec
	}

	out := judge.Merge(engineBlocked, verdict, s.judgePolicy)
	dec.Blocked = out.Blocked
	dec.Action = out.Action
	dec.Vendor = verdict.Vendor
	dec.Confidence = verdict.Confidence
	dec.Reason = verdict.Reason
	return dec
}

// redactForJudge produces the minimal text sent to the judge, reusing the SOC
// seam's secret scanner. Privacy posture:
//   - If the prompt trips the secret scanner (a credential/key/connection string
//     is present), we do NOT egress it at all — the whole prompt is replaced with
//     a structural placeholder. The judge is an ADDITIVE signal and the engines
//     already produced the verdict, so withholding a secret-bearing prompt costs
//     nothing on safety while guaranteeing no secret leaves the operator boundary.
//     (The scanner exposes only redacted labels, not the matched spans, so a
//     targeted span-replacement isn't possible; whole-prompt redaction is the
//     honest, conservative choice.)
//   - Otherwise the prompt is sent length-bounded.
func redactForJudge(prompt string) string {
	const maxJudgePromptLen = 2000 // mirrors the scan input cap
	if res := oracle.ScanForSecrets(prompt); res != nil && res.HasSecrets {
		return "[REDACTED: prompt withheld from judge — matched a secret pattern]"
	}
	p := prompt
	if len(p) > maxJudgePromptLen {
		p = p[:maxJudgePromptLen]
	}
	return p
}

// judgeCallBudget returns the seam-level bound for a single judge call.
func judgeCallBudget(cfg judge.Config) time.Duration {
	if cfg.TimeoutSeconds <= 0 {
		return 8 * time.Second
	}
	return time.Duration(cfg.TimeoutSeconds) * time.Second
}
