package orchestrator

import (
	"math"
	"testing"
)

func TestParseEngineScores_FFIFormat(t *testing.T) {
	// The exact format sentinel-core/src/ffi.rs emits: "engine/pattern (NN%)".
	indicators := []string{
		"prompt_injection/ignore_instructions (95%)",
		"jailbreak/dan_mode (80%)",
		"prompt_injection/role_override (88%)", // same engine, higher than... no, lower than 95
	}
	scores := ParseEngineScores(indicators)
	if len(scores) != 2 {
		t.Fatalf("expected 2 distinct engines, got %d: %v", len(scores), scores)
	}
	// Same engine fires twice → MAX confidence wins (0.95 over 0.88).
	if got := scores["prompt_injection"]; math.Abs(got-0.95) > 1e-9 {
		t.Errorf("prompt_injection: want 0.95 (max), got %v", got)
	}
	if got := scores["jailbreak"]; math.Abs(got-0.80) > 1e-9 {
		t.Errorf("jailbreak: want 0.80, got %v", got)
	}
}

func TestParseEngineScores_DecimalAndPrefixedSkipped(t *testing.T) {
	indicators := []string{
		"encoding/base64 (12.5%)",   // decimal percentage
		"shield/payload_inspection", // no percentage → skipped (other-tier indicator)
		"ml/jailbreak",              // no percentage → skipped
		"judge/escalated_block",     // no percentage → skipped
		"garbage-without-slash",     // unparseable → skipped
	}
	scores := ParseEngineScores(indicators)
	if len(scores) != 1 {
		t.Fatalf("expected only the encoding engine, got %d: %v", len(scores), scores)
	}
	if got := scores["encoding"]; math.Abs(got-0.125) > 1e-9 {
		t.Errorf("encoding: want 0.125, got %v", got)
	}
}

func TestParseEngineScores_EmptyAndNil(t *testing.T) {
	if s := ParseEngineScores(nil); s != nil {
		t.Errorf("nil indicators should give nil map, got %v", s)
	}
	if s := ParseEngineScores([]string{"shield/x", "ml/y"}); s != nil {
		t.Errorf("all-unparseable should give nil map, got %v", s)
	}
}

func TestParseEngineScores_ClampsOutOfRange(t *testing.T) {
	// A malformed >100% must clamp to 1.0 (defensive).
	scores := ParseEngineScores([]string{"weird_engine/x (250%)"})
	if got := scores["weird_engine"]; got != 1.0 {
		t.Errorf("250%% should clamp to 1.0, got %v", got)
	}
}

func TestAggregateToVector_FixedOrder(t *testing.T) {
	a := AggregateFeatures{
		Risk:             0.9,
		CoreConfidence:   0.8,
		ShieldConfidence: 0.7,
		MLConfidence:     0.6,
		EnginesTriggered: 3,
		CoreBlocked:      true,
		ShieldBlocked:    false,
		MLBlocked:        true,
	}
	v := a.ToVector()
	want := []float64{0.9, 0.8, 0.7, 0.6, 3, 1, 0, 1}
	if len(v) != len(want) {
		t.Fatalf("vector length: want %d, got %d", len(want), len(v))
	}
	for i := range want {
		if math.Abs(v[i]-want[i]) > 1e-9 {
			t.Errorf("vector[%d]: want %v, got %v", i, want[i], v[i])
		}
	}
}

func TestToExportRow_AggregateOnlyWeightedDown(t *testing.T) {
	s := Sample{
		VectorComplete: false, // aggregate-only (today's reality)
		VectorSchema:   VectorSchema,
		Aggregate:      AggregateFeatures{Risk: 0.9, CoreConfidence: 0.9, EnginesTriggered: 1, CoreBlocked: true},
		Label:          LabelMalicious,
		Blocked:        true,
		Risk:           0.9,
	}
	row := s.ToExportRow()
	if row.VectorComplete {
		t.Error("aggregate-only row should not be marked vector_complete")
	}
	if row.Weight != 0.5 {
		t.Errorf("aggregate-only weight: want 0.5, got %v", row.Weight)
	}
	// The vector must be the aggregate vector (8 dims), not empty.
	if len(row.Vector) != 8 {
		t.Errorf("export vector should be the 8-dim aggregate vector, got %d", len(row.Vector))
	}
	if row.Label != LabelMalicious {
		t.Errorf("label: want malicious, got %v", row.Label)
	}
}

func TestToExportRow_DenseVectorFullWeight(t *testing.T) {
	// Forward-compat: once a real dense per-engine vector exists, it is used at
	// full weight.
	dense := make([]float64, 39)
	dense[0] = 0.9
	s := Sample{
		VectorComplete: true,
		VectorSchema:   "dense-v1",
		EngineVector:   dense,
		Label:          LabelBenign,
	}
	row := s.ToExportRow()
	if !row.VectorComplete || row.Weight != 1.0 {
		t.Errorf("dense row: want complete + weight 1.0, got complete=%v weight=%v", row.VectorComplete, row.Weight)
	}
	if len(row.Vector) != 39 {
		t.Errorf("dense vector length: want 39, got %d", len(row.Vector))
	}
}

func TestValidLabel(t *testing.T) {
	if !ValidLabel(LabelMalicious) || !ValidLabel(LabelBenign) {
		t.Error("malicious/benign must be valid")
	}
	if ValidLabel(LabelUnlabeled) || ValidLabel(Label("garbage")) {
		t.Error("empty/garbage labels must be invalid")
	}
}
