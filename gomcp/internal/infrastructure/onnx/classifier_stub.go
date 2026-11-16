//go:build !onnx

package onnx

import "context"

// ThreatCategory represents a detected threat type.
type ThreatCategory string

const (
	ThreatSafe              ThreatCategory = "safe"
	ThreatPromptInjection   ThreatCategory = "prompt_injection"
	ThreatJailbreak         ThreatCategory = "jailbreak"
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
	Severity      string             `json:"severity"`
}

// SafetyClassifier is a stub for when ONNX build tag is not set.
type SafetyClassifier struct{}

// ClassifierConfig holds configuration for the safety classifier.
type ClassifierConfig struct {
	ModelPath  string
	VocabPath  string
	LabelsPath string
	MaxSeqLen  int
}

// NewSafetyClassifier returns nil when ONNX is not available.
func NewSafetyClassifier(cfg ClassifierConfig) (*SafetyClassifier, error) {
	return nil, nil // No-op when ONNX build tag is not set
}

// Classify always returns safe when ONNX is not available.
func (sc *SafetyClassifier) Classify(ctx context.Context, text string) (*ClassificationResult, error) {
	return &ClassificationResult{
		Category:   ThreatSafe,
		Confidence: 1.0,
		IsThreat:   false,
		Severity:   "INFO",
	}, nil
}

// Close is a no-op.
func (sc *SafetyClassifier) Close() error { return nil }
