package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"math"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// htmlTagRegex strips HTML/script tags from user input (M5 XSS prevention).
var htmlTagRegex = regexp.MustCompile(`<[^>]*>`)

// reservedSlugPrefixes are the namespaces used by spectorn-PROVISIONED tenant ids
// (Variant A): the gomcp tenant slug == the spectorn tenant_id. A self-service
// registration must NEVER be allowed to claim one — otherwise a caller could
// pre-register (squat) a victim's deterministic spectorn tenant_id
// ("u_"+blake3(email)) and have the signed provision/SSO channel then act on the
// attacker-owned tenant (mega-review 17.06, cross-plane slug squatting). The
// charset rule below already rejects "u_" (underscore is not allowed); these
// prefixes additionally reserve the gomcp internal id namespace.
var reservedSlugPrefixes = []string{"u_", "tnt-", "tnt_"}

// selfServiceSlugRegex constrains a self-chosen org slug to a safe lowercase
// DNS-ish label (2-63 chars, [a-z0-9-], no leading hyphen, no underscore). The
// signed provisioning path creates slugs directly and does NOT pass through this
// validator, so it can still use the reserved namespaces.
var selfServiceSlugRegex = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{1,62}$`)

// validSelfServiceSlug reports whether a PUBLICLY-registered org slug is safe and
// outside the spectorn-provisioned namespace.
func validSelfServiceSlug(slug string) bool {
	if !selfServiceSlugRegex.MatchString(slug) {
		return false
	}
	for _, p := range reservedSlugPrefixes {
		if strings.HasPrefix(slug, p) {
			return false
		}
	}
	return true
}

var stripeWebhookCache sync.Map
var stripeWebhookCommitMu sync.Mutex

// EmailSendFunc is a callback for sending verification emails.
// Signature: func(toEmail, userName, code string) error
type EmailSendFunc func(toEmail, userName, code string) error

// HandleRegister processes new tenant + owner registration.
// POST /api/auth/register { email, password, name, org_name, org_slug }
// Returns verification_required — user must verify email before login.
//
// The code is never in the response. The comment here used to say it was, and so did the startup
// warning in cmd/soc — both described a leak that a previous fix had already closed. A false
// security note is worse than none: an operator reads the warning and hardens against the wrong
// thing, and a reader trusts the doc over the code.
//
// What was actually broken is the opposite direction. With no email sender the handler created the
// account, generated a code, and answered «Verification code sent to your email» — while no email
// existed. The user waits for a message that was never sent, and retrying is refused because their
// address is now taken. Silent, and entirely on the user's side.
//
// So: with no sender, registration refuses BEFORE creating anything, unless an operator has opted
// in with SOC_EMAIL_DEV_MODE=1. That is the same shape as the sentinel-core stub gate in
// cmd/soc/main.go — a degraded mode has to be asked for, never fallen into.
func HandleRegister(userStore *UserStore, tenantStore *TenantStore, jwtSecret []byte, emailFn EmailSendFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userStore.Ready() != nil || tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		// SEC-M4: Server-side registration gate
		if os.Getenv("SOC_REGISTRATION_OPEN") == "false" {
			http.Error(w, `{"error":"registration is closed — contact admin for an invitation"}`, http.StatusForbidden)
			return
		}

		// Checked before any row is written. Refusing after the user and tenant exist would leave a
		// half-registered account nobody can verify and nobody can re-register.
		emailDevMode := os.Getenv("SOC_EMAIL_DEV_MODE") == "1"
		if emailFn == nil && !emailDevMode {
			slog.Error("register refused: no email sender configured",
				"remedy", "set RESEND_API_KEY, or SOC_EMAIL_DEV_MODE=1 to read codes from this log")
			http.Error(w, `{"error":"email_delivery_unavailable","message":"Registration needs email verification and this deployment cannot send email. Nothing was created; please contact support."}`, http.StatusServiceUnavailable)
			return
		}

		var req struct {
			Email    string `json:"email"`
			Password string `json:"password"`
			Name     string `json:"name"`
			OrgName  string `json:"org_name"`
			OrgSlug  string `json:"org_slug"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}
		if req.Email == "" || req.Password == "" || req.OrgName == "" || req.OrgSlug == "" {
			http.Error(w, `{"error":"email, password, org_name, org_slug are required"}`, http.StatusBadRequest)
			return
		}
		if len(req.Password) < 8 {
			http.Error(w, `{"error":"password must be at least 8 characters"}`, http.StatusBadRequest)
			return
		}
		// SEC (mega-review 17.06 — cross-plane slug squatting): reject reserved /
		// malformed slugs so a self-service caller can never claim a spectorn
		// tenant_id namespace and have the signed provision/SSO channel act on it.
		if !validSelfServiceSlug(req.OrgSlug) {
			http.Error(w, `{"error":"invalid org_slug: 2-63 lowercase chars [a-z0-9-], no reserved prefix"}`, http.StatusBadRequest)
			return
		}
		if req.Name == "" {
			req.Name = req.Email
		}

		// SEC-M5: Strip HTML tags from user input to prevent stored XSS
		req.Name = htmlTagRegex.ReplaceAllString(req.Name, "")
		req.OrgName = htmlTagRegex.ReplaceAllString(req.OrgName, "")

		// Create user first (admin of new tenant)
		user, err := userStore.CreateUser(req.Email, req.Name, req.Password, "admin")
		if err != nil {
			if err == ErrUserExists {
				http.Error(w, `{"error":"email already registered"}`, http.StatusConflict)
				return
			}
			http.Error(w, `{"error":"failed to create user"}`, http.StatusInternalServerError)
			return
		}

		// Create tenant
		tenant, err := tenantStore.CreateTenant(req.OrgName, req.OrgSlug, user.ID, "free")
		if err != nil {
			if err == ErrTenantExists {
				http.Error(w, `{"error":"organization slug already taken"}`, http.StatusConflict)
				return
			}
			http.Error(w, `{"error":"failed to create organization"}`, http.StatusInternalServerError)
			return
		}

		// Update user with tenant_id
		// CRITICAL: pgx/v5 requires $1/$2 placeholders, NOT ? (silently fails with ?)
		if err := userStore.setTenant(user.ID, tenant.ID, false); err != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account update unavailable")
			return
		}

		// Generate verification code
		code, err := userStore.SetVerifyToken(req.Email)
		if err != nil {
			http.Error(w, `{"error":"failed to generate verification code"}`, http.StatusInternalServerError)
			return
		}

		// Send verification email if email service is configured
		resp := map[string]interface{}{
			"status":  "verification_required",
			"email":   req.Email,
			"message": "Verification code sent to your email",
			"tenant":  tenant,
		}

		// The message has to match what happened. «Verification code sent to your email» printed
		// after a failed send is the reason a user sits waiting instead of asking for help.
		switch {
		case emailFn == nil:
			// Reachable only with SOC_EMAIL_DEV_MODE=1; the refusal above covers every other case.
			slog.Warn("email service not configured — verification code logged (dev mode)",
				"email", req.Email, "code", code)
			resp["message"] = "Email delivery is not configured on this deployment. The verification code was written to the server log."
			resp["email_delivered"] = false
		default:
			if err := emailFn(req.Email, req.Name, code); err != nil {
				slog.Error("failed to send verification email", "email", req.Email, "error", err)
				// The account and the code exist, so this is recoverable — but only if the user is
				// told to ask for a resend rather than told to check an inbox nothing arrived in.
				resp["message"] = "Your account was created, but we could not send the verification email. Please request a new code."
				resp["email_delivered"] = false
			} else {
				resp["email_delivered"] = true
			}
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(resp)
	}
}

