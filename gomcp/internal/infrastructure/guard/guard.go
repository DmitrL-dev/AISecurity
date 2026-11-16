// Package guard implements the SEC-002 eBPF Runtime Guard policy engine.
//
// The guard monitors SOC processes at the kernel level using eBPF tracepoints
// and enforces per-process security policies defined in YAML.
//
// Modes of operation:
//   - audit:   log violations, never block
//   - enforce: block violations via eBPF return codes
//   - alert:   send SOC events on violations
//
// On Windows/macOS: runs in audit-only mode using process monitoring fallback.
package guard

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"gopkg.in/yaml.v3"
)

// Mode defines the guard operation mode.
type Mode string

const (
	ModeAudit   Mode = "audit"   // Log only
	ModeEnforce Mode = "enforce" // Block + log
	ModeAlert   Mode = "alert"   // Alert only (SOC event)
)

// Policy is the top-level runtime guard policy.
type Policy struct {
	Version   string                   `yaml:"version"`
	Mode      Mode                     `yaml:"mode"`
	Processes map[string]ProcessPolicy `yaml:"processes"`
	Alerts    AlertConfig              `yaml:"alerts"`
}

// ProcessPolicy defines allowed/blocked behavior for a single process.
type ProcessPolicy struct {
	Description     string   `yaml:"description"`
	AllowedExec     []string `yaml:"allowed_exec"`
	BlockedSyscalls []string `yaml:"blocked_syscalls"`
	AllowedFiles    []string `yaml:"allowed_files"`
	BlockedFiles    []string `yaml:"blocked_files"`
	AllowedNetwork  []string `yaml:"allowed_network"`
	BlockedNetwork  []string `yaml:"blocked_network"`
	MaxMemoryMB     int      `yaml:"max_memory_mb"`
	MaxCPUPercent   int      `yaml:"max_cpu_percent"`
}

// AlertConfig defines alert routing.
type AlertConfig struct {
	OnViolation []string `yaml:"on_violation"`
	OnCritical  []string `yaml:"on_critical"`
}

// Violation represents a detected policy violation.
type Violation struct {
	Timestamp   time.Time `json:"timestamp"`
	ProcessName string    `json:"process_name"`
	PID         int       `json:"pid"`
	Type        string    `json:"type"`             // syscall, file, network, resource
	Detail      string    `json:"detail"`           // Specific violation description
	Severity    string    `json:"severity"`         // LOW, MEDIUM, HIGH, CRITICAL
	Action      string    `json:"action"`           // logged, blocked, alerted, killed
	SrcIP       string    `json:"src_ip,omitempty"` // peer IP for network violations (for enforcement/forwarding)
	PolicyMode  Mode      `json:"policy_mode"`
}

// ViolationHandler is called when a policy violation is detected.
type ViolationHandler func(v Violation)

// ViolationEnforcer is an optional hook that performs REAL containment for a
// violation and reports the truthful outcome. It is the honesty seam between
// detection (this package) and enforcement (cmd/immune): when set, recordViolation
// asks it what ACTUALLY happened and uses that — so the guard never counts a
// "blocked" it did not enforce. action is the verbatim outcome ("blocked",
// "killed", "logged", "alerted"); enforced is true ONLY when a real effect
// occurred. Returning ("", false) leaves the provisional action unchanged.
type ViolationEnforcer func(v Violation) (action string, enforced bool)

// Guard is the runtime guard engine.
type Guard struct {
	mu       sync.RWMutex
	policy   *Policy
	handlers []ViolationHandler
	enforcer ViolationEnforcer // optional; finalizes the truthful action
	logger   *slog.Logger
	statsMu  sync.Mutex // protects stats
	stats    GuardStats
}

