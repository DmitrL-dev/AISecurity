package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// Review 13.06 (audit A2): with the API-key system disabled (the default), a
// JWT-authenticated caller must still be role-checked — a viewer cannot reach an
// admin route — while callers with no claims (sensor ingest) pass through.
func TestRBAC_Disabled_EnforcesJWTRole(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: false})
	admin := rbac.Require(RoleAdmin, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	cases := []struct {
		role string
		want int
	}{
		{"viewer", http.StatusForbidden},
		{"analyst", http.StatusForbidden},
		{"admin", http.StatusOK},
		{"superadmin", http.StatusOK},
		{"", http.StatusForbidden}, // unknown/empty role denied
	}
	for _, c := range cases {
		req := httptest.NewRequest("GET", "/admin", nil)
		req = req.WithContext(auth.SetClaimsContext(req.Context(), &auth.Claims{Role: c.role}))
		rec := httptest.NewRecorder()
		admin(rec, req)
		if rec.Code != c.want {
			t.Fatalf("role %q on admin route: want %d, got %d", c.role, c.want, rec.Code)
		}
	}

	// No claims at all (e.g. sensor ingest on a JWT-public path) → pass through.
	req := httptest.NewRequest("GET", "/ingest", nil)
	rec := httptest.NewRecorder()
	admin(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("no-claims request must pass through, got %d", rec.Code)
	}
}

func TestRBAC_Disabled_PassesThrough(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: false})

	handler := rbac.Require(RoleAdmin, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	req := httptest.NewRequest("GET", "/test", nil)
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestRBAC_Enabled_NoKey_Returns401(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})

	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("GET", "/test", nil)
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rec.Code)
	}
}

func TestRBAC_Enabled_ValidKey_AdminAccess(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("admin-key", "sk-admin-123", RoleAdmin)

	handler := rbac.Require(RoleAdmin, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("admin"))
	})

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer sk-admin-123")
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestRBAC_Enabled_InsufficientRole_Returns403(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("viewer-key", "sk-viewer-456", RoleViewer)

	handler := rbac.Require(RoleAdmin, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer sk-viewer-456")
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("expected 403, got %d", rec.Code)
	}
}

func TestRBAC_XAPIKeyHeader(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("sensor", "sk-sensor-789", RoleSensor)

	handler := rbac.Require(RoleSensor, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("POST", "/ingest", nil)
	req.Header.Set("X-API-Key", "sk-sensor-789")
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestRBAC_RevokedKey_Returns401(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("temp-key", "sk-temp-000", RoleAdmin)
	rbac.RevokeKey("sk-temp-000")

	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer sk-temp-000")
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rec.Code)
	}
}

func TestRBAC_ListKeys_MasksKeys(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("admin", "sk-admin-very-long-key-12345", RoleAdmin)

	keys := rbac.ListKeys()
	if len(keys) != 1 {
		t.Fatalf("expected 1 key, got %d", len(keys))
	}
	if keys[0].Key == "sk-admin-very-long-key-12345" {
		t.Fatal("key should be masked")
	}
	if keys[0].Name != "admin" {
		t.Fatalf("expected name='admin', got %q", keys[0].Name)
	}
	t.Logf("masked key: %s", keys[0].Key)
}

func TestRBAC_RoleHierarchy(t *testing.T) {
	tests := []struct {
		userRole Role
		minRole  Role
		allowed  bool
	}{
		{RoleAdmin, RoleAdmin, true},
		{RoleAdmin, RoleSensor, true},
		{RoleAnalyst, RoleViewer, true},
		{RoleViewer, RoleAnalyst, false},
		{RoleSensor, RoleViewer, false},
		{RoleExternal, RoleAdmin, false},
		{RoleSensor, RoleSensor, true},
	}
	for _, tt := range tests {
		got := hasPermission(tt.userRole, tt.minRole)
		if got != tt.allowed {
			t.Errorf("hasPermission(%s, %s) = %v, want %v", tt.userRole, tt.minRole, got, tt.allowed)
		}
	}
}

// ── Security Regression Tests (T4 bug bounty patches) ──────────────

