package httpserver

import (
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// Variant A tenant-provisioning admin channel (owner-decided 2026-06-17).
//
// spectorn is the billing/identity authority: on signup/upgrade it PROVISIONS the
// customer's gomcp SOC tenant and syncs its plan to the purchased tier — one
// identity, no separate gomcp signup. Same asymmetric trust model as the erasure
// channel (erasure_admin.go): spectorn SIGNS each request with its Ed25519 private
// key; gomcp holds ONLY the public half and can verify but never forge. The
// canonical message is DOMAIN-SEPARATED from erasure ("syntrex-soc-provision" vs
// "syntrex-soc-erase") so a captured signature for one operation can never be
// replayed as the other. Provisioning deliberately uses a distinct service key
// from erasure/SSO so channels can rotate and fail closed independently.
//
//   - INTERNAL-only: the SOC API binds 127.0.0.1 behind nginx; nginx must NOT
//     proxy /api/soc/admin/* — no public attack surface.
//   - Anti-replay: timestamp (TTL window) + per-request nonce, in-memory cache.
//   - Fail-closed: with no public key configured the endpoint is disabled.
//   - Kill-switch: SOC_PROVISION_DISABLED=1 hard-disables provisioning.
//   - Idempotent: the spectorn tenant_id is the gomcp tenant SLUG, so a repeat is
//     an upsert (create, or update-plan) — never a duplicate.
//
// Provisioning a tenant is NOT quota enforcement: it makes the tenant exist with
// the right plan so the gateway->SOC feed and tier-aware limits are correct.
// Monthly caps stay OFF until pricing is turned on (owner decision #6).

const (
	provisionClockSkew       = 60 * time.Second
	provisionNonceTTL        = 5 * time.Minute
	provisionCanonicalPrefix = "syntrex-soc-provision\nv1\n"
	provisionMaxNonceCache   = 100_000
)

// provisionVerifier verifies Ed25519-signed tenant-provisioning requests. Holds
// only public keys.
type provisionVerifier struct {
	pubkeys   []ed25519.PublicKey
	mu        sync.Mutex
	seen      map[string]time.Time // nonce -> first-seen (replay cache)
	lastPrune time.Time            // amortize the O(n) prune scan (mega-review 17.06)
}

// newProvisionVerifier loads verify key(s) from SOC_ADMIN_PROVISION_PUBKEY only.
// It does not fall back to SOC_ADMIN_ERASURE_PUBKEY; provisioning has a separate
// service key. Comma-separated hex
// Ed25519 public keys (rotation overlap). Empty → disabled, endpoint fails closed.
func newProvisionVerifier() *provisionVerifier {
	v := &provisionVerifier{seen: make(map[string]time.Time)}
	raw := os.Getenv("SOC_ADMIN_PROVISION_PUBKEY")
	for _, h := range strings.Split(raw, ",") {
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		}
		b, err := hex.DecodeString(h)
		if err != nil || len(b) != ed25519.PublicKeySize {
			slog.Warn("provision: ignoring malformed pubkey entry")
			continue
		}
		v.pubkeys = append(v.pubkeys, ed25519.PublicKey(b))
	}
	return v
}

func (v *provisionVerifier) enabled() bool { return v != nil && len(v.pubkeys) > 0 }

type provisionRequest struct {
	TenantID  string `json:"tenant_id"` // spectorn tenant id → gomcp tenant slug
	PlanID    string `json:"plan_id"`   // gomcp plan: free|starter|professional|enterprise
	Name      string `json:"name"`      // display name (optional; defaults to tenant_id)
	TS        int64  `json:"ts"`        // unix seconds
	Nonce     string `json:"nonce"`     // per-request random
	Signature string `json:"signature"` // hex Ed25519 signature over the canonical message
}

// provisionCanonicalMessage is the EXACT byte string both the signer (spectorn,
// Rust) and the verifier (gomcp, Go) construct — domain-separated, versioned,
// newline-delimited. Pinned by an interop test on both sides.
func provisionCanonicalMessage(tenantID, planID string, ts int64, nonce string) []byte {
	return []byte(provisionCanonicalPrefix + tenantID + "\n" + planID + "\n" + strconv.FormatInt(ts, 10) + "\n" + nonce)
}

func (v *provisionVerifier) verify(req provisionRequest, now time.Time) error {
	if !v.enabled() {
		return errProvisionDisabled
	}
	if req.TenantID == "" || req.PlanID == "" || req.Nonce == "" {
		return errProvisionMalformed
	}
	// Printable-ASCII fields cannot inject the canonical-message newline delimiter
	// (tenant ids are server-issued slugs/UUIDs, plan ids a fixed set, nonces hex).
	if !erasureFieldClean(req.TenantID) || !erasureFieldClean(req.PlanID) || !erasureFieldClean(req.Nonce) {
		return errProvisionMalformed
	}
	skew := now.Unix() - req.TS
	if skew < 0 {
		skew = -skew
	}
	if skew > int64(provisionClockSkew.Seconds()) {
		return errProvisionStale
	}
	sig, err := hex.DecodeString(req.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errProvisionBadSig
	}
	msg := provisionCanonicalMessage(req.TenantID, req.PlanID, req.TS, req.Nonce)
	verified := false
	for _, pk := range v.pubkeys {
		if ed25519.Verify(pk, msg, sig) {
			verified = true
			break
		}
	}
	if !verified {
		return errProvisionBadSig
	}
	// Replay guard — only after the signature is proven.
	v.mu.Lock()
	defer v.mu.Unlock()
	// Amortize pruning: a full O(n) scan on every request serializes the channel
	// under load. Eviction-when-full bounds the cache regardless, and a nonce
	// lingering slightly past TTL only STRENGTHENS replay protection (mega-review
	// 17.06). Scan at most once per interval.
	if now.Sub(v.lastPrune) >= 30*time.Second {
		v.pruneLocked(now)
		v.lastPrune = now
	}
	if _, dup := v.seen[req.Nonce]; dup {
		return errProvisionReplay
	}
	if len(v.seen) >= provisionMaxNonceCache {
		v.evictOldestLocked()
	}
	v.seen[req.Nonce] = now
	return nil
}

