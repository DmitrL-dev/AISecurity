package judge

import (
	"context"
	"testing"
)

// ── Config / env ────────────────────────────────────────────────────────────

func TestLoadConfigFromEnv_DefaultsAndDisabled(t *testing.T) {
	withEnv(t, map[string]string{}) // all unset
	cfg := LoadConfigFromEnv()
	if cfg.Enabled {
		t.Fatal("JUDGE_ENABLED must default to false")
	}
	if cfg.Vendor != VendorOpenAICompatible {
		t.Fatalf("default vendor = %q, want %q", cfg.Vendor, VendorOpenAICompatible)
	}
	if cfg.EscalateLow != DefaultEscalateLow || cfg.EscalateHigh != DefaultEscalateHigh {
		t.Fatalf("default band = [%v,%v], want [%v,%v]", cfg.EscalateLow, cfg.EscalateHigh, DefaultEscalateLow, DefaultEscalateHigh)
	}
	if cfg.TimeoutSeconds != 8 {
		t.Fatalf("default timeout = %d, want 8", cfg.TimeoutSeconds)
	}
}

func TestLoadConfigFromEnv_Parsed(t *testing.T) {
	withEnv(t, map[string]string{
		"JUDGE_ENABLED":       "yes",
		"JUDGE_VENDOR":        "Anthropic",
		"JUDGE_BASE_URL":      "https://judge.internal/v1",
		"JUDGE_API_KEY":       "sk-test",
		"JUDGE_MODEL":         "claude-haiku-4-5",
		"JUDGE_ESCALATE_LOW":  "0.3",
		"JUDGE_ESCALATE_HIGH": "0.7",
	})
	cfg := LoadConfigFromEnv()
	if !cfg.Enabled {
		t.Fatal("JUDGE_ENABLED=yes must enable")
	}
	if cfg.Vendor != VendorAnthropic { // lowercased
		t.Fatalf("vendor = %q", cfg.Vendor)
	}
	if cfg.EscalateLow != 0.3 || cfg.EscalateHigh != 0.7 {
		t.Fatalf("band = [%v,%v]", cfg.EscalateLow, cfg.EscalateHigh)
	}
}

// ── New: default-OFF no-op + validation ─────────────────────────────────────

func TestNew_DisabledIsNoOp(t *testing.T) {
	j, err := New(Config{Enabled: false})
	if err != nil {
		t.Fatalf("disabled New must not error, got %v", err)
	}
	if j != nil {
		t.Fatal("disabled New must return a nil judge (clean no-op)")
	}
}

func TestNew_EnabledRequiresKeyAndModel(t *testing.T) {
	if _, err := New(Config{Enabled: true, Model: "m"}); err != ErrMissingAPIKey {
		t.Fatalf("missing key: want ErrMissingAPIKey, got %v", err)
	}
	if _, err := New(Config{Enabled: true, APIKey: "k"}); err != ErrMissingModel {
		t.Fatalf("missing model: want ErrMissingModel, got %v", err)
	}
}

func TestNew_UnknownVendor(t *testing.T) {
	_, err := New(Config{Enabled: true, APIKey: "k", Model: "m", Vendor: "cohere"})
	if err == nil {
		t.Fatal("unknown vendor must error")
	}
}

func TestNew_ValidVendors(t *testing.T) {
	for _, v := range []string{VendorOpenAICompatible, "openai", "", VendorAnthropic} {
		j, err := New(Config{Enabled: true, APIKey: "k", Model: "m", Vendor: v, BaseURL: "https://x.example/v1"})
		if err != nil {
			t.Fatalf("vendor %q: unexpected error %v", v, err)
		}
		if j == nil {
			t.Fatalf("vendor %q: nil judge", v)
		}
	}
}

// ── URL validation (SSRF/safety) ────────────────────────────────────────────

func TestValidateBaseURL(t *testing.T) {
	cases := []struct {
		url string
		ok  bool
	}{
		{"", true}, // empty → adapter default
		{"https://api.openai.com/v1", true},
		{"https://judge.corp.internal:8443/v1", true},
		{"http://api.openai.com/v1", false}, // not https
		{"ftp://x/v1", false},               // wrong scheme
		{"://nope", false},                  // malformed
		{"https://", false},                 // no host
		{"not a url at all", false},         // no scheme/host
	}
	for _, c := range cases {
		err := ValidateBaseURL(c.url)
		if c.ok && err != nil {
			t.Errorf("ValidateBaseURL(%q) = %v, want nil", c.url, err)
		}
		if !c.ok && err == nil {
			t.Errorf("ValidateBaseURL(%q) = nil, want error", c.url)
		}
	}
}

