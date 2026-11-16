// Package main provides the gomcp-ingest CLI — a one-shot tool that reads
// a Claude Code JSONL transcript and persists every user/assistant message
// into the conversation_log layer of the RLM. Designed to run from a
// SessionEnd hook in ~/.claude/settings.json so every conversation flows
// into shared memory automatically.
//
// Usage:
//
//	gomcp-ingest -rlm-dir <path> -transcript <path>
//	gomcp-ingest -rlm-dir .rlm -transcript ~/.claude/projects/foo/abc123.jsonl
//
// Exits 0 on success even if the file was already fully ingested.
// Exits 1 on argument error, 2 on IO/db error.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/syntrex/gomcp/internal/application/tools"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func main() {
	rlmDir := flag.String("rlm-dir", ".rlm", "Path to .rlm directory containing memory_bridge_v2.db")
	transcript := flag.String("transcript", "", "Path to Claude Code JSONL transcript")
	sessionOverride := flag.String("session-id", "", "Override session ID (default: read from transcript)")
	quiet := flag.Bool("quiet", false, "Suppress progress output (errors still go to stderr)")
	tenantID := flag.String("tenant-id", envOrDefault("GOMCP_TENANT_ID", rlmscope.DefaultTenantID), "RLM tenant ID")
	projectID := flag.String("project-id", envOrDefault("GOMCP_PROJECT_ID", rlmscope.DefaultProjectID), "RLM project ID")
	flag.Parse()

	if *transcript == "" {
		fmt.Fprintln(os.Stderr, "error: -transcript is required")
		flag.Usage()
		os.Exit(1)
	}

	dbPath := filepath.Join(*rlmDir, "memory", "memory_bridge_v2.db")
	db, err := sqlite.Open(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: open db %s: %v\n", dbPath, err)
		os.Exit(2)
	}
	defer db.Close()

	repo, err := sqlite.NewConversationLogRepo(db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: init conversation_log: %v\n", err)
		os.Exit(2)
	}

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New(*tenantID, *projectID))
	result, err := tools.IngestTranscript(ctx, repo, *transcript, *sessionOverride)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: ingest %s: %v\n", *transcript, err)
		os.Exit(2)
	}

	if !*quiet {
		out, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(out))
	}
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