func (v *provisionVerifier) evictOldestLocked() {
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

func (v *provisionVerifier) pruneLocked(now time.Time) {
	for n, t := range v.seen {
		if now.Sub(t) > provisionNonceTTL {
			delete(v.seen, n)
		}
	}
}

var (
	errProvisionDisabled  = erasureErr("provision endpoint disabled")
	errProvisionMalformed = erasureErr("missing tenant_id, plan_id or nonce")
	errProvisionStale     = erasureErr("timestamp outside allowed window")
	errProvisionBadSig    = erasureErr("signature verification failed")
	errProvisionReplay    = erasureErr("replayed nonce")
	// Slug collides with a self-service (non-spectorn-provisioned) tenant — the
	// signed channel refuses to touch it (mega-review 17.06, slug squatting).
	errProvisionSlugConflict = erasureErr("tenant slug owned by a non-provisioned tenant")
)

func provisionKillSwitch() bool { return os.Getenv("SOC_PROVISION_DISABLED") == "1" }

// handleAdminProvisionTenant fulfils a signed Variant-A provisioning request.
// INTERNAL endpoint (nginx must not proxy /api/soc/admin/*) — authenticated by
// Ed25519 signature, not user RBAC.
func (s *Server) handleAdminProvisionTenant(w http.ResponseWriter, r *http.Request) {
	if provisionKillSwitch() {
		writeError(w, http.StatusServiceUnavailable, "tenant provisioning temporarily disabled")
		return
	}
	limitBody(w, r)
	defer r.Body.Close()

	var req provisionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := s.provisionVerifier.verify(req, time.Now()); err != nil {
		slog.Warn("provision request rejected", "tenant", req.TenantID, "reason", err.Error())
		writeError(w, http.StatusForbidden, "provision request not authorized")
		return
	}
	// Defense in depth: the plan id must be a real plan (verify only checks non-empty).
	if _, ok := auth.DefaultPlans[req.PlanID]; !ok {
		writeError(w, http.StatusBadRequest, "unknown plan_id")
		return
	}

	created, err := s.provisionTenant(req.TenantID, req.PlanID, req.Name)
	if err != nil {
		if errors.Is(err, errProvisionSlugConflict) {
			slog.Warn("provision refused: slug owned by a non-provisioned tenant", "tenant", req.TenantID)
			writeError(w, http.StatusConflict, "tenant slug not available for provisioning")
			return
		}
		writeError(w, http.StatusInternalServerError, "provision failed: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"tenant_id":   req.TenantID,
		"plan_id":     req.PlanID,
		"created":     created,
		"provisioned": true,
	})
}

// provisionTenant upserts a gomcp tenant keyed by slug == spectorn tenant_id:
// existing → UpdatePlan (if the tier changed); absent → CreateTenant. Returns
// whether a new tenant was created. The owner user is left empty — spectorn is the
// identity authority and human SSO is a later layer; the tenant RECORD + plan is
// what the gateway->SOC feed and tier-aware limits need now.
func (s *Server) provisionTenant(spectornTenantID, planID, name string) (bool, error) {
	if s.tenantStore == nil {
		return false, fmt.Errorf("tenant store unavailable")
	}
	if existing, err := s.tenantStore.GetTenantBySlug(spectornTenantID); err == nil && existing != nil {
		// SEC (mega-review 17.06): act ONLY on tenants this signed channel itself
		// created. A spectorn-provisioned tenant has an EMPTY owner; a self-service
		// tenant (public register) has a real owner. Refuse to upgrade a self-service
		// tenant whose slug collides with a spectorn tenant_id — defense-in-depth
		// behind the register-side namespace reservation.
		if existing.OwnerUserID != "" {
			return false, errProvisionSlugConflict
		}
		if existing.PlanID != planID {
			if err := s.tenantStore.UpdatePlan(existing.ID, planID); err != nil {
				return false, err
			}
		}
		return false, nil
	}
	if name == "" {
		name = spectornTenantID
	}
	if _, err := s.tenantStore.CreateTenant(name, spectornTenantID, "", planID); err != nil {
		// Race: another provision created it between our lookup and create. Treat
		// as the update path so the call stays idempotent.
		if errors.Is(err, auth.ErrTenantExists) {
			if existing, e2 := s.tenantStore.GetTenantBySlug(spectornTenantID); e2 == nil && existing != nil {
				if existing.OwnerUserID != "" {
					return false, errProvisionSlugConflict
				}
				if existing.PlanID != planID {
					if e3 := s.tenantStore.UpdatePlan(existing.ID, planID); e3 != nil {
						return false, e3
					}
				}
				return false, nil
			}
		}
		return false, err
	}
	return true, nil
}
