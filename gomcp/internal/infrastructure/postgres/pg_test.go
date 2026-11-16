package postgres

import (
	"strings"
	"testing"
)

// `redactDSN` had a real leak and no test.
//
// The comment above it records what happened: «Review 14.06 round-3: the previous slice-based
// redaction leaked the username and the start of the password, which sit at the FRONT of the
// DSN.» The fix landed; nothing pinned it. This whole package had zero test files until
// 2026-08-06 — found when Go first entered the gate, which is also the first time anything ran
// its tests.
//
// A redaction function is the right place to spend care: it is called precisely when something
// has gone wrong and a DSN is about to be written somewhere durable, and the failure is silent —
// a leaked credential in a log looks exactly like a redacted one until somebody reads it.
//
// Note on scope: this package is NOT deployed. Neither contour runs a SOC container (checked
// 2026-08-06: `docker ps -a` shows none on RU or Global), and the RU override points
// SOC_INTERNAL_URL at `soc-plane-disabled.invalid`. So these are tests for latent code, written
// because it is cheaper to pin a pure function now than to rediscover the leak when the plane
// ships.

func TestRedactDSNKeepsNoCredentialMaterial(t *testing.T) {
	cases := []struct {
		name string
		dsn  string
		must []string // substrings that MUST NOT survive
	}{
		{
			name: "user and password in userinfo",
			dsn:  "postgres://socuser:sup3rs3cret@db.internal:5432/soc",
			must: []string{"socuser", "sup3rs3cret", "sup3r", "s3cret"},
		},
		{
			name: "password in query, which is where libpq also accepts it",
			dsn:  "postgres://db.internal:5432/soc?password=sup3rs3cret&sslmode=require",
			must: []string{"sup3rs3cret", "password="},
		},
		{
			name: "user only, no password",
			dsn:  "postgres://socuser@db.internal:5432/soc",
			must: []string{"socuser"},
		},
		{
			name: "empty password still means the username must go",
			dsn:  "postgres://socuser:@db.internal:5432/soc",
			must: []string{"socuser"},
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := redactDSN(c.dsn)
			for _, forbidden := range c.must {
				if strings.Contains(got, forbidden) {
					t.Errorf("redacted DSN still contains %q: %q", forbidden, got)
				}
			}
			// What it must KEEP, or the log line is useless for diagnosis.
			if !strings.Contains(got, "db.internal:5432") {
				t.Errorf("host was dropped, leaving nothing to diagnose with: %q", got)
			}
		})
	}
}

func TestRedactDSNRefusesToGuessAtWhatItCannotParse(t *testing.T) {
	// Keyword-style DSNs are valid for libpq and are NOT URLs. The function returns "***"
	// rather than attempting a partial redaction, and that is the right call: a partial
	// redaction of an unparsed string is how the original leak worked.
	for _, dsn := range []string{
		"host=db.internal port=5432 user=socuser password=sup3rs3cret dbname=soc",
		"not a dsn at all",
		"",
		"postgres://",          // parses, but no host
		"://db.internal/soc",   // malformed scheme
	} {
		got := redactDSN(dsn)
		if got != "***" {
			t.Errorf("redactDSN(%q) = %q, want \"***\" — an unparseable DSN must not be "+
				"partially echoed", dsn, got)
		}
	}
}

func TestRedactDSNIsStableAndCarriesTheDatabaseName(t *testing.T) {
	const dsn = "postgres://u:p@db.internal:5432/soc"
	first := redactDSN(dsn)
	if first != redactDSN(dsn) {
		t.Fatal("redactDSN is not deterministic")
	}
	// Scheme, host and path are what an operator needs to tell one deployment from another;
	// dropping the path would make two DSNs on the same host indistinguishable in a log.
	for _, want := range []string{"postgres://", "db.internal:5432", "/soc"} {
		if !strings.Contains(first, want) {
			t.Errorf("redacted DSN lost %q: %q", want, first)
		}
	}
}
