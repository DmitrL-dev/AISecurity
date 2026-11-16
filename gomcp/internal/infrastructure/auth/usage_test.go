package auth

import (
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	_ "modernc.org/sqlite"
	"path/filepath"
	"sync"
	"sync/atomic"
	"testing"
)

func quotaDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "quota.db"))
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	return db
}
func quotaExec(t *testing.T, db *sql.DB, q string, args ...any) {
	t.Helper()
	if _, err := db.Exec(q, args...); err != nil {
		t.Fatal(err)
	}
}
func TestQuotaAtomicConcurrentCapAcrossTrackers(t *testing.T) {
	db := quotaDB(t)
	a, b := NewUsageTracker(db), NewUsageTracker(db)
	if err := a.Ready(); err != nil {
		t.Fatal(err)
	}
	var success atomic.Int64
	var wg sync.WaitGroup
	for i := 0; i < 40; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			tracker := a
			if i%2 == 1 {
				tracker = b
			}
			_, err := tracker.RecordScanWithLimit("user", "", 7)
			if err == nil {
				success.Add(1)
			} else if !errors.Is(err, ErrQuotaExceeded) {
				t.Errorf("record: %v", err)
			}
		}(i)
	}
	wg.Wait()
	info, err := a.GetUsageChecked("user", "")
	if err != nil || success.Load() != 7 || info.ScansUsed != 7 || info.Remaining != 0 {
		t.Fatalf("success=%d info=%+v err=%v", success.Load(), info, err)
	}
}
func TestQuotaFaultsNeverAllowAndCommitFailureRollsBack(t *testing.T) {
	for _, fault := range []string{"insert", "update", "commit", "query"} {
		t.Run(fault, func(t *testing.T) {
			db := quotaDB(t)
			tracker := NewUsageTracker(db)
			if fault == "insert" {
				quotaExec(t, db, `CREATE TRIGGER fail_insert BEFORE INSERT ON usage_quotas BEGIN SELECT RAISE(ABORT,'fixture'); END`)
			}
			if fault == "update" {
				quotaExec(t, db, `CREATE TRIGGER fail_update BEFORE UPDATE ON usage_quotas BEGIN SELECT RAISE(ABORT,'fixture'); END`)
			}
			if fault == "query" {
				quotaExec(t, db, `DROP TABLE usage_quotas`)
			}
			if fault == "commit" {
				quotaExec(t, db, `PRAGMA foreign_keys=ON`)
				quotaExec(t, db, `CREATE TABLE quota_parent(id INTEGER PRIMARY KEY)`)
				quotaExec(t, db, `CREATE TABLE quota_child(id INTEGER REFERENCES quota_parent(id) DEFERRABLE INITIALLY DEFERRED)`)
				quotaExec(t, db, `CREATE TRIGGER fail_commit AFTER UPDATE ON usage_quotas BEGIN INSERT INTO quota_child VALUES(1); END`)
			}
			for _, user := range []string{"", "authenticated"} {
				if _, err := tracker.RecordScanWithLimit(user, "fixture-ip", -1); !errors.Is(err, ErrUsageUnavailable) {
					t.Fatalf("%s allowed/fault misclassified: %v", user, err)
				}
			}
			if fault != "query" {
				var n int
				if err := db.QueryRow(`SELECT COUNT(*) FROM usage_quotas`).Scan(&n); err != nil || n != 0 {
					t.Fatalf("rollback rows=%d err=%v", n, err)
				}
			}
		})
	}
}
func TestQuotaLegacyDuplicateAndNegativeRowsFailClosed(t *testing.T) {
	for _, column := range []string{"user_id", "ip_addr"} {
		t.Run(column, func(t *testing.T) {
			db := quotaDB(t)
			tracker := NewUsageTracker(db)
			quotaExec(t, db, `DROP INDEX idx_usage_user_period_unique`)
			quotaExec(t, db, `DROP INDEX idx_usage_ip_period_unique`)
			start, end := currentPeriod()
			for _, id := range []string{"one", "two"} {
				quotaExec(t, db, `INSERT INTO usage_quotas(id,`+column+`,period_start,period_end) VALUES($1,$2,$3,$4)`, id, "identity", start, end)
			}
			restarted := NewUsageTracker(db)
			if restarted.Ready() == nil {
				t.Fatal("duplicate migration allowed")
			}
			user, ip := "identity", ""
			if column == "ip_addr" {
				user, ip = "", "identity"
			}
			if _, err := tracker.GetUsageChecked(user, ip); !errors.Is(err, ErrUsageUnavailable) {
				t.Fatalf("duplicate query: %v", err)
			}
			if _, err := tracker.RecordScanWithLimit(user, ip, 10); !errors.Is(err, ErrUsageUnavailable) {
				t.Fatalf("duplicate record: %v", err)
			}
			var n int
			db.QueryRow(`SELECT COUNT(*) FROM usage_quotas`).Scan(&n)
			if n != 2 {
				t.Fatal("legacy rows modified")
			}
		})
	}
	db := quotaDB(t)
	tracker := NewUsageTracker(db)
	start, end := currentPeriod()
	quotaExec(t, db, `INSERT INTO usage_quotas(id,user_id,scans_used,period_start,period_end) VALUES('negative','u',-1,$1,$2)`, start, end)
	if _, err := tracker.GetUsageChecked("u", ""); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
	if _, err := tracker.RecordScanWithLimit("u", "", 10); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
}
func TestQuotaUnavailableAndPlanChanges(t *testing.T) {
	tracker := NewUsageTracker(nil)
	if _, err := tracker.RecordScanWithLimit("u", "", 10); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
	if _, err := tracker.GetUsageChecked("u", ""); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
	db := quotaDB(t)
	tracker = NewUsageTracker(db)
	for _, limit := range []int{1, 3, -1} {
		if _, err := tracker.RecordScanWithLimit("u", "", limit); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := tracker.RecordScanWithLimit("u", "", 2); !errors.Is(err, ErrQuotaExceeded) {
		t.Fatal(err)
	}
	info, err := tracker.GetUsageChecked("u", "")
	if err != nil || info.ScansUsed != 3 || !info.Unlimited {
		t.Fatalf("%+v %v", info, err)
	}
	db.Close()
	if _, err := tracker.GetUsageChecked("u", ""); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
}

// A driver outside the explicitly supported SQL contracts is never attempted.
type unsupportedQuotaDriver struct{}

func (unsupportedQuotaDriver) Open(string) (driver.Conn, error) {
	return nil, errors.New("unexpected driver open")
}
func init() { sql.Register("quota-unsupported-fixture", unsupportedQuotaDriver{}) }
func TestQuotaUnsupportedDriverAndInitializationFailure(t *testing.T) {
	db, err := sql.Open("quota-unsupported-fixture", "")
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	tracker := NewUsageTracker(db)
	if !errors.Is(tracker.Ready(), ErrUsageUnavailable) {
		t.Fatal("unsupported SQL driver accepted")
	}
	realDB := quotaDB(t)
	quotaExec(t, realDB, `CREATE TABLE usage_quotas (id TEXT PRIMARY KEY)`)
	tracker = NewUsageTracker(realDB)
	if !errors.Is(tracker.Ready(), ErrUsageUnavailable) {
		t.Fatal("malformed legacy schema accepted")
	}
	if _, err = tracker.RecordScanWithLimit("authenticated", "", 100); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatalf("initialization failure bypass: %v", err)
	}
}

