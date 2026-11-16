package httpserver

import (
	"bytes"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Round-6 B-2: the waitlist handler persists to the deletable store and logs NO
// cleartext PII (email/company). End-to-end: handler → service → sqlite repo.
func TestHandleWaitlist_PersistsAndNoCleartextInLogs(t *testing.T) {
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	svc := appsoc.NewService(repo, nil)
	srv := New(svc, 0)

	var buf bytes.Buffer
	old := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&buf, nil)))
	defer slog.SetDefault(old)

	const email, company = "dave@corp-xyz.com", "TopSecretLLC"
	body := `{"email":"` + email + `","company":"` + company + `","use_case":"mcp"}`
	r := httptest.NewRequest(http.MethodPost, "/api/waitlist", strings.NewReader(body))
	w := httptest.NewRecorder()
	srv.handleWaitlist(w, r)
	if w.Code != http.StatusOK {
		t.Fatalf("waitlist submit must be 200, got %d (%s)", w.Code, w.Body.String())
	}

	// Persisted to the deletable store with cleartext intact.
	entries, err := svc.ListWaitlist(0)
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(entries) != 1 || entries[0].Email != email || entries[0].Company != company {
		t.Fatalf("entry not persisted correctly: %+v", entries)
	}

	// No cleartext PII in the handler's logs.
	logged := buf.String()
	if strings.Contains(logged, company) {
		t.Errorf("company must not be logged by the handler; log=%q", logged)
	}
	if strings.Contains(logged, email) {
		t.Errorf("raw email must not be logged by the handler; log=%q", logged)
	}
}
