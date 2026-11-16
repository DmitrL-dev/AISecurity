package guard

import (
	"os"
	"testing"
)

func testPolicy() *Policy {
	return &Policy{
		Version: "1.0",
		Mode:    ModeAudit,
		Processes: map[string]ProcessPolicy{
			"soc-ingest": {
				Description:     "test ingest",
				BlockedSyscalls: []string{"ptrace", "process_vm_readv"},
				AllowedFiles:    []string{"/var/lib/sentinel/data/*", "/tmp/*"},
				BlockedFiles:    []string{"/etc/shadow", "/root/*"},
				AllowedNetwork:  []string{"0.0.0.0:9750"},
				MaxMemoryMB:     512,
			},
			"soc-correlate": {
				Description:     "test correlate — no network",
				BlockedSyscalls: []string{"ptrace", "execve", "fork", "socket"},
				AllowedFiles:    []string{"/var/lib/sentinel/data/*"},
				BlockedFiles:    []string{"/etc/*", "/root/*"},
				AllowedNetwork:  []string{}, // NONE
				MaxMemoryMB:     1024,
			},
		},
	}
}

func TestCheckSyscall_Blocked(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckSyscall("soc-ingest", 1234, "ptrace")
	if v == nil {
		t.Fatal("expected violation for ptrace")
	}
	if v.Severity != "CRITICAL" {
		t.Errorf("severity = %s, want CRITICAL", v.Severity)
	}
	if v.Action != "logged" {
		t.Errorf("action = %s, want logged (audit mode)", v.Action)
	}
}

func TestCheckSyscall_Allowed(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckSyscall("soc-ingest", 1234, "read")
	if v != nil {
		t.Errorf("unexpected violation for read: %+v", v)
	}
}

func TestCheckSyscall_EnforceMode(t *testing.T) {
	p := testPolicy()
	p.Mode = ModeEnforce
	g := New(p)

	v := g.CheckSyscall("soc-correlate", 5678, "execve")
	if v == nil {
		t.Fatal("expected violation for execve")
	}
	if v.Action != "blocked" {
		t.Errorf("action = %s, want blocked (enforce mode)", v.Action)
	}
}

func TestCheckSyscall_UnknownProcess(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckSyscall("unknown-proc", 9999, "ptrace")
	if v != nil {
		t.Errorf("expected nil for unknown process, got %+v", v)
	}
}

func TestCheckFileAccess_Blocked(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckFileAccess("soc-ingest", 1234, "/etc/shadow")
	if v == nil {
		t.Fatal("expected violation for /etc/shadow")
	}
	if v.Severity != "HIGH" {
		t.Errorf("severity = %s, want HIGH", v.Severity)
	}
}

func TestCheckFileAccess_Allowed(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckFileAccess("soc-ingest", 1234, "/var/lib/sentinel/data/soc.db")
	if v != nil {
		t.Errorf("unexpected violation for allowed path: %+v", v)
	}
}

func TestCheckFileAccess_Unauthorized(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckFileAccess("soc-ingest", 1234, "/opt/something/secret")
	if v == nil {
		t.Fatal("expected violation for unauthorized path")
	}
	if v.Severity != "MEDIUM" {
		t.Errorf("severity = %s, want MEDIUM", v.Severity)
	}
}

func TestCheckNetwork_NoNetworkAllowed(t *testing.T) {
	g := New(testPolicy())

	// soc-correlate has AllowedNetwork: [] — no network at all.
	v := g.CheckNetwork("soc-correlate", 5678, "8.8.8.8:443")
	if v == nil {
		t.Fatal("expected violation for network on correlate")
	}
	if v.Severity != "CRITICAL" {
		t.Errorf("severity = %s, want CRITICAL", v.Severity)
	}
}

func TestCheckMemory_Exceeded(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckMemory("soc-ingest", 1234, 600) // 600MB > 512MB limit
	if v == nil {
		t.Fatal("expected violation for memory exceeded")
	}
	if v.Severity != "HIGH" {
		t.Errorf("severity = %s, want HIGH", v.Severity)
	}
}

func TestCheckMemory_Within(t *testing.T) {
	g := New(testPolicy())

	v := g.CheckMemory("soc-ingest", 1234, 400) // 400MB < 512MB
	if v != nil {
		t.Errorf("unexpected violation for memory within limit: %+v", v)
	}
}

func TestStats(t *testing.T) {
	g := New(testPolicy())

	g.CheckSyscall("soc-ingest", 1, "ptrace")
	g.CheckSyscall("soc-ingest", 1, "process_vm_readv")
	g.CheckFileAccess("soc-ingest", 1, "/etc/shadow")

	stats := g.Stats()
	if stats.Violations != 3 {
		t.Errorf("violations = %d, want 3", stats.Violations)
	}
	if stats.ByProcess["soc-ingest"] != 3 {
		t.Errorf("by_process[soc-ingest] = %d, want 3", stats.ByProcess["soc-ingest"])
	}
	if stats.ByType["syscall"] != 2 {
		t.Errorf("by_type[syscall] = %d, want 2", stats.ByType["syscall"])
	}
}

func TestSetMode(t *testing.T) {
	g := New(testPolicy())
	if g.CurrentMode() != ModeAudit {
		t.Fatalf("initial mode = %s, want audit", g.CurrentMode())
	}

	g.SetMode(ModeEnforce)
	if g.CurrentMode() != ModeEnforce {
		t.Errorf("mode after set = %s, want enforce", g.CurrentMode())
	}
}

func TestViolationHandler(t *testing.T) {
	g := New(testPolicy())

	var received []Violation
	g.OnViolation(func(v Violation) {
		received = append(received, v)
	})

	g.CheckSyscall("soc-ingest", 1, "ptrace")

	if len(received) != 1 {
		t.Fatalf("handler received %d violations, want 1", len(received))
	}
	if received[0].Type != "syscall" {
		t.Errorf("type = %s, want syscall", received[0].Type)
	}
}

func TestLoadPolicy(t *testing.T) {
	// Write temp policy file.
	content := `
version: "1.0"
mode: enforce
processes:
  test-proc:
    blocked_syscalls: [ptrace]
    allowed_files: [/tmp/*]
`
	tmpFile := t.TempDir() + "/test_policy.yaml"
	if err := writeFile(tmpFile, content); err != nil {
		t.Fatalf("write temp policy: %v", err)
	}

	policy, err := LoadPolicy(tmpFile)
	if err != nil {
		t.Fatalf("LoadPolicy: %v", err)
	}
	if policy.Mode != ModeEnforce {
		t.Errorf("mode = %s, want enforce", policy.Mode)
	}
	if _, ok := policy.Processes["test-proc"]; !ok {
		t.Error("expected test-proc in processes")
	}
}

func writeFile(path, content string) error {
	return os.WriteFile(path, []byte(content), 0644)
}
