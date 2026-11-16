package resources

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/session"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func newTestProvider(t *testing.T) (*Provider, *sqlite.DB, *sqlite.DB) {
	t.Helper()

	factDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { factDB.Close() })

	stateDB, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { stateDB.Close() })

	factRepo, err := sqlite.NewFactRepo(factDB)
	require.NoError(t, err)

	stateRepo, err := sqlite.NewStateRepo(stateDB)
	require.NoError(t, err)

	return NewProvider(factRepo, stateRepo), factDB, stateDB
}

func TestNewProvider(t *testing.T) {
	p, _, _ := newTestProvider(t)
	require.NotNil(t, p)
	assert.NotNil(t, p.factStore)
	assert.NotNil(t, p.stateStore)
}

func TestProvider_GetFacts_Empty(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	result, err := p.GetFacts(ctx)
	require.NoError(t, err)

	var facts []interface{}
	require.NoError(t, json.Unmarshal([]byte(result), &facts))
	assert.Empty(t, facts)
}

func TestProvider_GetFacts_WithData(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	// Add L0 facts directly via factStore.
	f1 := memory.NewFact("Project uses Go", memory.LevelProject, "core", "")
	f2 := memory.NewFact("Domain fact", memory.LevelDomain, "backend", "")
	require.NoError(t, p.factStore.Add(ctx, f1))
	require.NoError(t, p.factStore.Add(ctx, f2))

	result, err := p.GetFacts(ctx)
	require.NoError(t, err)

	// Should only return L0 facts.
	assert.Contains(t, result, "Project uses Go")
	assert.NotContains(t, result, "Domain fact")
}

func TestProvider_RequestScopeOverridesDefaultScope(t *testing.T) {
	p, _, _ := newTestProvider(t)
	defaultScope := rlmscope.New("tenant-a", "project-alpha")
	betaScope := rlmscope.New("tenant-a", "project-beta")
	p.WithScope(defaultScope)

	alphaCtx := rlmscope.WithScope(context.Background(), defaultScope)
	betaCtx := rlmscope.WithScope(context.Background(), betaScope)
	require.NoError(t, p.factStore.Add(alphaCtx, memory.NewFact("alpha resource fact", memory.LevelProject, "scope", "")))
	require.NoError(t, p.factStore.Add(betaCtx, memory.NewFact("beta resource fact", memory.LevelProject, "scope", "")))

	defaultResult, err := p.GetFacts(context.Background())
	require.NoError(t, err)
	assert.Contains(t, defaultResult, "alpha resource fact")
	assert.NotContains(t, defaultResult, "beta resource fact")

	betaResult, err := p.GetFacts(betaCtx)
	require.NoError(t, err)
	assert.Contains(t, betaResult, "beta resource fact")
	assert.NotContains(t, betaResult, "alpha resource fact")
}

func TestProvider_GetStats(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	// Add some facts.
	f1 := memory.NewFact("fact1", memory.LevelProject, "core", "")
	f2 := memory.NewFact("fact2", memory.LevelDomain, "core", "")
	require.NoError(t, p.factStore.Add(ctx, f1))
	require.NoError(t, p.factStore.Add(ctx, f2))

	result, err := p.GetStats(ctx)
	require.NoError(t, err)
	assert.Contains(t, result, "total_facts")

	var stats map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(result), &stats))
	assert.Equal(t, float64(2), stats["total_facts"])
}

func TestProvider_GetStats_Empty(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	result, err := p.GetStats(ctx)
	require.NoError(t, err)

	var stats map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(result), &stats))
	assert.Equal(t, float64(0), stats["total_facts"])
}

func TestProvider_GetState(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	// Save a state first.
	state := session.NewCognitiveStateVector("test-session")
	state.SetGoal("Build GoMCP", 0.5)
	state.AddFact("Go 1.25", "requirement", 1.0)
	checksum := state.Checksum()
	require.NoError(t, p.stateStore.Save(ctx, state, checksum))

	result, err := p.GetState(ctx, "test-session")
	require.NoError(t, err)
	assert.Contains(t, result, "test-session")
	assert.Contains(t, result, "Build GoMCP")
}

func TestProvider_GetState_NotFound(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	_, err := p.GetState(ctx, "nonexistent")
	assert.Error(t, err)
}

func TestProvider_GetFacts_JSONFormat(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	f := memory.NewFact("JSON test", memory.LevelProject, "test", "")
	require.NoError(t, p.factStore.Add(ctx, f))

	result, err := p.GetFacts(ctx)
	require.NoError(t, err)

	// Should be valid indented JSON.
	assert.True(t, json.Valid([]byte(result)))
	assert.Contains(t, result, "\n") // Indented.
}

func TestProvider_GetStats_JSONFormat(t *testing.T) {
	p, _, _ := newTestProvider(t)
	ctx := context.Background()

	result, err := p.GetStats(ctx)
	require.NoError(t, err)
	assert.True(t, json.Valid([]byte(result)))
}
