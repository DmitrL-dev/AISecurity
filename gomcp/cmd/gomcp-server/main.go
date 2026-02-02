// GoMCP Server - Next-generation Model Context Protocol server
package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sentinel-community/gomcp/pkg/supervisor"
)

var (
	version = "0.1.0-proto"
	mode    = flag.String("mode", "stdio", "Server mode: stdio, grpc, http")
	timeout = flag.Duration("timeout", 30*time.Second, "Default tool timeout")
)

func main() {
	flag.Parse()

	log.Printf("GoMCP Server v%s starting...", version)
	log.Printf("Mode: %s, Default timeout: %s", *mode, *timeout)

	// Create supervisor
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout:  *timeout,
		MaxWorkers:      10,
		HeartbeatPeriod: 5 * time.Second,
	})

	// Handle shutdown gracefully
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	switch *mode {
	case "stdio":
		log.Println("Starting stdio adapter (MCP v1 compatible)...")
		runStdioAdapter(sup)
	case "grpc":
		log.Println("Starting gRPC server (native GoMCP)...")
		runGRPCServer(sup)
	case "http":
		log.Println("Starting HTTP/SSE server...")
		runHTTPServer(sup)
	default:
		log.Fatalf("Unknown mode: %s", *mode)
	}

	<-sigChan
	log.Println("Shutting down...")
	sup.Shutdown()
}

func runStdioAdapter(sup *supervisor.Supervisor) {
	// TODO: Implement MCP v1 stdio adapter
	fmt.Println("stdio adapter not yet implemented")
}

func runGRPCServer(sup *supervisor.Supervisor) {
	// TODO: Implement gRPC server
	fmt.Println("gRPC server not yet implemented")
}

func runHTTPServer(sup *supervisor.Supervisor) {
	// TODO: Implement HTTP/SSE server
	fmt.Println("HTTP server not yet implemented")
}
