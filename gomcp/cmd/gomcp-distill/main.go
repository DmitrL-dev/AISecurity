// Package main is the gomcp-distill CLI — collapses raw conversation_log
// messages into hierarchical_facts (L2 session summaries + L3 notable
// user-question facts).
//
// Designed for cron / one-shot invocations:
//
//	gomcp-distill -rlm-dir <path> -project-id PID                      # batch, idle=30m default
//	gomcp-distill -rlm-dir <path> -project-id PID -session SID         # one specific session
//	gomcp-distill -rlm-dir <path> -project-id PID -idle 5m -limit 200  # tighter idle, more sessions
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/application/tools"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func main() {
	rlmDir := flag.String("rlm-dir", ".rlm", "Path to .rlm directory")
	sessionID := flag.String("session", "", "Distill only this session (omit = batch by idle)")
	idle := flag.Duration("idle", 30*time.Minute, "Sessions whose latest message is older than this are eligible for batch distillation")
	limit := flag.Int("limit", 50, "Max sessions per batch")
	quiet := flag.Bool("quiet", false, "Suppress JSON output")
	tenantID := flag.String("tenant-id", envOrDefault("GOMCP_TENANT_ID", rlmscope.DefaultTenantID), "RLM tenant ID")
	projectID := flag.String("project-id", strings.TrimSpace(os.Getenv("GOMCP_PROJECT_ID")), "RLM project ID (required; default is reserved for legacy memory)")
	flag.Parse()

	dbPath := filepath.Join(*rlmDir, "memory", "memory_bridge_v2.db")
	db, err := sqlite.Open(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: open db %s: %v\n", dbPath, err)
		os.Exit(2)
	}
	defer db.Close()

	factRepo, err := sqlite.NewFactRepo(db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: init fact repo: %v\n", err)
		os.Exit(2)
	}
	convRepo, err := sqlite.NewConversationLogRepo(db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: init conversation repo: %v\n", err)
		os.Exit(2)
	}

	svc := tools.NewDistillerService(convRepo, factRepo)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New(*tenantID, *projectID))
	var res tools.DistillResult
	if *sessionID != "" {
		res, err = svc.DistillSession(ctx, *sessionID)
	} else {
		res, err = svc.DistillBatch(ctx, *idle, *limit)
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(2)
	}

	if !*quiet {
		out, _ := json.MarshalIndent(res, "", "  ")
		fmt.Println(string(out))
	}
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
