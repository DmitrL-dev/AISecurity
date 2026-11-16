// Package main provides the SOC Correlate process (SEC-001 Process Isolation).
//
// Responsibility: Receives persisted events from soc-ingest via IPC,
// runs 15 correlation rules + clustering, creates incidents.
// Forwards incidents to soc-respond via IPC.
//
// This process has NO network access (by design) — only IPC pipes.
//
// Usage:
//
//	go run ./cmd/soc-correlate/
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"runtime"
	"runtime/debug"
	"syscall"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/ipc"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func main() {
	defer func() {
		if r := recover(); r != nil {
			buf := make([]byte, 4096)
			n := runtime.Stack(buf, false)
			fmt.Fprintf(os.Stderr, "SOC-CORRELATE FATAL PANIC: %v\n%s\n", r, buf[:n])
			os.Exit(2)
		}
	}()

	logger := logging.New(env("SOC_LOG_FORMAT", "text"), env("SOC_LOG_LEVEL", "info"))
	slog.SetDefault(logger)

	// SEC-003: Memory safety — correlate needs more RAM for rule evaluation.
	if limitStr := os.Getenv("GOMEMLIMIT"); limitStr == "" {
		debug.SetMemoryLimit(512 * 1024 * 1024) // 512 MiB
	}

	dbPath := env("SOC_DB_PATH", "soc.db")

	logger.Info("starting SOC-CORRELATE (SEC-001 isolated process)",
		"db", dbPath,
		"upstream_pipe", "soc-ingest-to-correlate",
		"downstream_pipe", "soc-correlate-to-respond",
	)

	// Infrastructure — SQLite access for correlation context.
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

	socSvc := appsoc.NewService(socRepo, decisionLogger)
	_ = domsoc.DefaultSOCCorrelationRules() // Loaded inside socSvc

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// IPC: Listen for events from soc-ingest.
	ingestListener, err := ipc.Listen("soc-ingest-to-correlate")
	if err != nil {
		logger.Error("failed to listen for ingest", "error", err)
		os.Exit(1)
	}
	defer ingestListener.Close()
	logger.Info("IPC listener ready", "pipe", "soc-ingest-to-correlate")

	// IPC: Connect to downstream soc-respond.
	respondConn, err := ipc.DialWithRetry(ctx, "soc-correlate-to-respond", 30)
	var respondSender *ipc.BufferedSender
	if err != nil {
		logger.Warn("soc-respond not available — incidents will only be stored", "error", err)
	} else {
		respondSender = ipc.NewBufferedSender(respondConn, "soc-correlate-to-respond")
		defer respondSender.Close()
		logger.Info("IPC connected to soc-respond")
	}

	// Accept ingest connection and process events.
	go func() {
		for {
			conn, err := ingestListener.Accept()
			if err != nil {
				if ctx.Err() != nil {
					return // Shutting down.
				}
				logger.Error("accept failed", "error", err)
				continue
			}

			go handleIngestConnection(ctx, conn, socSvc, respondSender, logger)
		}
	}()

	<-ctx.Done()
	logger.Info("SOC-CORRELATE shutting down")
}

// handleIngestConnection processes events from a single soc-ingest connection.
func handleIngestConnection(
	ctx context.Context,
	conn net.Conn,
	socSvc *appsoc.Service,
	respondSender *ipc.BufferedSender,
	logger *slog.Logger,
) {
	defer conn.Close()
	receiver := ipc.NewReceiver(conn, "ingest")

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		msg, err := receiver.Next()
		if err == io.EOF {
			logger.Info("ingest connection closed")
			return
		}
		if err != nil {
			logger.Error("read event", "error", err)
			continue
		}

		if msg.Type != ipc.SOCMsgEvent {
			continue
		}

		// Deserialize event and run correlation.
		var event domsoc.SOCEvent
		if err := json.Unmarshal(msg.Payload, &event); err != nil {
			logger.Error("unmarshal event", "error", err)
			continue
		}

		// Run correlation rules via service.
		_, incident, err := socSvc.IngestEvent(event)
		if err != nil {
			logger.Error("correlate", "error", err)
			continue
		}

		// Forward incident to soc-respond.
		if incident != nil && respondSender != nil {
			incMsg, _ := ipc.NewSOCMessage(ipc.SOCMsgIncident, incident)
			if err := respondSender.Send(incMsg); err != nil {
				logger.Error("forward incident to respond", "error", err)
			}
		}
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
