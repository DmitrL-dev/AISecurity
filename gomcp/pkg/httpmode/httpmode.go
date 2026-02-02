// Package httpmode provides a Docker-native HTTP server for GoMCP.
package httpmode

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/sentinel-community/gomcp/pkg/batching"
	"github.com/sentinel-community/gomcp/pkg/health"
	"github.com/sentinel-community/gomcp/pkg/security"
	"github.com/sentinel-community/gomcp/pkg/tenant"
)

// ToolRequest represents a single tool call request
type ToolRequest struct {
	Tool      string          `json:"tool"`
	Arguments json.RawMessage `json:"arguments"`
	TenantID  string          `json:"tenant_id,omitempty"`
}

// ToolResponse represents a tool call response
type ToolResponse struct {
	Success bool            `json:"success"`
	Output  json.RawMessage `json:"output,omitempty"`
	Error   string          `json:"error,omitempty"`
	Latency string          `json:"latency"`
}

// BatchToolRequest for multiple tool calls
type BatchToolRequest struct {
	Requests    []ToolRequest `json:"requests"`
	Parallel    bool          `json:"parallel"`
	MaxParallel int           `json:"max_parallel,omitempty"`
}

// BatchToolResponse for batch results
type BatchToolResponse struct {
	Responses    []ToolResponse `json:"responses"`
	TotalLatency string         `json:"total_latency"`
	SuccessCount int            `json:"success_count"`
	ErrorCount   int            `json:"error_count"`
}

// ToolHandler is the interface for executing tools
type ToolHandler interface {
	Execute(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error)
	ListTools() []ToolInfo
}

