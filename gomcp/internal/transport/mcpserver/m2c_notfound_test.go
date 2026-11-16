package mcpserver

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
)

func TestM2cSQLiteMissingFactHasTypedCause(t *testing.T) {
	srv := newTestServer(t)
	_, err := srv.facts.Store().Get(context.Background(), "nonexistent-m2c-id")
	require.True(t, errors.Is(err, memory.ErrFactNotFound))
	require.EqualError(t, err, "fact not found")
}
