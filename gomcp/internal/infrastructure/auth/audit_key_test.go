package auth

import (
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
)

func TestAuditAPIKeyPersistsRequiredPrefixAndRefusesMissingOwner(t *testing.T) {
	db, err := sqlite.OpenMemory()
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	store := NewUserStore(db.SqlDB())
	users := store.ListUsers()
	if len(users) == 0 {
		t.Fatal("fixture admin missing")
	}
	user := users[0]
	if err := store.setTenant(user.ID, "fixture-tenant", false); err != nil {
		t.Fatal(err)
	}
	key, issued, err := store.CreateAPIKey(user.ID, "audit fixture", user.Role)
	if err != nil {
		t.Fatal(err)
	}
	var prefix string
	if err := db.SqlDB().QueryRow(`SELECT key_prefix FROM api_keys WHERE id=$1`, issued.ID).Scan(&prefix); err != nil {
		t.Fatal(err)
	}
	if prefix != issued.KeyPrefix {
		t.Fatal("required prefix was not persisted")
	}
	store.mu.Lock()
	store.users = make(map[string]*User)
	store.mu.Unlock()
	called := false
	handler := APIKeyMiddleware(store, http.HandlerFunc(func(http.ResponseWriter, *http.Request) { called = true }))
	request := httptest.NewRequest("GET", "/private", nil)
	request.Header.Set("Authorization", "Bearer "+key)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if called || response.Code != http.StatusUnauthorized {
		t.Fatal("missing owner did not fail closed")
	}
}
func TestAuditInactiveTenantCannotAccessSOCOrIngest(t *testing.T) {
	tenant := Tenant{PlanID: "enterprise", Active: false}
	if tenant.CanAccessSOC() || tenant.CanIngestEvent() {
		t.Fatal("inactive tenant retained SOC rights")
	}
	tenant.Active = true
	if !tenant.CanAccessSOC() || !tenant.CanIngestEvent() {
		t.Fatal("active enterprise tenant denied")
	}
}

func TestAuditAPIKeyScopeIsCappedByCurrentOwnerWithoutPromotion(t *testing.T) {
	cases := []struct {
		name, ownerRole, keyRole string
		inactive, missing, allow bool
	}{
		{name: "admin owner with viewer key", ownerRole: "admin", keyRole: "viewer", allow: true},
		{name: "admin owner with analyst key", ownerRole: "admin", keyRole: "analyst", allow: true},
		{name: "downgraded owner with old admin key", ownerRole: "viewer", keyRole: "admin"},
		{name: "unknown key role", ownerRole: "admin", keyRole: "unknown"},
		{name: "unknown owner role", ownerRole: "unknown", keyRole: "viewer"},
		{name: "inactive owner", ownerRole: "admin", keyRole: "viewer", inactive: true},
		{name: "missing owner", ownerRole: "admin", keyRole: "viewer", missing: true},
		{name: "viewer owner with sensor key", ownerRole: "viewer", keyRole: "sensor", allow: true},
		{name: "sensor owner cannot issue viewer authority", ownerRole: "sensor", keyRole: "viewer"},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			db, err := sqlite.OpenMemory()
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			store := NewUserStore(db.SqlDB())
			owners := store.ListUsers()
			if len(owners) == 0 {
				t.Fatal("fixture owner missing")
			}
			owner := owners[0]
			if err := store.UpdateUser(owner.ID, "", test.ownerRole, true); err != nil {
				t.Fatal(err)
			}
			if err := store.setTenant(owner.ID, "fixture-tenant", false); err != nil {
				t.Fatal(err)
			}
			key, _, err := store.CreateAPIKey(owner.ID, "scope fixture", test.keyRole)
			if err != nil {
				t.Fatal(err)
			}
			if err := store.UpdateUser(owner.ID, "", test.ownerRole, !test.inactive); err != nil {
				t.Fatal(err)
			}
			if test.missing {
				store.mu.Lock()
				store.users = make(map[string]*User)
				store.mu.Unlock()
			}
			var got *Claims
			handler := APIKeyMiddleware(store, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				got = GetClaims(r.Context())
				w.WriteHeader(http.StatusNoContent)
			}))
			request := httptest.NewRequest("GET", "/private", nil)
			request.Header.Set("Authorization", "Bearer "+key)
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if test.allow {
				if got == nil || response.Code != http.StatusNoContent {
					t.Fatalf("downscoped key denied: status %d", response.Code)
				}
				if got.Role != test.keyRole || got.TenantID != "fixture-tenant" {
					t.Fatal("key claims were promoted or lost owner tenant")
				}
			} else if got != nil || response.Code != http.StatusUnauthorized {
				t.Fatalf("invalid or excessive key authority accepted: status %d", response.Code)
			}
		})
	}
}

func TestAuditAPIKeyAuthenticationSnapshotsConcurrentOwnerChanges(t *testing.T) {
	db, err := sqlite.OpenMemory()
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	store := NewUserStore(db.SqlDB())
	owners := store.ListUsers()
	if len(owners) == 0 {
		t.Fatal("fixture owner missing")
	}
	ownerID := owners[0].ID
	if err := store.UpdateUser(ownerID, "", "admin", true); err != nil {
		t.Fatal(err)
	}
	if err := store.setTenant(ownerID, "fixture-tenant", false); err != nil {
		t.Fatal(err)
	}
	key, _, err := store.CreateAPIKey(ownerID, "concurrent scope fixture", "viewer")
	if err != nil {
		t.Fatal(err)
	}
	handler := APIKeyMiddleware(store, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "viewer" || claims.TenantID != "fixture-tenant" {
			t.Error("authentication promoted or tore owner snapshot")
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	start := make(chan struct{})
	var workers sync.WaitGroup
	workers.Add(2)
	go func() {
		defer workers.Done()
		<-start
		for index := 0; index < 32; index++ {
			role := "admin"
			if index%2 == 0 {
				role = "viewer"
			}
			if err := store.UpdateUser(ownerID, "", role, index%3 != 0); err != nil {
				t.Error(err)
				return
			}
		}
	}()
	go func() {
		defer workers.Done()
		<-start
		for index := 0; index < 32; index++ {
			request := httptest.NewRequest("GET", "/private", nil)
			request.Header.Set("Authorization", "Bearer "+key)
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if response.Code != http.StatusNoContent && response.Code != http.StatusUnauthorized {
				t.Errorf("unexpected authorization status %d", response.Code)
			}
		}
	}()
	close(start)
	workers.Wait()
}
