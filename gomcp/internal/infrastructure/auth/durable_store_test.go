package auth

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	_ "modernc.org/sqlite"
	"path/filepath"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func durableFixture(t *testing.T) (*sql.DB, *UserStore, *TenantStore, *User) {
	t.Helper()
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "auth.db"))
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	s := NewUserStore(db)
	tenants := NewTenantStore(db)
	if s.Ready() != nil || tenants.Ready() != nil {
		t.Fatal("fixture init unavailable")
	}
	u, err := s.CreateUserInTenant("owner@example.test", "Owner", "synthetic-only-password", "admin", "tenant-fixture")
	if err != nil {
		t.Fatal(err)
	}
	if err = s.mutateUser(u.ID, func(u *User) error {
		u.EmailVerified = true
		u.VerifyToken = "synthetic-code"
		v := time.Now().Add(time.Hour)
		u.VerifyExpiry = &v
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	return db, s, tenants, u
}
func TestAuditDurableUserWriteFailuresNeverPublish(t *testing.T) {
	for _, operation := range []string{"create", "update", "password", "token", "verify", "delete"} {
		t.Run(operation, func(t *testing.T) {
			db, s, _, u := durableFixture(t)
			before := cloneUser(s.users[u.Email])
			event := "UPDATE"
			if operation == "create" {
				event = "INSERT"
			}
			if operation == "delete" {
				event = "DELETE"
			}
			if _, err := db.Exec("CREATE TRIGGER reject_user_write BEFORE " + event + " ON users BEGIN SELECT RAISE(ABORT,'synthetic rejection'); END"); err != nil {
				t.Fatal(err)
			}
			var err error
			switch operation {
			case "create":
				_, err = s.CreateUser("new@example.test", "New", "synthetic-only-password", "viewer")
			case "update":
				err = s.UpdateUser(u.ID, "", "viewer", false)
			case "password":
				err = s.ChangePassword(u.ID, "different-synthetic-password")
			case "token":
				_, err = s.SetVerifyToken(u.Email)
			case "verify":
				err = s.VerifyEmail(u.Email, "synthetic-code")
			case "delete":
				err = s.DeleteUser(u.ID)
			}
			if !errors.Is(err, ErrStoreUnavailable) || s.Ready() == nil {
				t.Fatalf("write did not fail closed: %v", err)
			}
			got := s.users[u.Email]
			if got == nil || got.Role != before.Role || got.Active != before.Active || got.PasswordHash != before.PasswordHash || got.VerifyToken != before.VerifyToken || got.EmailVerified != before.EmailVerified {
				t.Fatal("failed candidate published")
			}
			if _, err = s.GetByEmail(u.Email); !errors.Is(err, ErrStoreUnavailable) {
				t.Fatal("unhealthy read authorized")
			}
			if _, err = s.Authenticate(u.Email, "synthetic-only-password"); !errors.Is(err, ErrStoreUnavailable) {
				t.Fatal("unhealthy authentication authorized")
			}
			if _, err = s.apiKeyOwnerSnapshot(u.ID); !errors.Is(err, ErrStoreUnavailable) {
				t.Fatal("unhealthy API key owner authorized")
			}
		})
	}
}
func TestAuditDurableTenantFailuresAndCopies(t *testing.T) {
	for _, operation := range []string{"create", "plan", "stripe", "events", "deactivate"} {
		t.Run(operation, func(t *testing.T) {
			db, _, s, u := durableFixture(t)
			v, err := s.CreateTenant("Fixture", "fixture", u.ID, "starter")
			if err != nil {
				t.Fatal(err)
			}
			before := cloneTenant(s.tenants[v.ID])
			event := "UPDATE"
			if operation == "create" {
				event = "INSERT"
			}
			// Candidate updates currently use an upsert; SQLite runs the INSERT trigger
			// first, then the UPDATE trigger. Reject both write variants.
			for _, ev := range []string{event, "INSERT"} {
				if _, err = db.Exec("CREATE TRIGGER IF NOT EXISTS reject_tenant_" + ev + " BEFORE " + ev + " ON tenants BEGIN SELECT RAISE(ABORT,'synthetic rejection'); END"); err != nil && ev != event {
					continue
				} else if err != nil {
					t.Fatal(err)
				}
			}
			switch operation {
			case "create":
				_, err = s.CreateTenant("Other", "other", u.ID, "starter")
			case "plan":
				err = s.UpdatePlan(v.ID, "enterprise")
			case "stripe":
				err = s.SetStripeIDs(v.ID, "fixture-customer", "fixture-sub")
			case "events":
				err = s.IncrementEvents(v.ID, 1)
			case "deactivate":
				err = s.DeactivateTenant(v.ID)
			}
			if !errors.Is(err, ErrStoreUnavailable) || s.Ready() == nil {
				t.Fatalf("tenant write did not fail closed: %v", err)
			}
			got := s.tenants[v.ID]
			if got.PlanID != before.PlanID || got.Active != before.Active || got.EventsThisMonth != before.EventsThisMonth || got.PaymentSubID != before.PaymentSubID {
				t.Fatal("tenant candidate published")
			}
		})
	}
	_, users, tenants, u := durableFixture(t)
	v, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	u.Role = "superadmin"
	read, _ := users.GetByID(u.ID)
	if read.Role != "admin" {
		t.Fatal("returned user mutated store")
	}
	read.VerifyExpiry.Add(time.Hour)
	read.Role = "viewer"
	again, _ := users.GetByEmail(u.Email)
	if again.Role != "admin" {
		t.Fatal("getter aliases user")
	}
	n := 7
	if err = tenants.mutateTenant(v.ID, func(t *Tenant) error { t.CustomMaxScans = &n; return nil }); err != nil {
		t.Fatal(err)
	}
	copy, _ := tenants.GetTenant(v.ID)
	*copy.CustomMaxScans = 99
	againTenant, _ := tenants.GetTenant(v.ID)
	if *againTenant.CustomMaxScans != 7 {
		t.Fatal("tenant pointer field aliases store")
	}
}

// A real SQLite write commits, then this driver loses the reply. The store
// cannot classify an error as guaranteed rollback and must latch closed.
type lostReplyDriver struct {
	base  driver.Driver
	armed *atomic.Bool
}
type lostReplyConn struct {
	driver.Conn
	armed *atomic.Bool
}

func (d lostReplyDriver) Open(name string) (driver.Conn, error) {
	c, e := d.base.Open(name)
	if e != nil {
		return nil, e
	}
	return &lostReplyConn{c, d.armed}, nil
}
func (c *lostReplyConn) ExecContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Result, error) {
	return c.Conn.(driver.ExecerContext).ExecContext(ctx, q, args)
}
func (c *lostReplyConn) BeginTx(ctx context.Context, opts driver.TxOptions) (driver.Tx, error) {
	tx, err := c.Conn.(driver.ConnBeginTx).BeginTx(ctx, opts)
	if err != nil {
		return nil, err
	}
	return lostReplyTx{tx, c.armed}, nil
}

