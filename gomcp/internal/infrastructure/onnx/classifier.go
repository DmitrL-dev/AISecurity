//go:build onnx

package onnx

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"sync"

	ort "github.com/yalue/onnxruntime_go"
)

// ThreatCategory represents a detected threat type.
type ThreatCategory string

const (
	ThreatSafe              ThreatCategory = "safe"
	ThreatJailbreak         ThreatCategory = "jailbreak"
	ThreatPromptInjection   ThreatCategory = "prompt_injection"
	ThreatToolAbuse         ThreatCategory = "tool_abuse"
	ThreatExfiltration      ThreatCategory = "exfiltration"
	ThreatPIILeak           ThreatCategory = "pii_leak"
	ThreatAuthBypass        ThreatCategory = "auth_bypass"
	ThreatEncoding          ThreatCategory = "encoding"
	ThreatPersistence       ThreatCategory = "persistence"
	ThreatSensorAnomaly     ThreatCategory = "sensor_anomaly"
	ThreatDoS               ThreatCategory = "dos"
	ThreatModelTheft        ThreatCategory = "model_theft"
	ThreatSupplyChain       ThreatCategory = "supply_chain"
	ThreatDataPoisoning     ThreatCategory = "data_poisoning"
	ThreatEvasion           ThreatCategory = "evasion"
	ThreatSocialEngineering ThreatCategory = "social_engineering"
)

// ClassificationResult holds the output of the safety classifier.
type ClassificationResult struct {
	Category      ThreatCategory     `json:"category"`
	Confidence    float64            `json:"confidence"`
	Probabilities map[string]float64 `json:"probabilities,omitempty"`
	IsThreat      bool               `json:"is_threat"`
	Severity      string             `json:"severity"` // INFO, LOW, MEDIUM, HIGH, CRITICAL
}

// Severity mapping for threat categories.
var categorySeverity = map[ThreatCategory]string{
	ThreatSafe:              "INFO",
	ThreatJailbreak:         "HIGH",
	ThreatPromptInjection:   "CRITICAL",
	ThreatToolAbuse:         "HIGH",
	ThreatExfiltration:      "CRITICAL",
	ThreatPIILeak:           "HIGH",
	ThreatAuthBypass:        "CRITICAL",
	ThreatEncoding:          "MEDIUM",
	ThreatPersistence:       "HIGH",
	ThreatSensorAnomaly:     "MEDIUM",
	ThreatDoS:               "HIGH",
	ThreatModelTheft:        "HIGH",
	ThreatSupplyChain:       "CRITICAL",
	ThreatDataPoisoning:     "CRITICAL",
	ThreatEvasion:           "HIGH",
	ThreatSocialEngineering: "MEDIUM",
}

// expectedNumLabels is the contract: the Go safety classifier is a 16-class
// head (15 threat categories + safe). A model whose output dimension does not
// match this is rejected at load time (fail-loud) rather than silently
// mis-mapping logits to the wrong category.
const expectedNumLabels = 16

// SafetyClassifier implements multi-class threat detection using ONNX Runtime.
// Uses mDeBERTa-v3-base fine-tuned on 16 threat categories.
type SafetyClassifier struct {
	mu        sync.Mutex
	session   *ort.DynamicAdvancedSession
	tokenizer *UnigramTokenizer
	labels    []string
	numLabels int
	maxSeqLen int64
	modelPath string
}

// ClassifierConfig holds configuration for the safety classifier.
type ClassifierConfig struct {
	ModelPath  string // Direct path to the .onnx model (e.g. model.onnx / model_fp32.onnx)
	VocabPath  string // Direct path to the HF tokenizer.json (REQUIRED to load a real tokenizer)
	LabelsPath string // Direct path to labels.json ({"0":"safe",...,"15":"social_engineering"})
	MaxSeqLen  int    // Max sequence length (default: 256)
}