func TestNew_RejectsBadBaseURL(t *testing.T) {
	_, err := New(Config{Enabled: true, APIKey: "k", Model: "m", BaseURL: "http://insecure/v1"})
	if err == nil {
		t.Fatal("New must reject a non-https base URL")
	}
}

// ── Ambiguity band gating ───────────────────────────────────────────────────

func TestConfig_InBand(t *testing.T) {
	cfg := Config{EscalateLow: 0.40, EscalateHigh: 0.60}
	in := []float64{0.40, 0.50, 0.60} // inclusive bounds
	out := []float64{0.0, 0.39, 0.61, 1.0}
	for _, r := range in {
		if !cfg.InBand(r) {
			t.Errorf("risk %v should be IN band", r)
		}
	}
	for _, r := range out {
		if cfg.InBand(r) {
			t.Errorf("risk %v should be OUT of band", r)
		}
	}
}

func TestConfig_InBand_InvertedIsClosed(t *testing.T) {
	// A misconfigured (inverted) band must never silently escalate everything.
	cfg := Config{EscalateLow: 0.60, EscalateHigh: 0.40}
	for _, r := range []float64{0.0, 0.5, 0.6, 1.0} {
		if cfg.InBand(r) {
			t.Fatalf("inverted band must be closed, but risk %v reported in-band", r)
		}
	}
}

// ── Strict JSON parse + fail-honest ─────────────────────────────────────────

func TestParseVerdict_Valid(t *testing.T) {
	v, err := ParseVerdict(`{"block": true, "confidence": 0.83, "reason": "obvious injection"}`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !v.Block || v.Confidence != 0.83 || v.Reason != "obvious injection" {
		t.Fatalf("parsed wrong: %+v", v)
	}
}

func TestParseVerdict_FenceTolerated(t *testing.T) {
	raw := "```json\n{\"block\": false, \"confidence\": 0.1, \"reason\": \"benign\"}\n```"
	v, err := ParseVerdict(raw)
	if err != nil {
		t.Fatalf("fence should be tolerated, got %v", err)
	}
	if v.Block {
		t.Fatal("expected block=false")
	}
}

func TestParseVerdict_FailHonest(t *testing.T) {
	bad := []string{
		"",                                       // empty
		"   ",                                    // whitespace
		"I think this is an injection, block it", // prose, no JSON — must NOT be scraped
		`{"confidence": 0.9}`,                    // missing block
		`{"block": "yes"}`,                       // block not a bool
		`{"block": true, "confidence": 1.5}`,     // confidence out of range
		`{"block": true, "confidence": "high"}`,  // non-numeric confidence
		`{"block": true} trailing junk`,          // trailing content
		`not json`,                               // garbage
	}
	for _, b := range bad {
		if _, err := ParseVerdict(b); err == nil {
			t.Errorf("ParseVerdict(%q) must fail honest (error), got nil", b)
		}
	}
}

func TestParseVerdict_ReasonClamped(t *testing.T) {
	long := make([]byte, 500)
	for i := range long {
		long[i] = 'x'
	}
	v, err := ParseVerdict(`{"block": true, "confidence": 0.5, "reason": "` + string(long) + `"}`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(v.Reason) > maxReasonLen {
		t.Fatalf("reason not clamped: len=%d", len(v.Reason))
	}
}

// ── Pool ────────────────────────────────────────────────────────────────────

type fakeJudge struct{ name string }

func (f *fakeJudge) Name() string { return f.name }
func (f *fakeJudge) Evaluate(_ context.Context, _ string, _ EngineVerdict) (JudgeVerdict, error) {
	return JudgeVerdict{Vendor: f.name}, nil
}

func TestPool(t *testing.T) {
	a := &fakeJudge{name: "openai-compatible"}
	b := &fakeJudge{name: "anthropic"}
	p := NewPool("anthropic", a, b)
	if p.Active() != b {
		t.Fatal("active should be anthropic")
	}
	if got, ok := p.Get("openai-compatible"); !ok || got != a {
		t.Fatal("Get(openai-compatible) failed")
	}
	if _, ok := p.Get("missing"); ok {
		t.Fatal("Get(missing) should be false")
	}
	if len(p.Names()) != 2 {
		t.Fatalf("Names len = %d, want 2", len(p.Names()))
	}

	// nil pool is a safe no-op.
	var np *Pool
	if np.Active() != nil {
		t.Fatal("nil pool Active must be nil")
	}
}
