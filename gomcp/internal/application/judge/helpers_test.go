package judge

import "testing"

// withEnv stubs the package-level Getenv with a fixed map for the duration of a
// test, restoring the original on cleanup. This avoids mutating the real process
// environment (so tests stay parallel-safe and hermetic).
func withEnv(t *testing.T, m map[string]string) {
	t.Helper()
	orig := Getenv
	Getenv = func(key string) string { return m[key] }
	t.Cleanup(func() { Getenv = orig })
}
