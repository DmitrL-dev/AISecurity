package httpserver

import (
	"crypto/hmac"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// Role defines access level for RBAC.
type Role string

const (
	RoleSuperadmin Role = "superadmin" // Cross-tenant super-user (JWT role)
	RoleAdmin      Role = "admin"      // Full access: read + write + config
	RoleAnalyst    Role = "analyst"    // Read + write (ingest, verdict)
	RoleViewer     Role = "viewer"     // Read-only
	RoleSensor     Role = "sensor"     // Ingest only (POST events + heartbeat)
	RoleExternal   Role = "external"   // Kill Chain + dashboard only
)

// APIKey represents a registered API key with role.
type APIKey struct {
	Key       string    `json:"key"`
	Name      string    `json:"name"`
	Role      Role      `json:"role"`
	CreatedAt time.Time `json:"created_at"`
	LastUsed  time.Time `json:"last_used,omitempty"`
	Active    bool      `json:"active"`
}

// RBACConfig holds authentication configuration.
type RBACConfig struct {
	Enabled bool              `yaml:"enabled" json:"enabled"`
	Keys    map[string]APIKey // key hash → APIKey
}

// RBACMiddleware provides role-based access control for HTTP endpoints (§17).
type RBACMiddleware struct {
	mu     sync.RWMutex
	config RBACConfig
	keys   map[string]*APIKey // raw key → APIKey
}

// NewRBACMiddleware creates RBAC middleware. If not enabled, all requests pass through.
func NewRBACMiddleware(config RBACConfig) *RBACMiddleware {
	m := &RBACMiddleware{
		config: config,
		keys:   make(map[string]*APIKey),
	}
	return m
}

// RegisterKey adds an API key with a role.
func (m *RBACMiddleware) RegisterKey(name, key string, role Role) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.keys[key] = &APIKey{
		Key:       key,
		Name:      name,
		Role:      role,
		CreatedAt: time.Now(),
		Active:    true,
	}
}

// RevokeKey deactivates an API key.
func (m *RBACMiddleware) RevokeKey(key string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if k, ok := m.keys[key]; ok {
		k.Active = false
	}
}

// ListKeys returns all registered keys (with keys masked).
func (m *RBACMiddleware) ListKeys() []APIKey {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]APIKey, 0, len(m.keys))
	for _, k := range m.keys {
		masked := *k
		if len(masked.Key) > 8 {
			masked.Key = masked.Key[:4] + "..." + masked.Key[len(masked.Key)-4:]
		}
		result = append(result, masked)
	}
	return result
}

// Require returns middleware that enforces minimum role for the endpoint.
func (m *RBACMiddleware) Require(minRole Role, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !m.config.Enabled {
			// Review 13.06 (audit A2 CRITICAL): the API-key system is disabled by
			// default, but role separation must still hold. When the caller IS
			// JWT-authenticated, enforce the required role here (fail closed) so a
			// low-privilege token cannot reach admin routes. Callers with NO claims
			// (e.g. sensor ingest on a JWT-public path) pass through unchanged, so
			// keyless ingest is not broken. This closes the role-collapse without
			// requiring the full API-key rollout.
			if claims := auth.GetClaims(r.Context()); claims != nil && !hasPermission(Role(claims.Role), minRole) {
				writeError(w, http.StatusForbidden, "insufficient role for this endpoint")
				return
			}
			next(w, r)
			return
		}

		// Check if the user is already authenticated via JWT (UI session)
		jwtClaims := auth.GetClaims(r.Context())
		if jwtClaims != nil && hasPermission(Role(jwtClaims.Role), minRole) {
			next(w, r)
			return
		}

		// Extract API key from Authorization header or query param
		key := extractAPIKey(r)
		if key == "" {
			writeError(w, http.StatusUnauthorized, "missing API key: use Authorization: Bearer <key>")
			return
		}

		// Lookup key using constant-time comparison to prevent timing oracle.
		// A plain map lookup reveals key existence via variable-time hash probing.
		//
		// CONCURRENCY: snapshot the fields we need (Active, Role) WHILE holding the
		// read lock. The *APIKey is shared mutable state — RevokeKey mutates .Active
		// under the write lock — so reading apiKey.Active/.Role after RUnlock is a
		// data race (write at RevokeKey vs unlocked read here). Copy under the lock.
		m.mu.RLock()
		var apiKey *APIKey
		var keyActive bool
		var keyRole Role
		keyBytes := []byte(key)
		for storedKey, candidate := range m.keys {
			// HMAC comparison: constant-time regardless of match position
			if hmac.Equal(keyBytes, []byte(storedKey)) {
				apiKey = candidate
				keyActive = candidate.Active
				keyRole = candidate.Role
				break
			}
		}
		m.mu.RUnlock()

		if apiKey == nil || !keyActive {
			writeError(w, http.StatusUnauthorized, "invalid or revoked API key")
			return
		}

		// Check role hierarchy
		if !hasPermission(keyRole, minRole) {
			writeError(w, http.StatusForbidden, "insufficient permissions: requires "+string(minRole))
			return
		}

		// Update last used
		m.mu.Lock()
		apiKey.LastUsed = time.Now()
		m.mu.Unlock()

		next(w, r)
	}
}

// extractAPIKey gets the API key from Authorization header or X-API-Key header.
// Query parameter auth is intentionally NOT supported (credential leak vector).
func extractAPIKey(r *http.Request) string {
	// Try Authorization: Bearer <key>
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		return strings.TrimPrefix(auth, "Bearer ")
	}
	// Try X-API-Key header
	if key := r.Header.Get("X-API-Key"); key != "" {
		return key
	}
	// SECURITY: Query parameter auth removed — keys in URLs leak via
	// server logs, Referer headers, browser history, and CDN logs.
	return ""
}

// hasPermission checks if userRole >= requiredRole in the hierarchy.
// Default-deny: undefined roles map to 0 and are rejected.
func hasPermission(userRole, requiredRole Role) bool {
	hierarchy := map[Role]int{
		RoleSuperadmin: 200,
		RoleAdmin:      100,
		RoleAnalyst:    50,
		RoleViewer:     30,
		RoleSensor:     20,
		RoleExternal:   10,
	}
	userLevel, userOK := hierarchy[userRole]
	reqLevel, reqOK := hierarchy[requiredRole]
	// Reject if either role is undefined (defense against typos / injection)
	if !userOK || !reqOK {
		return false
	}
	return userLevel >= reqLevel
}
