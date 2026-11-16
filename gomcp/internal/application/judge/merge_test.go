package judge

import "testing"

func TestMerge_ConservativeDefault(t *testing.T) {
	def := MergePolicy{} // escalate>=0.70, downgrade OFF

	cases := []struct {
		name          string
		engineBlocked bool
		jv            JudgeVerdict
		wantBlocked   bool
		wantAction    string
	}{
		{
			name:          "escalate ambiguous allow to block (high conf)",
			engineBlocked: false,
			jv:            JudgeVerdict{Block: true, Confidence: 0.85},
			wantBlocked:   true,
			wantAction:    "escalated_block",
		},
		{
			name:          "do NOT escalate on low confidence",
			engineBlocked: false,
			jv:            JudgeVerdict{Block: true, Confidence: 0.55},
			wantBlocked:   false,
			wantAction:    "no_change",
		},
		{
			name:          "judge concurs with allow",
			engineBlocked: false,
			jv:            JudgeVerdict{Block: false, Confidence: 0.2},
			wantBlocked:   false,
			wantAction:    "concur",
		},
		{
			name:          "judge concurs with block",
			engineBlocked: true,
			jv:            JudgeVerdict{Block: true, Confidence: 0.9},
			wantBlocked:   true,
			wantAction:    "concur",
		},
		{
			name:          "judge must NOT silently clear a detection by default",
			engineBlocked: true,
			jv:            JudgeVerdict{Block: false, Confidence: 0.99},
			wantBlocked:   true, // kept blocked — downgrade disabled
			wantAction:    "no_change",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Merge(c.engineBlocked, c.jv, def)
			if got.Blocked != c.wantBlocked {
				t.Errorf("Blocked = %v, want %v", got.Blocked, c.wantBlocked)
			}
			if got.Action != c.wantAction {
				t.Errorf("Action = %q, want %q", got.Action, c.wantAction)
			}
		})
	}
}

func TestMerge_DowngradeWhenOptedIn(t *testing.T) {
	pol := MergePolicy{AllowDowngrade: true, DowngradeThreshold: 0.90}

	// High-confidence clear → downgraded.
	got := Merge(true, JudgeVerdict{Block: false, Confidence: 0.95}, pol)
	if got.Blocked || got.Action != "downgraded_allow" {
		t.Fatalf("expected downgrade, got %+v", got)
	}

	// Below threshold → kept blocked.
	got = Merge(true, JudgeVerdict{Block: false, Confidence: 0.80}, pol)
	if !got.Blocked || got.Action != "no_change" {
		t.Fatalf("below threshold must keep block, got %+v", got)
	}
}

func TestMerge_CustomBlockThreshold(t *testing.T) {
	pol := MergePolicy{BlockThreshold: 0.50}
	got := Merge(false, JudgeVerdict{Block: true, Confidence: 0.55}, pol)
	if !got.Blocked || got.Action != "escalated_block" {
		t.Fatalf("custom threshold escalate failed: %+v", got)
	}
}
