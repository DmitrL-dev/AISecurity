// RLM MCP Server - GoMCP-based MCP server for RLM Toolkit
//
// This server provides MCP protocol support for the RLM VSCode extension,
// replacing the Python spawn approach with a persistent Go process.
//
// Usage:
//
//	rlm-mcp-server --mode=stdio
//	rlm-mcp-server --mode=http --port=8080
//	rlm-mcp-server --mode=grpc --port=9090
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/sentinel-community/gomcp/pkg/hooks"
	"github.com/sentinel-community/gomcp/pkg/pythonbridge"
	"github.com/sentinel-community/gomcp/pkg/session"
	"github.com/sentinel-community/gomcp/pkg/tasks"
)

var (
	mode        = flag.String("mode", "stdio", "Server mode: stdio, http, grpc")
	port        = flag.Int("port", 8080, "Port for HTTP/gRPC mode")
	projectRoot = flag.String("project", "", "Project root path")
	pythonPath  = flag.String("python", "python", "Python interpreter path")
	workerPath  = flag.String("worker", "", "Python worker script path")
	debug       = flag.Bool("debug", false, "Enable debug logging")
)

// RLMServer is the main MCP server for RLM
type RLMServer struct {
	projectRoot string
	bridge      *pythonbridge.Bridge
	sessions    *session.Manager
	tasks       *tasks.Manager
	hooks       *hooks.Registry
}

// ServerInfo for MCP initialize
type ServerInfo struct {
	Name            string   `json:"name"`
	Version         string   `json:"version"`
	ProtocolVersion string   `json:"protocolVersion"`
	Capabilities    []string `json:"capabilities"`
}

// Tool represents an MCP tool
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

func main() {
	flag.Parse()

	// Determine project root
	root := *projectRoot
	if root == "" {
		root, _ = os.Getwd()
	}

	// Find worker script
	worker := *workerPath
	if worker == "" {
		worker = filepath.Join(root, "rlm_worker.py")
	}

	// Create server
	srv := NewRLMServer(root, *pythonPath, worker)

	// Start Python bridge
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := srv.Start(ctx); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer srv.Stop()

	// Handle shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	switch *mode {
	case "stdio":
		go srv.ServeStdio(ctx)
	case "http":
		go srv.ServeHTTP(ctx, *port)
	case "grpc":
		go srv.ServeGRPC(ctx, *port)
	default:
		log.Fatalf("Unknown mode: %s", *mode)
	}

	<-sigChan
	log.Println("Shutting down...")
}

// NewRLMServer creates a new RLM MCP server
func NewRLMServer(projectRoot, pythonPath, workerPath string) *RLMServer {
	return &RLMServer{
		projectRoot: projectRoot,
		bridge: pythonbridge.New(pythonbridge.Config{
			PythonPath:  pythonPath,
			WorkerPath:  workerPath,
			ProjectRoot: projectRoot,
		}),
		sessions: session.NewManager(),
		tasks:    tasks.NewManager(),
		hooks:    hooks.NewRegistry(),
	}
}

// Start initializes the server
func (s *RLMServer) Start(ctx context.Context) error {
	// Start Python bridge if worker exists
	if err := s.bridge.Start(ctx); err != nil {
		log.Printf("Warning: Python bridge failed to start: %v", err)
		// Continue without Python bridge - use fallback
	}

	// Register hooks
	s.registerHooks()

	return nil
}

// Stop shuts down the server
func (s *RLMServer) Stop() error {
	return s.bridge.Stop()
}

// registerHooks sets up lifecycle hooks
func (s *RLMServer) registerHooks() {
	// Log all tool calls
	s.hooks.Register("tools/call", hooks.PhaseBefore, hooks.HandlerFunc(
		func(ctx context.Context, event *hooks.Event) error {
			if *debug {
				log.Printf("[HOOK] Before tools/call: %v", event.Params)
			}
			return nil
		},
	))

	s.hooks.Register("tools/call", hooks.PhaseAfter, hooks.HandlerFunc(
		func(ctx context.Context, event *hooks.Event) error {
			if *debug {
				log.Printf("[HOOK] After tools/call: success")
			}
			return nil
		},
	))
}

// GetTools returns available RLM tools
func (s *RLMServer) GetTools() []Tool {
	return []Tool{
		{
			Name:        "rlm_status",
			Description: "Get RLM server status and index stats",
			InputSchema: map[string]any{"type": "object", "properties": map[string]any{}},
		},
		{
			Name:        "rlm_health_check",
			Description: "Health check for Memory Bridge components",
			InputSchema: map[string]any{"type": "object", "properties": map[string]any{}},
		},
		{
			Name:        "rlm_get_hierarchy_stats",
			Description: "Get statistics about hierarchical memory store",
			InputSchema: map[string]any{"type": "object", "properties": map[string]any{}},
		},
		{
			Name:        "rlm_discover_project",
			Description: "Smart cold start discovery for new projects",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"project_root": map[string]any{"type": "string"},
					"task_hint":    map[string]any{"type": "string"},
				},
			},
		},
		{
			Name:        "rlm_enterprise_context",
			Description: "One-call enterprise context with auto-discovery",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"query"},
				"properties": map[string]any{
					"query":          map[string]any{"type": "string"},
					"max_tokens":     map[string]any{"type": "integer", "default": 3000},
					"include_causal": map[string]any{"type": "boolean", "default": true},
				},
			},
		},
		{
			Name:        "rlm_reindex",
			Description: "Reindex project or specific path",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"path":  map[string]any{"type": "string"},
					"force": map[string]any{"type": "boolean", "default": false},
				},
			},
		},
		{
			Name:        "rlm_add_hierarchical_fact",
			Description: "Add fact with hierarchical levels (L0-L3)",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"content"},
				"properties": map[string]any{
					"content": map[string]any{"type": "string"},
					"level":   map[string]any{"type": "integer", "default": 0},
					"domain":  map[string]any{"type": "string"},
					"module":  map[string]any{"type": "string"},
				},
			},
		},
		{
			Name:        "rlm_search_facts",
			Description: "Hybrid search across facts (semantic + keyword + recency)",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"query"},
				"properties": map[string]any{
					"query":           map[string]any{"type": "string"},
					"top_k":           map[string]any{"type": "integer", "default": 10},
					"semantic_weight": map[string]any{"type": "number", "default": 0.5},
					"keyword_weight":  map[string]any{"type": "number", "default": 0.3},
					"recency_weight":  map[string]any{"type": "number", "default": 0.2},
				},
			},
		},
	}
}

