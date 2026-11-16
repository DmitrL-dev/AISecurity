package tools

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestSystemService(t *testing.T) *SystemService {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)

	return NewSystemService(repo)
}

func TestSystemService_Health(t *testing.T) {
	svc := newTestSystemService(t)
	ctx := context.Background()

	health := svc.Health(ctx)
	require.NotNil(t, health)
	assert.Equal(t, "healthy", health.Status)
	assert.NotEmpty(t, health.GoVersion)
	assert.NotEmpty(t, health.Version)
	assert.NotEmpty(t, health.OS)
	assert.NotEmpty(t, health.Arch)
	assert.NotEmpty(t, health.Uptime)
}

func TestSystemService_GetVersion(t *testing.T) {
	svc := newTestSystemService(t)

	ver := svc.GetVersion()
	require.NotNil(t, ver)
	assert.NotEmpty(t, ver.Version)
	assert.NotEmpty(t, ver.GoVersion)
	assert.Equal(t, Version, ver.Version)
	assert.Equal(t, GitCommit, ver.GitCommit)
	assert.Equal(t, BuildDate, ver.BuildDate)
}

func TestSystemService_Dashboard(t *testing.T) {
	svc := newTestSystemService(t)
	ctx := context.Background()

	data, err := svc.Dashboard(ctx)
	require.NoError(t, err)
	require.NotNil(t, data)
	assert.NotNil(t, data.Health)
	assert.Equal(t, "healthy", data.Health.Status)
	assert.NotNil(t, data.FactStats)
	assert.Equal(t, 0, data.FactStats.TotalFacts)
}

func TestSystemService_Dashboard_WithFacts(t *testing.T) {
	svc := newTestSystemService(t)
	ctx := context.Background()

	// Add facts through the underlying store.
	factSvc := NewFactService(svc.factStore, nil)
	_, _ = factSvc.AddFact(ctx, AddFactParams{Content: "f1", Level: 0, Domain: "core"})
	_, _ = factSvc.AddFact(ctx, AddFactParams{Content: "f2", Level: 1, Domain: "backend"})

	data, err := svc.Dashboard(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, data.FactStats.TotalFacts)
}

func TestSystemService_Dashboard_NilFactStore(t *testing.T) {
	svc := &SystemService{factStore: nil}

	data, err := svc.Dashboard(context.Background())
	require.NoError(t, err)
	assert.NotNil(t, data.Health)
	assert.Nil(t, data.FactStats)
}

func TestSystemService_Uptime(t *testing.T) {
	svc := newTestSystemService(t)
	ctx := context.Background()

	h1 := svc.Health(ctx)
	assert.NotEmpty(t, h1.Uptime)
	// Uptime should be a parseable duration string like "0s" or "1ms".
	assert.Contains(t, h1.Uptime, "s")
}
