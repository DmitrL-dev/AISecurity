package oracle

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestOracle_ExactMatch(t *testing.T) {
	o := New([]Rule{
		{ID: "r1", Pattern: "read", Verdict: VerdictAllow, Keywords: []string{"read"}},
	})
	r := o.Verify("read")
	assert.Equal(t, "ALLOW", r.Verdict)
	assert.Equal(t, 1.0, r.Confidence)
	assert.Equal(t, "exact match", r.Reason)
	require.NotNil(t, r.MatchedRule)
	assert.Equal(t, "r1", r.MatchedRule.ID)
}

func TestOracle_PrefixMatch(t *testing.T) {
	o := New([]Rule{
		{ID: "r1", Pattern: "read", Verdict: VerdictAllow},
	})
	r := o.Verify("read file from disk")
	assert.Equal(t, "ALLOW", r.Verdict)
	assert.Equal(t, 0.8, r.Confidence)
	assert.Contains(t, r.Reason, "deny-first")
}

func TestOracle_KeywordMatch(t *testing.T) {
	o := New([]Rule{
		{ID: "deny-exec", Pattern: "execute", Verdict: VerdictDeny,
			Keywords: []string{"exec", "run", "shell", "command"}},
	})
	r := o.Verify("please run this shell command")
	assert.Equal(t, "DENY", r.Verdict)
	assert.Contains(t, r.Reason, "keyword")
}

func TestOracle_DefaultDeny(t *testing.T) {
	o := New([]Rule{
		{ID: "r1", Pattern: "read", Verdict: VerdictAllow},
	})
	r := o.Verify("something completely unknown")
	assert.Equal(t, "DENY", r.Verdict)
	assert.Equal(t, 1.0, r.Confidence)
	assert.Contains(t, r.Reason, "default deny")
}

func TestOracle_EmptyAction(t *testing.T) {
	o := New(DefaultRules())
	r := o.Verify("")
	assert.Equal(t, "DENY", r.Verdict)
	assert.Contains(t, r.Reason, "empty")
}

func TestOracle_CaseInsensitive(t *testing.T) {
	o := New([]Rule{
		{ID: "r1", Pattern: "READ", Verdict: VerdictAllow},
	})
	r := o.Verify("read")
	assert.Equal(t, "ALLOW", r.Verdict)
}

func TestOracle_LowConfidenceKeyword_Review(t *testing.T) {
	o := New([]Rule{
		{ID: "r1", Pattern: "analyze", Verdict: VerdictAllow,
			Keywords: []string{"analyze", "check", "verify", "test", "validate"}},
	})
	// Only 1 out of 5 keywords matches → low confidence → REVIEW.
	r := o.Verify("please check")
	assert.Equal(t, "REVIEW", r.Verdict)
	assert.Less(t, r.Confidence, 0.5)
}

func TestOracle_DefaultRules_Exec(t *testing.T) {
	o := New(DefaultRules())
	r := o.Verify("execute shell command rm -rf")
	assert.Equal(t, "DENY", r.Verdict)
}

func TestOracle_DefaultRules_Read(t *testing.T) {
	o := New(DefaultRules())
	r := o.Verify("read")
	assert.Equal(t, "ALLOW", r.Verdict)
}

func TestOracle_DefaultRules_Network(t *testing.T) {
	o := New(DefaultRules())
	r := o.Verify("download file from http server")
	assert.Equal(t, "DENY", r.Verdict)
}

func TestOracle_AddRule(t *testing.T) {
	o := New(nil)
	assert.Equal(t, 0, o.RuleCount())

	o.AddRule(Rule{ID: "custom", Pattern: "deploy", Verdict: VerdictReview})
	assert.Equal(t, 1, o.RuleCount())

	r := o.Verify("deploy")
	assert.Equal(t, "REVIEW", r.Verdict)
}

func TestOracle_Rules_Immutable(t *testing.T) {
	o := New(DefaultRules())
	rules := o.Rules()
	original := len(rules)
	mutated := append(rules, Rule{ID: "hack"})
	assert.Len(t, mutated, original+1)
	assert.Equal(t, original, o.RuleCount(), "original should be unchanged")
}

func TestOracle_VerdictString(t *testing.T) {
	assert.Equal(t, "ALLOW", VerdictAllow.String())
	assert.Equal(t, "DENY", VerdictDeny.String())
	assert.Equal(t, "REVIEW", VerdictReview.String())
	assert.Equal(t, "UNKNOWN", Verdict(99).String())
}

func TestOracle_DurationMeasured(t *testing.T) {
	o := New(DefaultRules())
	r := o.Verify("read something")
	assert.GreaterOrEqual(t, r.DurationUs, int64(0))
}
