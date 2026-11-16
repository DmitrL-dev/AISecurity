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
)

// GDPR Art.17 tenant-erasure admin channel (Review 14.06 round-5, owner-decided).
//
// Security design (the most-robust practical option for the co-located deploy):
//   - INTERNAL-only: the SOC API binds 127.0.0.1 behind nginx; nginx must NOT
//     proxy /api/soc/admin/* — this endpoint has no public attack surface.
//   - ASYMMETRIC auth: the caller (spectorn control-plane) SIGNS each request
//     with its Ed25519 private key; gomcp holds ONLY the public key and can
//     verify but NEVER forge an erasure. A leaked verify-key is useless.
//   - Anti-replay: a request binds a timestamp (TTL window) + a nonce; replays
//     are rejected from an in-memory nonce cache.
//   - Fail-closed: with no public key configured the endpoint is disabled.
//   - Kill-switch: SOC_ERASURE_DISABLED=1 hard-disables erasure instantly.
//   - Key rotation: SOC_ADMIN_ERASURE_PUBKEY accepts TWO comma-separated keys so
//     a new key can be rolled out before the old is retired (overlap).

const (
	erasureClockSkew       = 60 * time.Second // max |now - request.ts|
	erasureNonceTTL        = 5 * time.Minute  // how long a nonce is remembered
	erasureCanonicalPrefix = "syntrex-soc-erase\nv1\n"
	erasureMaxNonceCache   = 100_000 // hard bound on the replay cache (memory guard)
)

// erasureVerifier verifies Ed25519-signed tenant-erasure requests. Holds only
// public keys.
type erasureVerifier struct {
	pubkeys   []ed25519.PublicKey // 1-2 keys (rotation overlap)
	mu        sync.Mutex
	seen      map[string]time.Time // nonce -> first-seen (replay cache)
	lastPrune time.Time            // amortize the O(n) prune scan (mega-review 17.06)
}

// newErasureVerifier loads the verify key(s) from SOC_ADMIN_ERASURE_PUBKEY
// (comma-separated hex Ed25519 public keys, 32 bytes each). Empty/none → the
// verifier is disabled and the endpoint fails closed.
func newErasureVerifier() *erasureVerifier {
	v := &erasureVerifier{seen: make(map[string]time.Time)}
	for _, h := range strings.Split(os.Getenv("SOC_ADMIN_ERASURE_PUBKEY"), ",") {
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		}
		b, err := hex.DecodeString(h)
		if err != nil || len(b) != ed25519.PublicKeySize {
			slog.Warn("erasure: ignoring malformed SOC_ADMIN_ERASURE_PUBKEY entry")
			continue
		}
		v.pubkeys = append(v.pubkeys, ed25519.PublicKey(b))
	}
	return v
}

func (v *erasureVerifier) enabled() bool { return v != nil && len(v.pubkeys) > 0 }

type erasureRequest struct {
	TenantID  string `json:"tenant_id"`
	TS        int64  `json:"ts"`        // unix seconds
	Nonce     string `json:"nonce"`     // per-request random
	Signature string `json:"signature"` // hex Ed25519 signature over the canonical message
}

// erasureCanonicalMessage is the EXACT byte string both the signer (spectorn,
// Rust) and the verifier (gomcp, Go) construct — it must match byte-for-byte, so
// it is domain-separated, versioned, and newline-delimited (tenant ids contain
// no newline). An interop test pins a fixed (key, inputs) → signature vector.
func erasureCanonicalMessage(tenantID string, ts int64, nonce string) []byte {
	return []byte(erasureCanonicalPrefix + tenantID + "\n" + strconv.FormatInt(ts, 10) + "\n" + nonce)
}

