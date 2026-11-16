package auth

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func principalFixture(t *testing.T) (*UserStore, *TenantStore, *User, *Tenant, []byte) {
	t.Helper()
	_, users, tenants, u := durableFixture(t)
	tenant, err := tenants.CreateTenant("Principal", "principal", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	if err = users.setTenant(u.ID, tenant.ID, true); err != nil {
		t.Fatal(err)
	}
	u, err = users.GetByID(u.ID)
	if err != nil {
		t.Fatal(err)
	}
	return users, tenants, u, tenant, []byte(strings.Repeat("s", 32))
}
func principalRequest(t *testing.T, m *JWTMiddleware, secret []byte, claims Claims, path string) (int, *Claims) {
	t.Helper()
	claims.Exp = time.Now().Add(time.Hour).Unix()
	claims.TokenType = "access"
	token, err := Sign(claims, secret)
	if err != nil {
		t.Fatal(err)
	}
	return principalTokenRequest(m, token, path)
}
func principalTokenRequest(m *JWTMiddleware, token, path string) (int, *Claims) {
	var seen *Claims
	handler := m.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { seen = GetClaims(r.Context()); w.WriteHeader(200) }))
	r := httptest.NewRequest("GET", path, nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, r)
	return w.Code, seen
}
func TestAuditPrincipalOldJWTCannotRetainRevokedAuthority(t *testing.T) {
	for _, change := range []string{"role", "disable", "delete"} {
		t.Run(change, func(t *testing.T) {
			users, tenants, u, v, secret := principalFixture(t)
			m := NewJWTMiddleware(secret)
			m.BindPrincipalStores(users, tenants)
			claims := Claims{Sub: u.Email, Role: "admin", TenantID: v.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}
			token, err := Sign(claims, secret)
			if err != nil {
				t.Fatal(err)
			}
			if code, _ := principalTokenRequest(m, token, "/protected"); code != 200 {
				t.Fatal("valid current principal rejected")
			}
			err = nil
			switch change {
			case "role":
				err = users.UpdateUser(u.ID, "", "viewer", true)
			case "disable":
				err = users.UpdateUser(u.ID, "", "admin", false)
			case "delete":
				err = users.DeleteUser(u.ID)
			}
			if err != nil {
				t.Fatal(err)
			}
			for _, path := range []string{"/protected", "/api/v1/scan"} {
				if code, seen := principalTokenRequest(m, token, path); code != 401 || seen != nil {
					t.Fatalf("revoked JWT reached %s: %d", path, code)
				}
			}
		})
	}
}
func TestAuditPrincipalScopeAndExplicitSuperadminSwitch(t *testing.T) {
	users, tenants, u, v, secret := principalFixture(t)
	other, err := tenants.CreateTenant("Other", "other", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	m := NewJWTMiddleware(secret)
	m.BindPrincipalStores(users, tenants)
	for _, subject := range []string{u.ID, u.Email} {
		code, seen := principalRequest(t, m, secret, Claims{Sub: subject, Role: "viewer", TenantID: v.ID}, "/protected")
		if code != 200 || seen.Role != "viewer" {
			t.Fatal("downscope promoted or valid subject denied")
		}
	}
	if code, _ := principalRequest(t, m, secret, Claims{Sub: u.Email, Role: "admin", TenantID: other.ID}, "/protected"); code != 401 {
		t.Fatal("foreign tenant accepted")
	}
	if code, _ := principalRequest(t, m, secret, Claims{Sub: u.Email, Role: "unknown", TenantID: v.ID}, "/protected"); code != 401 {
		t.Fatal("unknown role accepted")
	}
	if err = users.UpdateUser(u.ID, "", "superadmin", true); err != nil {
		t.Fatal(err)
	}
	code, seen := principalRequest(t, m, secret, Claims{Sub: u.Email, Role: "superadmin", TenantID: other.ID, Impersonator: u.Email}, "/protected")
	if code != 200 || seen.TenantID != other.ID || seen.Impersonator != u.Email {
		t.Fatal("explicit superadmin switch lost")
	}
	if err = users.UpdateUser(u.ID, "", "admin", true); err != nil {
		t.Fatal(err)
	}
	if code, _ = principalRequest(t, m, secret, Claims{Sub: u.Email, Role: "superadmin", TenantID: other.ID}, "/protected"); code != 401 {
		t.Fatal("former superadmin retained tenant switch")
	}
}
func TestAuditPrincipalUsesConfiguredDatabaseAuthority(t *testing.T) {
	users, tenants, u, v, secret := principalFixture(t)
	m := NewJWTMiddleware(secret)
	m.BindPrincipalStores(users, tenants)
	claims := Claims{Sub: u.Email, Role: "admin", TenantID: v.ID}
	if _, err := users.db.Exec(`UPDATE users SET role='viewer' WHERE id=$1`, u.ID); err != nil {
		t.Fatal(err)
	}
	if users.users[u.Email].Role != "admin" {
		t.Fatal("fixture RAM already changed")
	}
	if code, _ := principalRequest(t, m, secret, claims, "/protected"); code != 401 {
		t.Fatal("stale RAM role overrode configured DB")
	}
	claims.Role = "viewer"
	if _, err := users.db.Exec(`UPDATE tenants SET active=false WHERE id=$1`, v.ID); err != nil {
		t.Fatal(err)
	}
	if code, _ := principalRequest(t, m, secret, claims, "/protected"); code != 401 {
		t.Fatal("disabled authoritative tenant accepted")
	}
	users.db.Close()
	if code, _ := principalRequest(t, m, secret, claims, "/protected"); code != 503 || users.Ready() == nil {
		t.Fatal("database error fell back to stale RAM")
	}
}
func TestAuditPrincipalStandalonePrimitiveAndAnonymousPublicRemain(t *testing.T) {
	secret := []byte(strings.Repeat("s", 32))
	m := NewJWTMiddleware(secret)
	if code, _ := principalRequest(t, m, secret, Claims{Sub: "standalone", Role: "admin"}, "/protected"); code != 200 {
		t.Fatal("standalone JWT primitive ABI changed")
	}
	users, tenants, _, _, secret := principalFixture(t)
	m = NewJWTMiddleware(secret)
	m.BindPrincipalStores(users, tenants)
	called := false
	r := httptest.NewRequest("GET", "/api/v1/scan", nil)
	w := httptest.NewRecorder()
	m.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		if GetClaims(r.Context()) != nil {
			t.Fatal("anonymous request acquired principal")
		}
		w.WriteHeader(200)
	})).ServeHTTP(w, r)
	if !called || w.Code != 200 {
		t.Fatal("anonymous public endpoint closed")
	}
}

