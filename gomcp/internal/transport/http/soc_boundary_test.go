package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

func TestSOCScopedListRequiresClaimsEvenWithoutTenantStore(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	seedIncident(t, svc, "synthetic tenant A marker", "tenant-a")
	seedIncident(t, svc, "synthetic tenant B marker", "tenant-b")
	require.Nil(t, srv.tenantStore)
	routed := srv.rbac.Require(RoleViewer, srv.requireSOC(srv.handleIncidents))
	request := httptest.NewRequest(http.MethodGet, "/api/soc/incidents", nil)
	anonymous := httptest.NewRecorder()
	routed(anonymous, request)
	assert.Equal(t, http.StatusUnauthorized, anonymous.Code, "no claims must not read global incidents")
	assert.NotContains(t, anonymous.Body.String(), "synthetic tenant B marker")
	missingSub := httptest.NewRecorder()
	routed(missingSub, request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Role: "viewer", TenantID: "tenant-a"})))
	assert.Equal(t, http.StatusUnauthorized, missingSub.Code)
	missingTenant := httptest.NewRecorder()
	routed(missingTenant, request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Sub: "synthetic", Role: "viewer"})))
	assert.Equal(t, http.StatusForbidden, missingTenant.Code)
	scoped := httptest.NewRecorder()
	routed(scoped, request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Sub: "synthetic", Role: "viewer", TenantID: "tenant-a"})))
	require.Equal(t, http.StatusOK, scoped.Code)
	require.Contains(t, scoped.Body.String(), "synthetic tenant A marker")
	require.NotContains(t, scoped.Body.String(), "synthetic tenant B marker")
	operator := httptest.NewRecorder()
	routed(operator, request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Sub: "synthetic-operator", Role: "superadmin"})))
	require.Equal(t, http.StatusOK, operator.Code)
	require.Contains(t, operator.Body.String(), "synthetic tenant A marker")
	require.Contains(t, operator.Body.String(), "synthetic tenant B marker")
}
