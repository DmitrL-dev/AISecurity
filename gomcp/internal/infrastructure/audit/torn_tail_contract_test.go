package audit

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestDecisionLoggerRejectsTornTailWithoutModifyingAudit(t *testing.T) {
	dir := t.TempDir()
	l, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.NoError(t, l.Record(ModuleSOC, "SYNTHETIC", "first"))
	require.NoError(t, l.Close())
	path := filepath.Join(dir, "decisions.log")
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0)
	require.NoError(t, err)
	_, err = f.WriteString("synthetic torn line")
	require.NoError(t, err)
	require.NoError(t, f.Close())
	before, err := os.ReadFile(path)
	require.NoError(t, err)
	next, err := NewDecisionLogger(dir)
	if next != nil {
		_ = next.Close()
	}
	require.Error(t, err, "restart must refuse a torn tail instead of appending to it")
	after, err := os.ReadFile(path)
	require.NoError(t, err)
	require.Equal(t, before, after)
}

func TestDecisionLoggerDoesNotMoveAuditToTemporaryDirectory(t *testing.T) {
	temp := t.TempDir()
	t.Setenv("TMPDIR", temp)
	blocked := filepath.Join(temp, "blocked")
	require.NoError(t, os.WriteFile(blocked, []byte("fixture"), 0o600))
	logger, err := NewDecisionLogger(filepath.Join(blocked, "audit"))
	if logger != nil {
		_ = logger.Close()
	}
	require.Error(t, err, "an unusable audit path must fail rather than silently relocate")
	_, err = os.Stat(filepath.Join(temp, "sentinel-audit", "decisions.log"))
	require.True(t, os.IsNotExist(err))
}
