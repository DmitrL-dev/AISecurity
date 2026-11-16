package soc

import (
	"bytes"
	"log/slog"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Round-6 B-2: waitlist PII now lives in a DELETABLE store. Entries persist, are
// retrievable (so the business can contact signups), and are erasable per subject.
func TestWaitlist_PersistRetrieveDelete(t *testing.T) {
	svc := newTestService(t)

	require.NoError(t, svc.AddWaitlistEntry("alice@example.com", "ACME", "agents"))
	require.NoError(t, svc.AddWaitlistEntry("bob@example.com", "BetaCo", "ide"))

	// Retrievable, newest-first, with the cleartext intact (the business needs it).
	entries, err := svc.ListWaitlist(0)
	require.NoError(t, err)
	require.Len(t, entries, 2)
	got := map[string]string{} // email -> company
	for _, e := range entries {
		got[e.Email] = e.Company
		assert.NotEmpty(t, e.ID, "entry must have a generated ID")
		assert.False(t, e.CreatedAt.IsZero(), "entry must have a timestamp")
	}
	assert.Equal(t, "ACME", got["alice@example.com"])
	assert.Equal(t, "BetaCo", got["bob@example.com"])

	// Erasure path (GDPR Art.17): delete one subject by email.
	n, err := svc.DeleteWaitlistEntry("alice@example.com")
	require.NoError(t, err)
	assert.Equal(t, int64(1), n)

	entries, err = svc.ListWaitlist(0)
	require.NoError(t, err)
	require.Len(t, entries, 1)
	assert.Equal(t, "bob@example.com", entries[0].Email, "only the non-erased subject remains")

	// Deleting a missing email is a no-op (idempotent), and empty email is refused.
	n, err = svc.DeleteWaitlistEntry("nobody@example.com")
	require.NoError(t, err)
	assert.Equal(t, int64(0), n)
	_, err = svc.DeleteWaitlistEntry("")
	assert.Error(t, err, "empty email must be refused (never wipe the whole table)")
}

// The application log must carry NO cleartext PII — only a non-PII correlation
// prefix. (The full salted hash still goes to the audit chain; here logger is nil.)
func TestWaitlist_NoCleartextPIIInLogs(t *testing.T) {
	svc := newTestService(t)

	var buf bytes.Buffer
	old := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&buf, nil)))
	defer slog.SetDefault(old)

	const (
		email   = "carol@secret-domain-xyz.com"
		company = "ConfidentialCorpName"
		useCase = "highly-private-use-case-text"
	)
	require.NoError(t, svc.AddWaitlistEntry(email, company, useCase))

	logged := buf.String()
	assert.NotContains(t, logged, email, "raw email must not appear in logs")
	assert.NotContains(t, logged, company, "company must not appear in logs")
	assert.NotContains(t, logged, useCase, "use_case must not appear in logs")
	assert.Contains(t, logged, "email_sha256_prefix", "a non-PII correlation prefix should be logged")
}