// CallTool executes an RLM tool
func (s *RLMServer) CallTool(ctx context.Context, name string, params map[string]any) (map[string]any, error) {
	// Execute before hooks
	if err := s.hooks.ExecuteBefore(ctx, "tools/call", params); err != nil {
		return nil, err
	}

	var result map[string]any
	var err error

	// Route to appropriate handler
	switch name {
	case "rlm_status":
		result, err = s.handleStatus(ctx)
	case "rlm_health_check":
		result, err = s.handleHealthCheck(ctx)
	case "rlm_get_hierarchy_stats":
		result, err = s.handleHierarchyStats(ctx)
	default:
		// Delegate to Python bridge
		result, err = s.delegateToPython(ctx, name, params)
	}

	if err != nil {
		s.hooks.ExecuteError(ctx, "tools/call", err)
		return nil, err
	}

	// Execute after hooks
	s.hooks.ExecuteAfter(ctx, "tools/call", result)

	return result, nil
}

// handleStatus returns server status (Go native implementation)
func (s *RLMServer) handleStatus(ctx context.Context) (map[string]any, error) {
	return map[string]any{
		"success": true,
		"version": "2.1.0",
		"runtime": "gomcp",
		"uptime":  time.Since(time.Now()).String(),
		"project": s.projectRoot,
		"python_bridge": map[string]any{
			"running": s.bridge.IsRunning(),
		},
		"sessions": map[string]any{
			"count": s.sessions.Count(),
		},
	}, nil
}

// handleHealthCheck returns component health
func (s *RLMServer) handleHealthCheck(ctx context.Context) (map[string]any, error) {
	components := map[string]any{
		"server":        "healthy",
		"sessions":      "healthy",
		"tasks":         "healthy",
		"python_bridge": "healthy",
	}

	if !s.bridge.IsRunning() {
		components["python_bridge"] = "degraded"
	}

	return map[string]any{
		"success":    true,
		"status":     "healthy",
		"components": components,
		"timestamp":  time.Now().Format(time.RFC3339),
	}, nil
}

// handleHierarchyStats returns memory stats
func (s *RLMServer) handleHierarchyStats(ctx context.Context) (map[string]any, error) {
	// Delegate to Python for actual DB access
	return s.delegateToPython(ctx, "rlm_get_hierarchy_stats", nil)
}

// delegateToPython sends request to Python bridge
func (s *RLMServer) delegateToPython(ctx context.Context, tool string, params map[string]any) (map[string]any, error) {
	if !s.bridge.IsRunning() {
		return nil, fmt.Errorf("python bridge not available")
	}

	resp, err := s.bridge.Call(ctx, tool, params)
	if err != nil {
		return nil, fmt.Errorf("python call failed: %w", err)
	}

	if !resp.Success {
		return nil, fmt.Errorf("python tool error: %s", resp.Error)
	}

	return resp.Result, nil
}

// ServeStdio handles stdio MCP transport
func (s *RLMServer) ServeStdio(ctx context.Context) {
	decoder := json.NewDecoder(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		var request map[string]any
		if err := decoder.Decode(&request); err != nil {
			continue
		}

		response := s.handleRequest(ctx, request)
		encoder.Encode(response)
	}
}

// handleRequest processes JSON-RPC request
func (s *RLMServer) handleRequest(ctx context.Context, request map[string]any) map[string]any {
	method, _ := request["method"].(string)
	id := request["id"]
	params, _ := request["params"].(map[string]any)

	var result any
	var err error

	switch method {
	case "initialize":
		result = s.GetServerInfo()
	case "tools/list":
		result = map[string]any{"tools": s.GetTools()}
	case "tools/call":
		toolName, _ := params["name"].(string)
		toolArgs, _ := params["arguments"].(map[string]any)
		result, err = s.CallTool(ctx, toolName, toolArgs)
	default:
		err = fmt.Errorf("unknown method: %s", method)
	}

	if err != nil {
		return map[string]any{
			"jsonrpc": "2.0",
			"id":      id,
			"error": map[string]any{
				"code":    -32601,
				"message": err.Error(),
			},
		}
	}

	return map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"result":  result,
	}
}

// GetServerInfo returns MCP server info
func (s *RLMServer) GetServerInfo() ServerInfo {
	return ServerInfo{
		Name:            "rlm-mcp-server",
		Version:         "2.1.0",
		ProtocolVersion: "2025-11-25",
		Capabilities:    []string{"tools", "resources", "prompts"},
	}
}

// ServeHTTP starts HTTP server (placeholder)
func (s *RLMServer) ServeHTTP(ctx context.Context, port int) {
	log.Printf("HTTP server starting on port %d", port)
	// TODO: Implement HTTP transport
	<-ctx.Done()
}

// ServeGRPC starts gRPC server (placeholder)
func (s *RLMServer) ServeGRPC(ctx context.Context, port int) {
	log.Printf("gRPC server starting on port %d", port)
	// TODO: Implement gRPC transport
	<-ctx.Done()
}
