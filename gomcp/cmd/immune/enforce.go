package main

import (
	"fmt"
	"log/slog"
	"os"
	"syscall"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// enforcer turns a detected violation into a REAL containment action on the
// default (procfs) path, where — unlike the eBPF kernel-return path — nothing is
// blocked by the kernel automatically. It is the honest answer to "what did we
// actually do about this?":
//
//   - network violation  → block_ip via the shared soc.Firewall (nft/iptables/
//     cloud-http). Honest log-only when no backend is configured.
//   - severe process/syscall violation → optional process-kill (SIGKILL) when
//     SOC_IMMUNE_ALLOW_KILL=1 AND policy mode is enforce. Off by default.
//   - everything else → log-only.
//
// HONESTY CONTRACT: enforce() returns the action string that ACTUALLY happened
// ("blocked", "killed", "logged", "alerted") plus enforced=true ONLY when a real
// effect occurred (a firewall rule installed, or a process signalled). The caller
// overwrites Violation.Action with this truth so the agent, /stats, and the SOC
// event never claim a block that did not happen.
type enforcer struct {
	fw        domsoc.Firewall // block_ip backend (log-only by default)
	allowKill bool            // SOC_IMMUNE_ALLOW_KILL — gate on real process kills
	logger    *slog.Logger
}

func newEnforcer(fw domsoc.Firewall, allowKill bool, logger *slog.Logger) *enforcer {
	return &enforcer{fw: fw, allowKill: allowKill, logger: logger}
}

// blockTTL is how long a block_ip drop rule lives before the kernel expires it.
const blockTTL = 30 * time.Minute

// enforce attempts real containment for v and returns the truthful outcome. It
// satisfies guard.ViolationEnforcer, so the guard calls it inline and uses the
// result as the authoritative action. The offending source IP for network
// violations rides on v.SrcIP (empty → no IP block possible → honest log-only).
func (e *enforcer) enforce(v guard.Violation) (action string, enforced bool) {
	srcIP := v.SrcIP
	mode := v.PolicyMode

	// Alert mode never blocks — it only emits SOC signal.
	if mode == guard.ModeAlert {
		return "alerted", false
	}
	// Audit mode is observe-only by contract.
	if mode != guard.ModeEnforce {
		return "logged", false
	}

	// --- enforce mode: attempt a real effect ---

	switch v.Type {
	case "network":
		if srcIP == "" {
			e.logger.Warn("enforce: network violation but no source IP to block — log-only",
				"process", v.ProcessName, "pid", v.PID, "detail", v.Detail)
			return "logged", false
		}
		ok, detail, err := e.fw.Block(srcIP, blockTTL, fmt.Sprintf("immune guard: %s", v.Detail))
		if err != nil {
			e.logger.Error("enforce: block_ip failed", "ip", srcIP, "backend", e.fw.Type(), "error", err)
			return "logged", false
		}
		if ok {
			e.logger.Warn("enforce: source IP BLOCKED", "ip", srcIP, "backend", e.fw.Type(), "detail", detail)
			return "blocked", true
		}
		// Honest: backend present but not enforcing (e.g. log-only / non-Linux).
		e.logger.Warn("enforce: block_ip NOT enforced (log-only) — set SOC_FIREWALL_BACKEND to actually block",
			"ip", srcIP, "backend", e.fw.Type(), "detail", detail)
		return "logged", false

	case "syscall", "resource":
		// Process-kill is the only host-level containment we can apply to the
		// offending process itself from userspace. It is destructive, so it is
		// gated behind an explicit opt-in.
		if !e.allowKill {
			e.logger.Warn("enforce: would kill offending process but SOC_IMMUNE_ALLOW_KILL is not set — log-only",
				"process", v.ProcessName, "pid", v.PID, "type", v.Type)
			return "logged", false
		}
		if killed := e.killProcess(v.PID, v.ProcessName); killed {
			return "killed", true
		}
		return "logged", false

	default:
		return "logged", false
	}
}

// killProcess sends SIGKILL to pid. Returns true only if the signal was
// delivered (the process genuinely existed and we had permission).
func (e *enforcer) killProcess(pid int, name string) bool {
	if pid <= 1 {
		e.logger.Error("enforce: refusing to kill pid <= 1", "pid", pid, "process", name)
		return false
	}
	proc, err := os.FindProcess(pid)
	if err != nil {
		e.logger.Error("enforce: process not found for kill", "pid", pid, "process", name, "error", err)
		return false
	}
	if err := proc.Signal(syscall.SIGKILL); err != nil {
		e.logger.Error("enforce: SIGKILL failed (need privilege / process gone)", "pid", pid, "process", name, "error", err)
		return false
	}
	e.logger.Warn("enforce: offending process KILLED (SIGKILL)", "pid", pid, "process", name)
	return true
}
