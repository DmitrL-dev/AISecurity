package auth

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"time"
)

// AdminTenantStats returns usage statistics for a tenant.
type AdminTenantStats struct {
	TenantID     string `json:"tenant_id"`
	TenantName   string `json:"tenant_name"`
	PlanID       string `json:"plan_id"`
	Active       bool   `json:"active"`
	UserCount    int    `json:"user_count"`
	EventsUsed   int    `json:"events_used"`
	EventsLimit  int    `json:"events_limit"`
	ScansLimit   int    `json:"scans_limit"`
	UsersLimit   int    `json:"users_limit"`
	SensorsLimit int    `json:"sensors_limit"`
	CreatedAt    string `json:"created_at"`
}

// HandleAdminListTenants returns all tenants with stats for superadmin.
// GET /api/admin/tenants
func HandleAdminListTenants(tenantStore *TenantStore, userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil || userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenants := tenantStore.ListTenants()
		allUsers := userStore.ListUsers()

		stats := make([]AdminTenantStats, 0, len(tenants))
		for _, t := range tenants {
			plan := t.GetPlan()
			userCount := 0
			for _, u := range allUsers {
				if u.TenantID == t.ID {
					userCount++
				}
			}
			stats = append(stats, AdminTenantStats{
				TenantID:     t.ID,
				TenantName:   t.Name,
				PlanID:       t.PlanID,
				Active:       t.Active,
				UserCount:    userCount,
				EventsUsed:   t.EventsThisMonth,
				EventsLimit:  plan.MaxEventsMonth,
				ScansLimit:   plan.MaxScansMonth,
				UsersLimit:   plan.MaxUsers,
				SensorsLimit: plan.MaxSensors,
				CreatedAt:    t.CreatedAt.Format(time.RFC3339),
			})
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"tenants": stats,
			"total":   len(stats),
		})
	}
}

// HandleAdminCreateTenant creates a new tenant with optional owner user.
// POST /api/admin/tenants { name, slug, plan_id, owner_email?, owner_password? }
func HandleAdminCreateTenant(tenantStore *TenantStore, userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil || userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		var req struct {
			Name          string `json:"name"`
			Slug          string `json:"slug"`
			PlanID        string `json:"plan_id"`
			OwnerEmail    string `json:"owner_email"`
			OwnerPassword string `json:"owner_password"`
			OwnerName     string `json:"owner_name"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}
		if req.Name == "" || req.Slug == "" {
			http.Error(w, `{"error":"name and slug are required"}`, http.StatusBadRequest)
			return
		}
		if req.PlanID == "" {
			req.PlanID = "free"
		}
		if _, ok := DefaultPlans[req.PlanID]; !ok {
			http.Error(w, fmt.Sprintf(`{"error":"unknown plan: %s"}`, req.PlanID), http.StatusBadRequest)
			return
		}

		ownerID := claims.Sub // default: superadmin as owner
		if req.OwnerEmail != "" && req.OwnerPassword != "" {
			if req.OwnerName == "" {
				req.OwnerName = req.OwnerEmail
			}
			user, err := userStore.CreateUser(req.OwnerEmail, req.OwnerName, req.OwnerPassword, "admin")
			if err != nil {
				if err == ErrUserExists {
					existing, _ := userStore.GetByEmail(req.OwnerEmail)
					if existing != nil {
						ownerID = existing.ID
					} else {
						http.Error(w, `{"error":"email already registered"}`, http.StatusConflict)
						return
					}
				} else {
					http.Error(w, `{"error":"failed to create owner user"}`, http.StatusInternalServerError)
					return
				}
			} else {
				ownerID = user.ID
			}
		}

		tenant, err := tenantStore.CreateTenant(req.Name, req.Slug, ownerID, req.PlanID)
		if err != nil {
			if err == ErrTenantExists {
				http.Error(w, `{"error":"slug already taken"}`, http.StatusConflict)
				return
			}
			http.Error(w, `{"error":"failed to create tenant"}`, http.StatusInternalServerError)
			return
		}

		if ownerID != claims.Sub {
			if err := userStore.setTenant(ownerID, tenant.ID, false); err != nil {
				writeAuthError(w, http.StatusServiceUnavailable, "account update unavailable")
				return
			}
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(tenant)
	}
}

// HandleAdminUpdateTenant updates tenant properties (name, plan_id, active).
// PUT /api/admin/tenants/{id}
func HandleAdminUpdateTenant(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenantID := r.PathValue("id")
		if tenantID == "" {
			http.Error(w, `{"error":"tenant id required"}`, http.StatusBadRequest)
			return
		}

		if _, err := tenantStore.GetTenant(tenantID); err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		var req struct {
			Name   *string `json:"name"`
			PlanID *string `json:"plan_id"`
			Active *bool   `json:"active"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}

		// Validate the plan id before taking the lock (cheap early return); the
		// write itself is applied under the lock below.
		if req.PlanID != nil {
			if _, ok := DefaultPlans[*req.PlanID]; !ok {
				http.Error(w, fmt.Sprintf(`{"error":"unknown plan: %s"}`, *req.PlanID), http.StatusBadRequest)
				return
			}
		}

		if err := tenantStore.mutateTenant(tenantID, func(t *Tenant) error {
			if req.Name != nil {
				t.Name = *req.Name
			}
			if req.PlanID != nil {
				t.PlanID = *req.PlanID
			}
			if req.Active != nil {
				t.Active = *req.Active
			}
			return nil
		}); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "tenant update unavailable")
			return
		}
		snapshot, err := tenantStore.GetTenant(tenantID)
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "tenant unavailable")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(snapshot)
	}
}

