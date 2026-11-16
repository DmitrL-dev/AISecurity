package auth

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

// LoginRequest is the POST /api/auth/login body.
type LoginRequest struct {
	Email    string `json:"email"`
	Username string `json:"username"` // legacy alias for email
	Password string `json:"password"`
}

type TokenResponse struct {
	CSRFToken string `json:"csrf_token"`
	User      *User  `json:"user"`
}

// setCSRFCookie sets the CSRF token as a non-httpOnly cookie for the Double Submit Cookie pattern.
// SEC-CRIT3: Frontend reads this cookie via document.cookie (instead of localStorage)
// and sends it as X-CSRF-Token header. Backend verifies both match.
// The cookie is SameSite=Strict so cross-origin requests cannot include it.
func setCSRFCookie(w http.ResponseWriter, csrfToken string, maxAge int) {
	http.SetCookie(w, &http.Cookie{
		Name:     "syntrex_csrf",
		Value:    csrfToken,
		Path:     "/",
		HttpOnly: false, // Must be readable by JS for X-CSRF-Token header
		Secure:   true,
		SameSite: http.SameSiteStrictMode,
		MaxAge:   maxAge,
	})
}

// HandleLogin creates an HTTP handler for POST /api/auth/login.
func HandleLogin(store *UserStore, secret []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		var req LoginRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON body")
			return
		}

		// Support both "email" and legacy "username" field.
		// Both fields are decoded from the same body above; the prior
		// implementation declared an empty struct and never decoded into
		// it, so the legacy fallback always resolved to "".
		email := req.Email
		if email == "" {
			email = req.Username
		}

		user, err := store.Authenticate(email, req.Password)
		if err != nil {
			if err == ErrEmailNotVerified {
				writeAuthError(w, http.StatusForbidden, "email not verified — check your inbox for the verification code")
				return
			}
			writeAuthError(w, http.StatusUnauthorized, "invalid credentials")
			return
		}

		accessToken, err := Sign(Claims{
			Sub:       user.Email,
			Role:      user.Role,
			TenantID:  user.TenantID,
			TokenType: "access",
			Exp:       time.Now().Add(15 * time.Minute).Unix(),
		}, secret)
		if err != nil {
			writeAuthError(w, http.StatusInternalServerError, "token generation failed")
			return
		}

		refreshToken, err := Sign(Claims{
			Sub:       user.Email,
			Role:      user.Role,
			TenantID:  user.TenantID,
			TokenType: "refresh",
			Exp:       time.Now().Add(7 * 24 * time.Hour).Unix(),
		}, secret)
		if err != nil {
			writeAuthError(w, http.StatusInternalServerError, "token generation failed")
			return
		}

		// SEC: H1 - Use httpOnly Cookies instead of localStorage
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_token",
			Value:    accessToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   900,
		})
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_refresh",
			Value:    refreshToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   7 * 24 * 3600,
		})

		// SEC: M2 - Generate stateless CSRF token
		csrfToken := hmacSign([]byte(accessToken), secret)[:32]

		// SEC-CRIT3: Set CSRF as cookie (Double Submit Cookie pattern)
		setCSRFCookie(w, csrfToken, 900)

		resp := TokenResponse{
			CSRFToken: csrfToken,
			User:      user,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}
}

