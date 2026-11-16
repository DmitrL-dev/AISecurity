// Package main provides the SENTINEL immune agent (SEC-002 Runtime Guard).
//
// The immune agent monitors SOC processes against per-process security policies
// and forwards violations to the SOC. It is platform-honest about WHAT it can
// actually do on each OS — it never claims kernel enforcement it does not have:
//
//	Backend            Build              Detection          Enforcement
//	-----------------  -----------------  -----------------  --------------------------
//	procfs-polling     default, Linux     /proc sampling     best-effort: block_ip /
//	                                       (mem/fd/net)       process-kill, else log-only
//	disabled-on-this-  default, non-Linux none (no /proc)    none (honest no-op)
//	  os               (Windows/macOS)
//	ebpf               -tags ebpf, Linux  in-kernel          in-kernel -EPERM (real),
//	                   + clang + CAP_BPF   tracepoints        requires CAP_NET_ADMIN
//
// The eBPF backend is behind the `ebpf` build tag so the DEFAULT build needs no
// clang/eBPF toolchain. See cmd/immune/monitor_ebpf.go for build/run requirements.
//
// Usage:
//
//	go run ./cmd/immune/ --policy deploy/policies/soc_runtime_policy.yaml
//	SOC_GUARD_MODE=enforce SOC_BUS_URL=http://soc:9100 go run ./cmd/immune/
package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"runtime/debug"
	"strconv"
	"syscall"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/guard"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
)

func main() {
	// SEC-003: Panic recovery.
	defer func() {
		if r := recover(); r != nil {
			buf := make([]byte, 4096)
			n := runtime.Stack(buf, false)
			fmt.Fprintf(os.Stderr, "IMMUNE FATAL PANIC: %v\n%s\n", r, buf[:n])
			os.Exit(2)
		}
	}()

	logger := logging.New(env("SOC_LOG_FORMAT", "text"), env("SOC_LOG_LEVEL", "info"))
	slog.SetDefault(logger)

	// SEC-003: Memory safety — immune agent uses minimal RAM.
	if os.Getenv("GOMEMLIMIT") == "" {
		debug.SetMemoryLimit(128 * 1024 * 1024) // 128 MiB
	}

	policyPath := env("SOC_GUARD_POLICY", "deploy/policies/soc_runtime_policy.yaml")
	port, _ := strconv.Atoi(env("SOC_IMMUNE_PORT", "9760"))

	// Load policy.
	policy, err := guard.LoadPolicy(policyPath)
	if err != nil {
		logger.Error("failed to load policy", "path", policyPath, "error", err)
		os.Exit(1)
	}

	// Override mode from env if set.
	if modeOverride := os.Getenv("SOC_GUARD_MODE"); modeOverride != "" {
		policy.Mode = guard.Mode(modeOverride)
		logger.Info("mode overridden via env", "mode", policy.Mode)
	}

	g := guard.New(policy)

	// Honest startup banner: report the ACTUAL active backend and what it does on
	// THIS build/OS — not an aspirational "kernel enforcement" claim.
	logger.Info("starting SENTINEL immune agent (SEC-002 Runtime Guard)",
		"policy", policyPath,
		"port", port,
		"os", runtime.GOOS,
		"backend", backendName,
		"backend_detail", backendDetail,
		"mode", policy.Mode,
	)

	// SOC forwarding: real POST to /api/v1/soc/events (honest no-op + warn if unset).
	busURL := env("SOC_BUS_URL", os.Getenv("SIDECAR_BUS_URL"))
	sensorID := env("SOC_IMMUNE_SENSOR_ID", "sensor-immune-01")
	sensorKey := os.Getenv("SOC_SENSOR_KEY")
	forwarder := newSOCForwarder(busURL, sensorID, sensorKey, logger)

	// Enforcement backend: reuse the shared block_ip firewall (honest log-only by
	// default). Process-kill is gated behind SOC_IMMUNE_ALLOW_KILL.
	fw := domsoc.NewFirewall(domsoc.FirewallConfig{
		Backend:    os.Getenv("SOC_FIREWALL_BACKEND"),
		ChainOrSet: os.Getenv("SOC_FIREWALL_CHAIN"),
		Table:      os.Getenv("SOC_FIREWALL_TABLE"),
		APIURL:     os.Getenv("SOC_FIREWALL_API_URL"),
		APIToken:   os.Getenv("SOC_FIREWALL_API_TOKEN"),
	})
	allowKill := os.Getenv("SOC_IMMUNE_ALLOW_KILL") == "1"
	enf := newEnforcer(fw, allowKill, logger)
	if policy.Mode == guard.ModeEnforce {
		logger.Info("enforcement backend",
			"block_ip", fw.Type(),
			"process_kill", allowKill,
			"note", "block_ip is log-only unless SOC_FIREWALL_BACKEND is set; kill requires SOC_IMMUNE_ALLOW_KILL=1",
		)
	}

	// Register violation handler → forward to SOC. The handler sees the TRUTHFUL
	// action (the guard finalizes it via the enforcer before calling handlers).
	g.OnViolation(func(v guard.Violation) {
		forwarder.Forward(v)
	})

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Start the active platform backend (procfs / disabled / ebpf — selected at
	// build time via tags). runMonitor wires the enforcer into the guard.
	go runMonitor(ctx, g, enf, logger)

	// HTTP status endpoint for health checks and stats.
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"status":         "healthy",
			"mode":           g.CurrentMode(),
			"os":             runtime.GOOS,
			"backend":        backendName,   // ACTUAL active backend
			"backend_detail": backendDetail, // truthful description of what it does
			"monitoring":     backendName != "disabled-on-this-os",
			"soc_forwarding": forwarder.enabled,
			"enforcement": map[string]any{
				"block_ip_backend": fw.Type(),
				"process_kill":     allowKill,
			},
			"platform_matrix": platformMatrix(),
		})
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"backend":        backendName,
			"backend_detail": backendDetail,
			"os":             runtime.GOOS,
			"mode":           g.CurrentMode(),
			"soc_forwarding": forwarder.enabled,
			"guard":          g.Stats(),
		})
	})

	mux.HandleFunc("/mode", modeHandler(g))

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", port),
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		logger.Info("immune HTTP status endpoint ready", "port", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("HTTP server failed", "error", err)
		}
	}()

	<-ctx.Done()
	logger.Info("immune shutting down")
	srv.Shutdown(context.Background())
}

