package auth

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestAuditDurableStaleHandlesCannotResurrectExternalAuthority(t *testing.T) {
	db, users, tenants, u := durableFixture(t)
	v, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
	if err != nil {
		t.Fatal(err)
	}
	// A second independent handle commits authority changes while the first
	// stores deliberately retain their older cached copies.
	var databaseFile string
	var seq int
	var name string
	if err = db.QueryRow(`PRAGMA database_list`).Scan(&seq, &name, &databaseFile); err != nil {
		t.Fatal(err)
	}
	other, err := sql.Open("sqlite", databaseFile)
	if err != nil {
		t.Fatal(err)
	}
	defer other.Close()
	other.SetMaxOpenConns(1)
	if _, err = other.Exec(`UPDATE users SET active=false,role='viewer' WHERE id=$1`, u.ID); err != nil {
		t.Fatal(err)
	}
	if err = users.ChangePassword(u.ID, "changed-synthetic-password"); err != nil {
		t.Fatal(err)
	}
	var active bool
	var role string
	if err = other.QueryRow(`SELECT active,role FROM users WHERE id=$1`, u.ID).Scan(&active, &role); err != nil || active || role != "viewer" {
		t.Fatal("stale user writer resurrected authority")
	}
	if _, err = other.Exec(`UPDATE tenants SET active=false,plan_id='free' WHERE id=$1`, v.ID); err != nil {
		t.Fatal(err)
	}
	current, err := tenants.GetTenant(v.ID)
	if err != nil || current.Active || current.PlanID != "free" {
		t.Fatal("quota getter used stale plan or activation")
	}
	if err = tenants.IncrementEvents(v.ID, 1); err != nil {
		t.Fatal(err)
	}
	var plan string
	if err = other.QueryRow(`SELECT active,plan_id FROM tenants WHERE id=$1`, v.ID).Scan(&active, &plan); err != nil || active || plan != "free" {
		t.Fatal("stale tenant writer restored activation/plan")
	}
}

type mutationBarrierDriver struct {
	base             driver.Driver
	armed            *atomic.Bool
	reached, release chan struct{}
	target           string
}
type mutationBarrierConn struct {
	driver.Conn
	config mutationBarrierDriver
}

func (d mutationBarrierDriver) Open(name string) (driver.Conn, error) {
	c, e := d.base.Open(name)
	if e != nil {
		return nil, e
	}
	return &mutationBarrierConn{c, d}, nil
}
func (c *mutationBarrierConn) ExecContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Result, error) {
	if strings.HasPrefix(strings.TrimSpace(q), c.config.target) && c.config.armed.Swap(false) {
		close(c.config.reached)
		<-c.config.release
	}
	return c.Conn.(driver.ExecerContext).ExecContext(ctx, q, args)
}
func (c *mutationBarrierConn) QueryContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Rows, error) {
	return c.Conn.(driver.QueryerContext).QueryContext(ctx, q, args)
}
func (c *mutationBarrierConn) BeginTx(ctx context.Context, opts driver.TxOptions) (driver.Tx, error) {
	return c.Conn.(driver.ConnBeginTx).BeginTx(ctx, opts)
}
func TestAuditDurableReadWriteBarrierPreservesExternalRevocation(t *testing.T) {
	for _, kind := range []string{"user", "tenant"} {
		t.Run(kind, func(t *testing.T) {
			base, err := sql.Open("sqlite", ":memory:")
			if err != nil {
				t.Fatal(err)
			}
			defer base.Close()
			armed := new(atomic.Bool)
			reached, release := make(chan struct{}), make(chan struct{})
			target := "UPDATE users SET"
			if kind == "tenant" {
				target = "UPDATE tenants SET"
			}
			driverName := fmt.Sprintf("audit-auth-barrier-%d", lostReplySequence.Add(1))
			sql.Register(driverName, mutationBarrierDriver{base.Driver(), armed, reached, release, target})
			file := filepath.Join(t.TempDir(), "barrier.db")
			db, err := sql.Open(driverName, file)
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			db.SetMaxOpenConns(1)
			if _, err = db.Exec(`PRAGMA journal_mode=WAL;PRAGMA busy_timeout=1000`); err != nil {
				t.Fatal(err)
			}
			users := NewUserStore(db)
			tenants := NewTenantStore(db)
			u, err := users.CreateUserInTenant("barrier@example.test", "Fixture", "synthetic-only-password", "admin", "fixture")
			if err != nil {
				t.Fatal(err)
			}
			v, err := tenants.CreateTenant("Fixture", "fixture", u.ID, "starter")
			if err != nil {
				t.Fatal(err)
			}
			other, err := sql.Open("sqlite", file)
			if err != nil {
				t.Fatal(err)
			}
			defer other.Close()
			other.SetMaxOpenConns(1)
			if _, err = other.Exec(`PRAGMA busy_timeout=1000`); err != nil {
				t.Fatal(err)
			}
			armed.Store(true)
			done := make(chan error, 1)
			go func() {
				if kind == "user" {
					done <- users.ChangePassword(u.ID, "changed-synthetic-password")
				} else {
					done <- tenants.IncrementEvents(v.ID, 1)
				}
			}()
			select {
			case <-reached:
			case <-time.After(5 * time.Second):
				close(release)
				t.Fatal("writer did not reach read/write barrier")
			}
			if kind == "user" {
				_, err = other.Exec(`UPDATE users SET active=false,role='viewer' WHERE id=$1`, u.ID)
			} else {
				_, err = other.Exec(`UPDATE tenants SET active=false,plan_id='free' WHERE id=$1`, v.ID)
			}
			close(release)
			if err != nil {
				t.Fatal(err)
			}
			select {
			case err = <-done:
			case <-time.After(5 * time.Second):
				t.Fatal("conflicting writer did not finish")
			}
			if !errors.Is(err, ErrStoreUnavailable) {
				t.Fatalf("conflicting write did not fail closed: %v", err)
			}
			var active bool
			var authority string
			if kind == "user" {
				err = other.QueryRow(`SELECT active,role FROM users WHERE id=$1`, u.ID).Scan(&active, &authority)
				if users.Ready() == nil || authority != "viewer" {
					t.Fatal("user conflict retained authority")
				}
			} else {
				err = other.QueryRow(`SELECT active,plan_id FROM tenants WHERE id=$1`, v.ID).Scan(&active, &authority)
				if tenants.Ready() == nil || authority != "free" {
					t.Fatal("tenant conflict retained authority")
				}
			}
			if err != nil || active {
				t.Fatal("external revocation overwritten")
			}
		})
	}
}
