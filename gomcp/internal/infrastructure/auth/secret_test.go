package auth

import (
	"bytes"
	"testing"
)

func TestResolveSigningSecret_UsesEnvWhenStrong(t *testing.T) {
	strong := "this-is-a-sufficiently-long-secret-key-0123456789"
	t.Setenv("SOC_JWT_SECRET", strong)
	got := ResolveSigningSecret()
	if !bytes.Equal(got, []byte(strong)) {
		t.Fatalf("must use the configured SOC_JWT_SECRET verbatim")
	}
}

func TestResolveSigningSecret_RandomWhenUnset(t *testing.T) {
	t.Setenv("SOC_JWT_SECRET", "")
	a := ResolveSigningSecret()
	b := ResolveSigningSecret()
	if len(a) < MinSigningSecretBytes {
		t.Fatalf("ephemeral secret too short: %d", len(a))
	}
	if bytes.Equal(a, b) {
		t.Fatal("ephemeral secrets must be random (two calls produced the same key)")
	}
	// Must never be the old committed constant.
	if bytes.Equal(a, []byte("syntrex_game_day_secret_key_32bytes_required_here")) {
		t.Fatal("must never return the old hardcoded constant")
	}
}

func TestResolveSigningSecret_IgnoresShortSecret(t *testing.T) {
	t.Setenv("SOC_JWT_SECRET", "tooshort")
	got := ResolveSigningSecret()
	if bytes.Equal(got, []byte("tooshort")) {
		t.Fatal("a sub-32-byte secret must be ignored, not used")
	}
	if len(got) < MinSigningSecretBytes {
		t.Fatalf("fallback secret too short: %d", len(got))
	}
}
