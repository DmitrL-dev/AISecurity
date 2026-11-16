package httpserver

import (
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAuditProcessGlobalResilienceRoutesRequireOperator(t *testing.T) {
	routes := []struct {
		method, path, body string
		operatorStatus     int
	}{
		{"GET", "/api/v1/resilience/health", "", 503},
		{"GET", "/api/v1/resilience/metrics/fixture", "", 503},
		{"GET", "/api/v1/resilience/audit", "", 200},
		{"GET", "/api/v1/resilience/healing/fixture", "", 404},
		{"POST", "/api/v1/resilience/healing/initiate", `{"component":"synthetic"}`, 202},
		{"POST", "/api/v1/resilience/mode/activate", `{"mode":"SAFE"}`, 503},
		{"GET", "/api/soc/health/deep", "", 200},
	}
	for _, enabled := range []bool{false, true} {
		server := newTISrv(t)
		server.rbac = NewRBACMiddleware(RBACConfig{Enabled: enabled})
		mux := http.NewServeMux()
		NewResilienceAPI(nil, nil, nil, nil, nil).RegisterRoutes(mux, server.rbac)
		server.registerGlobalHealthRoute(mux)
		for _, role := range []string{"viewer", "analyst", "admin", "superadmin"} {
			for _, route := range routes {
				request := httptest.NewRequest(route.method, route.path, strings.NewReader(route.body))
				request = request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Sub: "fixture-operator", Role: role, TenantID: "tenant-a"}))
				response := httptest.NewRecorder()
				mux.ServeHTTP(response, request)
				expected := http.StatusForbidden
				if enabled {
					expected = http.StatusUnauthorized
				} // Existing enabled API-key mode falls back after a low-role JWT.
				if role == "superadmin" {
					expected = route.operatorStatus
				}
				if response.Code != expected {
					t.Fatalf("enabled=%t role=%s %s %s: status %d want %d", enabled, role, route.method, route.path, response.Code, expected)
				}
			}
		}
	}
}
