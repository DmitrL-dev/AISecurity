package judge

// MERGE POLICY (conservative by default)
//
// The judge is an ESCALATION tier for AMBIGUOUS engine verdicts. Its job is to
// help resolve the uncertain middle, NOT to override confident deterministic
// detections. The merge rule is therefore deliberately asymmetric:
//
//	1. Judge may ESCALATE-TO-BLOCK an ambiguous case. If the engines did NOT
//	   block (an ambiguous "allow") and the judge says block with confidence at
//	   or above BlockThreshold, the merged verdict becomes BLOCKED. This catches
//	   injections/jailbreaks the deterministic engines were unsure about.
//
//	2. Judge may DOWNGRADE (clear) a detection ONLY with HIGH confidence AND only
//	   inside the ambiguity band — and only when explicitly allowed by the
//	   operator (AllowDowngrade). By default the judge may RAISE a block but may
//	   NOT silently clear a detection (default-conservative: a false negative from
//	   an over-eager judge is worse than a retained false positive). Downgrade is
//	   off unless the operator opts in.
//
// The merge NEVER fabricates: it is only ever called with a real JudgeVerdict
// the caller obtained from Evaluate. On a judge error the caller does not call
// Merge at all and keeps the engine verdict verbatim (honest-degrade).

// MergePolicy parameterizes the merge. Zero value is the safe default
// (conservative): escalate-to-block at >=0.70 confidence, downgrade disabled.
type MergePolicy struct {
	// BlockThreshold is the minimum judge confidence to escalate an ambiguous
	// allow into a block. Default 0.70 when zero.
	BlockThreshold float64
	// AllowDowngrade lets the judge clear a detection (engine blocked → merged
	// allow) when its confidence is at/above DowngradeThreshold. Default false.
	AllowDowngrade bool
	// DowngradeThreshold is the minimum judge confidence to clear a detection
	// when AllowDowngrade is true. Default 0.90 when zero.
	DowngradeThreshold float64
}

func (p MergePolicy) blockThreshold() float64 {
	if p.BlockThreshold <= 0 {
		return 0.70
	}
	return p.BlockThreshold
}

func (p MergePolicy) downgradeThreshold() float64 {
	if p.DowngradeThreshold <= 0 {
		return 0.90
	}
	return p.DowngradeThreshold
}

// MergeOutcome reports the effect the judge had, for response/audit transparency.
type MergeOutcome struct {
	// Blocked is the final, merged block decision.
	Blocked bool
	// Action describes what the judge did: "escalated_block" | "downgraded_allow"
	// | "concur" | "no_change".
	Action string
	// Verdict is the judge verdict that drove the merge (echoed for audit).
	Verdict JudgeVerdict
}

// Merge applies the conservative policy to combine an engine verdict with a
// judge verdict. engineBlocked is the engines' decision for the ambiguous case.
//
// It returns the final decision plus an Action label. Merge is pure and
// deterministic — all the network/honesty concerns live in Evaluate.
func Merge(engineBlocked bool, jv JudgeVerdict, policy MergePolicy) MergeOutcome {
	switch {
	case !engineBlocked && jv.Block && jv.Confidence >= policy.blockThreshold():
		// (1) Escalate an ambiguous allow → block.
		return MergeOutcome{Blocked: true, Action: "escalated_block", Verdict: jv}

	case engineBlocked && !jv.Block && policy.AllowDowngrade && jv.Confidence >= policy.downgradeThreshold():
		// (2) Operator-opted, high-confidence clear of an ambiguous detection.
		return MergeOutcome{Blocked: false, Action: "downgraded_allow", Verdict: jv}

	case engineBlocked == jv.Block:
		// Judge agrees with the engines.
		return MergeOutcome{Blocked: engineBlocked, Action: "concur", Verdict: jv}

	default:
		// Judge disagreed but the policy does not permit the change (e.g. a
		// low-confidence block, or a downgrade with AllowDowngrade=false). Keep the
		// engine verdict — conservative.
		return MergeOutcome{Blocked: engineBlocked, Action: "no_change", Verdict: jv}
	}
}