func TestAuditBoundAPIKeyUsesCurrentDatabasePrincipal(t *testing.T) {
	for _, change := range []string{"role", "disable", "tenant"} {
		t.Run(change, func(t *testing.T) {
			users, tenants, u, v, secret := principalFixture(t)
			other, err := tenants.CreateTenant("Other", "other", u.ID, "starter")
			if err != nil {
				t.Fatal(err)
			}
			key, _, err := users.CreateAPIKey(u.ID, "fixture", "admin")
			if err != nil {
				t.Fatal(err)
			}
			m := NewJWTMiddleware(secret)
			m.BindPrincipalStores(users, tenants)
			reached := false
			handler := APIKeyMiddleware(users, m.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { reached = true; w.WriteHeader(200) })))
			request := func() int {
				reached = false
				r := httptest.NewRequest("GET", "/protected", nil)
				r.Header.Set("Authorization", "Bearer "+key)
				w := httptest.NewRecorder()
				handler.ServeHTTP(w, r)
				return w.Code
			}
			if request() != 200 || !reached {
				t.Fatal("valid API key rejected")
			}
			switch change {
			case "role":
				_, err = users.db.Exec(`UPDATE users SET role='viewer' WHERE id=$1`, u.ID)
			case "disable":
				_, err = users.db.Exec(`UPDATE users SET active=false WHERE id=$1`, u.ID)
			case "tenant":
				_, err = users.db.Exec(`UPDATE users SET tenant_id=$1 WHERE id=$2`, other.ID, u.ID)
			}
			if err != nil {
				t.Fatal(err)
			}
			if users.users[u.Email].Role != "admin" || !users.users[u.Email].Active || users.users[u.Email].TenantID != v.ID {
				t.Fatal("fixture RAM is not stale")
			}
			if request() != 401 || reached {
				t.Fatal("API key bypassed current database principal")
			}
		})
	}
}
func TestAuditPrincipalObsoleteAccessCookieCannotBlockRefreshOrLogout(t *testing.T) {
	users, tenants, u, v, secret := principalFixture(t)
	m := NewJWTMiddleware(secret)
	m.BindPrincipalStores(users, tenants)
	access, err := Sign(Claims{Sub: u.Email, Role: "admin", TenantID: v.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	refresh, err := Sign(Claims{Sub: u.Email, Role: "admin", TenantID: v.ID, TokenType: "refresh", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	if err = users.UpdateUser(u.ID, "", "viewer", true); err != nil {
		t.Fatal(err)
	}
	request := func(path string, handler http.HandlerFunc) *httptest.ResponseRecorder {
		r := httptest.NewRequest("POST", path, nil)
		r.AddCookie(&http.Cookie{Name: "syntrex_token", Value: access})
		r.AddCookie(&http.Cookie{Name: "syntrex_refresh", Value: refresh})
		w := httptest.NewRecorder()
		m.Middleware(handler).ServeHTTP(w, r)
		return w
	}
	response := request("/api/auth/refresh", HandleRefresh(users, secret))
	if response.Code != 200 {
		t.Fatalf("obsolete access blocked refresh: %d", response.Code)
	}
	found := false
	for _, cookie := range response.Result().Cookies() {
		if cookie.Name == "syntrex_token" {
			current, err := Verify(cookie.Value, secret)
			if err != nil || current.Role != "viewer" || current.TenantID != v.ID {
				t.Fatal("refresh did not retain current lower scope")
			}
			found = true
		}
	}
	if !found {
		t.Fatal("refresh cookie missing")
	}
	var renewed TokenResponse
	if err := json.Unmarshal(response.Body.Bytes(), &renewed); err != nil || renewed.User == nil || renewed.User.Role != "viewer" || renewed.User.TenantID != v.ID {
		t.Fatal("refresh response reported obsolete authority")
	}
	response = request("/api/auth/logout", HandleLogout())
	if response.Code != 200 {
		t.Fatal("obsolete access blocked logout")
	}
	cleared := false
	for _, cookie := range response.Result().Cookies() {
		if cookie.Name == "syntrex_token" && cookie.MaxAge < 0 {
			cleared = true
		}
	}
	if !cleared {
		t.Fatal("logout did not clear old cookie")
	}
	r := httptest.NewRequest("POST", "/api/auth/login", strings.NewReader(`{"email":"owner@example.test","password":"synthetic-only-password"}`))
	r.AddCookie(&http.Cookie{Name: "syntrex_token", Value: access})
	w := httptest.NewRecorder()
	m.Middleware(HandleLogin(users, secret)).ServeHTTP(w, r)
	if w.Code != 200 {
		t.Fatalf("obsolete access blocked credential login: %d", w.Code)
	}

}
