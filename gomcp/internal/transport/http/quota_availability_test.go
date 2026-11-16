package httpserver

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	_ "modernc.org/sqlite"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestQuotaHTTPUnavailableAndExhausted(t *testing.T) {
	for _, state := range []string{"missing", "nil-db", "closed", "exhausted"} {
		t.Run(state, func(t *testing.T) {
			srv := newGuardSrv(t)
			srv.SetSentinelCore(fakeReadyEngine{})
			if state == "missing" {
				srv.SetUsageTracker(nil)
			}
			if state == "nil-db" {
				srv.SetUsageTracker(auth.NewUsageTracker(nil))
			}
			if state == "closed" || state == "exhausted" {
				db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "quota.db"))
				if err != nil {
					t.Fatal(err)
				}
				defer db.Close()
				db.SetMaxOpenConns(1)
				tracker := auth.NewUsageTracker(db)
				srv.SetUsageTracker(tracker)
				if state == "closed" {
					db.Close()
				} else {
					t.Setenv("ANON_DEMO_SCAN_LIMIT", "1")
					if _, err = tracker.RecordScanWithLimit("", "192.0.2.10", 1); err != nil {
						t.Fatal(err)
					}
				}
			}
			r := httptest.NewRequest(http.MethodPost, "/api/v1/scan", strings.NewReader(`{"prompt":"synthetic quota fixture"}`))
			r.RemoteAddr = "192.0.2.10:12345"
			w := httptest.NewRecorder()
			srv.handlePublicScan(w, r)
			want := http.StatusServiceUnavailable
			if state == "exhausted" {
				want = http.StatusTooManyRequests
			}
			if w.Code != want {
				t.Fatalf("scan status=%d body=%s", w.Code, w.Body.String())
			}
			if state != "exhausted" {
				w = httptest.NewRecorder()
				srv.handleUsage(w, httptest.NewRequest(http.MethodGet, "/api/v1/usage", nil))
				if w.Code != http.StatusServiceUnavailable {
					t.Fatalf("usage status=%d", w.Code)
				}
			}
		})
	}
}

