package auth

import (
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestAuditDurablePostgresContract(t *testing.T) {
	dsn := os.Getenv("SPECTORN_TEST_PG_DSN")
	if dsn == "" {
		t.Skip("explicit private PostgreSQL fixture not supplied")
	}
	u, err := url.Parse(dsn)
	if err != nil || u.Hostname() != "audit-socket.invalid" || !strings.HasPrefix(u.Query().Get("host"), "/workspace/tmp/pgf-") || u.Query().Get("sslmode") != "disable" {
		t.Fatal("refusing non-fixture database")
	}
	t.Setenv("SYNTREX_ADMIN_PASSWORD", "")
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal("open fixture")
	}
	defer db.Close()
	if _, err = db.Exec(`CREATE SCHEMA audit_auth_durable_contract`); err != nil {
		t.Fatal("create private fixture schema")
	}
	db.Close()
	q := u.Query()
	q.Set("search_path", "audit_auth_durable_contract")
	u.RawQuery = q.Encode()
	db, err = sql.Open("pgx", u.String())
	if err != nil {
		t.Fatal("open scoped fixture")
	}
	defer db.Close()
	db.SetMaxOpenConns(2)
	files, err := filepath.Glob("../postgres/migrations/*.sql")
	if err != nil {
		t.Fatal(err)
	}
	// Apply the committed legacy schema before the additive custom-limit upgrade.
	for _, file := range files {
		if filepath.Base(file) > "007_incident_case_evidence.sql" {
			continue
		}
		body, err := os.ReadFile(file)
		if err != nil {
			t.Fatal(err)
		}
		up := strings.Split(string(body), "-- +goose Down")[0]
		if _, err = db.Exec(up); err != nil {
			t.Fatalf("fixture migration %s failed", filepath.Base(file))
		}
	}
	if _, err = db.Exec(`INSERT INTO tenants(id,name,slug,plan_id,owner_user_id) VALUES('legacy','Legacy','legacy','starter','synthetic-owner')`); err != nil {
		t.Fatal("seed legacy fixture")
	}
	users := NewUserStore(db)
	tenants := NewTenantStore(db)
	if users.Ready() != nil || tenants.Ready() != nil {
		t.Fatal("durable stores unavailable")
	}
	legacy, err := tenants.GetTenant("legacy")
	if err != nil || legacy.CustomMaxScans != nil {
		t.Fatal("legacy override not inherited")
	}
	migration, err := os.ReadFile("../postgres/migrations/008_tenant_custom_limits.sql")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(strings.Split(string(migration), "-- +goose Down")[0]); err != nil {
		t.Fatal("additive migration not idempotent")
	}
	owner, err := users.CreateUserInTenant("owner@example.test", "Synthetic", "synthetic-only-password", "admin", "legacy")
	if err != nil {
		t.Fatal("create failed")
	}
	if err = users.setTenant(owner.ID, "legacy", true); err != nil {
		t.Fatal(err)
	}
	if err = users.UpdateUser(owner.ID, "Changed", "viewer", true); err != nil {
		t.Fatal(err)
	}
	limits := []int{0, -1, 17, 23}
	if err = tenants.mutateTenant("legacy", func(v *Tenant) error {
		v.CustomMaxEvents = &limits[0]
		v.CustomMaxScans = &limits[1]
		v.CustomMaxUsers = &limits[2]
		v.CustomMaxSensors = &limits[3]
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	key, record, err := users.CreateAPIKey(owner.ID, "synthetic", "viewer")
	if err != nil {
		t.Fatal(err)
	}
	if err = users.DeleteAPIKey(record.ID, owner.ID); err != nil {
		t.Fatal(err)
	}
	restarted := NewUserStore(db)
	got, err := restarted.Authenticate(owner.Email, "synthetic-only-password")
	if err != nil || got.Role != "viewer" || got.DisplayName != "Changed" {
		t.Fatal("durable user restart mismatch")
	}
	if _, _, err = restarted.ValidateAPIKey(key); err == nil {
		t.Fatal("key revocation lost")
	}
	reloadedTenants := NewTenantStore(db)
	v, err := reloadedTenants.GetTenant("legacy")
	if err != nil || v.GetPlan().MaxScansMonth != -1 || v.GetPlan().MaxEventsMonth != 0 || v.GetPlan().MaxUsers != 17 || v.GetPlan().MaxSensors != 23 {
		t.Fatal("custom-limit roundtrip mismatch")
	}
	exercisePostgresMutationBarrier(t, db, u.String(), owner.ID, "legacy")
	if _, err = db.Exec(`UPDATE users SET role='viewer',active=true WHERE id=$1`, owner.ID); err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(`CREATE FUNCTION reject_auth_write() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$; CREATE TRIGGER reject_auth_write BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION reject_auth_write()`); err != nil {
		t.Fatal("create rejection fixture")
	}
	if err = restarted.UpdateUser(owner.ID, "", "superadmin", false); !errors.Is(err, ErrStoreUnavailable) || restarted.Ready() == nil {
		t.Fatal("database rejection did not fail closed")
	}
	if restarted.users[owner.Email].Role != "viewer" || !restarted.users[owner.Email].Active {
		t.Fatal("rejected candidate became authority")
	}
	var role string
	if err = db.QueryRow(`SELECT role FROM users WHERE id=$1`, owner.ID).Scan(&role); err != nil || role != "viewer" {
		t.Fatal("rejected write changed durable authority")
	}
}

func exercisePostgresMutationBarrier(t *testing.T, other *sql.DB, dsn, userID, tenantID string) {
	t.Helper()
	for _, kind := range []string{"user", "tenant"} {
		t.Run("SerializableBarrier-"+kind, func(t *testing.T) {
			if _, err := other.Exec(`UPDATE users SET role='admin',active=true WHERE id=$1`, userID); err != nil {
				t.Fatal(err)
			}
			if _, err := other.Exec(`UPDATE tenants SET active=true,plan_id='starter',custom_max_events=NULL,events_this_month=0 WHERE id=$1`, tenantID); err != nil {
				t.Fatal(err)
			}
			armed := new(atomic.Bool)
			reached, release := make(chan struct{}), make(chan struct{})
			target := "UPDATE users SET"
			if kind == "tenant" {
				target = "UPDATE tenants SET"
			}
			driverName := fmt.Sprintf("audit-pg-auth-barrier-%d", lostReplySequence.Add(1))
			sql.Register(driverName, mutationBarrierDriver{other.Driver(), armed, reached, release, target})
			db, err := sql.Open(driverName, dsn)
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			db.SetMaxOpenConns(1)
			users := NewUserStore(db)
			tenants := NewTenantStore(db)
			if users.Ready() != nil || tenants.Ready() != nil {
				t.Fatal("barrier store init failed")
			}
			armed.Store(true)
			done := make(chan error, 1)
			go func() {
				if kind == "user" {
					done <- users.ChangePassword(userID, "new-synthetic-password")
				} else {
					done <- tenants.IncrementEvents(tenantID, 1)
				}
			}()
			select {
			case <-reached:
			case <-time.After(5 * time.Second):
				close(release)
				t.Fatal("writer did not reach barrier")
			}
			if kind == "user" {
				_, err = other.Exec(`UPDATE users SET active=false,role='viewer' WHERE id=$1`, userID)
			} else {
				_, err = other.Exec(`UPDATE tenants SET active=false,plan_id='free' WHERE id=$1`, tenantID)
			}
			close(release)
			if err != nil {
				t.Fatal(err)
			}
			select {
			case err = <-done:
			case <-time.After(5 * time.Second):
				t.Fatal("serialization conflict did not finish")
			}
			if !errors.Is(err, ErrStoreUnavailable) {
				t.Fatalf("conflict allowed stale write: %v", err)
			}
			var active bool
			var authority string
			if kind == "user" {
				err = other.QueryRow(`SELECT active,role FROM users WHERE id=$1`, userID).Scan(&active, &authority)
				if users.Ready() == nil || authority != "viewer" {
					t.Fatal("user serialization boundary failed")
				}
			} else {
				err = other.QueryRow(`SELECT active,plan_id FROM tenants WHERE id=$1`, tenantID).Scan(&active, &authority)
				if tenants.Ready() == nil || authority != "free" {
					t.Fatal("tenant serialization boundary failed")
				}
			}
			if err != nil || active {
				t.Fatal("external authority resurrected")
			}
		})
	}
}