// HandleRefresh creates an HTTP handler for POST /api/auth/refresh.
func HandleRefresh(userStore *UserStore, secret []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		// Extract refresh token from cookie
		cookie, err := r.Cookie("syntrex_refresh")
		if err != nil {
			writeAuthError(w, http.StatusUnauthorized, "missing refresh token cookie")
			return
		}

		claims, err := Verify(cookie.Value, secret)
		if err != nil {
			writeAuthError(w, http.StatusUnauthorized, "invalid or expired refresh token")
			return
		}

		// SEC-C5: Only accept refresh tokens for token renewal
		if claims.TokenType != "refresh" {
			writeAuthError(w, http.StatusUnauthorized, "invalid token type — refresh token required")
			return
		}

		user, err := userStore.principalSnapshot(claims.Sub)
		if err != nil {
			writeAuthError(w, http.StatusUnauthorized, "user no longer exists")
			return
		}
		if !user.Active {
			writeAuthError(w, http.StatusUnauthorized, "account deactivated")
			return
		}

		// Calculate target TenantID. If the original refresh token had a TenantID (from Impersonation),
		// we verify the user STILL has superadmin rights to do that. Otherwise, they get demoted to their real tenant.
		targetRole := user.Role
		targetTenantID := user.TenantID

		if claims.TenantID != "" && claims.TenantID != user.TenantID {
			if user.Role == "superadmin" {
				targetTenantID = claims.TenantID // Valid impersonation renewal
			} else {
				// SEC-RT5-1: The user was previously a superadmin doing impersonation, but got demoted.
				// Fall back to their actual TenantID.
				targetTenantID = user.TenantID
			}
		}

		// SEC-CRIT2: Issue new access token using the truth from the DB (targetRole/targetTenantID)
		accessToken, err := Sign(Claims{
			Sub:       claims.Sub,
			Role:      targetRole,
			TenantID:  targetTenantID,
			TokenType: "access",
			Exp:       time.Now().Add(15 * time.Minute).Unix(),
		}, secret)
		if err != nil {
			writeAuthError(w, http.StatusInternalServerError, "token generation failed")
			return
		}

		// SEC: H1 - Set new httpOnly token with Secure flag
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_token",
			Value:    accessToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   900,
		})

		csrfToken := hmacSign([]byte(accessToken), secret)[:32]

		// SEC-CRIT3: Update CSRF cookie on refresh
		setCSRFCookie(w, csrfToken, 900)

		resp := TokenResponse{
			CSRFToken: csrfToken,
			User:      &User{Email: user.Email, Role: targetRole, TenantID: targetTenantID},
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}
}

// HandleLogout clears the auth cookies.
// POST /api/auth/logout
func HandleLogout() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_token",
			Value:    "",
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   -1,
		})
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_refresh",
			Value:    "",
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   -1,
		})
		// SEC-CRIT3: Clear CSRF cookie on logout
		setCSRFCookie(w, "", -1)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]bool{"success": true})
	}
}

// HandleMe returns the current authenticated user profile.
// GET /api/auth/me
func HandleMe(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil {
			writeAuthError(w, http.StatusUnauthorized, "not authenticated")
			return
		}

		user, err := store.GetByEmail(claims.Sub)
		if err != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}

		// Override tenant_id with JWT claims value — this reflects
		// impersonation context (JWT TenantID may differ from DB TenantID).
		user.TenantID = claims.TenantID

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(user)
	}
}

// HandleListUsers returns users scoped to the caller's tenant (admin only).
// GET /api/auth/users
// SEC-HIGH1: Returns empty list when TenantID is empty to prevent cross-tenant leak.
func HandleListUsers(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || (claims.Role != "admin" && claims.Role != "superadmin") {
			writeAuthError(w, http.StatusForbidden, "admin or superadmin role required")
			return
		}

		// SEC-HIGH1: Block listing when TenantID is empty — prevents
		// empty-string match showing all users without a tenant.
		if claims.TenantID == "" && claims.Role != "superadmin" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]any{
				"users": []*User{},
				"total": 0,
			})
			return
		}

		// SEC: Filter users by tenant_id to prevent cross-tenant data leak
		allUsers := store.ListUsers()
		var filtered []*User
		for _, u := range allUsers {
			if claims.Role == "superadmin" || u.TenantID == claims.TenantID {
				filtered = append(filtered, u)
			}
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"users": filtered,
			"total": len(filtered),
		})
	}
}

// roleRank orders roles for privilege comparisons. Review 13.06 (audit):
// user-mutation handlers must enforce these in-handler because RBAC is disabled.
var roleRank = map[string]int{"viewer": 1, "sensor": 1, "analyst": 2, "admin": 3, "superadmin": 4}

// requireAdminClaims returns the caller's claims if they are admin/superadmin,
// otherwise writes 403 and returns nil. The handler must stop on nil.
func requireAdminClaims(w http.ResponseWriter, r *http.Request) *Claims {
	claims := GetClaims(r.Context())
	if claims == nil || roleRank[claims.Role] < roleRank["admin"] {
		writeAuthError(w, http.StatusForbidden, "admin role required")
		return nil
	}
	return claims
}

