package httpserver

import (
	"bytes"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// Reuses provTestKey + provTestSeedHex from provision_admin_test.go (same package).

const ssoTestJWTSecret = "test-jwt-secret-at-least-32-bytes-long!!"

func signSSO(priv ed25519.PrivateKey, tenantID, sub string, ts int64, nonce string) string {
	return hex.EncodeToString(ed25519.Sign(priv, ssoCanonicalMessage(tenantID, sub, ts, nonce)))
}

func newSSOTestServer(t *testing.T) *Server {
	t.Helper()
	priv := provTestKey(t)
	t.Setenv("SOC_ADMIN_SSO_PUBKEY", hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	s := &Server{
		tenantStore: auth.NewTenantStore(nil),
		ssoVerifier: newSSOVerifier(),
		jwtSecret:   []byte(ssoTestJWTSecret),
	}
	// Seed the gomcp tenant (slug == spectorn tenant_id) that variant-A provisioning
	// would have created; SSO resolves by slug.
	if _, err := s.tenantStore.CreateTenant("Acme Corp", "tnt-spec-1", "", "professional"); err != nil {
		t.Fatalf("seed tenant: %v", err)
	}
	return s
}

func TestSSOVerifier_DoesNotFallbackToErasureKey(t *testing.T) {
	priv := provTestKey(t)
	t.Setenv("SOC_ADMIN_SSO_PUBKEY", "")
	t.Setenv("SOC_ADMIN_ERASURE_PUBKEY", hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	if newSSOVerifier().enabled() {
		t.Fatal("SSO verifier must require SOC_ADMIN_SSO_PUBKEY")
	}
}

func postSSO(t *testing.T, s *Server, priv ed25519.PrivateKey, tenantID, sub, nonce string) *httptest.ResponseRecorder {
	t.Helper()
	ts := time.Now().Unix()
	body, _ := json.Marshal(map[string]any{
		"tenant_id": tenantID,
		"sub":       sub,
		"ts":        ts,
		"nonce":     nonce,
		"signature": signSSO(priv, tenantID, sub, ts, nonce),
	})
	r := httptest.NewRequest("POST", "/api/soc/admin/sso-exchange", bytes.NewReader(body))
	w := httptest.NewRecorder()
	s.handleSSOExchange(w, r)
	return w
}

func TestSSOExchange_MintsTenantScopedAdminJWT(t *testing.T) {
	s := newSSOTestServer(t)
	priv := provTestKey(t)

	w := postSSO(t, s, priv, "tnt-spec-1", "u_user1", "nonce-1")
	if w.Code != http.StatusOK {
		t.Fatalf("exchange: HTTP %d body=%s", w.Code, w.Body.String())
	}
	var resp struct {
		Token    string `json:"token"`
		TenantID string `json:"tenant_id"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil || resp.Token == "" {
		t.Fatalf("bad response: %v body=%s", err, w.Body.String())
	}
	// The minted token must be a valid gomcp JWT scoped to the tenant, role admin,
	// and NEVER superadmin (SSO must not grant cross-tenant access).
	claims, err := auth.Verify(resp.Token, []byte(ssoTestJWTSecret))
	if err != nil {
		t.Fatalf("minted token does not verify: %v", err)
	}
	tn, _ := s.tenantStore.GetTenantBySlug("tnt-spec-1")
	if claims.TenantID != tn.ID {
		t.Fatalf("token TenantID = %q, want %q (the resolved gomcp tenant)", claims.TenantID, tn.ID)
	}
	if claims.Role != "admin" {
		t.Fatalf("role = %q, want admin", claims.Role)
	}
	if claims.Role == "superadmin" {
		t.Fatal("SSO must NEVER mint a cross-tenant superadmin token")
	}
	if claims.Sub != "u_user1" {
		t.Fatalf("sub = %q, want u_user1", claims.Sub)
	}
}

func TestSSOExchange_RejectsBadSignature(t *testing.T) {
	s := newSSOTestServer(t)
	body, _ := json.Marshal(map[string]any{
		"tenant_id": "tnt-spec-1", "sub": "u_x", "ts": time.Now().Unix(), "nonce": "n",
		"signature": hex.EncodeToString(make([]byte, ed25519.SignatureSize)),
	})
	r := httptest.NewRequest("POST", "/api/soc/admin/sso-exchange", bytes.NewReader(body))
	w := httptest.NewRecorder()
	s.handleSSOExchange(w, r)
	if w.Code != http.StatusForbidden {
		t.Fatalf("bad signature must be 403, got %d", w.Code)
	}
}

func TestSSOExchange_UnprovisionedTenantIs404(t *testing.T) {
	s := newSSOTestServer(t)
	priv := provTestKey(t)
	w := postSSO(t, s, priv, "tnt-does-not-exist", "u_x", "nonce-z")
	if w.Code != http.StatusNotFound {
		t.Fatalf("unprovisioned tenant must be 404, got %d", w.Code)
	}
}

func TestSSOExchange_RejectsReplay(t *testing.T) {
	s := newSSOTestServer(t)
	priv := provTestKey(t)
	if w := postSSO(t, s, priv, "tnt-spec-1", "u_user1", "same-nonce"); w.Code != http.StatusOK {
		t.Fatalf("first: %d", w.Code)
	}
	if w := postSSO(t, s, priv, "tnt-spec-1", "u_user1", "same-nonce"); w.Code != http.StatusForbidden {
		t.Fatalf("replayed nonce must be 403, got %d", w.Code)
	}
}

// Interop lock: the SAME vector spectorn's Rust SSO client pins.
func TestSSOCanonical_InteropLock(t *testing.T) {
	priv := provTestKey(t)
	want := "syntrex-soc-sso\nv1\ntnt-sso-vector\nu_abc\n1718000000\nabcdef0123456789"
	if got := string(ssoCanonicalMessage("tnt-sso-vector", "u_abc", 1_718_000_000, "abcdef0123456789")); got != want {
		t.Fatalf("canonical drift:\n got=%q\nwant=%q", got, want)
	}
	sig := signSSO(priv, "tnt-sso-vector", "u_abc", 1_718_000_000, "abcdef0123456789")
	// Deterministic Ed25519: spectorn's Rust SSO client must produce this exact sig.
	const wantSig = "320897eecec132efcf6cc6ce698b40f60369ae2935e6648855862132b8428a3c3c907f6236961a2fcd18aaa861ae6dc1674419a3fb2ed5eeff8a70de3da4bc05"
	if sig != wantSig {
		t.Fatalf("signature drift vs interop vector: %s", sig)
	}
}