// HandleVerifyEmail validates the verification code and issues JWT.
// POST /api/auth/verify { email, code }
func HandleVerifyEmail(userStore *UserStore, tenantStore *TenantStore, jwtSecret []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userStore.Ready() != nil || tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		var req struct {
			Email string `json:"email"`
			Code  string `json:"code"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}
		if req.Email == "" || req.Code == "" {
			http.Error(w, `{"error":"email and code required"}`, http.StatusBadRequest)
			return
		}

		if err := userStore.VerifyEmail(req.Email, req.Code); err != nil {
			if err == ErrInvalidVerifyCode {
				http.Error(w, `{"error":"invalid or expired verification code"}`, http.StatusBadRequest)
				return
			}
			http.Error(w, `{"error":"verification failed"}`, http.StatusInternalServerError)
			return
		}

		// Get user and tenant
		user, err := userStore.GetByEmail(req.Email)
		if err != nil {
			http.Error(w, `{"error":"user not found"}`, http.StatusNotFound)
			return
		}

		tenantID := user.TenantID
		if userStore.db != nil {
			if err := userStore.db.QueryRow(`SELECT tenant_id FROM users WHERE id=$1`, user.ID).Scan(&tenantID); err != nil {
				userStore.mu.Lock()
				userStore.unhealthy = true
				userStore.mu.Unlock()
				writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
				return
			}
		}

		// Issue JWT with tenant context
		accessToken, err := Sign(Claims{
			Sub:       user.Email,
			Role:      user.Role,
			TenantID:  tenantID,
			TokenType: "access",
			Exp:       time.Now().Add(15 * time.Minute).Unix(),
		}, jwtSecret)
		if err != nil {
			http.Error(w, `{"error":"failed to issue token"}`, http.StatusInternalServerError)
			return
		}

		refreshToken, _ := Sign(Claims{
			Sub:       user.Email,
			Role:      user.Role,
			TenantID:  tenantID,
			TokenType: "refresh",
			Exp:       time.Now().Add(7 * 24 * time.Hour).Unix(),
		}, jwtSecret)

		var tenant *Tenant
		if tenantID != "" {
			tenant, _ = tenantStore.GetTenant(tenantID)
		}

		// SEC: H1 - Use httpOnly Cookies instead of returning JSON tokens
		// SEC-HIGH5: SameSite=Strict + Secure=true — consistent with login handler
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
		csrfToken := hmacSign([]byte(accessToken), jwtSecret)[:32]

		// SEC-CRIT3: Set CSRF as cookie (Double Submit Cookie pattern)
		setCSRFCookie(w, csrfToken, 900)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"csrf_token": csrfToken,
			"user":       user,
			"tenant":     tenant,
		})
	}
}

// HandleGetTenant returns the current tenant info.
// GET /api/auth/tenant
func HandleGetTenant(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.TenantID == "" {
			http.Error(w, `{"error":"no tenant context"}`, http.StatusForbidden)
			return
		}

		tenant, err := tenantStore.GetTenant(claims.TenantID)
		if err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		plan := tenant.GetPlan()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"tenant": tenant,
			"plan":   plan,
			"usage": map[string]interface{}{
				"events_this_month": tenant.EventsThisMonth,
				"events_limit":      plan.MaxEventsMonth,
				"usage_percent":     usagePercent(tenant.EventsThisMonth, plan.MaxEventsMonth),
			},
		})
	}
}

// HandleUpdateTenantPlan upgrades/downgrades the tenant plan.
// POST /api/auth/tenant/plan { plan_id }
// SEC: Only allows downgrade to 'free' without payment. Paid upgrades require
// Stripe webhook confirmation (HandleStripeWebhook). This prevents users from
// clicking "Перейти" on paid plans and getting access without payment.
func HandleUpdateTenantPlan(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.Role != "admin" {
			http.Error(w, `{"error":"admin role required"}`, http.StatusForbidden)
			return
		}
		if claims.TenantID == "" {
			http.Error(w, `{"error":"no tenant context"}`, http.StatusForbidden)
			return
		}

		var req struct {
			PlanID string `json:"plan_id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request"}`, http.StatusBadRequest)
			return
		}

		// SEC: Block direct upgrades to paid plans — only Stripe webhook can do that
		if req.PlanID != "free" {
			http.Error(w, `{"error":"paid plan upgrades require payment — visit spectorn.ai/pricing"}`, http.StatusPaymentRequired)
			return
		}

		if err := tenantStore.UpdatePlan(claims.TenantID, req.PlanID); err != nil {
			slog.Error("plan update failed", "tenant_id", claims.TenantID, "plan", req.PlanID, "error", err)
			http.Error(w, `{"error":"plan update failed"}`, http.StatusBadRequest)
			return
		}

		tenant, _ := tenantStore.GetTenant(claims.TenantID)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"tenant": tenant,
			"plan":   tenant.GetPlan(),
		})
	}
}

// HandleListPlans returns all available pricing plans.
// GET /api/auth/plans
func HandleListPlans() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		plans := make([]Plan, 0, len(DefaultPlans))
		order := []string{"free", "starter", "professional", "enterprise"}
		for _, id := range order {
			if p, ok := DefaultPlans[id]; ok {
				plans = append(plans, p)
			}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"plans": plans})
	}
}

// HandleBillingStatus returns the billing status for the tenant.
// GET /api/auth/billing
func HandleBillingStatus(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		claims := GetClaims(r.Context())
		if claims == nil || claims.TenantID == "" {
			http.Error(w, `{"error":"no tenant context"}`, http.StatusForbidden)
			return
		}

		tenant, err := tenantStore.GetTenant(claims.TenantID)
		if err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		plan := tenant.GetPlan()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"plan":                plan,
			"payment_customer_id": tenant.PaymentCustomerID,
			"payment_sub_id":      tenant.PaymentSubID,
			"events_used":         tenant.EventsThisMonth,
			"events_limit":        plan.MaxEventsMonth,
			"usage_percent":       usagePercent(tenant.EventsThisMonth, plan.MaxEventsMonth),
			"next_reset":          tenant.MonthResetAt,
		})
	}
}

// verifyStripeSignature validates the Stripe-Signature header using HMAC-SHA256.
// SEC-CRIT2: Prevents forged webhook events from upgrading tenant plans.
// Format: "t=timestamp,v1=signature"
func verifyStripeSignature(payload []byte, sigHeader string, secret string) error {
	if secret == "" {
		return fmt.Errorf("STRIPE_WEBHOOK_SECRET not configured")
	}
	if sigHeader == "" {
		return fmt.Errorf("missing Stripe-Signature header")
	}

	var timestamp string
	var signatures []string
	for _, part := range strings.Split(sigHeader, ",") {
		kv := strings.SplitN(part, "=", 2)
		if len(kv) != 2 {
			continue
		}
		switch kv[0] {
		case "t":
			timestamp = kv[1]
		case "v1":
			signatures = append(signatures, kv[1])
		}
	}

	if timestamp == "" || len(signatures) == 0 {
		return fmt.Errorf("invalid Stripe-Signature format")
	}

	// Reject timestamps older than 5 minutes (replay protection)
	ts, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil {
		return fmt.Errorf("invalid timestamp in signature")
	}
	if math.Abs(float64(time.Now().Unix()-ts)) > 300 {
		return fmt.Errorf("webhook timestamp too old (>5 min)")
	}

	// Compute expected signature: HMAC-SHA256(secret, "timestamp.payload")
	signedPayload := timestamp + "." + string(payload)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signedPayload))
	expected := hex.EncodeToString(mac.Sum(nil))

	for _, sig := range signatures {
		if hmac.Equal([]byte(sig), []byte(expected)) {
			return nil
		}
	}
	return fmt.Errorf("signature mismatch")
}

// HandleStripeWebhook processes Stripe webhook events.
// POST /api/billing/webhook
// SEC-CRIT2: Verifies Stripe-Signature header to prevent forged webhook events.
func HandleStripeWebhook(tenantStore *TenantStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tenantStore.Ready() != nil {
			writeAuthError(w, http.StatusServiceUnavailable, "account store unavailable")
			return
		}
		// SEC-CRIT2: Read raw body for signature verification
		body, err := io.ReadAll(io.LimitReader(r.Body, 65536))
		if err != nil {
			http.Error(w, "failed to read body", http.StatusBadRequest)
			return
		}

		// SEC-CRIT2: Verify Stripe webhook signature
		webhookSecret := os.Getenv("STRIPE_WEBHOOK_SECRET")
		if err := verifyStripeSignature(body, r.Header.Get("Stripe-Signature"), webhookSecret); err != nil {
			slog.Warn("stripe webhook signature verification failed",
				"error", err,
				"remote", r.RemoteAddr,
			)
			http.Error(w, "webhook signature verification failed", http.StatusForbidden)
			return
		}

		var evt struct {
			ID   string `json:"id"`
			Type string `json:"type"`
			Data struct {
				Object struct {
					CustomerID     string `json:"customer"`
					SubscriptionID string `json:"id"`
					Status         string `json:"status"`
					Metadata       struct {
						TenantID string `json:"tenant_id"`
						PlanID   string `json:"plan_id"`
					} `json:"metadata"`
				} `json:"object"`
			} `json:"data"`
		}
		if err := json.Unmarshal(body, &evt); err != nil {
			http.Error(w, "invalid payload", http.StatusBadRequest)
			return
		}

		// Serialize local dedupe through the confirmed database commit.
		stripeWebhookCommitMu.Lock()
		defer stripeWebhookCommitMu.Unlock()
		if evt.ID != "" {
			if _, loaded := stripeWebhookCache.Load(evt.ID); loaded {
				w.WriteHeader(http.StatusOK)
				w.Write([]byte(`{"received":true,"duplicate":true}`))
				return
			}
		}
		tenantID := evt.Data.Object.Metadata.TenantID
		if tenantID != "" {
			var mutationErr error
			switch evt.Type {
			case "customer.subscription.created", "customer.subscription.updated":
				mutationErr = tenantStore.mutateTenant(tenantID, func(t *Tenant) error {
					plan := evt.Data.Object.Metadata.PlanID
					if plan != "" {
						if _, ok := DefaultPlans[plan]; !ok {
							return fmt.Errorf("invalid subscription plan")
						}
						t.PlanID = plan
					}
					t.PaymentCustomerID = evt.Data.Object.CustomerID
					t.PaymentSubID = evt.Data.Object.SubscriptionID
					return nil
				})
			case "customer.subscription.deleted":
				mutationErr = tenantStore.mutateTenant(tenantID, func(t *Tenant) error {
					t.PlanID = "free"
					t.PaymentCustomerID = evt.Data.Object.CustomerID
					t.PaymentSubID = ""
					return nil
				})
			}
			if mutationErr != nil {
				writeAuthError(w, http.StatusServiceUnavailable, "subscription update unavailable")
				return
			}
		}
		if evt.ID != "" {
			stripeWebhookCache.Store(evt.ID, time.Now())
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"received":true}`))
	}
}