// verify returns nil iff the request is authentic (valid signature from a
// configured key), fresh (within the clock window), and not a replay.
func (v *erasureVerifier) verify(req erasureRequest, now time.Time) error {
	if !v.enabled() {
		return errErasureDisabled
	}
	if req.TenantID == "" || req.Nonce == "" {
		return errErasureMalformed
	}
	// The canonical message is newline-delimited (prefix\ntenant\nts\nnonce). A
	// control char (esp. "\n") in tenant_id/nonce could make the signed bytes
	// ambiguous, so require printable-ASCII fields. (Tenant ids are server-issued
	// slugs/UUIDs and nonces are hex, so this never rejects a legitimate request.)
	if !erasureFieldClean(req.TenantID) || !erasureFieldClean(req.Nonce) {
		return errErasureMalformed
	}
	skew := now.Unix() - req.TS
	if skew < 0 {
		skew = -skew
	}
	if skew > int64(erasureClockSkew.Seconds()) {
		return errErasureStale
	}
	sig, err := hex.DecodeString(req.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errErasureBadSig
	}
	msg := erasureCanonicalMessage(req.TenantID, req.TS, req.Nonce)
	verified := false
	for _, pk := range v.pubkeys {
		if ed25519.Verify(pk, msg, sig) {
			verified = true
			break
		}
	}
	if !verified {
		return errErasureBadSig
	}
	// Replay guard — only after the signature is proven (don't let unsigned input
	// populate the cache).
	v.mu.Lock()
	defer v.mu.Unlock()
	// Amortize pruning (mega-review 17.06): bounded by eviction-when-full; a nonce
	// lingering slightly past TTL only strengthens replay protection.
	if now.Sub(v.lastPrune) >= 30*time.Second {
		v.pruneLocked(now)
		v.lastPrune = now
	}
	if _, dup := v.seen[req.Nonce]; dup {
		return errErasureReplay
	}
	// Memory guard: if the cache is at its bound even after pruning expired entries
	// (i.e. a flood of fresh, validly-signed nonces), evict the oldest to make room
	// rather than growing without limit. The oldest is nearest expiry anyway.
	if len(v.seen) >= erasureMaxNonceCache {
		v.evictOldestLocked()
	}
	v.seen[req.Nonce] = now
	return nil
}

// erasureFieldClean reports whether s is non-empty printable ASCII with no control
// characters (so it cannot inject the canonical-message newline delimiter).
func erasureFieldClean(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] < 0x20 || s[i] > 0x7e {
			return false
		}
	}
	return true
}

// evictOldestLocked removes the single oldest nonce. Caller holds v.mu.
func (v *erasureVerifier) evictOldestLocked() {
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

func (v *erasureVerifier) pruneLocked(now time.Time) {
	for n, t := range v.seen {
		if now.Sub(t) > erasureNonceTTL {
			delete(v.seen, n)
		}
	}
}

// Sentinel errors (kept generic to the client; detail is logged server-side).
var (
	errErasureDisabled  = erasureErr("erasure endpoint disabled")
	errErasureMalformed = erasureErr("missing tenant_id or nonce")
	errErasureStale     = erasureErr("timestamp outside allowed window")
	errErasureBadSig    = erasureErr("signature verification failed")
	errErasureReplay    = erasureErr("replayed nonce")
)

type erasureErr string

func (e erasureErr) Error() string { return string(e) }

func erasureKillSwitch() bool { return os.Getenv("SOC_ERASURE_DISABLED") == "1" }

// handleAdminEraseTenant fulfils a signed GDPR Art.17 erasure request. INTERNAL
// endpoint (nginx must not proxy /api/soc/admin/*) — authenticated by Ed25519
// signature, not user RBAC.
func (s *Server) handleAdminEraseTenant(w http.ResponseWriter, r *http.Request) {
	if erasureKillSwitch() {
		writeError(w, http.StatusServiceUnavailable, "tenant erasure temporarily disabled")
		return
	}
	limitBody(w, r)
	defer r.Body.Close()

	var req erasureRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := s.erasureVerifier.verify(req, time.Now()); err != nil {
		// Generic 403 to the client; the specific reason is logged here.
		slog.Warn("erasure request rejected", "tenant", req.TenantID, "reason", err.Error())
		writeError(w, http.StatusForbidden, "erasure request not authorized")
		return
	}

	rows, err := s.socSvc.EraseTenant(req.TenantID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "erasure failed: "+err.Error())
		return
	}

	// Data-capture flywheel: erase the tenant's training samples too (they are
	// tenant-scoped metadata; GDPR Art.17 covers them). Best-effort — a failure
	// here must not mask the SOC erasure that already succeeded; it is logged and
	// the residual surfaced in the response for the caller to retry/audit.
	var orchRows int64
	if s.orchestratorRepo != nil {
		if n, oErr := s.orchestratorRepo.DeleteByTenant(req.TenantID); oErr != nil {
			slog.Warn("tenant erasure: orchestrator samples not fully erased", "tenant", req.TenantID, "error", oErr)
			writeJSON(w, http.StatusInternalServerError, map[string]any{"tenant_id": req.TenantID, "rows_deleted": rows, "erased": false, "orchestrator_erasure_failed": true})
			return
		} else {
			orchRows = n
		}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"tenant_id":                 req.TenantID,
		"rows_deleted":              rows,
		"orchestrator_rows_deleted": orchRows,
		"erased":                    true,
	})
}
