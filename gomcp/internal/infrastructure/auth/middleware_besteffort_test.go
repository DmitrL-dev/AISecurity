package auth

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// Review 14.06 round-2: /api/v1/scan is JWT-exempt (public), but a present valid
// credential must still populate claims so the R3 SOC auto-feed + plan quota
// work. These cover the best-effort optional-claims path + the skip-if-already-
// authenticated path (APIKeyMiddleware upstream).

func accessCookie(t *testing.T, secret []byte, tenant string) *http.Cookie {
	t.Helper()
	tok, err := Sign(Claims{Sub: "u1", Role: "analyst", TenantID: tenant, TokenType: "access",
		Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatalf("sign: %v", err)
	}
	return &http.Cookie{Name: "syntrex_token", Value: tok}
}

func TestJWTMiddleware_PublicPathBestEffortClaims(t *testing.T) {
	secret := []byte("test-secret-at-least-32-bytes-long!!")
	m := NewJWTMiddleware(secret)

	var seen *Claims
	var reached bool
	probe := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = GetClaims(r.Context())
		reached = true
		w.WriteHeader(http.StatusOK)
	})
	h := m.Middleware(probe)

	// (1) Valid cookie on the public scan path → claims injected, still 200.
	seen, reached = nil, false
	r := httptest.NewRequest(http.MethodPost, "/api/v1/scan", nil)
	r.AddCookie(accessCookie(t, secret, "tnt-a"))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusOK || !reached {
		t.Fatalf("public scan with valid cookie must pass: code=%d reached=%v", w.Code, reached)
	}
	if seen == nil || seen.TenantID != "tnt-a" {
		t.Fatalf("claims must be injected on public path, got %+v", seen)
	}

	// (2) Anonymous → no claims, still reaches handler (no 401).
	seen, reached = nil, false
	r2 := httptest.NewRequest(http.MethodPost, "/api/v1/scan", nil)
	w2 := httptest.NewRecorder()
	h.ServeHTTP(w2, r2)
	if w2.Code != http.StatusOK || !reached {
		t.Fatalf("anonymous public scan must still pass: code=%d", w2.Code)
	}
	if seen != nil {
		t.Fatalf("anonymous scan must have nil claims, got %+v", seen)
	}

	// (3) Expired/invalid cookie → treated as anonymous (no claims, no 401).
	seen, reached = nil, false
	bad, _ := Sign(Claims{Sub: "u1", TokenType: "access", Exp: time.Now().Add(-time.Hour).Unix()}, secret)
	r3 := httptest.NewRequest(http.MethodPost, "/api/v1/scan", nil)
	r3.AddCookie(&http.Cookie{Name: "syntrex_token", Value: bad})
	w3 := httptest.NewRecorder()
	h.ServeHTTP(w3, r3)
	if w3.Code != http.StatusOK || seen != nil {
		t.Fatalf("expired cookie on public path must be anonymous-200, code=%d claims=%+v", w3.Code, seen)
	}
}

func TestJWTMiddleware_SkipsWhenAlreadyAuthenticated(t *testing.T) {
	secret := []byte("test-secret-at-least-32-bytes-long!!")
	m := NewJWTMiddleware(secret)

	var seen *Claims
	probe := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = GetClaims(r.Context())
		w.WriteHeader(http.StatusOK)
	})
	h := m.Middleware(probe)

	// A PROTECTED path with claims already set upstream (as APIKeyMiddleware would
	// from an stx_ key) must pass through WITHOUT a JWT and preserve the claims —
	// not 401, and not re-verify the API key as a JWT.
	r := httptest.NewRequest(http.MethodGet, "/api/soc/incidents", nil)
	r = r.WithContext(SetClaimsContext(r.Context(), &Claims{Sub: "key-user", Role: "analyst", TenantID: "tnt-b"}))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusOK {
		t.Fatalf("pre-authenticated request must pass JWT, got %d", w.Code)
	}
	if seen == nil || seen.TenantID != "tnt-b" {
		t.Fatalf("upstream claims must be preserved, got %+v", seen)
	}
}

func TestJWTMiddleware_SignedServiceEndpointsBypassJWT(t *testing.T) {
	secret := []byte("test-secret-at-least-32-bytes-long!!")
	m := NewJWTMiddleware(secret)

	h := m.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if claims := GetClaims(r.Context()); claims != nil {
			t.Fatalf("signed service endpoint should not synthesize user claims: %+v", claims)
		}
		w.WriteHeader(http.StatusOK)
	}))

	for _, path := range []string{
		"/api/soc/admin/erase",
		"/api/soc/admin/provision-tenant",
		"/api/soc/admin/sso-exchange",
	} {
		r := httptest.NewRequest(http.MethodPost, path, nil)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != http.StatusOK {
			t.Fatalf("%s must reach its Ed25519 verifier without JWT, got %d", path, w.Code)
		}
	}
}
