package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

func TestBuildBootInstructionsForModeBoundsManagedInitializeAndPreservesLegacy(t *testing.T) {
	facts := make([]*memory.Fact, 18)
	for index := range facts {
		facts[index] = memory.NewFact(
			fmt.Sprintf("legacy-l0-%02d:%s", index, strings.Repeat("x", 256*1024)),
			memory.LevelProject,
			"wire-budget",
			"",
		)
	}
	const summary = "legacy-session-summary-must-remain-visible"

	legacy := buildBootInstructionsForMode(facts, summary, false)
	if legacy != buildBootInstructions(facts, summary) {
		t.Fatal("standalone mode changed the legacy boot-instructions contract")
	}
	if len(legacy) <= 4*1024*1024 {
		t.Fatalf("legacy fixture no longer exercises the fixed wire limit: got %d bytes", len(legacy))
	}
	for _, marker := range []string{"legacy-l0-00:", "legacy-l0-17:", summary} {
		if !strings.Contains(legacy, marker) {
			t.Fatalf("standalone boot instructions omitted %q", marker)
		}
	}

	managed := buildBootInstructionsForMode(facts, summary, true)
	if len(managed) >= 1024*1024 {
		t.Fatalf("managed initialize instructions exceed one MiB: got %d bytes", len(managed))
	}
	for _, marker := range []string{"legacy-l0-00:", "legacy-l0-17:", summary, "[PROJECT FACTS]", "[LAST SESSION]"} {
		if strings.Contains(managed, marker) {
			t.Fatalf("managed initialize leaked persisted memory marker %q", marker)
		}
	}
	if !strings.Contains(managed, "[AGENT INSTRUCTIONS]") {
		t.Fatal("managed initialize lost static agent instructions")
	}
}

// Exercise the real managed entrypoint in a private empty subprocess. No kill
// switch is triggered and no customer data is involved.
func TestAuditManagedMemoryDoesNotStartStandaloneLifecycle(t *testing.T) {
	if directory := os.Getenv("GOMCP_AUDIT_MANAGED_HELPER"); directory != "" {
		if err := run(directory, filepath.Join(directory, "cache.db"), "", true, true,
			false, false, 0, rlmscope.Default(), false, true); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		os.Exit(0)
	}
	directory := t.TempDir()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestAuditManagedMemoryDoesNotStartStandaloneLifecycle$")
	cmd.Dir = directory
	cmd.Env = append(os.Environ(), "GOMCP_AUDIT_MANAGED_HELPER="+directory)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { cancel(); _ = cmd.Wait() }()
	encoder, decoder := json.NewEncoder(stdin), json.NewDecoder(stdout)
	if err := encoder.Encode(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": map[string]any{
		"protocolVersion": "2025-11-25", "capabilities": map[string]any{}, "clientInfo": map[string]any{"name": "audit-fixture", "version": "1"},
	}}); err != nil {
		t.Fatal(err)
	}
	var response map[string]any
	if err := decoder.Decode(&response); err != nil {
		t.Fatalf("initialize: %v (%s)", err, stderr.String())
	}
	if response["error"] != nil {
		t.Fatalf("initialize failed: %v", response["error"])
	}
	// Several leash intervals and the initial standalone heartbeat would run here.
	time.Sleep(4 * time.Second)
	for _, name := range []string{".sentinel_key", ".sentinel_leash", "genome.json"} {
		if _, err := os.Stat(filepath.Join(directory, name)); !os.IsNotExist(err) {
			t.Fatalf("managed child created standalone file %s: %v", name, err)
		}
	}
	db, err := sqlite.Open(filepath.Join(directory, "memory", "memory_bridge_v2.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	repo, err := sqlite.NewFactRepo(db)
	if err != nil {
		t.Fatal(err)
	}
	genes, err := repo.ListGenes(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(genes) != 0 {
		t.Fatalf("managed memory contains %d vendor genes", len(genes))
	}
	_ = stdin.Close()
	if err := cmd.Wait(); err != nil {
		t.Fatalf("managed child exit: %v (%s)", err, stderr.String())
	}
}