func TestQuotaAuthenticatedJWTRequiresAuthoritativePlan(t *testing.T) {
	for _, state := range []string{"missing-store", "missing-owner-store", "empty-tenant", "missing-tenant", "store-failure", "disabled", "zero-limit", "unknown-plan", "foreign", "disabled-owner", "valid-email-subject", "valid-id-subject", "platform-admin-explicit-tenant", "platform-admin-no-tenant", "downscoped-platform-admin", "stale-platform-admin"} {
		t.Run(state, func(t *testing.T) {
			t.Setenv("SENTINEL_ALLOW_STUB", "")
			db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "authenticated-quota.db"))
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			db.SetMaxOpenConns(1)
			tenants := auth.NewTenantStore(db)
			tenant, err := tenants.CreateTenant("synthetic", "synthetic", "fixture-owner", "free")
			if err != nil {
				t.Fatal(err)
			}
			users := auth.NewUserStore(db)
			role := "viewer"
			if strings.HasPrefix(state, "platform-admin") || state == "downscoped-platform-admin" || state == "missing-tenant" {
				role = "superadmin"
			}
			user, err := users.CreateUserInTenant("quota-fixture@example.invalid", "synthetic", "synthetic-password-for-fixture", role, tenant.ID)
			if err != nil {
				t.Fatal(err)
			}
			tracker := auth.NewUsageTracker(db)
			if err = tracker.Ready(); err != nil {
				t.Fatal(err)
			}
			srv := newGuardSrv(t)
			srv.SetSentinelCore(fakeReadyEngine{})
			srv.SetUsageTracker(tracker)
			srv.tenantStore = tenants
			srv.userStore = users
			claimTenant := tenant.ID
			subject := user.Email
			want := http.StatusForbidden
			switch state {
			case "missing-store":
				srv.tenantStore = nil
				want = http.StatusServiceUnavailable
			case "missing-owner-store":
				srv.userStore = nil
				want = http.StatusServiceUnavailable
			case "empty-tenant", "platform-admin-no-tenant":
				claimTenant = ""
			case "missing-tenant":
				claimTenant = "missing-fixture-tenant"
				if err = users.UpdateUser(user.ID, user.DisplayName, "superadmin", true); err != nil {
					t.Fatal(err)
				}
			case "store-failure":
				if _, err = db.Exec(`DROP TABLE tenants`); err != nil {
					t.Fatal(err)
				}
				if err = tenants.UpdatePlan(tenant.ID, "starter"); err == nil {
					t.Fatal("expected injected storage failure")
				}
				want = http.StatusServiceUnavailable
			case "disabled":
				if err = tenants.DeactivateTenant(tenant.ID); err != nil {
					t.Fatal(err)
				}
			case "zero-limit":
				if _, err = db.Exec(`UPDATE tenants SET custom_max_scans=0 WHERE id=$1`, tenant.ID); err != nil {
					t.Fatal(err)
				}
				srv.tenantStore = auth.NewTenantStore(db)
			case "unknown-plan":
				if _, err = db.Exec(`UPDATE tenants SET plan_id='unknown-fixture-plan' WHERE id=$1`, tenant.ID); err != nil {
					t.Fatal(err)
				}
				srv.tenantStore = auth.NewTenantStore(db)
				want = http.StatusServiceUnavailable
			case "foreign", "downscoped-platform-admin", "stale-platform-admin":
				foreign, e := tenants.CreateTenant("foreign", "foreign", "foreign-owner", "enterprise")
				if e != nil {
					t.Fatal(e)
				}
				claimTenant = foreign.ID
			case "disabled-owner":
				if err = users.UpdateUser(user.ID, user.DisplayName, user.Role, false); err != nil {
					t.Fatal(err)
				}
			case "valid-email-subject":
				want = http.StatusOK
			case "valid-id-subject":
				subject = user.ID
				want = http.StatusOK
			case "platform-admin-explicit-tenant":
				foreign, e := tenants.CreateTenant("foreign", "foreign", "foreign-owner", "free")
				if e != nil {
					t.Fatal(e)
				}
				claimTenant = foreign.ID
				want = http.StatusOK
			}
			if state == "downscoped-platform-admin" {
				role = "viewer"
			}
			if state == "stale-platform-admin" {
				role = "superadmin"
			}
			secret := []byte("synthetic-quota-jwt-secret-long-enough")
			token, err := auth.Sign(auth.Claims{Sub: subject, Role: role, TenantID: claimTenant, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
			if err != nil {
				t.Fatal(err)
			}
			r := httptest.NewRequest(http.MethodPost, "/api/v1/scan", strings.NewReader(`{"prompt":"synthetic authenticated quota fixture"}`))
			r.RemoteAddr = "192.0.2.20:12345"
			r.Header.Set("Authorization", "Bearer "+token)
			response := httptest.NewRecorder()
			auth.NewJWTMiddleware(secret).Middleware(http.HandlerFunc(srv.handlePublicScan)).ServeHTTP(response, r)
			if response.Code != want {
				t.Fatalf("status=%d want=%d body=%s", response.Code, want, response.Body.String())
			}
			var rows, used int
			if err = db.QueryRow(`SELECT COUNT(*),COALESCE(SUM(scans_used),0) FROM usage_quotas`).Scan(&rows, &used); err != nil {
				t.Fatal(err)
			}
			if want == http.StatusOK {
				if rows != 1 || used != 1 {
					t.Fatalf("successful scan usage rows=%d used=%d", rows, used)
				}
			} else if rows != 0 || used != 0 {
				t.Fatalf("unknown/forbidden plan consumed quota rows=%d used=%d", rows, used)
			}
		})
	}
}

