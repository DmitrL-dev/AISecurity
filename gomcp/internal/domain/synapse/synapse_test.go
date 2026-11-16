package synapse

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// --- Status Constants ---

func TestStatusConstants(t *testing.T) {
	assert.Equal(t, Status("PENDING"), StatusPending)
	assert.Equal(t, Status("VERIFIED"), StatusVerified)
	assert.Equal(t, Status("REJECTED"), StatusRejected)
}

func TestStatusConstants_Distinct(t *testing.T) {
	statuses := []Status{StatusPending, StatusVerified, StatusRejected}
	seen := make(map[Status]bool)
	for _, s := range statuses {
		assert.False(t, seen[s], "duplicate status: %s", s)
		seen[s] = true
	}
}

// --- Synapse Struct ---

func TestSynapseStruct_ZeroValue(t *testing.T) {
	var s Synapse
	assert.Zero(t, s.ID)
	assert.Empty(t, s.FactIDA)
	assert.Empty(t, s.FactIDB)
	assert.Zero(t, s.Confidence)
	assert.Empty(t, s.Status)
	assert.True(t, s.CreatedAt.IsZero())
}

func TestSynapseStruct_FieldAssignment(t *testing.T) {
	s := Synapse{
		ID:         42,
		FactIDA:    "fact-001",
		FactIDB:    "fact-002",
		Confidence: 0.95,
		Status:     StatusVerified,
	}
	assert.Equal(t, int64(42), s.ID)
	assert.Equal(t, "fact-001", s.FactIDA)
	assert.Equal(t, "fact-002", s.FactIDB)
	assert.InDelta(t, 0.95, s.Confidence, 0.001)
	assert.Equal(t, StatusVerified, s.Status)
}

// --- SynapseStore Interface Compliance ---

// Verify that the SynapseStore interface is well-formed by checking
// it can be used as a type constraint.
func TestSynapseStoreInterface_Compilable(t *testing.T) {
	// This test verifies the interface definition compiles correctly.
	// runtime verification uses a nil assertion.
	var store SynapseStore
	assert.Nil(t, store, "nil interface should work")
}
