// GoMCP Server - Next-generation Model Context Protocol server
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/sentinel-community/gomcp/pkg/pythonbridge"
	"github.com/sentinel-community/gomcp/pkg/security"
	"github.com/sentinel-community/gomcp/pkg/stdio"
	"github.com/sentinel-community/gomcp/pkg/supervisor"
)

var (
	version     = "3.0.0"
	mode        = flag.String("mode", "stdio", "Server mode: stdio, grpc, http")
	timeout     = flag.Duration("timeout", 60*time.Second, "Default tool timeout")
	pythonPath  = flag.String("python", "python", "Path to Python executable")
	workerPath  = flag.String("worker", "", "Path to RLM worker script")
	projectRoot = flag.String("project", "", "Project root directory")
)

func main() {
	flag.Parse()

	log.Printf("GoMCP Server v%s starting...", version)
	log.Printf("Mode: %s, Default timeout: %s", *mode, *timeout)

	// Determine project root
	project := *projectRoot
	if project == "" {
		project = os.Getenv("RLM_PROJECT_ROOT")
	}
	if project == "" {
		project, _ = os.Getwd()
	}
	log.Printf("Project root: %s", project)

	// Find worker path
	worker := *workerPath
	if worker == "" {
		worker = findWorkerPath(project)
	}
	if worker == "" {
		log.Fatal("Error: Could not find rlm_worker.py. Please set -worker flag or RLM_WORKER_PATH env var.")
	}
	log.Printf("Worker path: %s", worker)

	// Handle shutdown gracefully
	ctx, cancel := context.WithCancel(context.Background())
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("Shutting down...")
		cancel()
	}()

	switch *mode {
	case "stdio":
		log.Println("Starting stdio adapter (MCP v1 compatible)...")
		runStdioAdapter(ctx, project, worker)
	case "grpc":
		log.Println("Starting gRPC server (native GoMCP)...")
		sup := supervisor.New(supervisor.Config{
			DefaultTimeout:  *timeout,
			MaxWorkers:      10,
			HeartbeatPeriod: 5 * time.Second,
		})
		runGRPCServer(sup)
	case "http":
		log.Println("Starting HTTP/SSE server...")
		sup := supervisor.New(supervisor.Config{
			DefaultTimeout:  *timeout,
			MaxWorkers:      10,
			HeartbeatPeriod: 5 * time.Second,
		})
		runHTTPServer(sup)
	default:
		log.Fatalf("Unknown mode: %s", *mode)
	}
}

func runStdioAdapter(ctx context.Context, projectRoot, workerPath string) {
	// Create Python bridge
	bridge := pythonbridge.New(pythonbridge.Config{
		PythonPath:  *pythonPath,
		WorkerPath:  workerPath,
		ProjectRoot: projectRoot,
	})

	// Start bridge
	if err := bridge.Start(ctx); err != nil {
		log.Printf("Warning: Python bridge failed to start: %v", err)
		// Continue anyway, will retry on first call
	} else {
		log.Println("Python bridge started successfully")
	}
	defer bridge.Stop()

	// Create RLM handler
	handler := NewRLMToolHandler(bridge)

	// Create security validator
	validator := security.NewStrictValidator()

	// Create stdio adapter
	adapter := stdio.NewAdapter(stdio.Config{
		Handler:       handler,
		Validator:     validator,
		ServerName:    "rlm-toolkit",
		ServerVersion: version,
	})

	// Run adapter
	if err := adapter.Run(ctx); err != nil && err != context.Canceled {
		log.Printf("Stdio adapter error: %v", err)
	}
}

func runGRPCServer(sup *supervisor.Supervisor) {
	// TODO: Implement gRPC server using pkg/grpcserver
	fmt.Println("gRPC server not yet implemented")
}

func runHTTPServer(sup *supervisor.Supervisor) {
	// TODO: Implement HTTP/SSE server using pkg/httpmode
	fmt.Println("HTTP server not yet implemented")
}

// findWorkerPath locates the RLM worker script
// REFACTORED (Gemini): Removed magic search logic. Configuration should be explicit.
func findWorkerPath(projectRoot string) string {
	// 1. Check env var
	if envPath := os.Getenv("RLM_WORKER_PATH"); envPath != "" {
		return envPath
	}

	// 2. Check standard convention (gomcp/scripts relative to project root)
	standardPath := filepath.Join(projectRoot, "gomcp", "scripts", "rlm_worker.py")
	if _, err := os.Stat(standardPath); err == nil {
		return standardPath
	}

	// 3. Fallback to bundled script next to executable (for binary distributions)
	exePath, err := os.Executable()
	if err == nil {
		bundledPath := filepath.Join(filepath.Dir(exePath), "scripts", "rlm_worker.py")
		if _, err := os.Stat(bundledPath); err == nil {
			return bundledPath
		}
	}

	return ""
}