func TestQuotaCanonicalOwnerSharesJWTAndAPIKeyAndPreservesLegacySpend(t *testing.T) {
	for _, legacy := range []bool{false, true} {
		t.Run(fmt.Sprintf("legacy_%t", legacy), func(t *testing.T) {
			db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "canonical-owner.db"))
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			db.SetMaxOpenConns(1)
			tenants := auth.NewTenantStore(db)
			tenant, err := tenants.CreateTenant("quota", "quota", "fixture-owner", "free")
			if err != nil {
				t.Fatal(err)
			}
			if _, err = db.Exec(`UPDATE tenants SET custom_max_scans=1 WHERE id=$1`, tenant.ID); err != nil {
				t.Fatal(err)
			}
			tenants = auth.NewTenantStore(db)
			users := auth.NewUserStore(db)
			user, err := users.CreateUserInTenant("canonical-owner@example.invalid", "synthetic", "synthetic-fixture-password", "viewer", tenant.ID)
			if err != nil {
				t.Fatal(err)
			}
			apiKey, _, err := users.CreateAPIKey(user.ID, "synthetic fixture", "viewer")
			if err != nil {
				t.Fatal(err)
			}
			tracker := auth.NewUsageTracker(db)
			if err = tracker.Ready(); err != nil {
				t.Fatal(err)
			}
			if legacy {
				if _, err = tracker.RecordScanWithLimit(user.Email, "", 1); err != nil {
					t.Fatal(err)
				}
			}
			srv := newGuardSrv(t)
			srv.SetSentinelCore(fakeReadyEngine{})
			srv.SetUsageTracker(tracker)
			srv.userStore = users
			srv.tenantStore = tenants
			secret := []byte("synthetic-quota-jwt-secret-long-enough")
			token, err := auth.Sign(auth.Claims{Sub: user.Email, Role: "viewer", TenantID: tenant.ID, TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
			if err != nil {
				t.Fatal(err)
			}
			serve := func(method, path, credential string) *httptest.ResponseRecorder {
				r := httptest.NewRequest(method, path, strings.NewReader(`{"prompt":"synthetic canonical owner fixture"}`))
				r.RemoteAddr = "192.0.2.30:12345"
				r.Header.Set("Authorization", "Bearer "+credential)
				handler := http.HandlerFunc(srv.handleUsage)
				if method == http.MethodPost {
					handler = srv.handlePublicScan
				}
				response := httptest.NewRecorder()
				auth.APIKeyMiddleware(users, auth.NewJWTMiddleware(secret).Middleware(handler)).ServeHTTP(response, r)
				return response
			}
			first := serve(http.MethodPost, "/api/v1/scan", token)
			second := serve(http.MethodPost, "/api/v1/scan", apiKey)
			if legacy {
				if first.Code != 503 || second.Code != 503 {
					t.Fatalf("legacy bypass: email=%d id=%d", first.Code, second.Code)
				}
			} else if first.Code != 200 || second.Code != 429 {
				t.Fatalf("shared cap: email=%d id=%d body=%s", first.Code, second.Code, second.Body.String())
			}
			for _, credential := range []string{token, apiKey} {
				response := serve(http.MethodGet, "/api/v1/usage", credential)
				if legacy {
					if response.Code != 503 {
						t.Fatalf("legacy usage fabricated: %d", response.Code)
					}
				} else {
					var info auth.UsageInfo
					if response.Code != 200 || json.Unmarshal(response.Body.Bytes(), &info) != nil || info.ScansUsed != 1 || info.Remaining != 0 {
						t.Fatalf("canonical usage status=%d body=%s", response.Code, response.Body.String())
					}
				}
			}
			var rows, used int
			var key string
			if err = db.QueryRow(`SELECT COUNT(*),COALESCE(SUM(scans_used),0),MIN(user_id) FROM usage_quotas`).Scan(&rows, &used, &key); err != nil {
				t.Fatal(err)
			}
			expected := user.ID
			if legacy {
				expected = user.Email
			}
			if rows != 1 || used != 1 || key != expected {
				t.Fatalf("rows=%d used=%d keyIsExpected=%t", rows, used, key == expected)
			}
		})
	}
}
