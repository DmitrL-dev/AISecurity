// Package main is the gomcp-decay CLI — the cold-decay pass.
// Archives cold facts that already feed into a parent (their content lives
// on at L2/L1), marks the rest stale for review.
//
//	gomcp-decay -rlm-dir <path>                 # default: 90d, apply
//	gomcp-decay -rlm-dir <path> -older 365d -dry-run
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
	older := flag.Duration("older", 90*24*time.Hour, "Decay facts older than this (≥30d due to underlying floor)")
	dryRun := flag.Bool("dry-run", false, "Report what would happen without modifying data")
	noCentroids := flag.Bool("no-centroids", false, "Skip centroid recompute after apply")
	quiet := flag.Bool("quiet", false, "Suppress JSON output")
	tenantID := flag.String("tenant-id", envOrDefault("GOMCP_TENANT_ID", rlmscope.DefaultTenantID), "RLM tenant ID")
	projectID := flag.String("project-id", envOrDefault("GOMCP_PROJECT_ID", rlmscope.DefaultProjectID), "RLM project ID")
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

	svc := tools.NewDecayService(factRepo)
	if !*noCentroids && !*dryRun {
		centroidRepo, err := sqlite.NewCentroidRepo(db)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: init centroid repo: %v\n", err)
			os.Exit(2)
		}
		svc.SetCentroidService(tools.NewCentroidService(factRepo, centroidRepo))
	}

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New(*tenantID, *projectID))
	res, err := svc.Decay(ctx, *older, *dryRun)
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
