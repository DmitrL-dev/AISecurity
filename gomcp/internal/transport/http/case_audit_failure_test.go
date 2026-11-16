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
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

func TestSOCCaseAuditFailureReturnsServiceUnavailableBeforeMutation(t *testing.T) {
	cases := []struct {
		name, body string
		call       func(*Server, http.ResponseWriter, *http.Request)
	}{
		{"verdict", `{"status":"INVESTIGATING"}`, (*Server).handleVerdict},
		{"assign", `{"analyst":"synthetic"}`, (*Server).handleIncidentAssign},
		{"status", `{"status":"INVESTIGATING"}`, (*Server).handleIncidentStatus},
		{"note", `{"content":"synthetic"}`, (*Server).handleIncidentNotes},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			srv, base := setupIsoSrv(t)
			incident := seedIncident(t, base, "synthetic", "tenant-a")
			prior, err := base.GetIncident(incident.ID)
			require.NoError(t, err)
			logger, err := audit.NewDecisionLogger(t.TempDir())
			require.NoError(t, err)
			require.NoError(t, logger.Close())
			srv.socSvc = appsoc.NewService(base.Repo(), logger)
			req := httptest.NewRequest(http.MethodPost, "/api/soc/incidents/fixture", strings.NewReader(tc.body))
			req.SetPathValue("id", incident.ID)
			req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Sub: "synthetic", Role: "analyst", TenantID: "tenant-a"}))
			rec := httptest.NewRecorder()
			tc.call(srv, rec, req)
			assert.Equal(t, http.StatusServiceUnavailable, rec.Code, "audit error must not be reported as success or not found")
			assert.NotContains(t, rec.Body.String(), logger.Path())
			current, err := base.GetIncident(incident.ID)
			require.NoError(t, err)
			assert.Equal(t, prior, current)
		})
	}
}