// NewSafetyClassifier creates a new safety classifier with ONNX Runtime.
//
// Honest loading contract (WS3): the classifier loads ONLY when a real model
// AND a real tokenizer are present and the artifact matches the 16-class
// contract (see docs/MODEL_ARTIFACT_CONTRACT.md). Any failure returns an error
// so the caller keeps ML OFFLINE — it NEVER falls back to a placeholder that
// would emit fabricated class scores.
func NewSafetyClassifier(cfg ClassifierConfig) (*SafetyClassifier, error) {
	// Discover the model file. Env/explicit path wins; otherwise search the
	// standard ship locations. NOTE: "model.onnx" (the name the export scripts
	// write) is included so a freshly-exported artifact is found without a rename.
	modelPath := cfg.ModelPath
	if modelPath != "" {
		if _, err := os.Stat(modelPath); err != nil {
			return nil, fmt.Errorf("SAFETY_CLASSIFIER_MODEL %q: %w", modelPath, err)
		}
	} else {
		searchDirs := []string{".", "models", "models/safety-classifier-v2", "/app/models/safety-classifier-v2"}
		if exe, err := os.Executable(); err == nil {
			searchDirs = append(searchDirs,
				filepath.Join(filepath.Dir(exe), "models"),
				filepath.Join(filepath.Dir(exe), "models", "safety-classifier-v2"),
			)
		}
		for _, dir := range searchDirs {
			candidates := []string{
				filepath.Join(dir, "model_fp16.onnx"),
				filepath.Join(dir, "model_fp32.onnx"),
				filepath.Join(dir, "model.onnx"),
				filepath.Join(dir, "safety_classifier.onnx"),
			}
			for _, candidate := range candidates {
				if _, err := os.Stat(candidate); err == nil {
					modelPath = candidate
					break
				}
			}
			if modelPath != "" {
				break
			}
		}
	}
	if modelPath == "" {
		return nil, fmt.Errorf("safety classifier model not found (set SAFETY_CLASSIFIER_MODEL or place model.onnx under models/safety-classifier-v2/)")
	}

	// Load + validate labels. The contract is exactly 16 classes in the
	// documented order. A labels.json with a different count is rejected.
	labels, err := loadAndValidateLabels(cfg.LabelsPath)
	if err != nil {
		return nil, err
	}

	maxSeqLen := cfg.MaxSeqLen
	if maxSeqLen <= 0 {
		maxSeqLen = 256
	}

	// Load the REAL tokenizer. Resolve tokenizer.json: explicit VocabPath wins,
	// otherwise look for tokenizer.json next to the model. A missing tokenizer
	// is fatal-to-load (→ classifier stays offline) — we do NOT tokenize with a
	// placeholder, which would yield meaningless logits.
	tokPath := cfg.VocabPath
	if tokPath == "" {
		cand := filepath.Join(filepath.Dir(modelPath), "tokenizer.json")
		if _, err := os.Stat(cand); err == nil {
			tokPath = cand
		}
	}
	tokenizer, err := NewUnigramTokenizerFromFile(tokPath, maxSeqLen)
	if err != nil {
		return nil, fmt.Errorf("tokenizer load (a real tokenizer.json matching the model vocab is required): %w", err)
	}

	// Resolve + set the ONNX Runtime shared library path BEFORE init, so the
	// runtime is found even when it is not on the default loader path (mirrors
	// the embedder). Best-effort: if discovery fails we still try the default
	// loader path, and InitializeEnvironment surfaces a clear error.
	if libPath := discoverRuntimeLib(modelPath); libPath != "" {
		ort.SetSharedLibraryPath(libPath)
	}
	if err := ort.InitializeEnvironment(); err != nil {
		return nil, fmt.Errorf("onnx init (ensure the ONNX Runtime shared library %q is installed/on the loader path): %w", runtimeLibName(), err)
	}

	// Create ONNX session.
	// DeBERTa inputs: input_ids [1, seq_len], attention_mask [1, seq_len]
	// (NO token_type_ids — type_vocab_size=0). Output: logits [1, 16].
	inputNames := []string{"input_ids", "attention_mask"}
	outputNames := []string{"logits"}

	session, err := ort.NewDynamicAdvancedSession(
		modelPath,
		inputNames,
		outputNames,
		nil,
	)
	if err != nil {
		_ = ort.DestroyEnvironment()
		return nil, fmt.Errorf("onnx session (model must expose inputs %v and output %v): %w", inputNames, outputNames, err)
	}

	sc := &SafetyClassifier{
		session:   session,
		tokenizer: tokenizer,
		labels:    labels,
		numLabels: len(labels),
		maxSeqLen: int64(maxSeqLen),
		modelPath: modelPath,
	}

	// Validate the output dimension against the contract with a real inference
	// pass on a fixed probe. A model whose head ≠ 16 is rejected (fail-loud):
	// shipping it would silently mis-map logits to the wrong threat categories.
	if err := sc.validateOutputShape(); err != nil {
		_ = sc.Close()
		return nil, err
	}

	log.Printf("Safety Classifier v2 loaded: model=%s tokenizer=%s (%d labels, seq_len=%d)",
		modelPath, tokPath, sc.numLabels, maxSeqLen)
	return sc, nil
}

