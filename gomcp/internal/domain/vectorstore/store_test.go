package vectorstore

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNew_Empty(t *testing.T) {
	s := New(nil)
	assert.Equal(t, 0, s.Count())
}

func TestStore_Add(t *testing.T) {
	s := New(nil)
	id := s.Add(&IntentRecord{
		Text:    "read user data",
		Vector:  []float64{1.0, 0.0, 0.0},
		Route:   "read",
		Verdict: "ALLOW",
	})
	assert.Contains(t, id, "intent-")
	assert.Equal(t, 1, s.Count())
}

func TestStore_Get(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{ID: "test-1", Text: "hello"})
	rec := s.Get("test-1")
	require.NotNil(t, rec)
	assert.Equal(t, "hello", rec.Text)
	assert.Nil(t, s.Get("nonexistent"))
}

func TestStore_Search_ExactMatch(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{
		ID: "r1", Text: "read data", Vector: []float64{1.0, 0.0, 0.0}, Route: "read",
	})
	s.Add(&IntentRecord{
		ID: "w1", Text: "write data", Vector: []float64{0.0, 1.0, 0.0}, Route: "write",
	})
	s.Add(&IntentRecord{
		ID: "e1", Text: "execute code", Vector: []float64{0.0, 0.0, 1.0}, Route: "exec",
	})

	results := s.Search([]float64{1.0, 0.0, 0.0}, 1)
	require.Len(t, results, 1)
	assert.Equal(t, "r1", results[0].Record.ID)
	assert.InDelta(t, 1.0, results[0].Similarity, 0.001)
}

func TestStore_Search_TopK(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{ID: "a", Vector: []float64{1.0, 0.0}})
	s.Add(&IntentRecord{ID: "b", Vector: []float64{0.9, 0.1}})
	s.Add(&IntentRecord{ID: "c", Vector: []float64{0.0, 1.0}})

	results := s.Search([]float64{1.0, 0.0}, 2)
	require.Len(t, results, 2)
	assert.Equal(t, "a", results[0].Record.ID) // closest
	assert.Equal(t, "b", results[1].Record.ID) // second closest
}

func TestStore_Search_Empty(t *testing.T) {
	s := New(nil)
	assert.Nil(t, s.Search([]float64{1.0}, 5))
}

func TestStore_SearchByRoute(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{ID: "r1", Route: "read"})
	s.Add(&IntentRecord{ID: "r2", Route: "read"})
	s.Add(&IntentRecord{ID: "w1", Route: "write"})

	reads := s.SearchByRoute("read")
	assert.Len(t, reads, 2)
	writes := s.SearchByRoute("write")
	assert.Len(t, writes, 1)
	assert.Empty(t, s.SearchByRoute("nonexistent"))
}

func TestStore_LRU_Eviction(t *testing.T) {
	s := New(&Config{Capacity: 3})

	s.Add(&IntentRecord{ID: "a", Text: "first"})
	s.Add(&IntentRecord{ID: "b", Text: "second"})
	s.Add(&IntentRecord{ID: "c", Text: "third"})
	assert.Equal(t, 3, s.Count())

	// Adding 4th should evict oldest ("a").
	s.Add(&IntentRecord{ID: "d", Text: "fourth"})
	assert.Equal(t, 3, s.Count())
	assert.Nil(t, s.Get("a"), "oldest should be evicted")
	assert.NotNil(t, s.Get("d"), "newest should exist")
}

func TestStore_Stats(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{Route: "read", Verdict: "ALLOW", Entropy: 3.0})
	s.Add(&IntentRecord{Route: "read", Verdict: "ALLOW", Entropy: 4.0})
	s.Add(&IntentRecord{Route: "exec", Verdict: "DENY", Entropy: 5.0})

	stats := s.GetStats()
	assert.Equal(t, 3, stats.TotalRecords)
	assert.Equal(t, 2, stats.RouteCount["read"])
	assert.Equal(t, 1, stats.RouteCount["exec"])
	assert.Equal(t, 2, stats.VerdictCount["ALLOW"])
	assert.Equal(t, 1, stats.VerdictCount["DENY"])
	assert.InDelta(t, 4.0, stats.AvgEntropy, 0.001)
}

func TestCosineSimilarity(t *testing.T) {
	// Identical vectors.
	assert.InDelta(t, 1.0, CosineSimilarity(
		[]float64{1, 0, 0}, []float64{1, 0, 0}), 0.001)

	// Orthogonal vectors.
	assert.InDelta(t, 0.0, CosineSimilarity(
		[]float64{1, 0, 0}, []float64{0, 1, 0}), 0.001)

	// Opposite vectors.
	assert.InDelta(t, -1.0, CosineSimilarity(
		[]float64{1, 0, 0}, []float64{-1, 0, 0}), 0.001)

	// Different lengths.
	assert.Equal(t, 0.0, CosineSimilarity(
		[]float64{1, 0}, []float64{1, 0, 0}))

	// Empty.
	assert.Equal(t, 0.0, CosineSimilarity(nil, nil))

	// Zero vector.
	assert.Equal(t, 0.0, CosineSimilarity(
		[]float64{0, 0, 0}, []float64{1, 0, 0}))
}

func TestStore_CustomID(t *testing.T) {
	s := New(nil)
	id := s.Add(&IntentRecord{ID: "custom-id"})
	assert.Equal(t, "custom-id", id)
}

// TestStore_Search_NonPositiveK guards against a makeslice panic when k <= 0.
// A negative k previously slipped past the `k > len(scores)` clamp and reached
// make([]SearchResult, k), crashing the store.
func TestStore_Search_NonPositiveK(t *testing.T) {
	s := New(nil)
	s.Add(&IntentRecord{ID: "a", Vector: []float64{1.0, 0.0}})
	s.Add(&IntentRecord{ID: "b", Vector: []float64{0.0, 1.0}})

	assert.NotPanics(t, func() {
		assert.Nil(t, s.Search([]float64{1.0, 0.0}, -1))
		assert.Nil(t, s.Search([]float64{1.0, 0.0}, 0))
	})
}

// TestStore_SearchQJL_NonPositiveK guards the QJL path against the same panic.
// A negative k made rankPool = 2*k negative, panicking make([]scored, 0, rankPool).
func TestStore_SearchQJL_NonPositiveK(t *testing.T) {
	s := New(&Config{QJLProjections: 64, QJLVectorDim: 2})
	s.Add(&IntentRecord{ID: "a", Vector: []float64{1.0, 0.0}})
	s.Add(&IntentRecord{ID: "b", Vector: []float64{0.0, 1.0}})

	assert.NotPanics(t, func() {
		assert.Nil(t, s.SearchQJL([]float64{1.0, 0.0}, -1))
		assert.Nil(t, s.SearchQJL([]float64{1.0, 0.0}, 0))
	})
}
