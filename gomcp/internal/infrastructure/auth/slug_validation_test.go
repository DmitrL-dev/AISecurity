package auth

import "testing"

// Regression for the mega-review 17.06 HIGH: a public self-service org_slug must
// be a safe lowercase label AND outside the spectorn-provisioned tenant-id
// namespace, so it can never squat a victim's deterministic spectorn tenant_id.
func TestValidSelfServiceSlug(t *testing.T) {
	good := []string{"acme", "acme-corp", "a1", "my-org-123", "x9"}
	for _, s := range good {
		if !validSelfServiceSlug(s) {
			t.Errorf("expected %q to be a valid self-service slug", s)
		}
	}

	bad := map[string]string{
		"u_abcdef1234567890":  "spectorn tenant_id namespace (and underscore)",
		"tnt-abcdef":          "gomcp internal id namespace",
		"tnt_abc":             "reserved prefix + underscore",
		"Acme":                "uppercase",
		"-acme":               "leading hyphen",
		"a":                   "too short",
		"ab cd":               "space",
		"org_underscore":      "underscore not allowed",
		"":                    "empty",
		"slug.with.dots":      "dot not allowed",
	}
	for s, why := range bad {
		if validSelfServiceSlug(s) {
			t.Errorf("expected %q to be REJECTED (%s)", s, why)
		}
	}
}