// GuardStats tracks guard operation metrics.
// This is a pure data struct (no mutex) so it can be safely returned by value.
type GuardStats struct {
	TotalEvents int64            `json:"total_events"`
	Violations  int64            `json:"violations"`
	Blocked     int64            `json:"blocked"`
	ByProcess   map[string]int64 `json:"by_process"`
	ByType      map[string]int64 `json:"by_type"`
	StartedAt   time.Time        `json:"started_at"`
}

// New creates a new runtime guard with the given policy.
func New(policy *Policy) *Guard {
	return &Guard{
		policy: policy,
		logger: slog.Default().With("component", "sec-002-guard"),
		stats: GuardStats{
			ByProcess: make(map[string]int64),
			ByType:    make(map[string]int64),
			StartedAt: time.Now(),
		},
	}
}

// LoadPolicy reads and parses a YAML policy file.
func LoadPolicy(path string) (*Policy, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("guard: read policy %s: %w", path, err)
	}

	var policy Policy
	if err := yaml.Unmarshal(data, &policy); err != nil {
		return nil, fmt.Errorf("guard: parse policy %s: %w", path, err)
	}

	// Validate.
	if policy.Version == "" {
		policy.Version = "1.0"
	}
	if policy.Mode == "" {
		policy.Mode = ModeAudit
	}
	if len(policy.Processes) == 0 {
		return nil, fmt.Errorf("guard: policy has no process definitions")
	}

	return &policy, nil
}

// OnViolation registers a handler called on every violation.
func (g *Guard) OnViolation(h ViolationHandler) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.handlers = append(g.handlers, h)
}

// CheckSyscall validates a syscall against the process policy.
func (g *Guard) CheckSyscall(processName string, pid int, syscall string) *Violation {
	g.mu.RLock()
	proc, exists := g.policy.Processes[processName]
	mode := g.policy.Mode
	g.mu.RUnlock()

	if !exists {
		return nil // Unknown process — not monitored.
	}

	for _, blocked := range proc.BlockedSyscalls {
		if strings.EqualFold(blocked, syscall) {
			v := Violation{
				Timestamp:   time.Now(),
				ProcessName: processName,
				PID:         pid,
				Type:        "syscall",
				Detail:      fmt.Sprintf("blocked syscall: %s", syscall),
				Severity:    syscallSeverity(syscall),
				PolicyMode:  mode,
			}

			switch mode {
			case ModeEnforce:
				v.Action = "blocked"
			case ModeAudit:
				v.Action = "logged"
			case ModeAlert:
				v.Action = "alerted"
			}

			g.recordViolation(v)
			return &v
		}
	}

	return nil
}

// CheckFileAccess validates file access against the process policy.
func (g *Guard) CheckFileAccess(processName string, pid int, filepath string) *Violation {
	g.mu.RLock()
	proc, exists := g.policy.Processes[processName]
	mode := g.policy.Mode
	g.mu.RUnlock()

	if !exists {
		return nil
	}

	// Check blocked files first.
	for _, pattern := range proc.BlockedFiles {
		if matchGlob(pattern, filepath) {
			v := Violation{
				Timestamp:   time.Now(),
				ProcessName: processName,
				PID:         pid,
				Type:        "file",
				Detail:      fmt.Sprintf("blocked file access: %s (pattern: %s)", filepath, pattern),
				Severity:    "HIGH",
				PolicyMode:  mode,
			}

			if mode == ModeEnforce {
				v.Action = "blocked"
			} else {
				v.Action = "logged"
			}

			g.recordViolation(v)
			return &v
		}
	}

	// Check if file is in allowed list.
	allowed := false
	for _, pattern := range proc.AllowedFiles {
		if matchGlob(pattern, filepath) {
			allowed = true
			break
		}
	}

	if !allowed && len(proc.AllowedFiles) > 0 {
		v := Violation{
			Timestamp:   time.Now(),
			ProcessName: processName,
			PID:         pid,
			Type:        "file",
			Detail:      fmt.Sprintf("unauthorized file access: %s", filepath),
			Severity:    "MEDIUM",
			PolicyMode:  mode,
		}
		if mode == ModeEnforce {
			v.Action = "blocked"
		} else {
			v.Action = "logged"
		}
		g.recordViolation(v)
		return &v
	}

	return nil
}

