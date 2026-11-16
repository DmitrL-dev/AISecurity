package httpserver

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

func TestIncidentPrincipalRequiredBeforeReadOrMutation(t *testing.T) {
	srv, svc := setupIsoSrv(t)
	incident := seedIncident(t, svc, "synthetic authority boundary", "tenant-a")
	target := "/api/soc/incidents/" + incident.ID
	request := httptest.NewRequest(http.MethodGet, target, nil)
	request.SetPathValue("id", incident.ID)
	response := httptest.NewRecorder()
	srv.handleIncidentDetail(response, request)
	assert.Equal(t, http.StatusNotFound, response.Code, "missing principal must not read incident")
	mutation := httptest.NewRequest(http.MethodPost, target+"/assign", strings.NewReader(`{"analyst":"synthetic analyst"}`))
	mutation.SetPathValue("id", incident.ID)
	result := httptest.NewRecorder()
	srv.handleIncidentAssign(result, mutation)
	assert.Equal(t, http.StatusNotFound, result.Code, "missing principal must not mutate incident")
	current, err := svc.GetIncident(incident.ID)
	require.NoError(t, err)
	assert.Empty(t, current.AssignedTo)
	emptySubject := httptest.NewRequest(http.MethodGet, target, nil)
	emptySubject = emptySubject.WithContext(auth.SetClaimsContext(emptySubject.Context(), &auth.Claims{Role: "analyst", TenantID: "tenant-a"}))
	emptySubject.SetPathValue("id", incident.ID)
	invalid := httptest.NewRecorder()
	srv.handleIncidentDetail(invalid, emptySubject)
	assert.Equal(t, http.StatusNotFound, invalid.Code, "empty subject must not read incident")
	missingTenant := isoReq(http.MethodGet, target, "analyst", "")
	missingTenant.SetPathValue("id", incident.ID)
	empty := httptest.NewRecorder()
	srv.handleIncidentDetail(empty, missingTenant)
	require.Equal(t, http.StatusNotFound, empty.Code)
	other := isoReq(http.MethodGet, target, "analyst", "tenant-b")
	other.SetPathValue("id", incident.ID)
	denied := httptest.NewRecorder()
	srv.handleIncidentDetail(denied, other)
	require.Equal(t, http.StatusNotFound, denied.Code)
	owner := isoReq(http.MethodGet, target, "analyst", "tenant-a")
	owner.SetPathValue("id", incident.ID)
	allowed := httptest.NewRecorder()
	srv.handleIncidentDetail(allowed, owner)
	require.Equal(t, http.StatusOK, allowed.Code)
	operator := isoReq(http.MethodGet, target, "superadmin", "tenant-b")
	operator.SetPathValue("id", incident.ID)
	admin := httptest.NewRecorder()
	srv.handleIncidentDetail(admin, operator)
	require.Equal(t, http.StatusOK, admin.Code)
}
