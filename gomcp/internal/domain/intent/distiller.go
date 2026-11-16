// Package intent provides the Intent Distiller — recursive compression
// of user input into a pure intent vector (DIP H0.2).
//
// The distillation process:
//  1. Embed raw text → surface vector
//  2. Extract key phrases (top-N by TF weight)
//  3. Re-embed compressed text → deep vector
//  4. Compute cosine similarity(surface, deep)
//  5. If similarity > threshold → converged (intent = deep vector)
//  6. If similarity < threshold → iterate with further compression
//  7. Final sincerity check: high divergence between surface and deep = manipulation
package intent

import (
	"context"
	"fmt"
	"math"
	"strings"
	"time"
)

// EmbeddingFunc abstracts the embedding computation (bridges to Python NLP).
type EmbeddingFunc func(ctx context.Context, text string) ([]float64, error)

// DistillConfig configures the distillation pipeline.
type DistillConfig struct {
	MaxIterations        int     // Maximum distillation iterations (default: 5)
	ConvergenceThreshold float64 // Cosine similarity threshold for convergence (default: 0.92)
	SincerityThreshold   float64 // Max surface-deep divergence before flagging manipulation (default: 0.35)
	MinTextLength        int     // Minimum text length to attempt distillation (default: 10)
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() DistillConfig {
	return DistillConfig{
		MaxIterations:        5,
		ConvergenceThreshold: 0.92,
		SincerityThreshold:   0.35,
		MinTextLength:        10,
	}
}

// DistillResult holds the output of intent distillation.
type DistillResult struct {
	// Core outputs
	IntentVector   []float64 `json:"intent_vector"`   // Pure intent embedding
	SurfaceVector  []float64 `json:"surface_vector"`  // Raw text embedding
	CompressedText string    `json:"compressed_text"` // Final compressed form

	// Metrics
	Iterations     int     `json:"iterations"`      // Distillation iterations used
	Convergence    float64 `json:"convergence"`     // Final cosine similarity
	SincerityScore float64 `json:"sincerity_score"` // 1.0 = sincere, 0.0 = manipulative
	IsSincere      bool    `json:"is_sincere"`      // Passed sincerity check
	IsManipulation bool    `json:"is_manipulation"` // Failed sincerity check

	// Timing
	DurationMs int64 `json:"duration_ms"`
}

// Distiller performs recursive intent extraction.
type Distiller struct {
	cfg   DistillConfig
	embed EmbeddingFunc
}

// NewDistiller creates a new Intent Distiller.
func NewDistiller(embedFn EmbeddingFunc, cfg *DistillConfig) *Distiller {
	c := DefaultConfig()
	if cfg != nil {
		if cfg.MaxIterations > 0 {
			c.MaxIterations = cfg.MaxIterations
		}
		if cfg.ConvergenceThreshold > 0 {
			c.ConvergenceThreshold = cfg.ConvergenceThreshold
		}
		if cfg.SincerityThreshold > 0 {
			c.SincerityThreshold = cfg.SincerityThreshold
		}
		if cfg.MinTextLength > 0 {
			c.MinTextLength = cfg.MinTextLength
		}
	}
	return &Distiller{cfg: c, embed: embedFn}
}

// Distill performs recursive intent distillation on the input text.
//
// The process iteratively compresses the text and compares embeddings
// until convergence (the meaning stabilizes) or max iterations.
// A sincerity check compares the original surface embedding against
// the final deep embedding — high divergence signals manipulation.
func (d *Distiller) Distill(ctx context.Context, text string) (*DistillResult, error) {
	start := time.Now()

	if len(strings.TrimSpace(text)) < d.cfg.MinTextLength {
		return nil, fmt.Errorf("text too short for distillation (min %d chars)", d.cfg.MinTextLength)
	}

	// Step 1: Surface embedding (raw text as-is).
	surfaceVec, err := d.embed(ctx, text)
	if err != nil {
		return nil, fmt.Errorf("surface embedding: %w", err)
	}

	// Step 2: Iterative compression loop.
	currentText := text
	var prevVec []float64
	currentVec := surfaceVec
	iterations := 0
	convergence := 0.0

	for i := 0; i < d.cfg.MaxIterations; i++ {
		iterations = i + 1

		// Compress text: extract core phrases.
		compressed := compressText(currentText)
		if compressed == currentText || len(compressed) < d.cfg.MinTextLength {
			break // Cannot compress further
		}

		// Re-embed compressed text.
		prevVec = currentVec
		currentVec, err = d.embed(ctx, compressed)
		if err != nil {
			return nil, fmt.Errorf("iteration %d embedding: %w", i, err)
		}

		// Check convergence.
		convergence = cosineSimilarity(prevVec, currentVec)
		if convergence >= d.cfg.ConvergenceThreshold {
			currentText = compressed
			break // Intent has stabilized
		}

		currentText = compressed
	}

	// Step 3: Sincerity check.
	surfaceDeepSim := cosineSimilarity(surfaceVec, currentVec)
	divergence := 1.0 - surfaceDeepSim
	isSincere := divergence <= d.cfg.SincerityThreshold

	result := &DistillResult{
		IntentVector:   currentVec,
		SurfaceVector:  surfaceVec,
		CompressedText: currentText,
		Iterations:     iterations,
		Convergence:    convergence,
		SincerityScore: surfaceDeepSim,
		IsSincere:      isSincere,
		IsManipulation: !isSincere,
		DurationMs:     time.Since(start).Milliseconds(),
	}

	return result, nil
}

// compressText extracts the semantic core of text by removing
// filler words, decorations, and social engineering wrappers.
func compressText(text string) string {
	words := strings.Fields(text)
	if len(words) <= 3 {
		return text
	}

	// Remove common filler/manipulation patterns
	fillers := map[string]bool{
		"please": true, "пожалуйста": true, "kindly": true,
		"just": true, "simply": true, "только": true,
		"imagine": true, "представь": true, "pretend": true,
		"suppose": true, "допустим": true, "assuming": true,
		"hypothetically": true, "гипотетически": true,
		"for": true, "для": true, "as": true, "как": true,
		"the": true, "a": true, "an": true, "и": true,
		"is": true, "are": true, "was": true, "were": true,
		"that": true, "this": true, "these": true, "those": true,
		"будь": true, "будьте": true, "можешь": true,
		"could": true, "would": true, "should": true,
		"actually": true, "really": true, "very": true,
		"you": true, "your": true, "ты": true, "твой": true,
		"my": true, "мой": true, "i": true, "я": true,
		"в": true, "на": true, "с": true, "к": true,
		"не": true, "но": true, "из": true, "от": true,
	}

	var core []string
	for _, w := range words {
		lower := strings.ToLower(w)
		// Strip punctuation for check, keep original
		cleaned := strings.Trim(lower, ".,!?;:'\"()-[]{}«»")
		if !fillers[cleaned] && len(cleaned) > 1 {
			core = append(core, w)
		}
	}

	if len(core) == 0 {
		return text // Don't compress to nothing
	}

	// Keep max 70% of original words (progressive compression)
	maxWords := int(float64(len(words)) * 0.7)
	if maxWords < 3 {
		maxWords = 3
	}
	if len(core) > maxWords {
		core = core[:maxWords]
	}

	return strings.Join(core, " ")
}

// cosineSimilarity computes cosine similarity between two vectors.
func cosineSimilarity(a, b []float64) float64 {
	if len(a) != len(b) || len(a) == 0 {
		return 0
	}

	var dot, normA, normB float64
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}

	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return dot / denom
}