// CheckNetwork validates network access against the process policy.
func (g *Guard) CheckNetwork(processName string, pid int, addr string) *Violation {
	g.mu.RLock()
	proc, exists := g.policy.Processes[processName]
	mode := g.policy.Mode
	g.mu.RUnlock()

	if !exists {
		return nil
	}

	// soc-correlate should have NO network at all.
	if len(proc.AllowedNetwork) == 0 {
		v := Violation{
			Timestamp:   time.Now(),
			ProcessName: processName,
			PID:         pid,
			Type:        "network",
			Detail:      fmt.Sprintf("network access denied (no network allowed): %s", addr),
			Severity:    "CRITICAL",
			SrcIP:       addr,
			PolicyMode:  mode,
		}
		if mode == ModeEnforce {
			v.Action = "blocked"
		} else {
			v.Action = "logged"
		}
		g.recordViolation(v)
		return &v
	}

	return nil
}

// CheckMemory validates memory usage against limits.
func (g *Guard) CheckMemory(processName string, pid int, memoryMB int) *Violation {
	g.mu.RLock()
	proc, exists := g.policy.Processes[processName]
	mode := g.policy.Mode
	g.mu.RUnlock()

	if !exists || proc.MaxMemoryMB == 0 {
		return nil
	}

	if memoryMB > proc.MaxMemoryMB {
		v := Violation{
			Timestamp:   time.Now(),
			ProcessName: processName,
			PID:         pid,
			Type:        "resource",
			Detail:      fmt.Sprintf("memory limit exceeded: %dMB > %dMB", memoryMB, proc.MaxMemoryMB),
			Severity:    "HIGH",
			PolicyMode:  mode,
		}
		if mode == ModeEnforce {
			v.Action = "blocked"
		} else {
			v.Action = "logged"
		}
		g.recordViolation(v)
		return &v
	}

	return nil
}

// Stats returns current guard statistics.
func (g *Guard) Stats() GuardStats {
	g.statsMu.Lock()
	defer g.statsMu.Unlock()

	// Return a copy.
	cp := GuardStats{
		TotalEvents: g.stats.TotalEvents,
		Violations:  g.stats.Violations,
		Blocked:     g.stats.Blocked,
		StartedAt:   g.stats.StartedAt,
		ByProcess:   make(map[string]int64),
		ByType:      make(map[string]int64),
	}
	for k, v := range g.stats.ByProcess {
		cp.ByProcess[k] = v
	}
	for k, v := range g.stats.ByType {
		cp.ByType[k] = v
	}
	return cp
}

// Mode returns the current enforcement mode.
func (g *Guard) CurrentMode() Mode {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.policy.Mode
}

// SetMode changes the enforcement mode at runtime.
func (g *Guard) SetMode(mode Mode) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.logger.Info("guard mode changed", "from", g.policy.Mode, "to", mode)
	g.policy.Mode = mode
}

// recordViolation finalizes the action via the enforcer (if any), updates stats,
// and notifies handlers — in that order, so handlers (e.g. the SOC forwarder)
// always see the TRUTHFUL action and stats.Blocked never counts an unenforced
// block.
func (g *Guard) recordViolation(v Violation) {
	g.mu.RLock()
	enforcer := g.enforcer
	handlers := g.handlers
	g.mu.RUnlock()

	// Honest action: when an enforcer is wired, what it ACTUALLY did is
	// authoritative over the provisional action set by the Check* methods.
	blockedReal := v.Action == "blocked"
	if enforcer != nil {
		action, enforced := enforcer(v)
		if action != "" {
			v.Action = action
		}
		blockedReal = enforced
	}

	g.statsMu.Lock()
	g.stats.TotalEvents++
	g.stats.Violations++
	if blockedReal {
		g.stats.Blocked++
	}
	g.stats.ByProcess[v.ProcessName]++
	g.stats.ByType[v.Type]++
	g.statsMu.Unlock()

	g.logger.Warn("policy violation",
		"process", v.ProcessName,
		"pid", v.PID,
		"type", v.Type,
		"detail", v.Detail,
		"severity", v.Severity,
		"action", v.Action,
		"enforced", blockedReal,
		"mode", v.PolicyMode,
	)

	for _, h := range handlers {
		h(v)
	}
}

