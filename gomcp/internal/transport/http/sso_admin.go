package httpserver

import (
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// Variant A single sign-on — token exchange (owner-decided 2026-06-17).
//
// Completes "one identity, single login": a user already authenticated to
// spectorn exchanges a SHORT-LIVED Ed25519-signed identity assertion for a normal
// gomcp SOC JWT, instead of a separate gomcp login. Same asymmetric trust model as
// the erasure/provision channels (spectorn signs, gomcp verifies with the public
// key), domain-separated ("syntrex-soc-sso"). gomcp's existing JWT auth stays the
// single source of truth for every SOC request — this endpoint only MINTS that JWT
// after verifying the assertion, so no downstream auth changes.
//
//   - INTERNAL-only: lives under /api/soc/admin/* (nginx must NOT proxy it); the
//     spectorn control plane calls it server-to-server.
//   - Anti-replay: timestamp (TTL) + per-request nonce.
//   - Fail-closed: no public key configured → disabled. Kill-switch SOC_SSO_DISABLED=1.
//   - Least privilege: mints a TENANT-SCOPED "admin" token for the caller's OWN
//     tenant (RBAC enforces tenant isolation). NEVER superadmin (cross-tenant).
//   - The tenant must already be provisioned (slug == spectorn tenant_id); else 404.

const (
	ssoClockSkew       = 60 * time.Second
	ssoNonceTTL        = 5 * time.Minute
	ssoCanonicalPrefix = "syntrex-soc-sso\nv1\n"
	ssoMaxNonceCache   = 100_000
	ssoTokenTTL        = time.Hour
)

// ssoVerifier verifies Ed25519-signed SSO identity assertions. Holds only public keys.
type ssoVerifier struct {
	pubkeys   []ed25519.PublicKey
	mu        sync.Mutex
	seen      map[string]time.Time // nonce -> first-seen (replay cache)
	lastPrune time.Time            // amortize the O(n) prune scan (mega-review 17.06)
}

// newSSOVerifier loads verify key(s) from SOC_ADMIN_SSO_PUBKEY only.
// It does not fall back to SOC_ADMIN_ERASURE_PUBKEY; SSO has a separate service key.
func newSSOVerifier() *ssoVerifier {
	v := &ssoVerifier{seen: make(map[string]time.Time)}
	raw := os.Getenv("SOC_ADMIN_SSO_PUBKEY")
	for _, h := range strings.Split(raw, ",") {
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		}
		b, err := hex.DecodeString(h)
		if err != nil || len(b) != ed25519.PublicKeySize {
			slog.Warn("sso: ignoring malformed pubkey entry")
			continue
		}
		v.pubkeys = append(v.pubkeys, ed25519.PublicKey(b))
	}
	return v
}

func (v *ssoVerifier) enabled() bool { return v != nil && len(v.pubkeys) > 0 }

type ssoExchangeRequest struct {
	TenantID  string `json:"tenant_id"` // spectorn tenant id (== gomcp tenant slug)
	Sub       string `json:"sub"`       // authenticated subject — currently the spectorn TENANT id (SOC audit is tenant-granular until per-user SSO; mega-review 17.06)
	TS        int64  `json:"ts"`
	Nonce     string `json:"nonce"`
	Signature string `json:"signature"`
}

func ssoCanonicalMessage(tenantID, sub string, ts int64, nonce string) []byte {
	return []byte(ssoCanonicalPrefix + tenantID + "\n" + sub + "\n" + strconv.FormatInt(ts, 10) + "\n" + nonce)
}

func (v *ssoVerifier) verify(req ssoExchangeRequest, now time.Time) error {
	if !v.enabled() {
		return errSSODisabled
	}
	if req.TenantID == "" || req.Sub == "" || req.Nonce == "" {
		return errSSOMalformed
	}
	if !erasureFieldClean(req.TenantID) || !erasureFieldClean(req.Sub) || !erasureFieldClean(req.Nonce) {
		return errSSOMalformed
	}
	skew := now.Unix() - req.TS
	if skew < 0 {
		skew = -skew
	}
	if skew > int64(ssoClockSkew.Seconds()) {
		return errSSOStale
	}
	sig, err := hex.DecodeString(req.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errSSOBadSig
	}
	msg := ssoCanonicalMessage(req.TenantID, req.Sub, req.TS, req.Nonce)
	verified := false
	for _, pk := range v.pubkeys {
		if ed25519.Verify(pk, msg, sig) {
			verified = true
			break
		}
	}
	if !verified {
		return errSSOBadSig
	}
	v.mu.Lock()
	defer v.mu.Unlock()
	// Amortize pruning (mega-review 17.06): bounded by eviction-when-full; a nonce
	// lingering slightly past TTL only strengthens replay protection.
	if now.Sub(v.lastPrune) >= 30*time.Second {
		v.pruneLocked(now)
		v.lastPrune = now
	}
	if _, dup := v.seen[req.Nonce]; dup {
		return errSSOReplay
	}
	if len(v.seen) >= ssoMaxNonceCache {
		v.evictOldestLocked()
	}
	v.seen[req.Nonce] = now
	return nil
}