type lostReplyTx struct {
	driver.Tx
	armed *atomic.Bool
}

func (t lostReplyTx) Commit() error {
	err := t.Tx.Commit()
	if err == nil && t.armed.Swap(false) {
		return errors.New("synthetic reply lost after commit")
	}
	return err
}

func (c *lostReplyConn) QueryContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Rows, error) {
	return c.Conn.(driver.QueryerContext).QueryContext(ctx, q, args)
}

var lostReplySequence atomic.Uint64

func TestAuditDurableUnknownWriteAndRestart(t *testing.T) {
	base, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer base.Close()
	flag := new(atomic.Bool)
	name := fmt.Sprintf("audit-auth-lost-%d", lostReplySequence.Add(1))
	sql.Register(name, lostReplyDriver{base.Driver(), flag})
	file := filepath.Join(t.TempDir(), "unknown.db")
	db, err := sql.Open(name, file)
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	defer db.Close()
	s := NewUserStore(db)
	u, err := s.CreateUser("unknown@example.test", "Fixture", "synthetic-only-password", "admin")
	if err != nil {
		t.Fatal(err)
	}
	flag.Store(true)
	if err = s.UpdateUser(u.ID, "", "viewer", false); !errors.Is(err, ErrStoreUnavailable) {
		t.Fatal("lost reply reported success")
	}
	if s.Ready() == nil {
		t.Fatal("lost reply did not latch")
	}
	if s.users[u.Email].Role != "admin" {
		t.Fatal("unknown candidate published")
	}
	var role string
	if err = db.QueryRow(`SELECT role FROM users WHERE id=$1`, u.ID).Scan(&role); err != nil || role != "viewer" {
		t.Fatal("fixture did not commit before losing reply")
	}

	restarted := NewUserStore(db)
	got, err := restarted.GetByID(u.ID)
	if err != nil || got.Role != "viewer" || got.Active {
		t.Fatalf("restart did not honor authoritative state: %v", err)
	}
}
func TestAuditDurableLoginCannotOverwriteRoleOrDisable(t *testing.T) {
	_, s, _, u := durableFixture(t)
	var wg sync.WaitGroup
	wg.Add(2)
	go func() { defer wg.Done(); _, _ = s.Authenticate(u.Email, "synthetic-only-password") }()
	go func() {
		defer wg.Done()
		if err := s.UpdateUser(u.ID, "", "viewer", false); err != nil {
			t.Error(err)
		}
	}()
	wg.Wait()
	restarted := NewUserStore(s.db)
	got, err := restarted.GetByID(u.ID)
	if err != nil || got.Active || got.Role != "viewer" {
		t.Fatal("login resurrected obsolete authority")
	}
	if _, err = s.Authenticate(u.Email, "synthetic-only-password"); !errors.Is(err, ErrUserDisabled) {
		t.Fatal("disabled principal authenticated")
	}
}
func TestAuditDurableInitFailureNeverCreatesFreshAuthority(t *testing.T) {
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "closed.db"))
	if err != nil {
		t.Fatal(err)
	}
	db.Close()
	s := NewUserStore(db)
	tenants := NewTenantStore(db)
	if s.Ready() == nil || tenants.Ready() == nil || len(s.users) != 0 || len(tenants.tenants) != 0 {
		t.Fatal("unavailable configured DB became fresh authority")
	}
}

