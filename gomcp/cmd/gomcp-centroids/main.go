// Package main is the gomcp-centroids CLI — recomputes per-domain centroids
// from live facts in the RLM. Designed for cron / one-shot invocations:
//
//	gomcp-centroids -rlm-dir <path>            # recompute all
//	gomcp-centroids -rlm-dir <path> -domain X  # recompute one
//	gomcp-centroids -rlm-dir <path> -list      # list current centroids
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

type centroidSummary struct {
	Domain    string `json:"domain"`
	FactCount int    `json:"fact_count"`
	VectorDim int    `json:"vector_dim"`
	UpdatedAt string `json:"updated_at"`
}

func main() {
	rlmDir := flag.String("rlm-dir", ".rlm", "Path to .rlm directory containing memory_bridge_v2.db")
	domain := flag.String("domain", "", "Recompute only this domain (omit = all)")
	listOnly := flag.Bool("list", false, "List stored centroids without recomputing")
	verbose := flag.Bool("verbose", false, "Include full vectors in output (default: summary only)")
	quiet := flag.Bool("quiet", false, "Suppress output entirely")
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

	// FactRepo's migrate creates domain_centroids; we need it before
	// CentroidRepo can read/write the table.
	factRepo, err := sqlite.NewFactRepo(db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: init fact repo: %v\n", err)
		os.Exit(2)
	}
	centroidRepo, err := sqlite.NewCentroidRepo(db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: init centroid repo: %v\n", err)
		os.Exit(2)
	}
	svc := tools.NewCentroidService(factRepo, centroidRepo)

	ctx := rlmscope.WithScope(context.Background(), rlmscope.New(*tenantID, *projectID))

	if *listOnly {
		all, err := svc.List(ctx)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: list centroids: %v\n", err)
			os.Exit(2)
		}
		if !*quiet {
			if *verbose {
				emitJSON(map[string]interface{}{"count": len(all), "centroids": all})
			} else {
				summaries := make([]centroidSummary, 0, len(all))
				for _, c := range all {
					summaries = append(summaries, centroidSummary{
						Domain:    c.Domain,
						FactCount: c.FactCount,
						VectorDim: len(c.Vector),
						UpdatedAt: c.UpdatedAt.Format("2006-01-02T15:04:05Z07:00"),
					})
				}
				emitJSON(map[string]interface{}{"count": len(all), "centroids": summaries})
			}
		}
		return
	}

	if *domain != "" {
		c, err := svc.Recompute(ctx, *domain)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: recompute %q: %v\n", *domain, err)
			os.Exit(2)
		}
		if !*quiet {
			if c == nil {
				emitJSON(map[string]string{"domain": *domain, "status": "no_embeddings_available"})
			} else {
				emitJSON(centroidSummary{
					Domain:    c.Domain,
					FactCount: c.FactCount,
					VectorDim: len(c.Vector),
					UpdatedAt: c.UpdatedAt.Format("2006-01-02T15:04:05Z07:00"),
				})
			}
		}
		return
	}

	written, err := svc.RecomputeAll(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: recompute all: %v\n", err)
		os.Exit(2)
	}
	if !*quiet {
		emitJSON(map[string]int{"centroids_written": written})
	}
}

func emitJSON(v interface{}) {
	out, _ := json.MarshalIndent(v, "", "  ")
	fmt.Println(string(out))
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
