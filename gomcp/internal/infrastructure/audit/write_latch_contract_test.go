package audit

import (
	"os"
	"testing"

	"github.com/stretchr/testify/require"
)

// No live storage is touched: the descriptor is deliberately closed in a temp fixture.
func TestAuditWriteFailureLatchesBeforeFurtherAppend(t *testing.T) {
	dir := t.TempDir()
	logger, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.NoError(t, logger.Record(ModuleSOC, "SYNTHETIC", "before fault"))
	path := logger.Path()
	original, err := os.ReadFile(path)
	require.NoError(t, err)
	require.NoError(t, logger.file.Close())
	require.Error(t, logger.Record(ModuleSOC, "SYNTHETIC", "fault"))
	fresh, err := os.OpenFile(path, os.O_WRONLY|os.O_APPEND, 0o600)
	require.NoError(t, err)
	logger.file = fresh
	require.Error(t, logger.Record(ModuleSOC, "SYNTHETIC", "after fault"), "unacknowledged write must latch this logger")
	require.NoError(t, logger.Close())
	result, err := os.ReadFile(path)
	require.NoError(t, err)
	require.Equal(t, original, result)
}