func TestQuotaInvalidStoredLimitAndOverflowFailClosed(t *testing.T) {
	for _, values := range []struct{ used, limit int }{{0, -1}, {2147483647, 0}} {
		t.Run(fmt.Sprintf("%d_%d", values.used, values.limit), func(t *testing.T) {
			db := quotaDB(t)
			tracker := NewUsageTracker(db)
			start, end := currentPeriod()
			quotaExec(t, db, `INSERT INTO usage_quotas(id,user_id,scans_used,scans_limit,period_start,period_end) VALUES('invalid','u',$1,$2,$3,$4)`, values.used, values.limit, start, end)
			if _, err := tracker.RecordScanWithLimit("u", "", -1); !errors.Is(err, ErrUsageUnavailable) {
				t.Fatal(err)
			}
			var used int
			if err := db.QueryRow(`SELECT scans_used FROM usage_quotas`).Scan(&used); err != nil || used != values.used {
				t.Fatal("invalid counter changed")
			}
		})
	}
	tracker := NewUsageTracker(quotaDB(t))
	if _, err := tracker.RecordScanWithLimit("u", "", 0); !errors.Is(err, ErrQuotaExceeded) {
		t.Fatal(err)
	}
	if _, err := tracker.RecordScanWithLimit("u", "", -2); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatal(err)
	}
}

func TestQuotaIndependentSQLiteHandlesNeverOvershoot(t *testing.T) {
	path := filepath.Join(t.TempDir(), "shared-quota.db")
	open := func() *sql.DB {
		db, err := sql.Open("sqlite", path)
		if err != nil {
			t.Fatal(err)
		}
		db.SetMaxOpenConns(1)
		t.Cleanup(func() { db.Close() })
		return db
	}
	first, second := open(), open()
	a, b := NewUsageTracker(first), NewUsageTracker(second)
	if err := a.Ready(); err != nil {
		t.Fatal(err)
	}
	if err := b.Ready(); err != nil {
		t.Fatal(err)
	}
	// Two independent pools and trackers start against the same persisted identity.
	var accepted atomic.Int64
	var wg sync.WaitGroup
	start := make(chan struct{})
	for i := 0; i < 40; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			<-start
			tracker := a
			if i%2 == 1 {
				tracker = b
			}
			_, err := tracker.RecordScanWithLimit("shared-user", "", 5)
			switch {
			case err == nil:
				accepted.Add(1)
			case errors.Is(err, ErrQuotaExceeded):
			case errors.Is(err, ErrUsageUnavailable):
			default:
				t.Errorf("unexpected error %v", err)
			}
		}(i)
	}
	close(start)
	wg.Wait()
	var rows, used int
	if err := first.QueryRow(`SELECT COUNT(*),COALESCE(SUM(scans_used),0) FROM usage_quotas`).Scan(&rows, &used); err != nil {
		t.Fatal(err)
	}
	if rows != 1 || accepted.Load() < 1 || accepted.Load() > 5 || int64(used) != accepted.Load() {
		t.Fatalf("rows=%d persisted=%d accepted=%d", rows, used, accepted.Load())
	}
	// SQLite may explicitly reject a contending transaction as unavailable. That
	// rejected call must not consume quota; fill only the remaining durable cap.
	for used < 5 {
		if _, err := a.RecordScanWithLimit("shared-user", "", 5); err != nil {
			t.Fatal(err)
		}
		used++
	}
	if _, err := b.RecordScanWithLimit("shared-user", "", 5); !errors.Is(err, ErrQuotaExceeded) {
		t.Fatalf("overshoot permitted: %v", err)
	}
}
