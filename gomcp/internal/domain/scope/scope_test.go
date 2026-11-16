package scope

import (
	"context"
	"strings"
	"testing"
)

// The tenant/project isolation primitive had no tests at all.
//
// Found 2026-08-05 while adding Go to the gate: of the 16 packages `go test ./...` reported as
// having no test files, ten are `cmd/*` entry points and one is `docs`, but this one decides which
// tenant's memory a request reads and writes. 152 lines, load-bearing, unverified — not because
// anyone chose that, but because nothing had ever run the Go suite.
//
// These tests pin behaviour rather than propose changes. One of the properties they pin is
// uncomfortable and deliberate — see TestAnEmptyScopeSilentlyBecomesTheSharedDefault.

func TestNormalizeFillsAndTrims(t *testing.T) {
	got := New("  acme  ", "  billing  ")
	if got.TenantID != "acme" || got.ProjectID != "billing" {
		t.Fatalf("New did not trim: %+v", got)
	}
	// Padding must not create a distinct tenant. " acme" and "acme" addressing different memory
	// would be an isolation bug that looks like a typo.
	if New(" acme", "billing") != New("acme", "billing ") {
		t.Fatal("whitespace produces distinct scopes")
	}
}

func TestAnEmptyScopeSilentlyBecomesTheSharedDefault(t *testing.T) {
	// This is FAIL-OPEN, and it is pinned here so it is a known property rather than a surprise.
	//
	// `New("", "")` does not error — it returns local/default, the shared backward-compatible
	// scope. So a code path that loses the tenant id does not fail; it reads and writes the
	// default tenant's memory. That is intentional for single-project installs and it is exactly
	// the shape isolation bugs hide in on multi-tenant ones.
	//
	// `Validate()` cannot catch it either: `Normalize()` runs first, so by the time validation
	// sees the scope the empty value is already gone. Anything deriving a scope from untrusted
	// input has to reject empty ITSELF, before calling New — this test exists so that
	// requirement is written down somewhere.
	empty := New("", "")
	if !empty.IsDefault() {
		t.Fatalf("New(\"\",\"\") = %+v, expected the default scope", empty)
	}
	if err := empty.Validate(); err != nil {
		t.Fatalf("Validate rejected the normalised default: %v", err)
	}
	if empty != Default() {
		t.Fatalf("New(\"\",\"\") = %+v but Default() = %+v", empty, Default())
	}
}

func TestFromContextFallsBackToDefaultAndLookupDoesNot(t *testing.T) {
	bare := context.Background()

	// FromContext is the convenient accessor and it fails open by design.
	if got := FromContext(bare); !got.IsDefault() {
		t.Fatalf("FromContext on a bare context = %+v, expected default", got)
	}
	// Lookup is the honest one: it reports whether a scope was actually carried. Any decision
	// that must not silently land in the default tenant has to use this, not FromContext.
	if _, ok := Lookup(bare); ok {
		t.Fatal("Lookup claimed a scope on a context that carries none")
	}

	scoped := WithScope(bare, New("acme", "billing"))
	got, ok := Lookup(scoped)
	if !ok {
		t.Fatal("Lookup found no scope after WithScope")
	}
	if got.TenantID != "acme" || got.ProjectID != "billing" {
		t.Fatalf("round trip lost the scope: %+v", got)
	}
}

func TestWithScopeNormalizesWhatItStores(t *testing.T) {
	// Otherwise a padded id would round-trip as a distinct tenant through the context, which is
	// the same isolation bug as above wearing a different hat.
	got := FromContext(WithScope(context.Background(), Scope{TenantID: " acme ", ProjectID: ""}))
	if got.TenantID != "acme" {
		t.Errorf("tenant not normalised through context: %q", got.TenantID)
	}
	if got.ProjectID != DefaultProjectID {
		t.Errorf("empty project not defaulted through context: %q", got.ProjectID)
	}
}

