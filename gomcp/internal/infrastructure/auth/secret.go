package auth

import (
	"crypto/rand"
	"encoding/hex"
	"log/slog"
	"os"
)

// MinSigningSecretBytes is the minimum accepted JWT signing-secret length.
const MinSigningSecretBytes = 32

// ResolveSigningSecret returns the JWT signing secret for the SOC/admin API.
//
// Review 13.06 (audit CRITICAL — committed-key auth bypass): this MUST NEVER
// fall back to a source-committed constant or a space-padded password. A signing
// key that is knowable from the source tree (or derivable from a short password)
// lets anyone forge a valid superadmin JWT for any tenant and take over the
// whole multi-tenant API. The Dockerfile starts the API by default, so the old
// hardcoded fallback shipped a public admin key.
//
// Precedence:
//  1. SOC_JWT_SECRET env, if >= 32 bytes — the production path (stable tokens).
//  2. otherwise a cryptographically-random EPHEMERAL secret, with a loud warning.
//     Tokens will not survive a restart, which keeps local dev/demo working
//     WITHOUT ever shipping a predictable key. Production must set SOC_JWT_SECRET.
func ResolveSigningSecret() []byte {
	raw := os.Getenv("SOC_JWT_SECRET")
	if len(raw) >= MinSigningSecretBytes {
		return []byte(raw)
	}
	if raw != "" {
		slog.Warn("SOC_JWT_SECRET is set but shorter than the 32-byte minimum — ignoring it and generating an ephemeral key",
			"got_len", len(raw), "min", MinSigningSecretBytes)
	}
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		// crypto/rand must not fail; degrading to a guessable key is unacceptable.
		panic("auth: cannot generate a random JWT signing secret: " + err.Error())
	}
	slog.Warn("SOC_JWT_SECRET not configured — using an EPHEMERAL random signing key; " +
		"JWT tokens will NOT survive a restart. Set SOC_JWT_SECRET (>=32 bytes) for production.")
	return []byte(hex.EncodeToString(buf)) // 64 hex chars
}