func TestAuditDurableCustomLimitsUpgradeAndRestart(t *testing.T) {
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "legacy-limits.db"))
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	defer db.Close()
	_, err = db.Exec(`CREATE TABLE tenants(id TEXT PRIMARY KEY,name TEXT NOT NULL,slug TEXT UNIQUE NOT NULL,plan_id TEXT NOT NULL,stripe_customer_id TEXT,stripe_sub_id TEXT,owner_user_id TEXT NOT NULL,active BOOLEAN NOT NULL,created_at TIMESTAMPTZ NOT NULL,events_this_month INTEGER NOT NULL,month_reset_at TIMESTAMPTZ NOT NULL);
 INSERT INTO tenants VALUES('legacy','Legacy','legacy','starter','','','owner',true,CURRENT_TIMESTAMP,0,CURRENT_TIMESTAMP);`)
	if err != nil {
		t.Fatal(err)
	}
	s := NewTenantStore(db)
	if err = s.Ready(); err != nil {
		t.Fatal(err)
	}
	before, err := s.GetTenant("legacy")
	if err != nil {
		t.Fatal(err)
	}
	if before.CustomMaxEvents != nil || before.CustomMaxScans != nil || before.CustomMaxUsers != nil || before.CustomMaxSensors != nil {
		t.Fatal("legacy row acquired overrides")
	}
	limits := []int{0, -1, 17, 23}
	if err = s.mutateTenant("legacy", func(v *Tenant) error {
		v.CustomMaxEvents = &limits[0]
		v.CustomMaxScans = &limits[1]
		v.CustomMaxUsers = &limits[2]
		v.CustomMaxSensors = &limits[3]
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	limits[0] = 99
	live, _ := s.GetTenant("legacy")
	if *live.CustomMaxEvents != 0 {
		t.Fatal("published override aliases caller")
	}
	restarted := NewTenantStore(db)
	got, err := restarted.GetTenant("legacy")
	if err != nil {
		t.Fatal(err)
	}
	plan := got.GetPlan()
	if plan.MaxEventsMonth != 0 || plan.MaxScansMonth != -1 || plan.MaxUsers != 17 || plan.MaxSensors != 23 {
		t.Fatal("custom limits did not survive restart")
	}
}
func TestAuditDurableStrictLoadRejectsMalformedRows(t *testing.T) {
	db, _, tenants, u := durableFixture(t)
	if _, err := db.Exec(`UPDATE users SET created_at='invalid time' WHERE id=$1`, u.ID); err != nil {
		t.Fatal(err)
	}
	broken := NewUserStore(db)
	if broken.Ready() == nil || len(broken.users) != 0 {
		t.Fatal("partial/invalid users became authority")
	}
	tenant, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(`UPDATE tenants SET month_reset_at='invalid time' WHERE id=$1`, tenant.ID); err != nil {
		t.Fatal(err)
	}
	brokenTenant := NewTenantStore(db)
	if brokenTenant.Ready() == nil || len(brokenTenant.tenants) != 0 {
		t.Fatal("partial/invalid tenants became authority")
	}
}
func TestAuditDurableLegacyTimestampCodec(t *testing.T) {
	for _, value := range []string{"2026-10-25 23:51:26.577445991 +0000 UTC m=+0.122001572", "2026-10-25 23:51:26", "2026-10-25T23:51:26Z"} {
		var v storeTime
		if err := v.Scan(value); err != nil || !v.Valid {
			t.Fatal("valid legacy encoding rejected")
		}
	}
	for _, value := range []any{"bad time", "2026-10-25 23:51:26 +0000 UTC m=garbage", 123} {
		var v storeTime
		if v.Scan(value) == nil {
			t.Fatal("unknown timestamp accepted")
		}
	}
}

func TestAuditDurableAuthAndTenantRoundTrip(t *testing.T) {
	db, s, tenants, u := durableFixture(t)
	code, err := s.SetVerifyToken(u.Email)
	if err != nil {
		t.Fatal(err)
	}
	if err = s.VerifyEmail(u.Email, code); err != nil {
		t.Fatal(err)
	}
	if err = s.ChangePassword(u.ID, "changed-synthetic-password"); err != nil {
		t.Fatal(err)
	}
	if err = s.UpdateUser(u.ID, "Changed", "viewer", true); err != nil {
		t.Fatal(err)
	}
	key, issued, err := s.CreateAPIKey(u.ID, "fixture", "viewer")
	if err != nil {
		t.Fatal(err)
	}
	if err = s.DeleteAPIKey(issued.ID, u.ID); err != nil {
		t.Fatal(err)
	}
	v, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	if err = tenants.SetStripeIDs(v.ID, "synthetic-customer", "synthetic-sub"); err != nil {
		t.Fatal(err)
	}
	if err = tenants.IncrementEvents(v.ID, 3); err != nil {
		t.Fatal(err)
	}
	if err = tenants.UpdatePlan(v.ID, "professional"); err != nil {
		t.Fatal(err)
	}
	if err = tenants.DeactivateTenant(v.ID); err != nil {
		t.Fatal(err)
	}
	restarted := NewUserStore(db)
	got, err := restarted.Authenticate(u.Email, "changed-synthetic-password")
	if err != nil || got.Role != "viewer" || got.DisplayName != "Changed" || !got.EmailVerified {
		t.Fatal("confirmed user write lost on restart")
	}
	if _, _, err = restarted.ValidateAPIKey(key); err == nil {
		t.Fatal("revoked key survived restart")
	}
	tenantStore := NewTenantStore(db)
	record, err := tenantStore.GetTenant(v.ID)
	if err != nil || record.Active || record.PlanID != "professional" || record.EventsThisMonth != 3 || record.PaymentSubID != "synthetic-sub" {
		t.Fatal("confirmed tenant write lost on restart")
	}
	if err = restarted.DeleteUser(u.ID); err != nil {
		t.Fatal(err)
	}
	again := NewUserStore(db)
	if _, err = again.GetByID(u.ID); !errors.Is(err, ErrUserNotFound) {
		t.Fatal("deleted user survived restart")
	}
}
func TestAuditDurableCascadeFailureRollsBackBothStores(t *testing.T) {
	db, users, tenants, u := durableFixture(t)
	v, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	if err = users.setTenant(u.ID, v.ID, false); err != nil {
		t.Fatal(err)
	}
	_, _, err = users.CreateAPIKey(u.ID, "fixture", "viewer")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(`CREATE TRIGGER reject_cascade BEFORE DELETE ON users BEGIN SELECT RAISE(ABORT,'synthetic rejection');END`); err != nil {
		t.Fatal(err)
	}
	if err = deleteTenant(users, tenants, v.ID, true); !errors.Is(err, ErrStoreUnavailable) {
		t.Fatal("cascade error was hidden")
	}
	if users.Ready() == nil || tenants.Ready() == nil {
		t.Fatal("cascade unknown outcome did not latch both stores")
	}
	for _, q := range []string{`SELECT COUNT(*) FROM users WHERE email='owner@example.test'`, `SELECT COUNT(*) FROM api_keys`, `SELECT COUNT(*) FROM tenants`} {
		var n int
		if err = db.QueryRow(q).Scan(&n); err != nil || n != 1 {
			t.Fatal("failed cascade transaction changed durable records")
		}
	}
	if users.users[u.Email] == nil || tenants.tenants[v.ID] == nil {
		t.Fatal("failed cascade published deletion")
	}
}

func TestAuditDurableLegacyAmbiguityFailsClosedWithoutRepair(t *testing.T) {
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "ambiguous.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	if _, err = db.Exec(`CREATE TABLE users(id TEXT,email TEXT,role TEXT DEFAULT 'viewer',active BOOLEAN DEFAULT true,email_verified BOOLEAN DEFAULT true,created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);INSERT INTO users(id,email)VALUES('one','same@example.test'),('two','same@example.test')`); err != nil {
		t.Fatal(err)
	}
	store := NewUserStore(db)
	if store.Ready() == nil || len(store.users) != 0 {
		t.Fatal("ambiguous users accepted or partially published")
	}
	var n int
	if err = db.QueryRow(`SELECT COUNT(*) FROM users`).Scan(&n); err != nil || n != 2 {
		t.Fatal("legacy users repaired or removed")
	}
}