// HandleAdminDeleteTenant deletes a tenant and optionally its users.
// DELETE /api/admin/tenants/{id}?cascade=true
func HandleAdminDeleteTenant(tenantStore *TenantStore, userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil || userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenantID := r.PathValue("id")
		if tenantID == "" {
			http.Error(w, `{"error":"tenant id required"}`, http.StatusBadRequest)
			return
		}

		tenant, err := tenantStore.GetTenant(tenantID)
		if err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		cascade := r.URL.Query().Get("cascade") == "true"

		if err := deleteTenant(userStore, tenantStore, tenantID, cascade); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "tenant deletion unavailable")
			return
		}

		slog.Info("admin: tenant deleted", "tenant", tenant.Name, "cascade", cascade)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status":  "deleted",
			"tenant":  tenant.Name,
			"cascade": fmt.Sprintf("%t", cascade),
		})
	}
}

// HandleAdminSetLimits sets custom limits for a tenant (overrides plan).
// PUT /api/admin/tenants/{id}/limits { max_events, max_scans, max_users, max_sensors }
func HandleAdminSetLimits(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenantID := r.PathValue("id")
		if tenantID == "" {
			http.Error(w, `{"error":"tenant id required"}`, http.StatusBadRequest)
			return
		}

		if _, err := tenantStore.GetTenant(tenantID); err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		var req struct {
			MaxEvents  *int `json:"max_events"`
			MaxScans   *int `json:"max_scans"`
			MaxUsers   *int `json:"max_users"`
			MaxSensors *int `json:"max_sensors"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}

		for _, limit := range []*int{req.MaxEvents, req.MaxScans, req.MaxUsers, req.MaxSensors} {
			if limit != nil && *limit < -1 {
				writeAuthError(w, http.StatusBadRequest, "invalid custom limit")
				return
			}
		}

		if err := tenantStore.mutateTenant(tenantID, func(t *Tenant) error {
			if req.MaxEvents != nil {
				t.CustomMaxEvents = req.MaxEvents
			}
			if req.MaxScans != nil {
				t.CustomMaxScans = req.MaxScans
			}
			if req.MaxUsers != nil {
				t.CustomMaxUsers = req.MaxUsers
			}
			if req.MaxSensors != nil {
				t.CustomMaxSensors = req.MaxSensors
			}
			return nil
		}); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "tenant update unavailable")
			return
		}
		current, err := tenantStore.GetTenant(tenantID)
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "tenant unavailable")
			return
		}
		snapshot := *current

		// Build the response from the race-free snapshot, not the shared pointer.
		plan := snapshot.GetPlan()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"tenant_id": snapshot.ID,
			"limits": map[string]any{
				"max_events":  plan.MaxEventsMonth,
				"max_scans":   plan.MaxScansMonth,
				"max_users":   plan.MaxUsers,
				"max_sensors": plan.MaxSensors,
			},
			"custom": map[string]any{
				"max_events":  snapshot.CustomMaxEvents,
				"max_scans":   snapshot.CustomMaxScans,
				"max_users":   snapshot.CustomMaxUsers,
				"max_sensors": snapshot.CustomMaxSensors,
			},
		})
	}
}

// HandleAdminGetTenantUsers returns all users in a specific tenant.
// GET /api/admin/tenants/{id}/users
func HandleAdminGetTenantUsers(tenantStore *TenantStore, userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil || userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenantID := r.PathValue("id")
		if tenantID == "" {
			http.Error(w, `{"error":"tenant id required"}`, http.StatusBadRequest)
			return
		}

		if _, err := tenantStore.GetTenant(tenantID); err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		allUsers := userStore.ListUsers()
		var filtered []*User
		for _, u := range allUsers {
			if u.TenantID == tenantID {
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

// HandleAdminCreateUserInTenant creates a user in a specific tenant (bypasses registration flow).
// POST /api/admin/tenants/{id}/users { email, display_name, password, role }
func HandleAdminCreateUserInTenant(tenantStore *TenantStore, userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil || userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		tenantID := r.PathValue("id")
		if tenantID == "" {
			http.Error(w, `{"error":"tenant id required"}`, http.StatusBadRequest)
			return
		}

		if _, err := tenantStore.GetTenant(tenantID); err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		var req struct {
			Email       string `json:"email"`
			DisplayName string `json:"display_name"`
			Password    string `json:"password"`
			Role        string `json:"role"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}
		if req.Email == "" || req.Password == "" {
			http.Error(w, `{"error":"email and password are required"}`, http.StatusBadRequest)
			return
		}
		if req.Role == "" {
			req.Role = "viewer"
		}
		if req.DisplayName == "" {
			req.DisplayName = req.Email
		}

		user, err := userStore.CreateUser(req.Email, req.DisplayName, req.Password, req.Role)
		if err != nil {
			if err == ErrUserExists {
				http.Error(w, `{"error":"email already registered"}`, http.StatusConflict)
				return
			}
			http.Error(w, `{"error":"failed to create user"}`, http.StatusInternalServerError)
			return
		}

		if err := userStore.setTenant(user.ID, tenantID, true); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account update unavailable")
			return
		}
		user, err = userStore.GetByID(user.ID)
		if err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account unavailable")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(user)
	}
}

// HandleAdminDeleteUser deletes any user by ID (superadmin only).
// DELETE /api/admin/users/{id}
func HandleAdminDeleteUser(userStore *UserStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "superadmin" {
			http.Error(w, `{"error":"forbidden: superadmin only"}`, http.StatusForbidden)
			return
		}

		userID := r.PathValue("id")
		if userID == "" {
			http.Error(w, `{"error":"user id required"}`, http.StatusBadRequest)
			return
		}

		user, err := userStore.GetByID(userID)
		if err != nil {
			writeAuthError(w, http.StatusNotFound, "user not found")
			return
		}
		foundEmail := user.Email
		if err := userStore.DeleteUser(userID); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account deletion unavailable")
			return
		}

		slog.Info("admin: user deleted", "user_id", userID, "email", foundEmail)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status": "deleted",
			"user":   foundEmail,
		})
	}
}
