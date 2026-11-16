package auth

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"
)

type ctxKey string

const claimsKey ctxKey = "jwt_claims"

// JWTMiddleware validates Bearer tokens on protected routes.
type JWTMiddleware struct {
	secret           []byte
	resolvePrincipal func(*Claims) (*Claims, error)
	// PublicPaths are exempt from auth (e.g., /health, /api/auth/login).
	PublicPaths map[string]bool
}

// NewJWTMiddleware creates JWT middleware with the given secret.
func NewJWTMiddleware(secret []byte) *JWTMiddleware {
	return &JWTMiddleware{
		secret: secret,
		PublicPaths: map[string]bool{
			"/health":                         true,
			"/healthz":                        true,
			"/readyz":                         true,
			"/metrics":                        true,
			"/api/auth/login":                 true,
			"/api/auth/logout":                true,
			"/api/auth/refresh":               true,
			"/api/auth/register":              true,
			"/api/auth/verify":                true,
			"/api/auth/plans":                 true,
			"/api/auth/demo":                  true,
			"/api/billing/webhook":            true, // public webhook endpoint
			"/api/v1/scan":                    true, // public demo scanner
			"/api/v1/usage":                   true, // public usage/quota check
			"/api/waitlist":                   true, // public waitlist signup
			"/api/v1/soc/events":              true, // sensor ingest (PSK auth inside ingestEvent)
			"/api/v1/soc/events/batch":        true, // sensor batch ingest (PSK auth inside ingestEvent)
			"/api/soc/sensors/heartbeat":      true, // sensor heartbeat (PSK auth)
			"/api/soc/admin/erase":            true, // signed Ed25519 service channel
			"/api/soc/admin/provision-tenant": true, // signed Ed25519 service channel
			"/api/soc/admin/sso-exchange":     true, // signed Ed25519 service channel
		},
	}
}

