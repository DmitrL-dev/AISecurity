// Package router implements the Neuroplastic Router (DIP H2.2).
//
// The router matches new intents against known patterns stored in the
// Vector Store. It determines the optimal processing path based on
// cosine similarity to previously seen intents.
//
// Routing decisions:
//   - High confidence (≥ 0.85): auto-route to matched pattern's action
//   - Medium confidence (0.5-0.85): flag for review
//   - Low confidence (< 0.5): unknown intent, default-deny
//
// The router learns from every interaction, building a neuroplastic
// map of intent space over time.
package router

import (
	"context"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// Decision represents a routing decision.
type Decision int

const (
	DecisionRoute  Decision = iota // Auto-route to known action
	DecisionReview                 // Needs human review
	DecisionDeny                   // Unknown intent, default deny
	DecisionLearn                  // New pattern, store and route
)

// String returns the decision name.
func (d Decision) String() string {
	switch d {
	case DecisionRoute:
		return "ROUTE"
	case DecisionReview:
		return "REVIEW"
	case DecisionDeny:
		return "DENY"
	case DecisionLearn:
		return "LEARN"
	default:
		return "UNKNOWN"
	}
}

// Config configures the router.
type Config struct {
	// HighConfidence: similarity threshold for auto-routing.
	HighConfidence float64 // default: 0.85

	// LowConfidence: below this, deny.
	LowConfidence float64 // default: 0.50

	// AutoLearn: if true, store new intents automatically.
	AutoLearn bool // default: true

	// MaxSearchResults: how many similar intents to consider.
	MaxSearchResults int // default: 3
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() Config {
	return Config{
		HighConfidence:   0.85,
		LowConfidence:    0.50,
		AutoLearn:        true,
		MaxSearchResults: 3,
	}
}

// RouteResult holds the routing result.
type RouteResult struct {
	Decision     string                     `json:"decision"`
	Route        string                     `json:"route,omitempty"`
	Confidence   float64                    `json:"confidence"`
	Reason       string                     `json:"reason"`
	MatchedID    string                     `json:"matched_id,omitempty"`
	Alternatives []vectorstore.SearchResult `json:"alternatives,omitempty"`
	LearnedID    string                     `json:"learned_id,omitempty"` // if auto-learned
	DurationUs   int64                      `json:"duration_us"`
}

// Router performs neuroplastic intent routing.
type Router struct {
	cfg   Config
	store *vectorstore.Store
}

// New creates a new neuroplastic router.
func New(store *vectorstore.Store, cfg *Config) *Router {
	c := DefaultConfig()
	if cfg != nil {
		if cfg.HighConfidence > 0 {
			c.HighConfidence = cfg.HighConfidence
		}
		if cfg.LowConfidence > 0 {
			c.LowConfidence = cfg.LowConfidence
		}
		if cfg.MaxSearchResults > 0 {
			c.MaxSearchResults = cfg.MaxSearchResults
		}
		c.AutoLearn = cfg.AutoLearn
	}
	return &Router{cfg: c, store: store}
}

// Route determines the processing path for an intent vector.
func (r *Router) Route(_ context.Context, text string, vector []float64, verdict string) *RouteResult {
	start := time.Now()

	result := &RouteResult{}

	// Search for similar known intents.
	matches := r.store.Search(vector, r.cfg.MaxSearchResults)

	if len(matches) == 0 {
		// No known patterns — first intent ever.
		if r.cfg.AutoLearn {
			id := r.store.Add(&vectorstore.IntentRecord{
				Text:    text,
				Vector:  vector,
				Route:   "unknown",
				Verdict: verdict,
			})
			result.Decision = DecisionLearn.String()
			result.Route = "unknown"
			result.Confidence = 0
			result.Reason = "first intent in store, learned as new pattern"
			result.LearnedID = id
		} else {
			result.Decision = DecisionDeny.String()
			result.Confidence = 0
			result.Reason = "no known patterns"
		}
		result.DurationUs = time.Since(start).Microseconds()
		return result
	}

	best := matches[0]
	result.Confidence = best.Similarity
	result.MatchedID = best.Record.ID
	if len(matches) > 1 {
		result.Alternatives = matches[1:]
	}

	switch {
	case best.Similarity >= r.cfg.HighConfidence:
		// High confidence: auto-route.
		result.Decision = DecisionRoute.String()
		result.Route = best.Record.Route
		result.Reason = fmt.Sprintf(
			"matched known pattern %q (sim=%.3f)",
			best.Record.Route, best.Similarity)

	case best.Similarity >= r.cfg.LowConfidence:
		// Medium confidence: review.
		result.Decision = DecisionReview.String()
		result.Route = best.Record.Route
		result.Reason = fmt.Sprintf(
			"partial match to %q (sim=%.3f), needs review",
			best.Record.Route, best.Similarity)

		// Auto-learn new pattern in review zone.
		if r.cfg.AutoLearn {
			id := r.store.Add(&vectorstore.IntentRecord{
				Text:    text,
				Vector:  vector,
				Route:   best.Record.Route + "/pending",
				Verdict: verdict,
			})
			result.LearnedID = id
		}

	default:
		// Low confidence: deny.
		result.Decision = DecisionDeny.String()
		result.Reason = fmt.Sprintf(
			"no confident match (best sim=%.3f < threshold %.3f)",
			best.Similarity, r.cfg.LowConfidence)

		if r.cfg.AutoLearn {
			id := r.store.Add(&vectorstore.IntentRecord{
				Text:    text,
				Vector:  vector,
				Route:   "denied",
				Verdict: verdict,
			})
			result.LearnedID = id
		}
	}

	result.DurationUs = time.Since(start).Microseconds()
	return result
}

// GetStore returns the underlying vector store.
func (r *Router) GetStore() *vectorstore.Store {
	return r.store
}