func (v *ssoVerifier) evictOldestLocked() {
	var oldestNonce string
	var oldestAt time.Time
	first := true
	for n, t := range v.seen {
		if first || t.Before(oldestAt) {
			oldestNonce, oldestAt, first = n, t, false
		}
	}
	if !first {
		delete(v.seen, oldestNonce)
	}
}

func (v *ssoVerifier) pruneLocked(now time.Time) {
	for n, t := range v.seen {
		if now.Sub(t) > ssoNonceTTL {
			delete(v.seen, n)
		}
	}
}

var (
	errSSODisabled  = erasureErr("sso endpoint disabled")
	errSSOMalformed = erasureErr("missing tenant_id, sub or nonce")
	errSSOStale     = erasureErr("timestamp outside allowed window")
	errSSOBadSig    = erasureErr("signature verification failed")
	errSSOReplay    = erasureErr("replayed nonce")
)

func ssoKillSwitch() bool { return os.Getenv("SOC_SSO_DISABLED") == "1" }

// handleSSOExchange verifies a signed spectorn identity assertion and mints a
// normal, tenant-scoped gomcp SOC JWT for the provisioned tenant. INTERNAL
// endpoint — authenticated by Ed25519 signature, not user RBAC.
func (s *Server) handleSSOExchange(w http.ResponseWriter, r *http.Request) {
	if ssoKillSwitch() {
		writeError(w, http.StatusServiceUnavailable, "sso temporarily disabled")
		return
	}
	limitBody(w, r)
	defer r.Body.Close()

	var req ssoExchangeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := s.ssoVerifier.verify(req, time.Now()); err != nil {
		slog.Warn("sso exchange rejected", "tenant", req.TenantID, "reason", err.Error())
		writeError(w, http.StatusForbidden, "sso request not authorized")
		return
	}
	if s.tenantStore == nil {
		writeError(w, http.StatusServiceUnavailable, "sso unavailable")
		return
	}
	// Resolve the gomcp tenant provisioned for this spectorn tenant (variant A).
	tenant, err := s.tenantStore.GetTenantBySlug(req.TenantID)
	if err != nil || tenant == nil || !tenant.Active {
		writeError(w, http.StatusNotFound, "tenant not provisioned")
		return
	}
	// SEC (mega-review 17.06, slug squatting): only mint for spectorn-PROVISIONED
	// tenants (empty owner). A self-service tenant (real owner) that happens to share
	// the slug must NEVER receive an SSO-minted admin JWT — that would bind a
	// victim's session into an attacker-owned tenant. Return the same 404 as
	// "not provisioned" so this is not a tenant-existence oracle.
	if tenant.OwnerUserID != "" {
		slog.Warn("sso exchange refused: slug owned by a non-provisioned tenant", "tenant", req.TenantID)
		writeError(w, http.StatusNotFound, "tenant not provisioned")
		return
	}
	if len(s.jwtSecret) < 32 {
		writeError(w, http.StatusServiceUnavailable, "sso unavailable (jwt signing key not configured)")
		return
	}
	exp := time.Now().Add(ssoTokenTTL)
	token, err := auth.Sign(auth.Claims{
		Sub:       req.Sub,
		Role:      "admin", // tenant-scoped admin of their OWN tenant; RBAC enforces isolation. NEVER superadmin.
		TenantID:  tenant.ID,
		TokenType: "access",
		Exp:       exp.Unix(),
	}, s.jwtSecret)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "token mint failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"token":      token,
		"tenant_id":  tenant.ID,
		"token_type": "access",
		"expires_at": exp.Unix(),
	})
}
