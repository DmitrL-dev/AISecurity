package auth

import (
	"database/sql"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
	"time"
)

func lastUsed(t *testing.T, db *sql.DB, key string) sql.NullString {
	t.Helper()
	// A string, not a time: whether it is set is the question, and the sqlite driver need not parse TIMESTAMPTZ.
	var at sql.NullString
	if err := db.QueryRow(`SELECT last_used FROM api_keys WHERE key_hash = $1`, hashKey(key)).Scan(&at); err != nil {
		t.Fatal(err)
	}
	return at
}

// The write used to run in a goroutine nobody waited for. Its result is now visible the moment
// ValidateAPIKey returns, which is also what makes closing the database right after it safe.
func TestValidateAPIKeyWritesLastUsedBeforeReturning(t *testing.T) {
	db, users, _, u := durableFixture(t)
	key, _, err := users.CreateAPIKey(u.ID, "fixture", "admin")
	if err != nil {
		t.Fatal(err)
	}
	if lastUsed(t, db, key).Valid {
		t.Fatal("a fresh key already has last_used")
	}
	if _, _, err := users.ValidateAPIKey(key); err != nil {
		t.Fatal(err)
	}
	if !lastUsed(t, db, key).Valid {
		t.Fatal("last_used was not written by the time ValidateAPIKey returned")
	}
}

func TestValidateAPIKeyWritesLastUsedAtMostOncePerResolution(t *testing.T) {
	db, users, _, u := durableFixture(t)
	key, _, err := users.CreateAPIKey(u.ID, "fixture", "admin")
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := users.ValidateAPIKey(key); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(`UPDATE api_keys SET last_used = NULL WHERE key_hash = $1`, hashKey(key)); err != nil {
		t.Fatal(err)
	}
	if _, _, err := users.ValidateAPIKey(key); err != nil {
		t.Fatal(err)
	}
	if lastUsed(t, db, key).Valid {
		t.Fatal("a second use inside the resolution wrote last_used again")
	}

	// Once the resolution has passed, the next use writes it.
	users.mu.Lock()
	users.lastUsedWritten[hashKey(key)] = time.Now().Add(-lastUsedResolution)
	users.mu.Unlock()
	if _, _, err := users.ValidateAPIKey(key); err != nil {
		t.Fatal(err)
	}
	if !lastUsed(t, db, key).Valid {
		t.Fatal("a use after the resolution did not write last_used")
	}
}

// A database call started with `go` outlives whatever was supposed to own it: nothing waits for it
// before the database closes. One did, and it failed the CI go leg on 2026-10-27. This keeps the
// next one out of gomcp's production code.
var detachedDatabaseCall = regexp.MustCompile(`\bgo\s+[A-Za-z_][A-Za-z0-9_.]*\.(Exec|ExecContext|Query|QueryContext|QueryRow|QueryRowContext)\(`)

func detachedDatabaseCalls(source string) []string {
	var found []string
	for i, line := range strings.Split(source, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "//") {
			continue
		}
		if detachedDatabaseCall.MatchString(line) {
			found = append(found, strings.TrimSpace(line)+" (line "+strconv.Itoa(i+1)+")")
		}
	}
	return found
}

func TestNoProductionCodeStartsADetachedDatabaseCall(t *testing.T) {
	root := filepath.Join("..", "..", "..")
	offenders := map[string][]string{}
	scanned := 0
	sawUsers := false
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() && (d.Name() == "vendor" || d.Name() == "node_modules" || strings.HasPrefix(d.Name(), ".")) && path != root {
			return filepath.SkipDir
		}
		if d.IsDir() || !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		scanned++
		if filepath.Base(path) == "users.go" && strings.Contains(path, "auth") {
			sawUsers = true
		}
		source, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if found := detachedDatabaseCalls(string(source)); len(found) > 0 {
			offenders[path] = found
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	// A walk that finds nothing passes vacuously; this one must have read the file the defect lived in.
	if scanned < 50 || !sawUsers {
		t.Fatalf("walk read %d files, users.go seen: %v", scanned, sawUsers)
	}
	if len(offenders) > 0 {
		t.Fatalf("detached database calls: %v", offenders)
	}
}

func TestTheDetachedCallCheckSeesTheShape(t *testing.T) {
	for _, bad := range []string{
		"	go s.db.Exec(`UPDATE api_keys SET last_used = $1`, now)",
		"	go store.db.QueryRowContext(ctx, q)",
		"go db.Query(q)",
	} {
		if len(detachedDatabaseCalls(bad)) != 1 {
			t.Fatalf("missed: %s", bad)
		}
	}
	for _, fine := range []string{
		"	s.db.Exec(`UPDATE api_keys SET last_used = $1`, now)",
		"	// go s.db.Exec(q) was the old shape",
		"	go func() { defer wg.Done() }()",
	} {
		if len(detachedDatabaseCalls(fine)) != 0 {
			t.Fatalf("false positive: %s", fine)
		}
	}
}
