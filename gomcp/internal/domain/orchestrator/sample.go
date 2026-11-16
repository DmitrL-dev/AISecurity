// Package orchestrator holds the domain types for the data-capture flywheel
// (the "self-improving from customer traffic" loop).
//
// WHAT THIS IS — AND IS NOT (honest framing):
//
// This package persists, for each production scan, a compact TRAINING ROW: the
// per-engine confidence signal + the final verdict + a slot for an analyst LABEL
// attached later. Exported as a (features, label) table, it is the supervised
// corpus the learned orchestrator (the sentinel verdict-combiner / router) can be
// RETRAINED from over time.
//
// It does NOT improve detection today. It is plumbing whose payoff is FUTURE: it
// only produces training value once (a) real traffic flows AND (b) analysts
// disposition the resulting incidents (FALSE_POSITIVE / confirmed). Until then the
// table simply fills with unlabeled feature rows. The value is that the
// self-improvement loop becomes REAL and grounded in production traffic instead of
// a static gold corpus.
//
// PRIVACY INVARIANT: a Sample stores METADATA ONLY — the per-engine confidence
// vector + a SHA-256 hash of the prompt. The raw prompt is NEVER stored here (the
// hash is one-way; it supports dedup/traceability, not reconstruction).
package orchestrator

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Label is the supervised signal attached to a Sample after an analyst
// dispositions the related incident. Empty until then.
type Label string

const (
	// LabelUnlabeled is the default — no analyst disposition yet.
	LabelUnlabeled Label = ""
	// LabelMalicious — the scan correctly blocked a real threat (true positive),
	// or an analyst confirmed the incident.
	LabelMalicious Label = "malicious"
	// LabelBenign — the scan's block was a false positive (analyst marked the
	// incident FALSE_POSITIVE), i.e. the input was actually safe.
	LabelBenign Label = "benign"
)

// ValidLabel reports whether l is a recognized non-empty label.
func ValidLabel(l Label) bool {
	return l == LabelMalicious || l == LabelBenign
}

// VectorSchema versions the feature-vector layout so a retraining harness can
// reject or migrate rows captured under an older layout. Bump this whenever the
// MEANING or ORDER of EngineVector / AggregateFeatures changes.
//
// VectorSchema is the AGGREGATE-fallback layout (AggregateFeatures.ToVector),
// captured when the bridge does not supply a dense per-engine vector.
// DenseVectorSchema tags a row whose EngineVector is the real dense per-engine
// vector from the sentinel-core fan-out. A retraining harness keys on the row's
// VectorSchema field to know which layout (and therefore which interpretation +
// dimension) it is reading.
const (
	VectorSchema      = "agg-v1"
	DenseVectorSchema = "dense-v1"

	// DenseVectorLen is the sentinel-core fixed fan-out width (ENGINE_ORDER length).
	// A captured EngineVector is treated as the real dense vector only when it has
	// exactly this many slots; any other length falls back to the aggregate layout
	// (defends against an older/mismatched sentinel binary emitting a short vector).
	DenseVectorLen = 39
)

