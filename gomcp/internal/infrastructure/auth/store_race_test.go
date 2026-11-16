package auth

import (
	"database/sql"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"

	_ "modernc.org/sqlite"
)

// TestUserStore_ConcurrentAccess_NoRace hammers the UserStore's public methods
// from many goroutines under `go test -race`.
//
// Review 14.06 round-4 (CRITICAL): persistUser/persistTenant used to be launched
// as `go s.persistUser(u)` with a SHARED *User, then read its fields with no
// lock while UpdateUser/ChangePassword/VerifyEmail/Authenticate mutated the same
// pointer under s.mu — a data race (torn string reads are memory-unsafe). The
// fix passes the struct BY VALUE so `*u` snapshots under the held lock.
//
// Coverage note: this runs the in-memory store (db==nil), so persistUser itself
// is a no-op and this test does NOT reproduce the exact persist↔mutate race
// (that needs the Postgres backend the store is written for). What it DOES lock
// is that the public methods' own locking model is race-free under concurrency,
// and that the `*u`-under-lock snapshot at every `go s.persistUser(*u)` call
// site is correct. A full DB-backed -race test is left to the Postgres CI lane.
func TestUserStore_ConcurrentAccess_NoRace(t *testing.T) {
	s := NewUserStore() // in-memory, no DB

	const seed = "race-seed@syntrex.pro"
	u, err := s.CreateUser(seed, "Seed", "pw-original", "viewer")
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}

	var wg sync.WaitGroup
	const workers = 16

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			// Mix readers and writers that all touch s.users and/or the shared
			// *User fields under s.mu.
			_ = s.UpdateUser(u.ID, fmt.Sprintf("Name-%d", n), "analyst", n%2 == 0)
			_ = s.ChangePassword(u.ID, fmt.Sprintf("pw-%d", n))
			_, _ = s.SetVerifyToken(seed)
			_, _ = s.GetByEmail(seed)
			_, _ = s.GetByID(u.ID)
			_ = s.ListUsers()
			// A distinct create per worker exercises the map-write path.
			_, _ = s.CreateUser(fmt.Sprintf("c%d@syntrex.pro", n), "C", "pw", "viewer")
		}(i)
	}
	wg.Wait()
}

func TestUserStoreMigratesLegacyUsersWithoutPasswordHash(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open sqlite: %v", err)
	}
	defer db.Close()

	_, err = db.Exec(`
		CREATE TABLE users (
			id             TEXT PRIMARY KEY,
			email          TEXT UNIQUE NOT NULL,
			display_name   TEXT NOT NULL DEFAULT '',
			role           TEXT NOT NULL DEFAULT 'viewer',
			active         BOOLEAN NOT NULL DEFAULT true,
			email_verified BOOLEAN NOT NULL DEFAULT true,
			created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
		INSERT INTO users (id, email, display_name, role, active, email_verified)
		VALUES ('usr_admin', 'admin@syntrex.pro', 'Administrator', 'superadmin', true, true);
	`)
	if err != nil {
		t.Fatalf("seed legacy users table: %v", err)
	}

	const password = "legacy-upgrade-admin-password"
	t.Setenv("SYNTREX_ADMIN_PASSWORD", password)
	_ = os.Unsetenv("SOC_ALLOW_UNAUTH_INGEST")

	store := NewUserStore(db)
	admin, err := store.Authenticate("admin@syntrex.pro", password)
	if err != nil {
		t.Fatalf("authenticate migrated admin: %v", err)
	}
	if admin.Role != "superadmin" {
		t.Fatalf("admin role = %q, want superadmin", admin.Role)
	}
}

// TestTenantStore_ConcurrentAccess_NoRace is the tenant-side counterpart: it
// exercises UpdatePlan/SetStripeIDs/IncrementEvents/DeactivateTenant (each of
// which fires `go s.persistTenant(*t)`) concurrently, locking the same
// snapshot-under-lock invariant for the billing/identity record. Same coverage
// caveat as the user-store test (in-memory, persist is a no-op).
func TestTenantStore_ConcurrentAccess_NoRace(t *testing.T) {
	s := NewTenantStore(nil) // in-memory, no DB

	tn, err := s.CreateTenant("Race Co", "race-co", "usr-owner", "starter")
	if err != nil {
		t.Fatalf("seed tenant: %v", err)
	}

	var wg sync.WaitGroup
	const workers = 16

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			_ = s.UpdatePlan(tn.ID, "professional")
			_ = s.SetStripeIDs(tn.ID, fmt.Sprintf("cus_%d", n), fmt.Sprintf("sub_%d", n))
			_ = s.IncrementEvents(tn.ID, 1)
			_, _ = s.GetTenant(tn.ID)
			_ = s.ListTenants()
			if n%4 == 0 {
				_ = s.DeactivateTenant(tn.ID)
			}
		}(i)
	}
	wg.Wait()
}

// TestAdminHandlers_ConcurrentMutation_NoRace drives the superadmin mutation
// handlers concurrently against the SOC-ingest reader path under -race.
//
// Review 14.06 round-5: HandleAdminUpdateTenant / HandleAdminSetLimits used to
// mutate the LIVE *Tenant pointer's fields (PlanID, Name, Active, CustomMax*)
// WITHOUT the lock, while IncrementEvents/GetPlan read those exact fields UNDER
// the lock on the hot ingest path — a write-without-lock vs read-with-lock data
// race (the round-4 snapshot fix only covered the detached persist, not these
// writes). This test exercises the handler mutation path — which the prior race
// test did not — and fails under -race if the field writes are not relocated
// under the lock.
func TestAdminHandlers_ConcurrentMutation_NoRace(t *testing.T) {
	ts := NewTenantStore(nil) // in-memory, no DB (persist is a no-op)
	tn, err := ts.CreateTenant("Race Co", "race-co", "usr-owner", "starter")
	if err != nil {
		t.Fatalf("seed tenant: %v", err)
	}

	superadmin := &Claims{Sub: "root", Role: "superadmin"}
	updateH := HandleAdminUpdateTenant(ts)
	limitsH := HandleAdminSetLimits(ts)

	call := func(h http.HandlerFunc, body string) {
		req := httptest.NewRequest(http.MethodPut, "/api/admin/tenants/"+tn.ID, strings.NewReader(body))
		req.SetPathValue("id", tn.ID)
		req = req.WithContext(SetClaimsContext(req.Context(), superadmin))
		h(httptest.NewRecorder(), req)
	}

	var wg sync.WaitGroup
	const workers = 16
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			// Writers: the admin handlers mutate PlanID/Name/Active/CustomMax*.
			call(updateH, `{"plan_id":"professional","name":"X","active":true}`)
			call(limitsH, `{"max_events":100000,"max_scans":200000}`)
			// Readers on the SAME shared *Tenant, under the lock.
			_ = ts.IncrementEvents(tn.ID, 1) // GetPlan reads PlanID + CustomMax*
			_ = ts.ListTenants()
			_, _ = ts.GetTenant(tn.ID)
		}()
	}
	wg.Wait()
}
