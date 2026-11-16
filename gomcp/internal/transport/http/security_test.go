package httpserver

import (
	"testing"
)

// TestPromptHash_FullSHA256 verifies that promptHash returns a full
// 256-bit (64 hex char) hash, not truncated 128-bit (32 hex char).
// Regression test for T4-4 cache key truncation fix.
func TestPromptHash_FullSHA256(t *testing.T) {
	hash := promptHash("test prompt for hash length verification")

	// SHA-256 = 32 bytes = 64 hex characters
	if len(hash) != 64 {
		t.Fatalf("expected 64 hex chars (256-bit SHA-256), got %d chars: %s", len(hash), hash)
	}

	// Verify determinism
	hash2 := promptHash("test prompt for hash length verification")
	if hash != hash2 {
		t.Fatal("promptHash should be deterministic")
	}

	// Verify different input → different hash
	hash3 := promptHash("different prompt")
	if hash == hash3 {
		t.Fatal("different inputs should produce different hashes")
	}
}

// TestHasPermission_AllRoleCombinations exercises the full 5×5 matrix
// of valid roles plus undefined roles to verify default-deny behavior.
func TestHasPermission_AllRoleCombinations(t *testing.T) {
	// Expected permission matrix (row=user, col=required)
	// A=Admin(100), An=Analyst(50), V=Viewer(30), S=Sensor(20), E=External(10)
	type tc struct {
		user    Role
		req     Role
		allowed bool
	}

	tests := []tc{
		// Admin can access everything
		{RoleAdmin, RoleAdmin, true},
		{RoleAdmin, RoleAnalyst, true},
		{RoleAdmin, RoleViewer, true},
		{RoleAdmin, RoleSensor, true},
		{RoleAdmin, RoleExternal, true},

		// Analyst: yes for Analyst, Viewer, Sensor, External; no for Admin
		{RoleAnalyst, RoleAdmin, false},
		{RoleAnalyst, RoleAnalyst, true},
		{RoleAnalyst, RoleViewer, true},
		{RoleAnalyst, RoleSensor, true},
		{RoleAnalyst, RoleExternal, true},

		// Viewer: yes for Viewer, Sensor, External; no for Admin, Analyst
		{RoleViewer, RoleAdmin, false},
		{RoleViewer, RoleAnalyst, false},
		{RoleViewer, RoleViewer, true},
		{RoleViewer, RoleSensor, true},
		{RoleViewer, RoleExternal, true},

		// Sensor: yes for Sensor, External; no for Admin, Analyst, Viewer
		{RoleSensor, RoleAdmin, false},
		{RoleSensor, RoleAnalyst, false},
		{RoleSensor, RoleViewer, false},
		{RoleSensor, RoleSensor, true},
		{RoleSensor, RoleExternal, true},

		// External: yes for External only
		{RoleExternal, RoleAdmin, false},
		{RoleExternal, RoleAnalyst, false},
		{RoleExternal, RoleViewer, false},
		{RoleExternal, RoleSensor, false},
		{RoleExternal, RoleExternal, true},

		// Undefined roles — all denied (default-deny, P3 fix)
		{Role("root"), RoleViewer, false},
		{RoleAdmin, Role("superadmin"), false},
		{Role(""), Role(""), false},
		{Role("hacker"), Role("hacker"), false},
	}

	for _, tt := range tests {
		got := hasPermission(tt.user, tt.req)
		if got != tt.allowed {
			t.Errorf("hasPermission(%q, %q) = %v, want %v", tt.user, tt.req, got, tt.allowed)
		}
	}
}
