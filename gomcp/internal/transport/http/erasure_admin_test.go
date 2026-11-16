package httpserver

import (
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Shared interop vector. The spectorn (Rust ed25519_dalek) signer test MUST build
// the same canonical message from these inputs; since Ed25519/RFC8032 is
// deterministic, identical canonical bytes ⇒ identical signatures ⇒ spectorn's
// signature verifies here. The canonical-bytes assertion below is the interop lock.
const (
	erasureVecSeedHex = "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
	erasureVecTenant  = "tnt-erase-vector"
	erasureVecTS      = int64(1718000000)
	erasureVecNonce   = "abcdef0123456789"
	erasureVecMsg     = "syntrex-soc-erase\nv1\ntnt-erase-vector\n1718000000\nabcdef0123456789"
)

func erasureVecKey(t *testing.T) ed25519.PrivateKey {
	t.Helper()
	seed, err := hex.DecodeString(erasureVecSeedHex)
	if err != nil || len(seed) != ed25519.SeedSize {
		t.Fatalf("bad test seed")
	}
	return ed25519.NewKeyFromSeed(seed)
}

// TestErasureCanonical_InteropLock pins the exact canonical byte string. The Rust
// signer test asserts the same string; a drift on either side breaks interop and
// must fail a test, not silently mismatch in production.
func TestErasureCanonical_InteropLock(t *testing.T) {
	got := string(erasureCanonicalMessage(erasureVecTenant, erasureVecTS, erasureVecNonce))
	if got != erasureVecMsg {
		t.Fatalf("canonical message drift:\n got %q\nwant %q", got, erasureVecMsg)
	}
	// And a signature over it self-verifies (sanity of the primitive).
	priv := erasureVecKey(t)
	pub := priv.Public().(ed25519.PublicKey)
	sig := ed25519.Sign(priv, []byte(erasureVecMsg))
	if !ed25519.Verify(pub, []byte(erasureVecMsg), sig) {
		t.Fatal("self-verify failed")
	}
	t.Logf("interop vector: pub=%s sig=%s", hex.EncodeToString(pub), hex.EncodeToString(sig))
}

func signedReq(priv ed25519.PrivateKey, tenant, nonce string, ts int64) erasureRequest {
	sig := ed25519.Sign(priv, erasureCanonicalMessage(tenant, ts, nonce))
	return erasureRequest{TenantID: tenant, TS: ts, Nonce: nonce, Signature: hex.EncodeToString(sig)}
}

func TestErasureVerifier(t *testing.T) {
	priv := erasureVecKey(t)
	pub := priv.Public().(ed25519.PublicKey)
	v := &erasureVerifier{pubkeys: []ed25519.PublicKey{pub}, seen: make(map[string]time.Time)}
	now := time.Unix(erasureVecTS, 0)

	if err := v.verify(signedReq(priv, "tnt-a", "n1", erasureVecTS), now); err != nil {
		t.Fatalf("valid signed request must pass: %v", err)
	}
	// Replay of the same nonce is rejected.
	if err := v.verify(signedReq(priv, "tnt-a", "n1", erasureVecTS), now); err != errErasureReplay {
		t.Fatalf("replayed nonce must be rejected, got %v", err)
	}
	// Tampered tenant breaks the signature.
	bad := signedReq(priv, "tnt-a", "n2", erasureVecTS)
	bad.TenantID = "tnt-evil"
	if err := v.verify(bad, now); err != errErasureBadSig {
		t.Fatalf("tampered tenant must fail signature, got %v", err)
	}
	// Stale timestamp is rejected.
	if err := v.verify(signedReq(priv, "tnt-a", "n3", erasureVecTS), now.Add(10*time.Minute)); err != errErasureStale {
		t.Fatalf("stale ts must be rejected, got %v", err)
	}
	// A different key is rejected.
	_, otherPriv, _ := ed25519.GenerateKey(nil)
	if err := v.verify(signedReq(otherPriv, "tnt-a", "n4", erasureVecTS), now); err != errErasureBadSig {
		t.Fatalf("wrong key must be rejected, got %v", err)
	}
}

// Round-6 hardening: a control char (esp. the canonical "\n" delimiter) in
// tenant_id/nonce is rejected as malformed BEFORE signature verification, removing
// any canonical-message ambiguity surface.
func TestErasureVerifier_RejectsControlCharsInFields(t *testing.T) {
	priv := erasureVecKey(t)
	pub := priv.Public().(ed25519.PublicKey)
	v := &erasureVerifier{pubkeys: []ed25519.PublicKey{pub}, seen: make(map[string]time.Time)}
	now := time.Unix(erasureVecTS, 0)

	// Even with a VALID signature over the crafted canonical, the field check fires first.
	if err := v.verify(signedReq(priv, "tnt\na", "n1", erasureVecTS), now); err != errErasureMalformed {
		t.Fatalf("newline in tenant_id must be malformed, got %v", err)
	}
	if err := v.verify(signedReq(priv, "tnt-a", "n\n2", erasureVecTS), now); err != errErasureMalformed {
		t.Fatalf("newline in nonce must be malformed, got %v", err)
	}
	// Sanity: clean fields still pass.
	if err := v.verify(signedReq(priv, "tnt-a", "clean-nonce", erasureVecTS), now); err != nil {
		t.Fatalf("clean fields must pass, got %v", err)
	}
}

func TestErasureVerifier_DisabledFailsClosed(t *testing.T) {
	v := &erasureVerifier{seen: make(map[string]time.Time)} // no pubkeys configured
	if v.enabled() {
		t.Fatal("verifier with no keys must be disabled")
	}
	err := v.verify(erasureRequest{TenantID: "x", TS: time.Now().Unix(), Nonce: "n", Signature: "00"}, time.Now())
	if err != errErasureDisabled {
		t.Fatalf("disabled verifier must fail closed, got %v", err)
	}
}

func newEraseSrv(t *testing.T, pubHex string) *Server {
	t.Helper()
	t.Setenv("SOC_ADMIN_ERASURE_PUBKEY", pubHex)
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	return New(appsoc.NewService(repo, nil), 0)
}

func TestHandleAdminEraseTenant_HappyPath(t *testing.T) {
	priv := erasureVecKey(t)
	pub := priv.Public().(ed25519.PublicKey)
	srv := newEraseSrv(t, hex.EncodeToString(pub))

	req := signedReq(priv, "tnt-z", "nonce-z", time.Now().Unix())
	body, _ := json.Marshal(req)
	r := httptest.NewRequest(http.MethodPost, "/api/soc/admin/erase", strings.NewReader(string(body)))
	w := httptest.NewRecorder()
	srv.handleAdminEraseTenant(w, r)
	if w.Code != http.StatusOK {
		t.Fatalf("signed erase must be 200, got %d (%s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), `"erased":true`) {
		t.Fatalf("body must confirm erasure: %s", w.Body.String())
	}
}

func TestHandleAdminEraseTenant_KillSwitch(t *testing.T) {
	priv := erasureVecKey(t)
	srv := newEraseSrv(t, hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	t.Setenv("SOC_ERASURE_DISABLED", "1")

	body, _ := json.Marshal(signedReq(priv, "tnt-z", "nonce-z2", time.Now().Unix()))
	r := httptest.NewRequest(http.MethodPost, "/api/soc/admin/erase", strings.NewReader(string(body)))
	w := httptest.NewRecorder()
	srv.handleAdminEraseTenant(w, r)
	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("kill-switch must 503, got %d", w.Code)
	}
}

func TestHandleAdminEraseTenant_UnsignedRejected(t *testing.T) {
	priv := erasureVecKey(t)
	srv := newEraseSrv(t, hex.EncodeToString(priv.Public().(ed25519.PublicKey)))
	// Forged request: right shape, garbage signature.
	body, _ := json.Marshal(erasureRequest{TenantID: "tnt-z", TS: time.Now().Unix(), Nonce: "x", Signature: "deadbeef"})
	r := httptest.NewRequest(http.MethodPost, "/api/soc/admin/erase", strings.NewReader(string(body)))
	w := httptest.NewRecorder()
	srv.handleAdminEraseTenant(w, r)
	if w.Code != http.StatusForbidden {
		t.Fatalf("unsigned/forged request must be 403, got %d", w.Code)
	}
}
