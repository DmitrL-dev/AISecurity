package httpserver

import (
	"encoding/json"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAuditIncidentNoteAuthorComesFromAuthenticatedClaims(t *testing.T) {
	service := newTISrv(t)
	incident := domsoc.NewIncident("synthetic fixture", domsoc.SeverityHigh, "audit-rule")
	incident.TenantID = "tenant-a"
	if err := service.socSvc.Repo().InsertIncident(incident); err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest("POST", "/api/soc/incidents/fixture/notes", strings.NewReader(`{"author":"forged-actor","content":"synthetic note"}`))
	request.SetPathValue("id", incident.ID)
	request = request.WithContext(auth.SetClaimsContext(request.Context(), &auth.Claims{Sub: "verified-actor", TenantID: "tenant-a", Role: "analyst"}))
	response := httptest.NewRecorder()
	service.handleIncidentNotes(response, request)
	if response.Code != http.StatusCreated {
		t.Fatalf("note failed: %d %s", response.Code, response.Body.String())
	}
	var note domsoc.IncidentNote
	if err := json.Unmarshal(response.Body.Bytes(), &note); err != nil {
		t.Fatal(err)
	}
	if note.Author != "verified-actor" {
		t.Fatal("caller-controlled author entered incident note")
	}
}
