package router

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

func seedStore() *vectorstore.Store {
	s := vectorstore.New(nil)
	s.Add(&vectorstore.IntentRecord{
		ID: "read-1", Text: "read user profile", Route: "read",
		Vector: []float64{0.9, 0.1, 0.0}, Verdict: "ALLOW",
	})
	s.Add(&vectorstore.IntentRecord{
		ID: "write-1", Text: "save configuration", Route: "write",
		Vector: []float64{0.1, 0.9, 0.0}, Verdict: "ALLOW",
	})
	s.Add(&vectorstore.IntentRecord{
		ID: "exec-1", Text: "run shell command", Route: "exec",
		Vector: []float64{0.0, 0.1, 0.9}, Verdict: "DENY",
	})
	return s
}

func TestRouter_HighConfidence_Route(t *testing.T) {
	r := New(seedStore(), nil)
	result := r.Route(context.Background(),
		"read data", []float64{0.9, 0.1, 0.0}, "ALLOW")
	assert.Equal(t, "ROUTE", result.Decision)
	assert.Equal(t, "read", result.Route)
	assert.GreaterOrEqual(t, result.Confidence, 0.85)
	assert.Contains(t, result.Reason, "matched")
}

func TestRouter_MediumConfidence_Review(t *testing.T) {
	r := New(seedStore(), nil)
	// Vector between read(0.9,0.1,0) and write(0.1,0.9,0).
	result := r.Route(context.Background(),
		"update data", []float64{0.5, 0.5, 0.0}, "ALLOW")
	assert.Equal(t, "REVIEW", result.Decision)
	assert.Contains(t, result.Reason, "review")
}

func TestRouter_LowConfidence_Deny(t *testing.T) {
	r := New(seedStore(), &Config{HighConfidence: 0.99, LowConfidence: 0.99})
	// Even a decent match won't pass extreme threshold.
	result := r.Route(context.Background(),
		"something", []float64{0.5, 0.3, 0.2}, "ALLOW")
	assert.Equal(t, "DENY", result.Decision)
}

func TestRouter_EmptyStore_Learn(t *testing.T) {
	r := New(vectorstore.New(nil), nil)
	result := r.Route(context.Background(),
		"first ever intent", []float64{1.0, 0.0, 0.0}, "ALLOW")
	assert.Equal(t, "LEARN", result.Decision)
	assert.NotEmpty(t, result.LearnedID)
	assert.Equal(t, 1, r.GetStore().Count())
}

func TestRouter_EmptyStore_NoAutoLearn_Deny(t *testing.T) {
	r := New(vectorstore.New(nil), &Config{AutoLearn: false})
	result := r.Route(context.Background(),
		"intent", []float64{1.0}, "ALLOW")
	assert.Equal(t, "DENY", result.Decision)
	assert.Equal(t, 0, r.GetStore().Count())
}

func TestRouter_AutoLearn_StoresNew(t *testing.T) {
	store := seedStore()
	r := New(store, nil)
	initialCount := store.Count()

	// Medium confidence → review + auto-learn.
	result := r.Route(context.Background(),
		"update profile", []float64{0.5, 0.5, 0.0}, "ALLOW")
	assert.NotEmpty(t, result.LearnedID)
	assert.Equal(t, initialCount+1, store.Count())
}

func TestRouter_Alternatives(t *testing.T) {
	r := New(seedStore(), nil)
	result := r.Route(context.Background(),
		"get data", []float64{0.8, 0.2, 0.0}, "ALLOW")
	require.NotNil(t, result.Alternatives)
	assert.Greater(t, len(result.Alternatives), 0)
}

func TestRouter_DecisionString(t *testing.T) {
	assert.Equal(t, "ROUTE", DecisionRoute.String())
	assert.Equal(t, "REVIEW", DecisionReview.String())
	assert.Equal(t, "DENY", DecisionDeny.String())
	assert.Equal(t, "LEARN", DecisionLearn.String())
	assert.Equal(t, "UNKNOWN", Decision(99).String())
}

func TestRouter_DurationMeasured(t *testing.T) {
	r := New(seedStore(), nil)
	result := r.Route(context.Background(),
		"test", []float64{1.0, 0.0, 0.0}, "ALLOW")
	assert.GreaterOrEqual(t, result.DurationUs, int64(0))
}