// loadAndValidateLabels loads labels.json ({"0":"safe",...}) and enforces the
// 16-class contract. With no path it returns the canonical default labels.
func loadAndValidateLabels(labelsPath string) ([]string, error) {
	if labelsPath == "" {
		return []string{
			"safe", "jailbreak", "prompt_injection", "tool_abuse",
			"exfiltration", "pii_leak", "auth_bypass", "encoding",
			"persistence", "sensor_anomaly", "dos", "model_theft",
			"supply_chain", "data_poisoning", "evasion", "social_engineering",
		}, nil
	}
	data, err := os.ReadFile(labelsPath)
	if err != nil {
		return nil, fmt.Errorf("read labels %q: %w", labelsPath, err)
	}
	var labelMap map[string]string
	if err := json.Unmarshal(data, &labelMap); err != nil {
		return nil, fmt.Errorf("parse labels %q (expected {\"0\":\"safe\",...}): %w", labelsPath, err)
	}
	if len(labelMap) != expectedNumLabels {
		return nil, fmt.Errorf("labels.json has %d entries, contract requires %d (the Go classifier is a 16-class head)", len(labelMap), expectedNumLabels)
	}
	labels := make([]string, len(labelMap))
	for k, v := range labelMap {
		var idx int
		if _, err := fmt.Sscanf(k, "%d", &idx); err != nil {
			return nil, fmt.Errorf("labels.json key %q is not an integer index", k)
		}
		if idx < 0 || idx >= len(labels) {
			return nil, fmt.Errorf("labels.json index %d out of range [0,%d)", idx, len(labels))
		}
		labels[idx] = v
	}
	for i, l := range labels {
		if l == "" {
			return nil, fmt.Errorf("labels.json missing index %d (must define all 0..%d)", i, expectedNumLabels-1)
		}
	}
	return labels, nil
}

// validateOutputShape runs one inference and confirms the model's output
// dimension equals the label count (the 16-class contract).
func (sc *SafetyClassifier) validateOutputShape() error {
	inputIDs, attentionMask := sc.tokenizer.Encode("contract validation probe")
	seqLen := int64(len(inputIDs))
	shape := ort.Shape{1, seqLen}

	inputIDsTensor, err := ort.NewTensor(shape, inputIDs)
	if err != nil {
		return fmt.Errorf("validate: input_ids tensor: %w", err)
	}
	defer inputIDsTensor.Destroy()
	attMaskTensor, err := ort.NewTensor(shape, attentionMask)
	if err != nil {
		return fmt.Errorf("validate: attention_mask tensor: %w", err)
	}
	defer attMaskTensor.Destroy()

	outputTensor, err := ort.NewEmptyTensor[float32](ort.Shape{1, int64(sc.numLabels)})
	if err != nil {
		return fmt.Errorf("validate: output tensor: %w", err)
	}
	defer outputTensor.Destroy()

	if err := sc.session.Run(
		[]ort.ArbitraryTensor{inputIDsTensor, attMaskTensor},
		[]ort.ArbitraryTensor{outputTensor},
	); err != nil {
		return fmt.Errorf("validate: inference failed (model/contract mismatch?): %w", err)
	}
	if got := len(outputTensor.GetData()); got != sc.numLabels {
		return fmt.Errorf("model output dimension %d != contract %d labels — refusing to load (logits would mis-map to wrong categories)", got, sc.numLabels)
	}
	return nil
}

