package httpserver

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
)

func TestSOCIngestAuditFailureReturnsUnavailableWithoutPersistence(t *testing.T) {
	// Test-process-only fixture: no real sensor key or external network is used.
	t.Setenv("SOC_ALLOW_UNAUTH_INGEST", "1")
	event := `{"source":"sentinel-core","severity":"LOW","category":"synthetic","description":"synthetic event"}`
	for _, batch := range []bool{false, true} {
		t.Run(map[bool]string{false: "single", true: "batch"}[batch], func(t *testing.T) {
			srv, base := setupIsoSrv(t)
			logger, err := audit.NewDecisionLogger(t.TempDir())
			require.NoError(t, err)
			require.NoError(t, logger.Close())
			srv.socSvc = appsoc.NewService(base.Repo(), logger)
			body := event
			if batch {
				body = "[" + event + "]"
			}
			req := httptest.NewRequest(http.MethodPost, "/synthetic", strings.NewReader(body))
			rec := httptest.NewRecorder()
			if batch {
				srv.handleBatchIngest(rec, req)
			} else {
				srv.handleIngestEvent(rec, req)
			}
			assert.Equal(t, http.StatusServiceUnavailable, rec.Code, "audit failure must not report ingest success")
			assert.NotContains(t, rec.Body.String(), logger.Path())
			assert.Empty(t, rec.Header().Get("Retry-After"))
			if batch {
				assert.Contains(t, rec.Body.String(), `"status":"unavailable"`)
			}
			count, err := base.Repo().CountEvents("")
			require.NoError(t, err)
			assert.Zero(t, count)
		})
	}
}
