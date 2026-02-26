package session

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewCognitiveStateVector(t *testing.T) {
	csv := NewCognitiveStateVector("test-session")

	assert.Equal(t, "test-session", csv.SessionID)
	assert.Equal(t, 1, csv.Version)
	assert.False(t, csv.Timestamp.IsZero())
	assert.Nil(t, csv.PrimaryGoal)
	assert.Empty(t, csv.Hypotheses)
	assert.Empty(t, csv.Decisions)
	assert.Empty(t, csv.Facts)
	assert.Empty(t, csv.OpenQuestions)
	assert.NotNil(t, csv.ConfidenceMap)
}

func TestCognitiveStateVector_SetGoal(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	csv.SetGoal("Build GoMCP v2", 0.3)

	require.NotNil(t, csv.PrimaryGoal)
	assert.Equal(t, "Build GoMCP v2", csv.PrimaryGoal.Description)
	assert.InDelta(t, 0.3, csv.PrimaryGoal.Progress, 0.001)
	assert.NotEmpty(t, csv.PrimaryGoal.ID)
}

func TestCognitiveStateVector_SetGoal_ClampProgress(t *testing.T) {
	csv := NewCognitiveStateVector("s1")

	csv.SetGoal("over", 1.5)
	assert.InDelta(t, 1.0, csv.PrimaryGoal.Progress, 0.001)

	csv.SetGoal("under", -0.5)
	assert.InDelta(t, 0.0, csv.PrimaryGoal.Progress, 0.001)
}

func TestCognitiveStateVector_AddHypothesis(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	h := csv.AddHypothesis("Caching reduces latency by 50%")

	assert.NotEmpty(t, h.ID)
	assert.Equal(t, "Caching reduces latency by 50%", h.Statement)
	assert.Equal(t, HypothesisProposed, h.Status)
	assert.Len(t, csv.Hypotheses, 1)
}

func TestCognitiveStateVector_AddDecision(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	d := csv.AddDecision("Use SQLite", "Embedded, no server", []string{"PostgreSQL", "Redis"})

	assert.NotEmpty(t, d.ID)
	assert.Equal(t, "Use SQLite", d.Description)
	assert.Equal(t, "Embedded, no server", d.Rationale)
	assert.Equal(t, []string{"PostgreSQL", "Redis"}, d.Alternatives)
	assert.Len(t, csv.Decisions, 1)
}

func TestCognitiveStateVector_AddFact(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	f := csv.AddFact("Go 1.25 is required", "requirement", 0.95)

	assert.NotEmpty(t, f.ID)
	assert.Equal(t, "Go 1.25 is required", f.Content)
	assert.Equal(t, "requirement", f.EntityType)
	assert.InDelta(t, 0.95, f.Confidence, 0.001)
	assert.Len(t, csv.Facts, 1)
}

func TestCognitiveStateVector_BumpVersion(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	assert.Equal(t, 1, csv.Version)

	csv.BumpVersion()
	assert.Equal(t, 2, csv.Version)
}

func TestCognitiveStateVector_ToJSON_FromJSON(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	csv.SetGoal("Test serialization", 0.5)
	csv.AddHypothesis("JSON round-trips cleanly")
	csv.AddDecision("Use encoding/json", "stdlib", nil)
	csv.AddFact("fact1", "fact", 1.0)

	data, err := json.Marshal(csv)
	require.NoError(t, err)
	require.NotEmpty(t, data)

	var restored CognitiveStateVector
	err = json.Unmarshal(data, &restored)
	require.NoError(t, err)

	assert.Equal(t, csv.SessionID, restored.SessionID)
	assert.Equal(t, csv.Version, restored.Version)
	require.NotNil(t, restored.PrimaryGoal)
	assert.Equal(t, csv.PrimaryGoal.Description, restored.PrimaryGoal.Description)
	assert.Len(t, restored.Hypotheses, 1)
	assert.Len(t, restored.Decisions, 1)
	assert.Len(t, restored.Facts, 1)
}

func TestCognitiveStateVector_ToCompactString(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	csv.SetGoal("Build GoMCP", 0.4)
	csv.AddFact("Go 1.25", "requirement", 1.0)
	csv.AddDecision("Use mcp-go", "mature lib", nil)

	compact := csv.ToCompactString(500)
	assert.Contains(t, compact, "GOAL:")
	assert.Contains(t, compact, "Build GoMCP")
	assert.Contains(t, compact, "FACTS:")
	assert.Contains(t, compact, "Go 1.25")
	assert.Contains(t, compact, "DECISIONS:")
}

func TestCognitiveStateVector_ToCompactString_Truncation(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	csv.SetGoal("Goal", 0.0)
	for i := 0; i < 100; i++ {
		csv.AddFact("This is a moderately long fact content for testing truncation behavior", "fact", 1.0)
	}

	compact := csv.ToCompactString(100)
	assert.LessOrEqual(t, len(compact), 100*4) // max_tokens * 4 chars
}

func TestCognitiveStateVector_Checksum(t *testing.T) {
	csv := NewCognitiveStateVector("s1")
	csv.AddFact("fact", "fact", 1.0)

	c1 := csv.Checksum()
	assert.NotEmpty(t, c1)
	assert.Len(t, c1, 64) // SHA-256 hex

	// Same state = same checksum
	c2 := csv.Checksum()
	assert.Equal(t, c1, c2)

	// Different state = different checksum
	csv.AddFact("another fact", "fact", 1.0)
	c3 := csv.Checksum()
	assert.NotEqual(t, c1, c3)
}

func TestGoal_Validate(t *testing.T) {
	g := &Goal{ID: "g1", Description: "test", Progress: 0.5}
	assert.NoError(t, g.Validate())

	g.Description = ""
	assert.Error(t, g.Validate())

	g.Description = "test"
	g.Progress = -0.1
	assert.Error(t, g.Validate())

	g.Progress = 1.1
	assert.Error(t, g.Validate())
}

func TestHypothesisStatus_Valid(t *testing.T) {
	assert.True(t, HypothesisProposed.IsValid())
	assert.True(t, HypothesisTesting.IsValid())
	assert.True(t, HypothesisConfirmed.IsValid())
	assert.True(t, HypothesisRejected.IsValid())
	assert.False(t, HypothesisStatus("invalid").IsValid())
}

func TestSessionInfo(t *testing.T) {
	info := SessionInfo{
		SessionID: "s1",
		Version:   5,
		UpdatedAt: time.Now(),
	}
	assert.Equal(t, "s1", info.SessionID)
	assert.Equal(t, 5, info.Version)
}
