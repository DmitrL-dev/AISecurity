// Package auth provides JWT authentication for the SOC HTTP API.
// Uses HMAC-SHA256 (HS256) with configurable secret.
// Zero external dependencies — pure Go stdlib.
package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

// Standard JWT errors.
var (
	ErrInvalidToken    = errors.New("auth: invalid token")
	ErrExpiredToken    = errors.New("auth: token expired")
	ErrInvalidSecret   = errors.New("auth: secret too short (min 32 bytes)")
	ErrWrongTokenType  = errors.New("auth: wrong token type")
)

// Claims represents JWT payload.
type Claims struct {
	Sub       string `json:"sub"`                   // Subject (username or user ID)
	Role      string `json:"role"`                  // RBAC role: admin, operator, analyst, viewer
	TenantID  string `json:"tenant_id,omitempty"`   // Multi-tenant isolation
	TokenType    string `json:"token_type,omitempty"` // "access" or "refresh"
	Impersonator string `json:"impersonator,omitempty"` // SEC-V12: Superadmin sub that generated this token
	Exp          int64  `json:"exp"`                   // Expiration (Unix timestamp)
	Iat          int64  `json:"iat"`                   // Issued at
	Iss          string `json:"iss,omitempty"`         // Issuer
}

// IsExpired returns true if the token has expired.
func (c Claims) IsExpired() bool {
	return time.Now().Unix() > c.Exp
}

// header is the JWT header (always HS256).
var jwtHeader = base64URLEncode([]byte(`{"alg":"HS256","typ":"JWT"}`))

// Sign creates a JWT token string from claims.
func Sign(claims Claims, secret []byte) (string, error) {
	if len(secret) < 32 {
		return "", ErrInvalidSecret
	}

	if claims.Iat == 0 {
		claims.Iat = time.Now().Unix()
	}
	if claims.Iss == "" {
		claims.Iss = "sentinel-soc"
	}

	payload, err := json.Marshal(claims)
	if err != nil {
		return "", fmt.Errorf("auth: marshal claims: %w", err)
	}

	encodedPayload := base64URLEncode(payload)
	signingInput := jwtHeader + "." + encodedPayload
	signature := hmacSign([]byte(signingInput), secret)

	return signingInput + "." + signature, nil
}

// Verify validates a JWT token string and returns the claims.
func Verify(tokenStr string, secret []byte) (*Claims, error) {
	parts := strings.SplitN(tokenStr, ".", 3)
	if len(parts) != 3 {
		return nil, ErrInvalidToken
	}

	signingInput := parts[0] + "." + parts[1]
	expectedSig := hmacSign([]byte(signingInput), secret)

	if !hmac.Equal([]byte(parts[2]), []byte(expectedSig)) {
		return nil, ErrInvalidToken
	}

	payload, err := base64URLDecode(parts[1])
	if err != nil {
		return nil, fmt.Errorf("%w: bad payload encoding", ErrInvalidToken)
	}

	var claims Claims
	if err := json.Unmarshal(payload, &claims); err != nil {
		return nil, fmt.Errorf("%w: bad payload JSON", ErrInvalidToken)
	}

	if claims.IsExpired() {
		return nil, ErrExpiredToken
	}

	return &claims, nil
}

// NewAccessToken creates a short-lived access token (15 min default).
func NewAccessToken(subject, role string, secret []byte, ttl time.Duration) (string, error) {
	if ttl == 0 {
		ttl = 15 * time.Minute
	}
	return Sign(Claims{
		Sub:       subject,
		Role:      role,
		TokenType: "access",
		Exp:       time.Now().Add(ttl).Unix(),
	}, secret)
}

// NewRefreshToken creates a long-lived refresh token (7 days default).
func NewRefreshToken(subject, role string, secret []byte, ttl time.Duration) (string, error) {
	if ttl == 0 {
		ttl = 7 * 24 * time.Hour
	}
	return Sign(Claims{
		Sub:       subject,
		Role:      role,
		TokenType: "refresh",
		Exp:       time.Now().Add(ttl).Unix(),
	}, secret)
}

// --- base64url helpers (RFC 7515) ---

func base64URLEncode(data []byte) string {
	return base64.RawURLEncoding.EncodeToString(data)
}

func base64URLDecode(s string) ([]byte, error) {
	return base64.RawURLEncoding.DecodeString(s)
}

func hmacSign(data, secret []byte) string {
	mac := hmac.New(sha256.New, secret)
	mac.Write(data)
	return base64URLEncode(mac.Sum(nil))
}