// modeHandler serves GET/POST /mode for the immune agent.
//
// Review 13.06 (audit D5): the POST mutation toggles a security control, so it
// is gated behind a control token (FAIL CLOSED when SOC_IMMUNE_CONTROL_TOKEN is
// unset) and the value is validated against the allowed set. The GET path stays
// open for health / k8s liveness probes.
func modeHandler(g *guard.Guard) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			controlToken := os.Getenv("SOC_IMMUNE_CONTROL_TOKEN")
			if controlToken == "" {
				http.Error(w, "mode mutation disabled: set SOC_IMMUNE_CONTROL_TOKEN", http.StatusForbidden)
				return
			}
			provided := r.Header.Get("X-Control-Token")
			if subtle.ConstantTimeCompare([]byte(provided), []byte(controlToken)) != 1 {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}
			var req struct {
				Mode string `json:"mode"`
			}
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				slog.Error("invalid mode request", "error", err)
				http.Error(w, "invalid request body", http.StatusBadRequest)
				return
			}
			switch guard.Mode(req.Mode) {
			case guard.ModeAudit, guard.ModeEnforce, guard.ModeAlert:
				g.SetMode(guard.Mode(req.Mode))
			default:
				http.Error(w, "invalid mode (valid: audit, enforce, alert)", http.StatusBadRequest)
				return
			}
			w.WriteHeader(http.StatusOK)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"mode": string(g.CurrentMode())})
	}
}

// platformMatrix returns a TRUTHFUL description of what each backend does, so
// /health consumers understand the capability of this build/OS without guessing.
// This is documentation, not a claim about the running backend (see "backend").
func platformMatrix() map[string]string {
	return map[string]string{
		"procfs-polling (default, Linux)":              "samples /proc to detect mem/fd/network policy violations; userspace, not real-time; blocks best-effort via block_ip/process-kill or logs only",
		"disabled-on-this-os (default, non-Linux)":     "no /proc and no eBPF on Windows/macOS — no monitoring, no enforcement (honest no-op)",
		"ebpf (-tags ebpf, Linux+clang+CAP_NET_ADMIN)": "in-kernel tracepoints with real -EPERM blocking in enforce mode; needs kernel 5.10+, CAP_BPF/CAP_NET_ADMIN and a clang-built object",
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