// Sample is one captured training row: the engine signal for a single scan plus
// the verdict and (eventually) the analyst label.
type Sample struct {
	ID        string    `json:"id"`
	TenantID  string    `json:"tenant_id"`
	Timestamp time.Time `json:"timestamp"`

	// PromptHash is the SHA-256 (hex) of the raw prompt. The raw prompt is NEVER
	// stored — this hash is the only prompt-derived value persisted. It supports
	// dedup + the label-attach join, not reconstruction.
	PromptHash string `json:"prompt_hash"`

	// --- Features (the X in a (X, y) training row) ---

	// EngineVector is the fixed-order DENSE per-engine confidence vector that the
	// learned combiner ultimately wants (one slot per engine, 0.0 when an engine
	// did not fire).
	//
	// ⚠ DATA-AVAILABILITY GAP (honest): the sentinel-core FFI bridge does NOT emit
	// a dense per-engine vector today. It returns an AGGREGATE risk score, an
	// engines-triggered COUNT, and an `indicators` list of "engine/pattern (NN%)"
	// strings — only for engines that FIRED. So today EngineVector is left empty
	// and the recoverable per-engine confidences live in EngineScores (sparse).
	// When the bridge is extended to return a dense vector, populate this and set
	// VectorComplete=true; the schema/version already carries the layout contract.
	EngineVector []float64 `json:"engine_vector,omitempty"`

	// EngineScores is the SPARSE per-engine confidence map parsed from the
	// engine indicators (only engines that fired appear). This is what is actually
	// recoverable from production today.
	EngineScores map[string]float64 `json:"engine_scores,omitempty"`

	// Aggregate scalar features that ARE available today, captured verbatim so the
	// row is useful for retraining even before a dense vector exists.
	Aggregate AggregateFeatures `json:"aggregate"`

	// VectorComplete is true only when EngineVector is a real dense per-engine
	// vector. False today (aggregate + sparse only). Lets the export weight or
	// filter rows honestly.
	VectorComplete bool `json:"vector_complete"`

	// VectorSchema records the layout version this row was captured under.
	VectorSchema string `json:"vector_schema"`

	// --- Verdict (the decision the orchestrator produced) ---

	Blocked    bool    `json:"blocked"`
	Risk       float64 `json:"risk"`
	ThreatType string  `json:"threat_type,omitempty"`

	// ModelVersion is the engine/threshold version this verdict was produced under
	// (so a retraining run can segment by model generation). Free-form; e.g.
	// "sentinel-core/1.4.0|thr=default".
	ModelVersion string `json:"model_version,omitempty"`

	// --- Label (the y, attached later) ---

	Label       Label      `json:"label,omitempty"`
	LabelSource string     `json:"label_source,omitempty"` // e.g. "incident:RESOLVED", "incident:FALSE_POSITIVE"
	LabeledAt   *time.Time `json:"labeled_at,omitempty"`
}

// AggregateFeatures are the dense scalar signals available from the bridge TODAY.
// Fixed order is documented here and pinned by VectorSchema; ToVector emits them
// in this order so a retraining harness has a stable layout even before a real
// per-engine vector exists.
type AggregateFeatures struct {
	// Risk is the merged final risk score (0..1).
	Risk float64 `json:"risk"`
	// CoreConfidence is sentinel-core's aggregate confidence (0..1).
	CoreConfidence float64 `json:"core_confidence"`
	// ShieldConfidence is the Shield engine's confidence (0..1; 0 when offline).
	ShieldConfidence float64 `json:"shield_confidence"`
	// MLConfidence is the ONNX classifier's confidence (0..1; 0 when offline).
	MLConfidence float64 `json:"ml_confidence"`
	// EnginesTriggered is the COUNT of engines that fired (not a per-engine score).
	EnginesTriggered int `json:"engines_triggered"`
	// CoreBlocked / ShieldBlocked / MLBlocked are the per-tier block decisions.
	CoreBlocked   bool `json:"core_blocked"`
	ShieldBlocked bool `json:"shield_blocked"`
	MLBlocked     bool `json:"ml_blocked"`
}

// ToVector emits the aggregate features as a fixed-order dense float slice. This
// is the vector actually fillable today; the order is pinned by VectorSchema.
// Layout (agg-v1): [risk, core_conf, shield_conf, ml_conf, engines_triggered,
// core_blocked, shield_blocked, ml_blocked].
func (a AggregateFeatures) ToVector() []float64 {
	return []float64{
		a.Risk,
		a.CoreConfidence,
		a.ShieldConfidence,
		a.MLConfidence,
		float64(a.EnginesTriggered),
		b2f(a.CoreBlocked),
		b2f(a.ShieldBlocked),
		b2f(a.MLBlocked),
	}
}

func b2f(b bool) float64 {
	if b {
		return 1.0
	}
	return 0.0
}

// indicatorRe parses an engine indicator of the form "engine/pattern (NN%)" or
// "engine/pattern (NN.N%)" — the format the sentinel-core FFI emits (see
// sentinel-core/src/ffi.rs: format!("{}/{} ({:.0}%)", engine, pattern, conf*100)).
// Prefixed indicators from other tiers ("shield/...", "ml/...", "judge/...") have
// no percentage and are skipped by ParseEngineScores.
var indicatorRe = regexp.MustCompile(`^([^/]+)/.*\(([0-9]+(?:\.[0-9]+)?)%\)\s*$`)

