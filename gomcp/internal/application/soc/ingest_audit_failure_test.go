package soc

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
)

func TestSOCIngestRejectsDecisionLogFailureBeforePersistence(t *testing.T) {
	base := newTestService(t)
	logger, err := audit.NewDecisionLogger(t.TempDir())
	require.NoError(t, err)
	require.NoError(t, logger.Close())
	svc := NewService(base.repo, logger)
	event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "synthetic", "synthetic event")
	event.TenantID = "synthetic-tenant"
	id, incident, err := svc.IngestInternalEvent(event)
	assert.Error(t, err, "audit failure must stop ingest before persistence")
	assert.Empty(t, id)
	assert.Nil(t, incident)
	count, err := base.repo.CountEvents("synthetic-tenant")
	require.NoError(t, err)
	assert.Zero(t, count)
}

func TestSOCIngestContinuesWhenDecisionLogAccepts(t *testing.T) {
	base := newTestService(t)
	logger, err := audit.NewDecisionLogger(t.TempDir())
	require.NoError(t, err)
	t.Cleanup(func() { _ = logger.Close() })
	svc := NewService(base.repo, logger)
	event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "synthetic", "synthetic event")
	event.TenantID = "synthetic-tenant"
	id, _, err := svc.IngestInternalEvent(event)
	require.NoError(t, err)
	require.NotEmpty(t, id)
	count, err := base.repo.CountEvents("synthetic-tenant")
	require.NoError(t, err)
	require.Equal(t, 1, count)
}