// TestRBAC_QueryParamKey_Rejected verifies that API keys in query params
// are no longer accepted (P1 fix: credential leakage via URL).
func TestRBAC_QueryParamKey_Rejected(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("api-test", "sk-query-key-001", RoleAdmin)

	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	// Query param should NOT authenticate
	req := httptest.NewRequest("GET", "/test?api_key=sk-query-key-001", nil)
	rec := httptest.NewRecorder()
	handler(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("query param auth should be rejected (P1 fix), got %d", rec.Code)
	}
}

// TestRBAC_UndefinedRole_Denied verifies that undefined/fabricated roles
// are rejected by the permission check (P3 fix: default-deny).
func TestRBAC_UndefinedRole_Denied(t *testing.T) {
	tests := []struct {
		name     string
		user     Role
		required Role
	}{
		// Review 13.06: "superadmin" is now a DEFINED role (JWTs use it; added to
		// the hierarchy for the A2 fix), so use a genuinely-undefined role here.
		{"fabricated user role", Role("rootadmin"), RoleViewer},
		{"empty user role", Role(""), RoleViewer},
		{"fabricated required role", RoleAdmin, Role("superviewer")},
		{"both undefined", Role("ghost"), Role("phantom")},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if hasPermission(tt.user, tt.required) {
				t.Errorf("hasPermission(%q, %q) should be false (undefined role)", tt.user, tt.required)
			}
		})
	}
}

// TestRBAC_HMAC_MatchesRegisteredKey verifies that the HMAC-based
// constant-time lookup correctly authenticates valid keys.
func TestRBAC_HMAC_MatchesRegisteredKey(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	// Register multiple keys to ensure iteration works
	rbac.RegisterKey("key-a", "sk-aaaa-1111-2222-3333", RoleAdmin)
	rbac.RegisterKey("key-b", "sk-bbbb-4444-5555-6666", RoleAnalyst)
	rbac.RegisterKey("key-c", "sk-cccc-7777-8888-9999", RoleViewer)

	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	// Each key should authenticate successfully
	for _, key := range []string{"sk-aaaa-1111-2222-3333", "sk-bbbb-4444-5555-6666", "sk-cccc-7777-8888-9999"} {
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer "+key)
		rec := httptest.NewRecorder()
		handler(rec, req)

		if rec.Code != http.StatusOK {
			t.Errorf("key %s should authenticate, got %d", key[:10]+"...", rec.Code)
		}
	}
}

// TestRBAC_ConcurrentRequireRevoke is a concurrency regression test (run under
// -race). RevokeKey mutates the shared *APIKey's Active field under the write
// lock; Require must read Active/Role WHILE holding the read lock, not after
// releasing it. Before the fix, Require snapshotted the *APIKey pointer under
// RLock but read apiKey.Active after RUnlock — a data race with RevokeKey's
// write (proven: race detector flagged rbac.go:142 read vs rbac.go:76 write).
func TestRBAC_ConcurrentRequireRevoke(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("k", "sk-race-key-0001", RoleAdmin)
	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	done := make(chan struct{})
	go func() {
		for i := 0; i < 5000; i++ {
			rbac.RevokeKey("sk-race-key-0001")
			rbac.RegisterKey("k", "sk-race-key-0001", RoleAdmin)
		}
		close(done)
	}()
	for i := 0; i < 5000; i++ {
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer sk-race-key-0001")
		rec := httptest.NewRecorder()
		handler(rec, req)
	}
	<-done
}

// TestRBAC_HMAC_RejectsWrongKey verifies that similar-looking keys
// are rejected even if they share a common prefix.
func TestRBAC_HMAC_RejectsWrongKey(t *testing.T) {
	rbac := NewRBACMiddleware(RBACConfig{Enabled: true})
	rbac.RegisterKey("real-key", "sk-admin-secret-key-12345", RoleAdmin)

	handler := rbac.Require(RoleViewer, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	// Wrong keys — including prefix collision and off-by-one
	wrongKeys := []string{
		"sk-admin-secret-key-12346",  // off by last char
		"sk-admin-secret-key-1234",   // one char short
		"sk-admin-secret-key-123456", // one char extra
		"sk-admin-secret-key-12345 ", // trailing space
		"SK-ADMIN-SECRET-KEY-12345",  // wrong case
	}

	for _, key := range wrongKeys {
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer "+key)
		rec := httptest.NewRecorder()
		handler(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Errorf("wrong key %q should be rejected, got %d", key, rec.Code)
		}
	}
}
