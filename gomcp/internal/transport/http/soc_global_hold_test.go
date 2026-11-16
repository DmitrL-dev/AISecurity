package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestProcessGlobalSOCViewsRequireOperator(t *testing.T) {
	srv, _ := setupIsoSrv(t)
	handlers := []struct {
		name string
		call func(*Server, http.ResponseWriter, *http.Request)
	}{
		{"anomaly alerts", (*Server).handleAnomalyAlerts},
		{"anomaly baselines", (*Server).handleAnomalyBaselines},
	}
	for _, tc := range handlers {
		t.Run(tc.name, func(t *testing.T) {
			noClaims := httptest.NewRecorder()
			tc.call(srv, noClaims, httptest.NewRequest(http.MethodGet, "/synthetic", nil))
			assert.Equal(t, http.StatusUnauthorized, noClaims.Code, "process-global data requires a principal")
			for _, role := range []string{"viewer", "analyst", "admin"} {
				req := isoReq(http.MethodGet, "/synthetic", role, "tenant-a")
				result := httptest.NewRecorder()
				tc.call(srv, result, req)
				assert.Equal(t, http.StatusForbidden, result.Code, "tenant role must not read process-global data")
			}
			req := isoReq(http.MethodGet, "/synthetic", "superadmin", "tenant-a")
			allowed := httptest.NewRecorder()
			tc.call(srv, allowed, req)
			require.Equal(t, http.StatusOK, allowed.Code)
		})
	}
}