// ParseEngineScores extracts a SPARSE {engine: confidence} map (0..1) from the
// engine indicator strings. Only engines that fired (and emitted a percentage)
// appear. When the same engine fires multiple patterns, the MAX confidence wins.
// Indicators without a parseable "(NN%)" suffix are ignored.
//
// This is the best per-engine signal recoverable from the bridge today; it is
// NOT a dense vector (non-firing engines are simply absent).
func ParseEngineScores(indicators []string) map[string]float64 {
	if len(indicators) == 0 {
		return nil
	}
	out := make(map[string]float64)
	for _, ind := range indicators {
		m := indicatorRe.FindStringSubmatch(strings.TrimSpace(ind))
		if m == nil {
			continue
		}
		engine := strings.TrimSpace(m[1])
		pct, err := strconv.ParseFloat(m[2], 64)
		if err != nil {
			continue
		}
		conf := pct / 100.0
		if conf < 0 {
			conf = 0
		}
		if conf > 1 {
			conf = 1
		}
		if existing, ok := out[engine]; !ok || conf > existing {
			out[engine] = conf
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

// SortedEngines returns the engine names in a Sample's EngineScores, sorted — a
// deterministic order for tests and stable export rendering.
func (s *Sample) SortedEngines() []string {
	if len(s.EngineScores) == 0 {
		return nil
	}
	names := make([]string, 0, len(s.EngineScores))
	for k := range s.EngineScores {
		names = append(names, k)
	}
	sort.Strings(names)
	return names
}

// ExportRow is the JSONL shape the sentinel retraining harness consumes. It is a
// projection of a labeled Sample: features + label + weight (+ provenance). Only
// LABELED samples should be exported.
type ExportRow struct {
	// Vector is the dense feature vector. Today this is the AGGREGATE vector
	// (AggregateFeatures.ToVector); when a real per-engine vector exists it is
	// EngineVector. VectorComplete tells the consumer which it got.
	Vector         []float64          `json:"vector"`
	VectorComplete bool               `json:"vector_complete"`
	VectorSchema   string             `json:"vector_schema"`
	EngineScores   map[string]float64 `json:"engine_scores,omitempty"`
	Label          Label              `json:"label"`
	// Weight lets the harness down-weight rows it trusts less. Today: 1.0 for a
	// real dense per-engine vector, 0.5 for an aggregate-only row (honest signal
	// that the feature is coarse). The harness may override.
	Weight       float64   `json:"weight"`
	Blocked      bool      `json:"blocked"`
	Risk         float64   `json:"risk"`
	ThreatType   string    `json:"threat_type,omitempty"`
	ModelVersion string    `json:"model_version,omitempty"`
	TenantID     string    `json:"tenant_id"`
	PromptHash   string    `json:"prompt_hash"`
	Timestamp    time.Time `json:"timestamp"`
	LabelSource  string    `json:"label_source,omitempty"`
}

// ToExportRow projects a Sample into the harness JSONL shape. The vector is the
// dense per-engine vector when complete, else the aggregate vector; the weight
// reflects that distinction so the consumer is never misled about feature
// richness.
func (s *Sample) ToExportRow() ExportRow {
	vec := s.EngineVector
	weight := 1.0
	if !s.VectorComplete || len(vec) == 0 {
		vec = s.Aggregate.ToVector()
		weight = 0.5 // aggregate-only: coarse feature, down-weighted honestly
	}
	return ExportRow{
		Vector:         vec,
		VectorComplete: s.VectorComplete,
		VectorSchema:   s.VectorSchema,
		EngineScores:   s.EngineScores,
		Label:          s.Label,
		Weight:         weight,
		Blocked:        s.Blocked,
		Risk:           s.Risk,
		ThreatType:     s.ThreatType,
		ModelVersion:   s.ModelVersion,
		TenantID:       s.TenantID,
		PromptHash:     s.PromptHash,
		Timestamp:      s.Timestamp,
		LabelSource:    s.LabelSource,
	}
}