// sameTenantOrSuperadmin reports whether the caller may act on a target user.
func sameTenantOrSuperadmin(caller *Claims, target *User) bool {
	if caller.Role == "superadmin" {
		return true
	}
	return target.TenantID == caller.TenantID
}

// HandleCreateUser creates a new user (admin only).
// POST /api/auth/users
func HandleCreateUser(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		var req struct {
			Email       string `json:"email"`
			DisplayName string `json:"display_name"`
			Password    string `json:"password"`
			Role        string `json:"role"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON")
			return
		}

		if req.Email == "" || req.Password == "" {
			writeAuthError(w, http.StatusBadRequest, "email and password required")
			return
		}

		if req.Role == "" {
			req.Role = "viewer"
		}

		// Validate role
		validRoles := map[string]bool{"admin": true, "analyst": true, "viewer": true}
		if !validRoles[req.Role] {
			writeAuthError(w, http.StatusBadRequest, "invalid role (valid: admin, analyst, viewer)")
			return
		}

		// Review 13.06 (audit B6): require admin, scope the new user to the
		// caller's tenant, and forbid creating a role at/above the caller's own
		// (previously any tenant-bound viewer could mint an admin, and the new
		// user was orphaned with an empty tenant_id, breaking isolation).
		claims := requireAdminClaims(w, r)
		if claims == nil {
			return
		}
		if claims.TenantID == "" && claims.Role != "superadmin" {
			writeAuthError(w, http.StatusForbidden, "tenant context required to create users")
			return
		}
		if claims.Role != "superadmin" && roleRank[req.Role] >= roleRank[claims.Role] {
			writeAuthError(w, http.StatusForbidden, "cannot create a user with a role at or above your own")
			return
		}
		user, err := store.CreateUserInTenant(req.Email, req.DisplayName, req.Password, req.Role, claims.TenantID)
		if err != nil {
			if err == ErrUserExists {
				writeAuthError(w, http.StatusConflict, "user already exists")
			} else {
				slog.Error("failed to create user", "error", err)
				writeAuthError(w, http.StatusInternalServerError, "internal server error")
			}
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(user)
	}
}

// HandleUpdateUser updates a user's profile (admin only).
// PUT /api/auth/users/{id}
func HandleUpdateUser(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeAuthError(w, http.StatusBadRequest, "user id required")
			return
		}

		var req struct {
			DisplayName string `json:"display_name"`
			Role        string `json:"role"`
			Active      *bool  `json:"active"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON")
			return
		}

		// Review 13.06 (audit B5 CRITICAL): require admin, scope to the caller's
		// tenant, and never let the caller modify/assign a role at or above their
		// own. Previously this had NO authz at all → any viewer could PUT
		// {"role":"superadmin"} on themselves and take over any tenant's users.
		claims := requireAdminClaims(w, r)
		if claims == nil {
			return
		}
		target, terr := store.GetByID(id)
		if terr != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}
		if !sameTenantOrSuperadmin(claims, target) {
			writeAuthError(w, http.StatusNotFound, "user not found") // opaque, no existence leak
			return
		}
		if req.Role != "" {
			if _, ok := roleRank[req.Role]; !ok {
				writeAuthError(w, http.StatusBadRequest, "invalid role")
				return
			}
		}
		if claims.Role != "superadmin" {
			if roleRank[target.Role] >= roleRank[claims.Role] {
				writeAuthError(w, http.StatusForbidden, "cannot modify a user at or above your role")
				return
			}
			if req.Role != "" && roleRank[req.Role] >= roleRank[claims.Role] {
				writeAuthError(w, http.StatusForbidden, "cannot assign a role at or above your own")
				return
			}
		}

		active := true
		if req.Active != nil {
			active = *req.Active
		}

		if err := store.UpdateUser(id, req.DisplayName, req.Role, active); err != nil {
			slog.Error("failed to update user", "id", id, "error", err)
			writeAuthError(w, http.StatusNotFound, "user not found or update failed")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "updated"})
	}
}

