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

// Fixed interop seed — SHARED with spectorn's provision-client test. Reused from
// the erasure interop vector (same spectorn->gomcp service key); the message is
// domain-separated so the signatures differ.
const provTestSeedHex = "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"

func provTestKey(t *testing.T) ed25519.PrivateKey {
	t.Helper()
	seed, err := hex.DecodeString(provTestSeedHex)
	if err != nil {
		t.Fatalf("seed: %v", err)
	}
	return ed25519.NewKeyFromSeed(seed)
}

func signProvision(priv ed25519.PrivateKey, tenantID, planID string, ts int64, nonce string) string {
	return hex.EncodeToString(ed25519.Sign(priv, provisionCanonicalMessage(tenantID, planID, ts, nonce)))
}

func newProvisionTestServer(t *testing.T) *Server {
	t.Helper()
	priv := provTestKey(t)
	t.Setenv("SOC_ADMIN_PROVISION_PUBKEY", hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	return &Server{
		tenantStore:       auth.NewTenantStore(nil), // pure in-memory; no DB needed for this unit
		provisionVerifier: newProvisionVerifier(),
	}
}

func TestProvisionVerifier_DoesNotFallbackToErasureKey(t *testing.T) {
	priv := provTestKey(t)
	t.Setenv("SOC_ADMIN_PROVISION_PUBKEY", "")
	t.Setenv("SOC_ADMIN_ERASURE_PUBKEY", hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	if newProvisionVerifier().enabled() {
		t.Fatal("provision verifier must require SOC_ADMIN_PROVISION_PUBKEY")
	}
}

func postProvision(t *testing.T, s *Server, priv ed25519.PrivateKey, tenantID, planID, nonce string) *httptest.ResponseRecorder {
	t.Helper()
	ts := time.Now().Unix()
	body, _ := json.Marshal(map[string]any{
		"tenant_id": tenantID,
		"plan_id":   planID,
		"name":      "Acme Corp",
		"ts":        ts,
		"nonce":     nonce,
		"signature": signProvision(priv, tenantID, planID, ts, nonce),
	})
	r := httptest.NewRequest("POST", "/api/soc/admin/provision-tenant", bytes.NewReader(body))
	w := httptest.NewRecorder()
	s.handleAdminProvisionTenant(w, r)
	return w
}

// Interop lock: pin the canonical message + public key + signature so the Rust
// signer (spectorn) and this Go verifier can never drift apart.
func TestProvisionCanonical_InteropLock(t *testing.T) {
	priv := provTestKey(t)
	want := "syntrex-soc-provision\nv1\ntnt-prov-vector\nprofessional\n1718000000\nabcdef0123456789"
	got := string(provisionCanonicalMessage("tnt-prov-vector", "professional", 1_718_000_000, "abcdef0123456789"))
	if got != want {
		t.Fatalf("canonical drift:\n got=%q\nwant=%q", got, want)
	}
	if pub := hex.EncodeToString(priv.Public().(ed25519.PublicKey)); pub != "79b5562e8fe654f94078b112e8a98ba7901f853ae695bed7e0e3910bad049664" {
		t.Fatalf("pubkey drift: %s", pub)
	}
	sig := signProvision(priv, "tnt-prov-vector", "professional", 1_718_000_000, "abcdef0123456789")
	// Deterministic Ed25519: this EXACT signature must also be produced by
	// spectorn's Rust signer (provision_canonical_and_signature_match_gomcp_interop).
	const wantSig = "7d17c307b555836ed2bc065b6f5df8c0340f079320c53b67bf03edfde0c88217dbd4f9dd6d95f1f501b56e8c4f226ae8d3261743b78447d18376b9694e5c2d02"
	if sig != wantSig {
		t.Fatalf("signature drift vs interop vector: %s", sig)
	}
}

func TestProvisionTenant_CreateThenUpdateIdempotent(t *testing.T) {
	s := newProvisionTestServer(t)
	priv := provTestKey(t)

	// Create at starter.
	if w := postProvision(t, s, priv, "tnt-spec-1", "starter", "nonce-1"); w.Code != http.StatusOK {
		t.Fatalf("create: HTTP %d body=%s", w.Code, w.Body.String())
	}
	tn, err := s.tenantStore.GetTenantBySlug("tnt-spec-1")
	if err != nil || tn == nil {
		t.Fatalf("tenant not created: %v", err)
	}
	if tn.PlanID != "starter" {
		t.Fatalf("plan = %s, want starter", tn.PlanID)
	}

	// Upgrade to professional (new nonce) → same tenant, plan updated.
	if w := postProvision(t, s, priv, "tnt-spec-1", "professional", "nonce-2"); w.Code != http.StatusOK {
		t.Fatalf("update: HTTP %d", w.Code)
	}
	tn, _ = s.tenantStore.GetTenantBySlug("tnt-spec-1")
	if tn.PlanID != "professional" {
		t.Fatalf("plan not updated: %s", tn.PlanID)
	}
	if n := len(s.tenantStore.ListTenants()); n != 1 {
		t.Fatalf("idempotent upsert must keep ONE tenant, got %d", n)
	}
}

func TestProvisionTenant_RejectsBadSignature(t *testing.T) {
	s := newProvisionTestServer(t)
	body, _ := json.Marshal(map[string]any{
		"tenant_id": "tnt-x", "plan_id": "starter", "ts": time.Now().Unix(), "nonce": "n",
		"signature": hex.EncodeToString(make([]byte, ed25519.SignatureSize)),
	})
	r := httptest.NewRequest("POST", "/api/soc/admin/provision-tenant", bytes.NewReader(body))
	w := httptest.NewRecorder()
	s.handleAdminProvisionTenant(w, r)
	if w.Code != http.StatusForbidden {
		t.Fatalf("bad signature must be 403, got %d", w.Code)
	}
	if _, err := s.tenantStore.GetTenantBySlug("tnt-x"); err == nil {
		t.Fatal("unsigned request must NOT create a tenant")
	}
}

func TestProvisionTenant_RejectsReplay(t *testing.T) {
	s := newProvisionTestServer(t)
	priv := provTestKey(t)
	if w := postProvision(t, s, priv, "tnt-replay", "starter", "same-nonce"); w.Code != http.StatusOK {
		t.Fatalf("first: %d", w.Code)
	}
	if w := postProvision(t, s, priv, "tnt-replay", "starter", "same-nonce"); w.Code != http.StatusForbidden {
		t.Fatalf("replayed nonce must be 403, got %d", w.Code)
	}
}

func TestProvisionTenant_RejectsUnknownPlan(t *testing.T) {
	s := newProvisionTestServer(t)
	priv := provTestKey(t)
	if w := postProvision(t, s, priv, "tnt-y", "platinum", "nonce-p"); w.Code != http.StatusBadRequest {
		t.Fatalf("unknown plan must be 400, got %d", w.Code)
	}
}
