package auth

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func currentCredentialRequest(users *UserStore, tenants *TenantStore, secret []byte, credential string) (int, *Claims) {
	middleware := NewJWTMiddleware(secret)
	middleware.BindPrincipalStores(users, tenants)
	var seen *Claims
	handler := APIKeyMiddleware(users, middleware.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = GetClaims(r.Context())
		w.WriteHeader(http.StatusOK)
	})))
	request := httptest.NewRequest(http.MethodGet, "/protected-current-principal", nil)
	request.Header.Set("Authorization", "Bearer "+credential)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	return response.Code, seen
}

// Deactivation is a current-principal gate, not permanent per-token revocation.
// The same unexpired JWT and undeleted key resume only when current owner rights
// permit them again. Repeated cycles must still reject every disabled state.
func TestAuditCurrentPrincipalRepeatedActivationCycles(t *testing.T) {
	users, tenants, owner, tenant, secret := principalFixture(t)
	jwt, err := Sign(Claims{Sub: owner.Email, Role: "admin", TenantID: tenant.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	key, _, err := users.CreateAPIKey(owner.ID, "cycle fixture", "admin")
	if err != nil {
		t.Fatal(err)
	}
	for step, active := range []bool{true, false, true, false, true, false} {
		if err = users.UpdateUser(owner.ID, "", "admin", active); err != nil {
			t.Fatal(err)
		}
		for _, credential := range []string{jwt, key} {
			status, claims := currentCredentialRequest(users, tenants, secret, credential)
			if active {
				if status != 200 || claims == nil || claims.Role != "admin" {
					t.Fatalf("current enabled owner rejected at step %d: %d", step, status)
				}
			} else if status != 401 || claims != nil {
				t.Fatalf("disabled owner authorized at step %d: %d", step, status)
			}
		}
		// Persisted activation state must agree after reconstructing both stores.
		users = NewUserStore(users.db)
		tenants = NewTenantStore(tenants.db)
		for _, credential := range []string{jwt, key} {
			status, claims := currentCredentialRequest(users, tenants, secret, credential)
			want := 401
			if active {
				want = 200
			}
			if status != want || (active && claims == nil) || (!active && claims != nil) {
				t.Fatalf("restart changed activation semantics at step %d: %d", step, status)
			}
		}
	}
}

func TestAuditCurrentPrincipalDeletedKeyNeverReturnsAfterReactivation(t *testing.T) {
	users, tenants, owner, tenant, secret := principalFixture(t)
	jwt, err := Sign(Claims{Sub: owner.Email, Role: "admin", TenantID: tenant.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	key, record, err := users.CreateAPIKey(owner.ID, "deleted cycle fixture", "admin")
	if err != nil {
		t.Fatal(err)
	}
	if err = users.UpdateUser(owner.ID, "", "admin", false); err != nil {
		t.Fatal(err)
	}
	if err = users.DeleteAPIKey(record.ID, owner.ID); err != nil {
		t.Fatal(err)
	}
	for _, active := range []bool{true, false, true} {
		if err = users.UpdateUser(owner.ID, "", "admin", active); err != nil {
			t.Fatal(err)
		}
		users = NewUserStore(users.db)
		tenants = NewTenantStore(tenants.db)
		if status, claims := currentCredentialRequest(users, tenants, secret, key); status != 401 || claims != nil {
			t.Fatal("deleted key revived after activation/restart")
		}
		var count int
		if err = users.db.QueryRow(`SELECT COUNT(*) FROM api_keys WHERE id=$1`, record.ID).Scan(&count); err != nil || count != 0 {
			t.Fatal("deleted key record reappeared")
		}
		status, _ := currentCredentialRequest(users, tenants, secret, jwt)
		want := 401
		if active {
			want = 200
		}
		if status != want {
			t.Fatal("JWT current-principal activation contract changed")
		}
	}
}

func TestAuditCurrentPrincipalOwnerUpgradeNeverPromotesDownscope(t *testing.T) {
	users, tenants, owner, tenant, secret := principalFixture(t)
	jwt, err := Sign(Claims{Sub: owner.Email, Role: "viewer", TenantID: tenant.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	key, _, err := users.CreateAPIKey(owner.ID, "downscoped cycle fixture", "viewer")
	if err != nil {
		t.Fatal(err)
	}
	for _, role := range []string{"admin", "superadmin", "viewer", "admin", "superadmin"} {
		if err = users.UpdateUser(owner.ID, "", role, true); err != nil {
			t.Fatal(err)
		}
		for _, credential := range []string{jwt, key} {
			status, claims := currentCredentialRequest(users, tenants, secret, credential)
			if status != 200 || claims == nil || claims.Role != "viewer" || claims.TenantID != tenant.ID {
				t.Fatalf("owner role %s promoted/downscoped credential or changed its scope", role)
			}
		}
	}
}