// HandleDeleteUser deletes a user (admin only).
// DELETE /api/auth/users/{id}
func HandleDeleteUser(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeAuthError(w, http.StatusBadRequest, "user id required")
			return
		}

		// Review 13.06 (audit B5 CRITICAL): require admin, scope to the caller's
		// tenant, forbid deleting a peer at/above your role. Previously NO authz
		// → any authenticated user could delete any user in any tenant by ID.
		claims := requireAdminClaims(w, r)
		if claims == nil {
			return
		}
		target, terr := store.GetByID(id)
		if terr != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}
		if !sameTenantOrSuperadmin(claims, target) {
			writeAuthError(w, http.StatusNotFound, "user not found") // opaque
			return
		}
		if claims.Role != "superadmin" && roleRank[target.Role] >= roleRank[claims.Role] {
			writeAuthError(w, http.StatusForbidden, "cannot delete a user at or above your role")
			return
		}

		if err := store.DeleteUser(id); err != nil {
			slog.Error("failed to delete user", "id", id, "error", err)
			writeAuthError(w, http.StatusNotFound, "user not found or delete failed")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "deleted"})
	}
}

// HandleCreateAPIKey generates a new API key for the authenticated user.
// POST /api/auth/keys
func HandleCreateAPIKey(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil {
			writeAuthError(w, http.StatusUnauthorized, "not authenticated")
			return
		}

		user, err := store.GetByEmail(claims.Sub)
		if err != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}

		var req struct {
			Name string `json:"name"`
			Role string `json:"role"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if req.Name == "" {
			req.Name = "default"
		}
		// SEC-RT2-LOW-1: Sanitize key name to prevent stored XSS
		req.Name = strings.Map(func(r rune) rune {
			if r == '<' || r == '>' || r == '"' || r == '\'' || r == '&' || r == '/' || r == '\\' {
				return -1 // strip dangerous characters
			}
			return r
		}, req.Name)
		if len(req.Name) > 64 {
			req.Name = req.Name[:64]
		}
		if req.Role == "" {
			req.Role = user.Role
		}
		// SEC: Prevent role escalation — key role cannot exceed user's role
		allowedRoles := map[string]int{"viewer": 1, "analyst": 2, "admin": 3, "superadmin": 4, "sensor": 1}
		userLevel := allowedRoles[user.Role]
		keyLevel := allowedRoles[req.Role]
		if keyLevel > userLevel {
			writeAuthError(w, http.StatusForbidden, "cannot create key with higher privileges than your role")
			return
		}

		fullKey, ak, err := store.CreateAPIKey(user.ID, req.Name, req.Role)
		if err != nil {
			slog.Error("failed to create API key", "error", err)
			writeAuthError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"key":     fullKey, // shown only once
			"details": ak,
		})
	}
}

// HandleListAPIKeys returns API keys for the authenticated user, or all keys for superadmin.
// GET /api/auth/keys
func HandleListAPIKeys(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil {
			writeAuthError(w, http.StatusUnauthorized, "not authenticated")
			return
		}

		user, err := store.GetByEmail(claims.Sub)
		if err != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}

		var keys []APIKey
		if user.Role == "superadmin" {
			keys, err = store.ListAllAPIKeys()
		} else {
			keys, err = store.ListAPIKeys(user.ID)
		}

		if err != nil {
			slog.Error("failed to list API keys", "error", err)
			writeAuthError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		if err != nil {
			slog.Error("failed to list API keys", "error", err)
			writeAuthError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"keys": keys})
	}
}

// HandleDeleteAPIKey revokes an API key.
// DELETE /api/auth/keys/{id}
func HandleDeleteAPIKey(store *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil {
			writeAuthError(w, http.StatusUnauthorized, "not authenticated")
			return
		}

		user, err := store.GetByEmail(claims.Sub)
		if err != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}

		keyID := r.PathValue("id")
		if err := store.DeleteAPIKey(keyID, user.ID); err != nil {
			slog.Error("failed to delete API key", "error", err)
			writeAuthError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "revoked"})
	}
}

// APIKeyMiddleware checks for API key authentication alongside JWT.
// If Authorization header starts with "stx_", validate as API key.
// SEC-CRIT3: Now resolves user from DB to inject correct TenantID.
func APIKeyMiddleware(store *UserStore, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if strings.HasPrefix(authHeader, "Bearer stx_") {
			key := strings.TrimPrefix(authHeader, "Bearer ")
			userID, role, err := store.ValidateAPIKey(key)
			if err != nil {
				writeAuthError(w, http.StatusUnauthorized, "invalid API key")
				return
			}
			// SEC-CRIT3: Look up user to get TenantID for tenant isolation.
			// Also enforce deactivation: ValidateAPIKey only checks the key row,
			// so a disabled/terminated user's never-expiring key would otherwise
			// retain full access indefinitely (the refresh path already rejects
			// inactive users — API keys must too). Fail CLOSED on a known-inactive
			// owner and fail closed when its current tenant/role cannot be resolved.
			user, lookupErr := store.apiKeyOwnerSnapshot(userID)
			if lookupErr != nil || !user.Active || user.TenantID == "" {
				writeAuthError(w, http.StatusUnauthorized, "API key owner unavailable")
				return
			}
			keyLevel, keyKnown := roleRank[role]
			ownerLevel, ownerKnown := roleRank[user.Role]
			// Preserve downscoped keys without promoting them to the owner's
			// role. Revoked owner privileges cap existing keys too. Sensor is
			// below viewer in HTTP RBAC despite their shared mutation rank.
			if !keyKnown || !ownerKnown || keyLevel > ownerLevel || (user.Role == "sensor" && role != "sensor") {
				writeAuthError(w, http.StatusUnauthorized, "API key exceeds current owner privileges")
				return
			}
			claims := &Claims{Sub: userID, Role: role, TenantID: user.TenantID}

			ctx := SetClaimsContext(r.Context(), claims)
			next.ServeHTTP(w, r.WithContext(ctx))
			return
		}
		next.ServeHTTP(w, r)
	})
}

// HandleDemo provisions a read-only demo session and logs the user in.
// GET /api/auth/demo
func HandleDemo(userStore *UserStore, tenantStore *TenantStore, secret []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userStore.Ready() != nil || tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		const demoEmail = "demo@spectorn.ai"
		const demoTenantSlug = "syntrex-demo"

		if userStore.Ready() != nil || tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "demo unavailable")
			return
		}
		user, err := userStore.GetByEmail(demoEmail)
		if err == ErrUserNotFound {
			user, err = userStore.CreateUser(demoEmail, "Demo Visitor", "demo-random-pass-1234!!", "viewer")
		}
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "demo unavailable")
			return
		}
		tenant, err := tenantStore.GetTenantBySlug(demoTenantSlug)
		if err == ErrTenantNotFound {
			tenant, err = tenantStore.CreateTenant("Syntrex Demo", demoTenantSlug, user.ID, "enterprise")
		}
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "demo unavailable")
			return
		}
		if err = userStore.mutateUser(user.ID, func(u *User) error { u.EmailVerified = true; u.Role = "viewer"; u.TenantID = tenant.ID; return nil }); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "demo unavailable")
			return
		}
		user, err = userStore.GetByID(user.ID)
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "demo unavailable")
			return
		}

		// 2. Issuance of tokens
		accessToken, err := Sign(Claims{
			Sub:       user.Email,
			Role:      "viewer",
			TenantID:  tenant.ID,
			TokenType: "access",
			Exp:       time.Now().Add(15 * time.Minute).Unix(),
		}, secret)
		if err != nil {
			writeAuthError(w, http.StatusInternalServerError, "token generation failed")
			return
		}

		refreshToken, err := Sign(Claims{
			Sub:       user.Email,
			Role:      "viewer",
			TenantID:  tenant.ID,
			TokenType: "refresh",
			Exp:       time.Now().Add(7 * 24 * time.Hour).Unix(),
		}, secret)
		if err != nil {
			writeAuthError(w, http.StatusInternalServerError, "token generation failed")
			return
		}

		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_token",
			Value:    accessToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   900,
		})
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_refresh",
			Value:    refreshToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   7 * 24 * 3600,
		})

		csrfToken := hmacSign([]byte(accessToken), secret)[:32]

		// SEC-CRIT3: Set CSRF as cookie (Double Submit Cookie pattern)
		setCSRFCookie(w, csrfToken, 900)

		resp := TokenResponse{
			CSRFToken: csrfToken,
			User:      user,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}
}
