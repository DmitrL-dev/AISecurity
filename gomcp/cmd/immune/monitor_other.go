//go:build !linux && !ebpf

package main

import (
	"context"
	"log/slog"
	"runtime"

	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// backendName reports the ACTIVE backend on non-Linux platforms. There is no
// /proc and no eBPF, so the runtime guard is HONESTLY disabled — it does NOT
// monitor or enforce anything here. This is the dev-box (Windows/macOS) path.
const backendName = "disabled-on-this-os"

// backendDetail is the truthful description shown in /health and /stats.
var backendDetail = "runtime guard is UNAVAILABLE on " + runtime.GOOS +
	": there is no /proc to poll and no eBPF. No processes are monitored and " +
	"nothing is enforced. Deploy on Linux for procfs polling (default) or " +
	"build with -tags ebpf for in-kernel monitoring (Linux + clang + CAP_NET_ADMIN)."

// runMonitor is an honest no-op on non-Linux: it logs that the guard is
// unavailable and returns when ctx is cancelled, without claiming any monitoring.
func runMonitor(ctx context.Context, _ *guard.Guard, _ *enforcer, logger *slog.Logger) {
	logger.Warn("runtime guard UNAVAILABLE on this OS — no monitoring, no enforcement",
		"backend", backendName,
		"os", runtime.GOOS,
		"note", "deploy on Linux (procfs default) or build -tags ebpf for kernel monitoring",
	)
	<-ctx.Done()
	logger.Info("runtime guard (no-op) stopping")
}
