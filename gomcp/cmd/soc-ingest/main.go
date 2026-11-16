// Package main provides the SOC Ingest process (SEC-001 Process Isolation).
//
// Responsibility: HTTP endpoint, authentication, secret scanner,
// rate limiting, dedup, SQLite persistence.
// Forwards persisted events to soc-correlate via IPC.
//
// Usage:
//
//	go run ./cmd/soc-ingest/
//	SOC_DB_PATH=/data/soc.db SOC_INGEST_PORT=9750 go run ./cmd/soc-ingest/
package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"runtime"
	"runtime/debug"
	"strconv"
	"syscall"

	"github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"github.com/syntrex/gomcp/internal/infrastructure/ipc"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	sochttp "github.com/syntrex/gomcp/internal/transport/http"
)

func main() {
	// SEC-003: Panic recovery.
	defer func() {
		if r := recover(); r != nil {
			buf := make([]byte, 4096)
			n := runtime.Stack(buf, false)
			fmt.Fprintf(os.Stderr, "SOC-INGEST FATAL PANIC: %v\n%s\n", r, buf[:n])
			os.Exit(2)
		}
	}()

	logger := logging.New(env("SOC_LOG_FORMAT", "text"), env("SOC_LOG_LEVEL", "info"))
	slog.SetDefault(logger)

	// SEC-003: Memory safety.
	if limitStr := os.Getenv("GOMEMLIMIT"); limitStr == "" {
		debug.SetMemoryLimit(256 * 1024 * 1024) // 256 MiB for ingest
	}

	port, _ := strconv.Atoi(env("SOC_INGEST_PORT", "9750"))
	dbPath := env("SOC_DB_PATH", "soc.db")

	logger.Info("starting SOC-INGEST (SEC-001 isolated process)",
		"port", port, "db", dbPath,
		"ipc_pipe", "soc-ingest-to-correlate",
	)

	// Infrastructure.
	db, err := sqlite.Open(dbPath)
	if err != nil {
		logger.Error("database open failed", "error", err)
		os.Exit(1)
	}
	defer db.Close()

	socRepo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		logger.Error("SOC repo init failed", "error", err)
		os.Exit(1)
	}

	decisionLogger, err := audit.NewDecisionLogger(env("SOC_AUDIT_DIR", "."))
	if err != nil {
		logger.Error("decision logger init failed", "error", err)
		os.Exit(1)
	}

	// Service (ingest-only mode).
	socSvc := soc.NewService(socRepo, decisionLogger)
	// Review 13.06 (audit A4): enforce sensor authentication on ingest if set.
	if sensorKeys := soc.ParseSensorKeys(os.Getenv("SOC_SENSOR_KEYS")); len(sensorKeys) > 0 {
		socSvc.SetSensorKeys(sensorKeys)
		logger.Info("sensor ingest authentication enabled", "sensors", len(sensorKeys))
		// Review 14.06 round-4: optional "sensorID:key:tenant" binds events to a tenant.
		if sensorTenants := soc.ParseSensorTenants(os.Getenv("SOC_SENSOR_KEYS")); len(sensorTenants) > 0 {
			socSvc.SetSensorTenants(sensorTenants)
			logger.Info("sensor→tenant binding enabled", "bound_sensors", len(sensorTenants))
		}
	} else {
		logger.Warn("SOC_SENSOR_KEYS not set — ingest is UNAUTHENTICATED; set it to require sensor credentials")
	}

	// IPC: Connect to downstream soc-correlate.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	correlateConn, err := ipc.DialWithRetry(ctx, "soc-ingest-to-correlate", 30)
	if err != nil {
		logger.Warn("soc-correlate not available — running in standalone ingest mode", "error", err)
	} else {
		ipcSender := ipc.NewBufferedSender(correlateConn, "soc-ingest-to-correlate")
		defer ipcSender.Close()

		// Subscribe to event bus and forward events via IPC.
		eventCh := socSvc.EventBus().Subscribe("ipc-forwarder")
		go func() {
			for event := range eventCh {
				msg, err := ipc.NewSOCMessage(ipc.SOCMsgEvent, event)
				if err != nil {
					logger.Error("ipc: marshal event", "error", err)
					continue
				}
				if err := ipcSender.Send(msg); err != nil {
					logger.Error("ipc: forward to correlate", "error", err)
				}
			}
		}()
		logger.Info("IPC connected to soc-correlate", "pending_buffer", ipc.BufferSize)
	}

	// HTTP server (ingest endpoints only).
	srv := sochttp.New(socSvc, port)

	// JWT auth — ALWAYS enabled (Review 14.06 round-2). Previously this only ran
	// when SOC_JWT_SECRET was set, so an unset env left the full SOC HTTP API +
	// cross-tenant data UNAUTHENTICATED (a regression of the cmd/soc fix).
	// ResolveSigningSecret uses SOC_JWT_SECRET if set, else a random ephemeral key
	// (with a loud warning); the DB wires userStore/tenantStore so requireSOC
	// enforces tenant scoping. Sensor ingest stays JWT-exempt (PSK auth) by design.
	srv.SetJWTAuth(auth.ResolveSigningSecret(), db.SqlDB())

	logger.Info("SOC-INGEST ready", "port", port)
	if err := srv.Start(ctx); err != nil {
		logger.Error("server failed", "error", err)
		os.Exit(1)
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