// ToolInfo describes an available tool
type ToolInfo struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"input_schema,omitempty"`
}

// Server is the HTTP server for GoMCP
type Server struct {
	handler       ToolHandler
	validator     *security.Validator
	healthServer  *health.Server
	tenantManager *tenant.Manager
	batchProc     *batching.Processor

	mu      sync.RWMutex
	addr    string
	server  *http.Server
	running bool
}

// Config for the HTTP server
type Config struct {
	Addr          string
	Handler       ToolHandler
	Validator     *security.Validator
	HealthServer  *health.Server
	TenantManager *tenant.Manager
}

// NewServer creates a new HTTP server
func NewServer(cfg Config) *Server {
	if cfg.Addr == "" {
		cfg.Addr = ":8080"
	}

	s := &Server{
		handler:       cfg.Handler,
		validator:     cfg.Validator,
		healthServer:  cfg.HealthServer,
		tenantManager: cfg.TenantManager,
		addr:          cfg.Addr,
	}

	// Create batch processor if handler available
	if cfg.Handler != nil {
		s.batchProc = batching.NewProcessor(
			batching.ExecutorFunc(func(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error) {
				return cfg.Handler.Execute(ctx, tool, args)
			}),
			batching.ProcessorConfig{
				DefaultTimeout: 30 * time.Second,
				MaxParallel:    10,
			},
		)
	}

	return s
}

// Start starts the HTTP server
func (s *Server) Start() error {
	mux := http.NewServeMux()

	// Tool endpoints
	mux.HandleFunc("/v1/tools", s.handleListTools)
	mux.HandleFunc("/v1/tools/call", s.handleToolCall)
	mux.HandleFunc("/v1/tools/batch", s.handleBatchCall)

	// Health endpoints
	if s.healthServer != nil {
		s.healthServer.RegisterHandlers(mux)
	} else {
		mux.HandleFunc("/health", s.handleBasicHealth)
		mux.HandleFunc("/healthz", s.handleBasicHealth)
	}

	s.mu.Lock()
	s.server = &http.Server{
		Addr:         s.addr,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 60 * time.Second,
	}
	s.running = true
	s.mu.Unlock()

	return s.server.ListenAndServe()
}

// Stop gracefully stops the server
func (s *Server) Stop(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running || s.server == nil {
		return nil
	}

	s.running = false
	return s.server.Shutdown(ctx)
}

// IsRunning returns whether the server is running
func (s *Server) IsRunning() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.running
}

func (s *Server) handleListTools(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if s.handler == nil {
		s.jsonResponse(w, http.StatusOK, []ToolInfo{})
		return
	}

	tools := s.handler.ListTools()
	s.jsonResponse(w, http.StatusOK, tools)
}

func (s *Server) handleToolCall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ToolRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.jsonResponse(w, http.StatusBadRequest, ToolResponse{
			Success: false,
			Error:   "invalid request: " + err.Error(),
		})
		return
	}

	// Validate input
	if s.validator != nil {
		result := s.validator.ValidateJSON(req.Arguments)
		if !result.Valid {
			errMsg := "validation failed"
			if len(result.Errors) > 0 {
				errMsg = result.Errors[0].Error()
			}
			s.jsonResponse(w, http.StatusBadRequest, ToolResponse{
				Success: false,
				Error:   errMsg,
			})
			return
		}
	}

	// Check tenant access
	ctx := r.Context()
	if s.tenantManager != nil && req.TenantID != "" {
		t, err := s.tenantManager.GetTenant(req.TenantID)
		if err != nil {
			s.jsonResponse(w, http.StatusForbidden, ToolResponse{
				Success: false,
				Error:   "tenant not found",
			})
			return
		}
		if !t.IsToolAllowed(req.Tool) {
			s.jsonResponse(w, http.StatusForbidden, ToolResponse{
				Success: false,
				Error:   "tool not allowed for tenant",
			})
			return
		}
		ctx = tenant.WithTenant(ctx, t)
	}

	// Execute tool
	start := time.Now()
	if s.handler == nil {
		s.jsonResponse(w, http.StatusServiceUnavailable, ToolResponse{
			Success: false,
			Error:   "no handler configured",
			Latency: time.Since(start).String(),
		})
		return
	}

	output, err := s.handler.Execute(ctx, req.Tool, req.Arguments)
	latency := time.Since(start)

	if err != nil {
		s.jsonResponse(w, http.StatusOK, ToolResponse{
			Success: false,
			Error:   err.Error(),
			Latency: latency.String(),
		})
		return
	}

	s.jsonResponse(w, http.StatusOK, ToolResponse{
		Success: true,
		Output:  output,
		Latency: latency.String(),
	})
}

func (s *Server) handleBatchCall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req BatchToolRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.jsonResponse(w, http.StatusBadRequest, BatchToolResponse{
			ErrorCount: 1,
		})
		return
	}

	if s.batchProc == nil {
		s.jsonResponse(w, http.StatusServiceUnavailable, BatchToolResponse{
			ErrorCount: len(req.Requests),
		})
		return
	}

	// Convert to batching.Request
	batchReqs := make([]batching.Request, len(req.Requests))
	for i, r := range req.Requests {
		batchReqs[i] = batching.Request{
			ID:        fmt.Sprintf("req-%d", i),
			ToolName:  r.Tool,
			Arguments: r.Arguments,
		}
	}

	batchReq := batching.BatchRequest{
		Requests:    batchReqs,
		Parallel:    req.Parallel,
		MaxParallel: req.MaxParallel,
	}

	start := time.Now()
	result := s.batchProc.Process(r.Context(), batchReq)

	// Convert responses
	responses := make([]ToolResponse, len(result.Responses))
	for i, resp := range result.Responses {
		responses[i] = ToolResponse{
			Success: resp.Success,
			Output:  resp.Output,
			Latency: resp.Duration.String(),
		}
		if resp.Error != nil {
			responses[i].Error = resp.Error.Message
		}
	}

	s.jsonResponse(w, http.StatusOK, BatchToolResponse{
		Responses:    responses,
		TotalLatency: time.Since(start).String(),
		SuccessCount: result.SuccessCount,
		ErrorCount:   result.ErrorCount,
	})
}

func (s *Server) handleBasicHealth(w http.ResponseWriter, r *http.Request) {
	s.jsonResponse(w, http.StatusOK, map[string]string{"status": "healthy"})
}

func (s *Server) jsonResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

// Addr returns the server address
func (s *Server) Addr() string {
	return s.addr
}
