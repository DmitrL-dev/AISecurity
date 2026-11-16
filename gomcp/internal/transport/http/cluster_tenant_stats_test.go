package httpserver

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/require"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

func TestTenantClusterStatsScopedViews(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	for _, seed := range []struct {
		tenant, category string
		count            int
	}{{"tenant-a", "jailbreak", 2}, {"tenant-a", "auth_bypass", 1}, {"tenant-b", "jailbreak", 4}, {"", "jailbreak", 1}} {
		for i := 0; i < seed.count; i++ {
			event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, seed.category,
				fmt.Sprintf("synthetic cluster %s %s %d", seed.tenant, seed.category, i))
			event.TenantID = seed.tenant
			_, _, err := svc.IngestInternalEvent(event)
			require.NoError(t, err)
		}
	}
	routed := srv.rbac.Require(RoleViewer, srv.requireSOC(srv.handleClusters))
	for _, tc := range []struct {
		name, role, tenant, query string
		clusters, events, max     float64
		average                   float64
	}{
		{"tenant_a_viewer", "viewer", "tenant-a", "", 2, 3, 2, 1.5},
		{"tenant_a_analyst", "analyst", "tenant-a", "", 2, 3, 2, 1.5},
		{"tenant_a_admin", "admin", "tenant-a", "", 2, 3, 2, 1.5},
		{"tenant_b_viewer", "viewer", "tenant-b", "", 1, 4, 4, 4},
		{"empty_tenant_view", "viewer", "tenant-empty", "", 0, 0, 0, 0},
		{"query_cannot_override", "viewer", "tenant-a", "?tenant_id=tenant-b&scope=global", 2, 3, 2, 1.5},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := isoReq(http.MethodGet, "/api/soc/clusters"+tc.query, tc.role, tc.tenant)
			response := httptest.NewRecorder()
			routed(response, req)
			require.Equal(t, http.StatusOK, response.Code, "tenant cluster view must be available")
			var got map[string]any
			require.NoError(t, json.Unmarshal(response.Body.Bytes(), &got))
			require.Equal(t, map[string]any{
				"enabled": true, "scope": "tenant", "statistics_basis": "retained_clusters",
				"total_clusters": tc.clusters, "total_events": tc.events,
				"avg_cluster_size": tc.average, "max_cluster_size": tc.max,
			}, got, "tenant response must contain only its retained aggregates")
		})
	}
	t.Run("operator_global_compatibility", func(t *testing.T) {
		response := httptest.NewRecorder()
		routed(response, isoReq(http.MethodGet, "/api/soc/clusters", "superadmin", ""))
		require.Equal(t, http.StatusOK, response.Code)
		var got, want map[string]any
		require.NoError(t, json.Unmarshal(response.Body.Bytes(), &got))
		encoded, err := json.Marshal(svc.ClusterStats())
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(encoded, &want))
		require.Equal(t, want, got)
		require.Equal(t, float64(8), got["events_processed"])
		require.Equal(t, float64(8), got["total_events"])
	})
}

func TestTenantClusterStatsAuthorityBoundaries(t *testing.T) {
	srv, _ := setupIsoSrv(t)
	routed := srv.rbac.Require(RoleViewer, srv.requireSOC(srv.handleClusters))
	for _, tc := range []struct {
		name   string
		claims *auth.Claims
		status int
		direct bool
	}{
		{"no_claims", nil, http.StatusUnauthorized, false},
		{"empty_subject", &auth.Claims{Role: "viewer", TenantID: "tenant-a"}, http.StatusUnauthorized, false},
		{"blank_subject", &auth.Claims{Sub: " \t", Role: "viewer", TenantID: "tenant-a"}, http.StatusUnauthorized, false},
		{"empty_operator_subject", &auth.Claims{Role: "superadmin"}, http.StatusUnauthorized, false},
		{"missing_tenant", &auth.Claims{Sub: "synthetic", Role: "viewer"}, http.StatusForbidden, false},
		{"blank_tenant", &auth.Claims{Sub: "synthetic", Role: "viewer", TenantID: " \t"}, http.StatusForbidden, false},
		{"unknown_role", &auth.Claims{Sub: "synthetic", Role: "unknown", TenantID: "tenant-a"}, http.StatusForbidden, false},
		{"sensor_role", &auth.Claims{Sub: "synthetic", Role: "sensor", TenantID: "tenant-a"}, http.StatusForbidden, false},
		{"external_role", &auth.Claims{Sub: "synthetic", Role: "external", TenantID: "tenant-a"}, http.StatusForbidden, false},
		{"direct_handler_unknown_role", &auth.Claims{Sub: "synthetic", Role: "unknown", TenantID: "tenant-a"}, http.StatusForbidden, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/api/soc/clusters", nil)
			if tc.claims != nil {
				req = req.WithContext(auth.SetClaimsContext(req.Context(), tc.claims))
			}
			response := httptest.NewRecorder()
			if tc.direct {
				srv.handleClusters(response, req)
			} else {
				routed(response, req)
			}
			require.Equal(t, tc.status, response.Code)
		})
	}
}