func usagePercent(used, limit int) float64 {
	if limit <= 0 {
		return 0
	}
	pct := float64(used) / float64(limit) * 100
	if pct > 100 {
		return 100
	}
	return pct
}

// HandleListTenants returns a list of all tenants for superadmin dashboard.
// GET /api/auth/tenants
func HandleListTenants(tenantStore *TenantStore) http.HandlerFunc {
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

		tenants := tenantStore.ListTenants()

		type tenantResp struct {
			ID     string `json:"id"`
			Name   string `json:"name"`
			Slug   string `json:"slug"`
			PlanID string `json:"plan_id"`
			Active bool   `json:"active"`
		}

		res := make([]tenantResp, len(tenants))
		for i, t := range tenants {
			res[i] = tenantResp{
				ID:     t.ID,
				Name:   t.Name,
				Slug:   t.Slug,
				PlanID: t.PlanID,
				Active: t.Active,
			}
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(res)
	}
}

// HandleImpersonateTenant allows a superadmin to switch their working tenant context.
// POST /api/auth/impersonate
func HandleImpersonateTenant(tenantStore *TenantStore, jwtSecret []byte) http.HandlerFunc {
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

		var req struct {
			TenantID string `json:"tenant_id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}

		// Verify target tenant is valid
		if _, err := tenantStore.GetTenant(req.TenantID); err != nil {
			http.Error(w, `{"error":"tenant not found"}`, http.StatusNotFound)
			return
		}

		// Issue new token with updated TenantID
		// SEC-V12: "Zombie Admin" ban: Impersonated sessions must expire rigorously and carry the impersonator flag.
		accessClaims := Claims{
			Sub:          claims.Sub,
			Role:         claims.Role,  // Preserves superadmin explicitly
			TenantID:     req.TenantID, // The impersonated tenant ID
			TokenType:    "access",
			Impersonator: claims.Sub,
			Exp:          time.Now().Add(1 * time.Hour).Unix(),
		}

		refreshClaims := Claims{
			Sub:          claims.Sub,
			Role:         claims.Role,
			TenantID:     req.TenantID,
			TokenType:    "refresh",
			Impersonator: claims.Sub,
			Exp:          time.Now().Add(1 * time.Hour).Unix(), // Hard-cap at 1 hour, remove 7-day persistence
		}

		accessToken, err := Sign(accessClaims, jwtSecret)
		if err != nil {
			http.Error(w, `{"error":"token generation failed"}`, http.StatusInternalServerError)
			return
		}
		refreshToken, err := Sign(refreshClaims, jwtSecret)
		if err != nil {
			http.Error(w, `{"error":"token generation failed"}`, http.StatusInternalServerError)
			return
		}

		// SEC-V12-OPUS: Cookie MaxAge MUST match JWT Exp for impersonation (Invariant #4)
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_token",
			Value:    accessToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   3600, // 1 hour — matches impersonation JWT Exp
		})
		http.SetCookie(w, &http.Cookie{
			Name:     "syntrex_refresh",
			Value:    refreshToken,
			Path:     "/",
			HttpOnly: true,
			Secure:   true,
			SameSite: http.SameSiteStrictMode,
			MaxAge:   3600, // SEC-V12-OPUS: Hard-cap cookie to 1h, kill 7-day persistence
		})

		// Also provide CSRF token for strict SPA requirements
		csrfToken := hmacSign([]byte(accessToken), jwtSecret)[:32]

		// SEC-CRIT3: Set CSRF as cookie (Double Submit Cookie pattern)
		setCSRFCookie(w, csrfToken, 900)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{
			"status":     "success",
			"tenant_id":  req.TenantID,
			"csrf_token": csrfToken,
		})
	}
}