func TestValidateIDRejectsWhatMustNotBecomeAnIdentifier(t *testing.T) {
	rejected := map[string]string{
		"empty":              "",
		"whitespace only":    "   ",
		"slash":              "acme/billing",
		"backslash":          "acme\\billing",
		"percent":            "acme%20b",
		"quote":              "acme'--",
		"space inside":       "acme corp",
		"null byte":          "acme\x00",
		"newline":            "acme\nbilling",
		"cyrillic homograph": "асme", // а/с are Cyrillic: must not pass as the ASCII name
		"too long":           strings.Repeat("a", 129),
	}
	for name, id := range rejected {
		if err := ValidateID("tenant_id", id); err == nil {
			t.Errorf("%s: ValidateID accepted %q", name, id)
		}
	}

	accepted := []string{"acme", "acme-corp", "acme_corp", "acme.corp", "ACME9", strings.Repeat("a", 128)}
	for _, id := range accepted {
		if err := ValidateID("tenant_id", id); err != nil {
			t.Errorf("ValidateID rejected %q: %v", id, err)
		}
	}
}

func TestValidateChecksBothIdentifiers(t *testing.T) {
	if err := (Scope{TenantID: "ok", ProjectID: "bad/id"}).Validate(); err == nil {
		t.Error("Validate ignored an invalid project_id")
	}
	if err := (Scope{TenantID: "bad/id", ProjectID: "ok"}).Validate(); err == nil {
		t.Error("Validate ignored an invalid tenant_id")
	}
	// The message must name which field failed, or an operator reading a log cannot tell which
	// half of the scope was wrong.
	err := (Scope{TenantID: "ok", ProjectID: "bad/id"}).Validate()
	if err == nil || !strings.Contains(err.Error(), "project_id") {
		t.Errorf("error does not name the failing field: %v", err)
	}
}

func TestStringIsStableAndDistinguishesScopes(t *testing.T) {
	// Used in logs and cache keys; two different scopes sharing a string would collide silently.
	a := New("acme", "billing").String()
	b := New("acme", "billings").String()
	c := New("acmeb", "illing").String()
	if a == b || a == c || b == c {
		t.Fatalf("distinct scopes share a string: %q %q %q", a, b, c)
	}
	if New("acme", "billing").String() != a {
		t.Fatal("String is not stable across calls")
	}
}

func TestRequireSessionScopeRejectsReservedDefaultProjectCaseInsensitively(t *testing.T) {
	for _, projectID := range []string{"default", "DEFAULT", "DeFaUlT"} {
		ctx := WithScope(context.Background(), New("local", projectID))
		_, err := RequireSessionScope(ctx, "session-one")
		if err == nil || !strings.Contains(err.Error(), "reserved for legacy memory") {
			t.Errorf("project_id %q: expected reserved legacy-memory error, got %v", projectID, err)
		}
	}

	ctx := WithScope(context.Background(), New("local", "default-v2"))
	if _, err := RequireSessionScope(ctx, "session-one"); err != nil {
		t.Fatalf("non-reserved project rejected: %v", err)
	}
}

func TestRequireExactProjectRejectsNormalizationAliasesAndLegacyLeadingPunctuation(t *testing.T) {
	for _, projectID := range []string{
		" project-alpha", "project-alpha ", ".project-alpha", "-project-alpha", "_project-alpha",
	} {
		ctx := WithScope(context.Background(), Scope{TenantID: "local", ProjectID: projectID})
		_, err := RequireExactProject(ctx)
		if err == nil {
			t.Errorf("project_id %q: expected exact-project validation error", projectID)
		}
	}

	for _, projectID := range []string{"a", "A.project_1-v2", "9project"} {
		ctx := WithScope(context.Background(), Scope{TenantID: "local", ProjectID: projectID})
		if _, err := RequireExactProject(ctx); err != nil {
			t.Errorf("project_id %q: valid exact project rejected: %v", projectID, err)
		}
	}

	ctx := WithScope(context.Background(), Scope{TenantID: " local ", ProjectID: "project-alpha"})
	if _, err := RequireExactProject(ctx); err == nil || !strings.Contains(err.Error(), "tenant_id") {
		t.Fatalf("padded tenant_id must fail exact scope validation, got %v", err)
	}
}

func TestValidateTurnIDRequiresCanonicalDigestForm(t *testing.T) {
	valid := "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	if err := ValidateTurnID(valid); err != nil {
		t.Fatalf("valid turn id rejected: %v", err)
	}
	for _, invalid := range []string{
		"", "turn_", "turn_ABCDEFaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		"turn_gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
		"turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		"other_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
	} {
		if err := ValidateTurnID(invalid); err == nil {
			t.Errorf("invalid turn id accepted: %q", invalid)
		}
	}
}
