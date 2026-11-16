package auth

import (
	"database/sql"
	"errors"
	_ "github.com/jackc/pgx/v5/stdlib"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
)

func TestQuotaPostgresPrivateFixture(t *testing.T) {
	dsn := os.Getenv("SPECTORN_TEST_PG_DSN")
	if dsn == "" {
		t.Skip("private PostgreSQL fixture not supplied")
	}
	u, err := url.Parse(dsn)
	if err != nil || u.Hostname() != "audit-socket.invalid" || !strings.HasPrefix(u.Query().Get("host"), "/workspace/tmp/pgf-") || u.Query().Get("sslmode") != "disable" {
		t.Fatal("refusing non-fixture database")
	}
	socket := u.Query().Get("host")
	parent := filepath.Dir(socket)
	if filepath.Clean(socket) != socket || filepath.Base(socket) != "s" || filepath.Dir(parent) != "/workspace/tmp" || !strings.HasPrefix(filepath.Base(parent), "pgf-") {
		t.Fatal("refusing socket outside disposable fixture")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal(err)
	}
	quotaExec(t, db, `CREATE SCHEMA audit_quota_private`)
	db.Close()
	q := u.Query()
	q.Set("search_path", "audit_quota_private")
	u.RawQuery = q.Encode()
	db, err = sql.Open("pgx", u.String())
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(4)
	a, b := NewUsageTracker(db), NewUsageTracker(db)
	if err = a.Ready(); err != nil {
		t.Fatal(err)
	}
	var success atomic.Int64
	var wg sync.WaitGroup
	for i := 0; i < 30; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			tracker := a
			if i%2 == 1 {
				tracker = b
			}
			_, err := tracker.RecordScanWithLimit("user", "", 5)
			if err == nil {
				success.Add(1)
			} else if !errors.Is(err, ErrQuotaExceeded) {
				t.Errorf("record: %v", err)
			}
		}(i)
	}
	wg.Wait()
	info, err := a.GetUsageChecked("user", "")
	if err != nil || success.Load() != 5 || info.ScansUsed != 5 {
		t.Fatalf("success=%d info=%+v err=%v", success.Load(), info, err)
	}
	if remaining, err := a.RecordScanForOwner("canonical-fixture-owner", "canonical-fixture@example.invalid", "", 1); err != nil || remaining != 0 {
		t.Fatalf("canonical owner: remaining=%d error=%v", remaining, err)
	}
	if _, err := b.RecordScanForOwner("canonical-fixture-owner", "canonical-fixture@example.invalid", "", 1); !errors.Is(err, ErrQuotaExceeded) {
		t.Fatalf("canonical cap: %v", err)
	}
	if _, err := a.RecordScanWithLimit("legacy-fixture@example.invalid", "", 1); err != nil {
		t.Fatal(err)
	}
	if _, err := a.RecordScanForOwner("legacy-fixture-owner", "legacy-fixture@example.invalid", "", 1); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatalf("legacy alias admitted: %v", err)
	}
	if _, err := a.GetUsageForOwnerChecked("legacy-fixture-owner", "legacy-fixture@example.invalid", ""); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatalf("legacy usage reset: %v", err)
	}
	var canonicalRows int
	if err := db.QueryRow(`SELECT COUNT(*) FROM usage_quotas WHERE user_id='legacy-fixture-owner'`).Scan(&canonicalRows); err != nil || canonicalRows != 0 {
		t.Fatal("legacy alias created canonical quota")
	}
	quotaExec(t, db, `CREATE TABLE quota_parent(id INTEGER PRIMARY KEY)`)
	quotaExec(t, db, `CREATE TABLE quota_child(id INTEGER REFERENCES quota_parent(id) DEFERRABLE INITIALLY DEFERRED)`)
	quotaExec(t, db, `CREATE FUNCTION quota_commit_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO quota_child VALUES(1); RETURN NEW; END $$`)
	quotaExec(t, db, `CREATE TRIGGER quota_fail_commit AFTER UPDATE ON usage_quotas FOR EACH ROW EXECUTE FUNCTION quota_commit_fault()`)
	if _, err = a.RecordScanWithLimit("commit-fault", "", -1); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatalf("commit fault: %v", err)
	}
	var n int
	if err = db.QueryRow(`SELECT COUNT(*) FROM usage_quotas WHERE user_id='commit-fault'`).Scan(&n); err != nil || n != 0 {
		t.Fatal("failed commit persisted")
	}
	quotaExec(t, db, `DROP TRIGGER quota_fail_commit ON usage_quotas`)
	quotaExec(t, db, `DROP INDEX idx_usage_user_period_unique`)
	start, end := currentPeriod()
	for _, id := range []string{"legacy-one", "legacy-two"} {
		quotaExec(t, db, `INSERT INTO usage_quotas(id,user_id,period_start,period_end) VALUES($1,'legacy',$2,$3)`, id, start, end)
	}
	if NewUsageTracker(db).Ready() == nil {
		t.Fatal("legacy duplicates admitted")
	}
	if _, err = a.GetUsageChecked("legacy", ""); !errors.Is(err, ErrUsageUnavailable) {
		t.Fatalf("duplicate read: %v", err)
	}
}