// discoverRuntimeLib looks for the ONNX Runtime shared library near the model
// and in standard locations, returning "" if none found (the default loader
// path is then used).
func discoverRuntimeLib(modelPath string) string {
	name := runtimeLibName()
	dirs := []string{
		filepath.Dir(modelPath),
		".",
		"/usr/local/lib",
		"/usr/lib",
	}
	if exe, err := os.Executable(); err == nil {
		dirs = append(dirs, filepath.Dir(exe), filepath.Join(filepath.Dir(exe), "lib"))
	}
	for _, d := range dirs {
		p := filepath.Join(d, name)
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

// Classify analyzes text and returns threat classification.
func (sc *SafetyClassifier) Classify(ctx context.Context, text string) (*ClassificationResult, error) {
	sc.mu.Lock()
	defer sc.mu.Unlock()

	// Tokenize.
	inputIDs, attentionMask := sc.tokenizer.Encode(text)
	seqLen := int64(len(inputIDs))

	shape := ort.Shape{1, seqLen}

	// Create input tensors.
	inputIDsTensor, err := ort.NewTensor(shape, inputIDs)
	if err != nil {
		return nil, fmt.Errorf("create input_ids tensor: %w", err)
	}
	defer inputIDsTensor.Destroy()

	attMaskTensor, err := ort.NewTensor(shape, attentionMask)
	if err != nil {
		return nil, fmt.Errorf("create attention_mask tensor: %w", err)
	}
	defer attMaskTensor.Destroy()

	// Create output tensor.
	outputShape := ort.Shape{1, int64(sc.numLabels)}
	outputTensor, err := ort.NewEmptyTensor[float32](outputShape)
	if err != nil {
		return nil, fmt.Errorf("create output tensor: %w", err)
	}
	defer outputTensor.Destroy()

	// Run inference.
	if err := sc.session.Run(
		[]ort.ArbitraryTensor{inputIDsTensor, attMaskTensor},
		[]ort.ArbitraryTensor{outputTensor},
	); err != nil {
		return nil, fmt.Errorf("onnx inference: %w", err)
	}

	// Softmax + argmax.
	rawLogits := outputTensor.GetData()
	probabilities := softmax(rawLogits)

	maxIdx := 0
	maxProb := probabilities[0]
	for i, p := range probabilities {
		if p > maxProb {
			maxProb = p
			maxIdx = i
		}
	}

	// Bounds-check BEFORE indexing: the model's output dimension can exceed
	// len(labels) (e.g. a labels.json with fewer entries than the head), in
	// which case maxIdx would index out of range and panic. Guard first.
	category := ThreatSafe
	if maxIdx < len(sc.labels) {
		category = ThreatCategory(sc.labels[maxIdx])
	}

	// Build probability map.
	probMap := make(map[string]float64)
	for i, p := range probabilities {
		if i < len(sc.labels) {
			probMap[sc.labels[i]] = roundTo3(p)
		}
	}

	result := &ClassificationResult{
		Category:      category,
		Confidence:    roundTo3(maxProb),
		Probabilities: probMap,
		IsThreat:      category != ThreatSafe,
		Severity:      categorySeverity[category],
	}

	return result, nil
}

// Close releases ONNX resources.
func (sc *SafetyClassifier) Close() error {
	sc.mu.Lock()
	defer sc.mu.Unlock()
	if sc.session != nil {
		sc.session.Destroy()
	}
	return ort.DestroyEnvironment()
}

// softmax computes softmax over logits.
func softmax(logits []float32) []float64 {
	result := make([]float64, len(logits))
	var maxVal float32
	for _, v := range logits {
		if v > maxVal {
			maxVal = v
		}
	}

	var sum float64
	for i, v := range logits {
		exp := math.Exp(float64(v - maxVal))
		result[i] = exp
		sum += exp
	}

	if sum > 0 {
		for i := range result {
			result[i] /= sum
		}
	}
	return result
}

// roundTo3 rounds to 3 decimal places.
func roundTo3(v float64) float64 {
	return math.Round(v*1000) / 1000
}
