package engines

import (
	"strings"
	"testing"
)

func TestDecodeSentinelAnalyzeValid(t *testing.T) {
	for _, test := range []struct {
		name, input, payload string
		threat               bool
		confidence           float64
	}{
		{"safe", "ok", `{"is_threat":false,"confidence":0,"input_length":2}`, false, 0},
		{"threat_utf8", "ёж", `{"is_threat":true,"confidence":0.75,"input_length":4,"categories":["synthetic"],"future":{"x":1}}`, true, 0.75},
		// No invented relation between threat and confidence: both are explicit.
		{"explicit_true_zero", "", `{"is_threat":true,"confidence":0,"input_length":0}`, true, 0},
	} {
		t.Run(test.name, func(t *testing.T) {
			got, err := decodeSentinelAnalyze([]byte(test.payload), len(test.input))
			if err != nil || got.IsThreat != test.threat || got.Confidence != test.confidence || got.InputLength != len(test.input) {
				t.Fatalf("wrong result: %#v, %v", got, err)
			}
		})
	}
}

func TestDecodeSentinelAnalyzeRejectsAmbiguousResponses(t *testing.T) {
	tests := map[string]string{
		"empty": ``, "null_root": `null`, "empty_object": `{}`, "array": `[]`, "malformed": `{`,
		"missing_threat":      `{"confidence":0,"input_length":2}`,
		"missing_confidence":  `{"is_threat":false,"input_length":2}`,
		"missing_length":      `{"is_threat":false,"confidence":0}`,
		"null_threat":         `{"is_threat":null,"confidence":0,"input_length":2}`,
		"null_confidence":     `{"is_threat":false,"confidence":null,"input_length":2}`,
		"null_length":         `{"is_threat":false,"confidence":0,"input_length":null}`,
		"wrong_bool":          `{"is_threat":"false","confidence":0,"input_length":2}`,
		"wrong_confidence":    `{"is_threat":false,"confidence":"0","input_length":2}`,
		"fractional_length":   `{"is_threat":false,"confidence":0,"input_length":2.5}`,
		"negative_confidence": `{"is_threat":false,"confidence":-0.1,"input_length":2}`,
		"over_one":            `{"is_threat":false,"confidence":1.1,"input_length":2}`,
		"not_finite":          `{"is_threat":false,"confidence":1e999,"input_length":2}`,
		"bad_length":          `{"is_threat":false,"confidence":0,"input_length":1}`,
		"duplicate_threat":    `{"is_threat":false,"is_threat":true,"confidence":0,"input_length":2}`,
		"duplicate_nested":    `{"is_threat":false,"confidence":0,"input_length":2,"future":{"x":1,"x":2}}`,
		"case_alias":          `{"is_threat":false,"IS_THREAT":true,"confidence":0,"input_length":2}`,
		"case_error":          `{"is_threat":false,"confidence":0,"input_length":2,"Error":"synthetic secret"}`,
		"trailing":            `{"is_threat":false,"confidence":0,"input_length":2} {}`,
		"native_error":        `{"error":"synthetic secret"}`,
		"contradictory_error": `{"is_threat":false,"confidence":0,"input_length":2,"error":"synthetic secret"}`,
		"null_error":          `{"is_threat":false,"confidence":0,"input_length":2,"error":null}`,
	}
	for name, payload := range tests {
		t.Run(name, func(t *testing.T) {
			_, err := decodeSentinelAnalyze([]byte(payload), len("ok"))
			if err == nil {
				t.Fatal("expected failure")
			}
			if strings.Contains(err.Error(), "synthetic secret") || (payload != "" && strings.Contains(err.Error(), payload)) {
				t.Fatal("error exposed native payload")
			}
		})
	}
}

func TestValidSentinelInputRejectsInteriorNUL(t *testing.T) {
	if validSentinelInput("ok\x00tail") || !validSentinelInput("ёж") || !validSentinelInput("") {
		t.Fatal("incorrect NUL admission")
	}
}

func TestDecodeSentinelAnalyzeRejectsInvalidUTF8(t *testing.T) {
	payload := append([]byte(`{"is_threat":false,"confidence":0,"input_length":0,"future":"`), 0xff)
	payload = append(payload, []byte(`"}`)...)
	if _, err := decodeSentinelAnalyze(payload, 0); err == nil {
		t.Fatal("expected invalid UTF-8 failure")
	}
}