// Middleware wraps an http.Handler with JWT validation.
func (m *JWTMiddleware) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Already authenticated upstream (e.g. APIKeyMiddleware resolved an stx_
		// API key into claims)? Skip JWT — do NOT re-verify the API key as a JWT
		// (which would fail and 401). Review 14.06 round-2.
		if claims := GetClaims(r.Context()); claims != nil {
			if m.resolvePrincipal != nil {
				resolved, err := m.resolvePrincipal(claims)
				if err != nil {
					status := http.StatusUnauthorized
					if err == ErrStoreUnavailable {
						status = http.StatusServiceUnavailable
					}
					writeAuthError(w, status, "principal unavailable")
					return
				}
				r = r.WithContext(context.WithValue(r.Context(), claimsKey, resolved))
			}
			next.ServeHTTP(w, r)
			return
		}
		// Public paths require no auth, but do a BEST-EFFORT optional parse so a
		// present valid JWT (cookie/Bearer) still populates claims for
		// public-but-personalized handlers — e.g. /api/v1/scan needs the tenant
		// for SOC auto-feed (R3) and plan-aware quota. Invalid/absent → anonymous.
		if m.PublicPaths[r.URL.Path] {
			// These endpoints validate their own credentials or clear cookies.
			// An obsolete access cookie must not prevent reauthentication,
			// refresh into the current lower role, or logout.
			if r.URL.Path == "/api/auth/login" || r.URL.Path == "/api/auth/logout" || r.URL.Path == "/api/auth/refresh" {
				next.ServeHTTP(w, r)
				return
			}

			if claims := m.optionalJWTClaims(r); claims != nil {
				if m.resolvePrincipal != nil {
					resolved, err := m.resolvePrincipal(claims)
					if err != nil {
						status := http.StatusUnauthorized
						if err == ErrStoreUnavailable {
							status = http.StatusServiceUnavailable
						}
						writeAuthError(w, status, "principal unavailable")
						return
					}
					claims = resolved
				}
				r = r.WithContext(context.WithValue(r.Context(), claimsKey, claims))
			}
			next.ServeHTTP(w, r)
			return
		}

		var tokenStr string
		authHeader := r.Header.Get("Authorization")
		if strings.HasPrefix(authHeader, "Bearer stx_") {
			// Allow API keys via header
			parts := strings.SplitN(authHeader, " ", 2)
			tokenStr = parts[1]
		} else {
			// SEC: H1 - Read token from httpOnly cookie
			cookie, err := r.Cookie("syntrex_token")
			if err != nil || cookie.Value == "" {
				// Fallback to legacy bearer token (for clients that haven't migrated yet or testing)
				if authHeader != "" && strings.HasPrefix(authHeader, "Bearer ") {
					tokenStr = strings.TrimPrefix(authHeader, "Bearer ")
				} else {
					writeAuthError(w, http.StatusUnauthorized, "missing authentication cookie")
					return
				}
			} else {
				tokenStr = cookie.Value
			}
		}

		// SEC: M2 - Validate CSRF Token on mutating requests
		if r.Method == "POST" || r.Method == "PUT" || r.Method == "DELETE" || r.Method == "PATCH" {
			// Exempt API keys from CSRF if they used the header
			if !strings.HasPrefix(authHeader, "Bearer stx_") {
				csrfHeader := r.Header.Get("X-CSRF-Token")
				expectedCSRF := hmacSign([]byte(tokenStr), m.secret)[:32]
				if csrfHeader == "" || csrfHeader != expectedCSRF {
					slog.Warn("CSRF token missing or invalid", "path", r.URL.Path, "remote", r.RemoteAddr)
					writeAuthError(w, http.StatusForbidden, "invalid CSRF token")
					return
				}
			}
		}

		claims, err := Verify(tokenStr, m.secret)
		if err != nil {
			slog.Warn("JWT auth failed",
				"error", err,
				"path", r.URL.Path,
				"remote", r.RemoteAddr,
			)
			if err == ErrExpiredToken {
				writeAuthError(w, http.StatusUnauthorized, "token expired")
			} else {
				writeAuthError(w, http.StatusUnauthorized, "invalid token")
			}
			return
		}

		// SEC-C5: Reject refresh tokens used as access tokens.
		// Only "access" tokens (or legacy tokens without type) can access protected routes.
		if claims.TokenType == "refresh" {
			slog.Warn("refresh token used as access token",
				"sub", claims.Sub,
				"path", r.URL.Path,
				"remote", r.RemoteAddr,
			)
			writeAuthError(w, http.StatusUnauthorized, "access token required — refresh tokens cannot be used for API access")
			return
		}

		if m.resolvePrincipal != nil {
			resolved, err := m.resolvePrincipal(claims)
			if err != nil {
				status := http.StatusUnauthorized
				if err == ErrStoreUnavailable {
					status = http.StatusServiceUnavailable
				}
				writeAuthError(w, status, "principal unavailable")
				return
			}
			claims = resolved
		}

		// Inject claims into context for downstream handlers.
		ctx := context.WithValue(r.Context(), claimsKey, claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// GetClaims extracts JWT claims from request context.
func GetClaims(ctx context.Context) *Claims {
	if c, ok := ctx.Value(claimsKey).(*Claims); ok {
		return c
	}
	return nil
}

// SetClaimsContext injects claims into a context (used by API key auth).
func SetClaimsContext(ctx context.Context, claims *Claims) context.Context {
	return context.WithValue(ctx, claimsKey, claims)
}

// optionalJWTClaims does a best-effort, non-fatal token parse for public paths:
// returns valid ACCESS-token claims if a cookie or non-stx_ Bearer JWT is
// present and valid, else nil. It never writes an error — public paths stay
// public; this only enriches the context when a credential happens to be present.
// (stx_ API keys are handled separately by APIKeyMiddleware.)
func (m *JWTMiddleware) optionalJWTClaims(r *http.Request) *Claims {
	var tokenStr string
	authHeader := r.Header.Get("Authorization")
	if cookie, err := r.Cookie("syntrex_token"); err == nil && cookie.Value != "" {
		tokenStr = cookie.Value
	} else if strings.HasPrefix(authHeader, "Bearer ") && !strings.HasPrefix(authHeader, "Bearer stx_") {
		tokenStr = strings.TrimPrefix(authHeader, "Bearer ")
	}
	if tokenStr == "" {
		return nil
	}
	claims, err := Verify(tokenStr, m.secret)
	if err != nil || claims == nil || claims.TokenType == "refresh" {
		return nil
	}
	return claims
}

func writeAuthError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("WWW-Authenticate", `Bearer realm="sentinel-soc"`)
	w.WriteHeader(status)
	// SEC-MED4: Use json.NewEncoder instead of string concatenation
	// to prevent JSON injection via special characters in error messages.
	json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
