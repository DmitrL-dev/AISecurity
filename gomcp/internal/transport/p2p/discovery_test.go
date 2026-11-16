package transport

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// shortID must never slice-panic on short, untrusted peer IDs (announcements
// arrive as untrusted UDP broadcasts and are logged from a recovery-less
// goroutine — a sub-8-char peer_id previously crashed the process).
func TestShortID_NoPanicOnShortInput(t *testing.T) {
	cases := map[string]string{
		"":          "",
		"a":         "a",
		"1234567":   "1234567",
		"12345678":  "12345678",
		"123456789": "12345678",
	}
	for in, want := range cases {
		assert.NotPanics(t, func() {
			assert.Equal(t, want, shortID(in))
		}, "shortID(%q)", in)
	}
}