// SetEnforcer installs the optional containment hook. Pass nil to clear it.
// Wiring an enforcer is what makes the procfs path's "blocked" honest: stats and
// forwarded events reflect what enforcement actually achieved.
func (g *Guard) SetEnforcer(e ViolationEnforcer) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.enforcer = e
}

// IsMonitored reports whether the named process has a policy entry. The procfs
// scanner uses this to limit inspection to processes the policy actually covers.
func (g *Guard) IsMonitored(processName string) bool {
	g.mu.RLock()
	defer g.mu.RUnlock()
	_, ok := g.policy.Processes[processName]
	return ok
}

// Record ingests a fully-formed violation whose Action is already authoritative
// (e.g. the eBPF backend, where the kernel itself decided block-vs-log). It does
// NOT invoke the enforcer — the action is taken at face value: stats.Blocked is
// incremented iff Action=="blocked". Handlers (SOC forwarding) are notified.
func (g *Guard) Record(v Violation) {
	g.mu.RLock()
	handlers := g.handlers
	g.mu.RUnlock()

	g.statsMu.Lock()
	g.stats.TotalEvents++
	g.stats.Violations++
	if v.Action == "blocked" {
		g.stats.Blocked++
	}
	g.stats.ByProcess[v.ProcessName]++
	g.stats.ByType[v.Type]++
	g.statsMu.Unlock()

	g.logger.Warn("policy violation (kernel)",
		"process", v.ProcessName, "pid", v.PID, "type", v.Type,
		"detail", v.Detail, "severity", v.Severity, "action", v.Action, "mode", v.PolicyMode)

	for _, h := range handlers {
		h(v)
	}
}

// --- Helpers ---

func syscallSeverity(name string) string {
	critical := map[string]bool{
		"ptrace": true, "process_vm_readv": true, "process_vm_writev": true,
		"kexec_load": true, "init_module": true, "finit_module": true,
	}
	high := map[string]bool{
		"execve": true, "fork": true, "clone": true, "clone3": true,
	}
	if critical[name] {
		return "CRITICAL"
	}
	if high[name] {
		return "HIGH"
	}
	return "MEDIUM"
}

func matchGlob(pattern, path string) bool {
	// SEC-V6-1: Normalize path to prevent eBPF bypass via directory traversal (/etc//shadow, /etc/passwd/../shadow)
	cleanedPath := filepath.Clean(path)
	cleanedPath = filepath.ToSlash(cleanedPath) // Normalize to forward slashes for cross-platform glob matching.

	// Simple glob matching: * matches any sequence.
	if pattern == cleanedPath {
		return true
	}
	if strings.HasSuffix(pattern, "/*") {
		// "/etc/*" must match paths strictly under "/etc/", NOT siblings like
		// "/etcd" or "/etcfoo". Keep the trailing slash in the prefix; dropping
		// it (TrimSuffix("/*")) made the match over-broad — for allow-lists that
		// is a fail-OPEN bug (e.g. "/data/*" would authorize "/data_secret").
		prefix := strings.TrimSuffix(pattern, "*") // "/etc/*" -> "/etc/"
		return strings.HasPrefix(cleanedPath, prefix)
	}
	if strings.HasSuffix(pattern, "*") {
		prefix := strings.TrimSuffix(pattern, "*")
		return strings.HasPrefix(cleanedPath, prefix)
	}
	return false
}
