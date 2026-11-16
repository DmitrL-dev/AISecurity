package engines

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math"
	"strings"
	"unicode/utf8"
)

// sentinelAnalyzeResult matches the JSON returned by sentinel_analyze().
//
// EngineVector/EngineVectorOrder/Escalate/EscalateReason are ADDITIVE fields the
// sentinel FFI now emits (see sentinel-core/src/ffi.rs). They are backward-
// compatible: an older sentinel binary that does not emit them leaves EngineVector
// nil and Escalate false, and the rest of the contract is unchanged.
//   - EngineVector: dense 39-float per-engine confidence vector (0.0 where an
//     engine did not fire), in the fixed fan-out order described by
//     EngineVectorOrder. This is the real per-engine feature for retraining.
//   - Escalate/EscalateReason: the Layer-2 ambiguity-band signal. Redundant with
//     gomcp's own band test and false by default — parsed but no logic depends on it.
type sentinelAnalyzeResult struct {
	Confidence        float64   `json:"confidence"`
	Categories        []string  `json:"categories"`
	IsThreat          bool      `json:"is_threat"`
	InputLength       int       `json:"input_length"`
	AnalyzeCount      uint64    `json:"analyze_count"`
	EnginesTriggered  int       `json:"engines_triggered"`
	ProcessingTimeUs  uint64    `json:"processing_time_us"`
	Indicators        []string  `json:"indicators"`
	EngineVector      []float64 `json:"engine_vector,omitempty"`
	EngineVectorOrder []string  `json:"engine_vector_order,omitempty"`
	Escalate          bool      `json:"escalate,omitempty"`
	EscalateReason    string    `json:"escalate_reason,omitempty"`
	Error             string    `json:"error,omitempty"`
}

var errInvalidSentinelResponse = errors.New("invalid native analysis response")

func validSentinelInput(text string) bool { return strings.IndexByte(text, 0) < 0 }

// validateJSONValue rejects duplicate object names at every nesting level.
// It consumes one value and bounds nesting before descending.
func validateJSONValue(d *json.Decoder, depth int) error {
	if depth > 128 {
		return errInvalidSentinelResponse
	}
	token, err := d.Token()
	if err != nil {
		return errInvalidSentinelResponse
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	switch delimiter {
	case '{':
		seen := make(map[string]struct{})
		for d.More() {
			keyToken, err := d.Token()
			key, ok := keyToken.(string)
			if err != nil || !ok {
				return errInvalidSentinelResponse
			}
			if _, exists := seen[key]; exists {
				return errInvalidSentinelResponse
			}
			seen[key] = struct{}{}
			if err := validateJSONValue(d, depth+1); err != nil {
				return err
			}
		}
		end, err := d.Token()
		if err != nil || end != json.Delim('}') {
			return errInvalidSentinelResponse
		}
		return nil
	case '[':
		for d.More() {
			if err := validateJSONValue(d, depth+1); err != nil {
				return err
			}
		}
		end, err := d.Token()
		if err != nil || end != json.Delim(']') {
			return errInvalidSentinelResponse
		}
		return nil
	default:
		return errInvalidSentinelResponse
	}
}

// Validate required fields structurally; native failures and malformed
// responses are generic errors. Input length is UTF-8 bytes, per Rust str::len.
func decodeSentinelAnalyze(payload []byte, inputBytes int) (sentinelAnalyzeResult, error) {
	fail := func() (sentinelAnalyzeResult, error) { return sentinelAnalyzeResult{}, errInvalidSentinelResponse }
	trimmed := bytes.TrimSpace(payload)
	if len(trimmed) == 0 || trimmed[0] != '{' || inputBytes < 0 || !utf8.Valid(trimmed) {
		return fail()
	}
	scanner := json.NewDecoder(bytes.NewReader(trimmed))
	scanner.UseNumber()
	if validateJSONValue(scanner, 0) != nil {
		return fail()
	}
	if _, err := scanner.Token(); err != io.EOF {
		return fail()
	}
	var fields map[string]json.RawMessage
	if json.Unmarshal(trimmed, &fields) != nil || fields == nil {
		return fail()
	}
	// Go's struct decoder accepts case-insensitive field aliases; reject them
	// so a second spelling cannot replace any validated value or native error.
	reserved := []string{"confidence", "categories", "is_threat", "input_length", "analyze_count", "engines_triggered", "processing_time_us", "indicators", "engine_vector", "engine_vector_order", "escalate", "escalate_reason", "error"}
	for key := range fields {
		for _, canonical := range reserved {
			if key != canonical && strings.EqualFold(key, canonical) {
				return fail()
			}
		}
	}
	if value, exists := fields["error"]; exists {
		var nativeError string
		if bytes.Equal(bytes.TrimSpace(value), []byte("null")) || json.Unmarshal(value, &nativeError) != nil || nativeError != "" {
			return fail()
		}
	}
	required := []string{"is_threat", "confidence", "input_length"}
	for _, key := range required {
		value, ok := fields[key]
		if !ok || bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
			return fail()
		}
	}
	var threat bool
	var confidence float64
	var inputLength int
	if json.Unmarshal(fields["is_threat"], &threat) != nil || json.Unmarshal(fields["confidence"], &confidence) != nil || json.Unmarshal(fields["input_length"], &inputLength) != nil {
		return fail()
	}
	if math.IsNaN(confidence) || math.IsInf(confidence, 0) || confidence < 0 || confidence > 1 || inputLength != inputBytes {
		return fail()
	}
	var result sentinelAnalyzeResult
	if json.Unmarshal(trimmed, &result) != nil {
		return fail()
	}
	// Assign from the exactly named, checked fields; no unknown alias may alter them.
	result.IsThreat, result.Confidence, result.InputLength, result.Error = threat, confidence, inputLength, ""
	return result, nil
}
