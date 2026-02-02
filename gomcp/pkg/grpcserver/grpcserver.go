// Package grpcserver provides a gRPC server for native GoMCP communication.
package grpcserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"time"
)

// ToolHandler is the interface for tool execution
type ToolHandler interface {
	ListTools() []ToolDefinition
	CallTool(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error)
}

// ToolDefinition describes a tool
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description,omitempty"`
	InputSchema json.RawMessage `json:"inputSchema,omitempty"`
}

// Config for the gRPC server
type Config struct {
	Addr          string
	Handler       ToolHandler
	MaxRecvSize   int
	MaxConcurrent int
}

// Server handles gRPC communication
type Server struct {
	config   Config
	handler  ToolHandler
	listener net.Listener
	mu       sync.RWMutex

	// State
	running   bool
	startTime time.Time
	callCount int64

	done chan struct{}
}

// NewServer creates a new gRPC server
func NewServer(cfg Config) *Server {
	addr := cfg.Addr
	if addr == "" {
		addr = ":50051"
	}

	maxConcurrent := cfg.MaxConcurrent
	if maxConcurrent <= 0 {
		maxConcurrent = 100
	}

	return &Server{
		config:  cfg,
		handler: cfg.Handler,
		done:    make(chan struct{}),
	}
}

// Start starts the gRPC server
func (s *Server) Start() error {
	listener, err := net.Listen("tcp", s.config.Addr)
	if err != nil {
		return fmt.Errorf("failed to listen: %w", err)
	}

	s.mu.Lock()
	s.listener = listener
	s.running = true
	s.startTime = time.Now()
	s.mu.Unlock()

	// Accept connections in a loop
	go s.serve()

	return nil
}

func (s *Server) serve() {
	for {
		select {
		case <-s.done:
			return
		default:
			conn, err := s.listener.Accept()
			if err != nil {
				select {
				case <-s.done:
					return
				default:
					continue
				}
			}
			go s.handleConnection(conn)
		}
	}
}

func (s *Server) handleConnection(conn net.Conn) {
	defer conn.Close()

	decoder := json.NewDecoder(conn)
	encoder := json.NewEncoder(conn)

	for {
		var req RPCRequest
		if err := decoder.Decode(&req); err != nil {
			return
		}

		s.mu.Lock()
		s.callCount++
		s.mu.Unlock()

		resp := s.handleRequest(context.Background(), &req)
		if err := encoder.Encode(resp); err != nil {
			return
		}
	}
}

// RPCRequest is the gRPC request format
type RPCRequest struct {
	ID     string          `json:"id"`
	Method string          `json:"method"`
	Params json.RawMessage `json:"params,omitempty"`
}

// RPCResponse is the gRPC response format
type RPCResponse struct {
	ID     string          `json:"id"`
	Result json.RawMessage `json:"result,omitempty"`
	Error  *RPCError       `json:"error,omitempty"`
}

// RPCError for error responses
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Error codes
const (
	ErrInvalidRequest = 1
	ErrMethodNotFound = 2
	ErrInvalidParams  = 3
	ErrInternal       = 4
	ErrNotFound       = 5
)

func (s *Server) handleRequest(ctx context.Context, req *RPCRequest) *RPCResponse {
	switch req.Method {
	case "gomcp.ListTools":
		return s.handleListTools(req)
	case "gomcp.CallTool":
		return s.handleCallTool(ctx, req)
	case "gomcp.Health":
		return s.handleHealth(req)
	case "gomcp.Stats":
		return s.handleStats(req)
	default:
		return &RPCResponse{
			ID: req.ID,
			Error: &RPCError{
				Code:    ErrMethodNotFound,
				Message: fmt.Sprintf("method not found: %s", req.Method),
			},
		}
	}
}

func (s *Server) handleListTools(req *RPCRequest) *RPCResponse {
	var tools []ToolDefinition
	if s.handler != nil {
		tools = s.handler.ListTools()
	}
	if tools == nil {
		tools = []ToolDefinition{}
	}

	result := map[string]interface{}{"tools": tools}
	data, _ := json.Marshal(result)
	return &RPCResponse{ID: req.ID, Result: data}
}

// CallToolParams for tool call requests
type CallToolParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments,omitempty"`
	Timeout   time.Duration   `json:"timeout,omitempty"`
}

func (s *Server) handleCallTool(ctx context.Context, req *RPCRequest) *RPCResponse {
	var params CallToolParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return &RPCResponse{
			ID: req.ID,
			Error: &RPCError{
				Code:    ErrInvalidParams,
				Message: "invalid params: " + err.Error(),
			},
		}
	}

	if s.handler == nil {
		return &RPCResponse{
			ID: req.ID,
			Error: &RPCError{
				Code:    ErrInternal,
				Message: "no handler configured",
			},
		}
	}

	timeout := params.Timeout
	if timeout <= 0 {
		timeout = 30 * time.Second
	}

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	start := time.Now()
	result, err := s.handler.CallTool(ctx, params.Name, params.Arguments)
	duration := time.Since(start)

	if err != nil {
		return &RPCResponse{
			ID: req.ID,
			Error: &RPCError{
				Code:    ErrInternal,
				Message: err.Error(),
			},
		}
	}

	response := map[string]interface{}{
		"output":   result,
		"duration": duration.String(),
	}
	data, _ := json.Marshal(response)
	return &RPCResponse{ID: req.ID, Result: data}
}

func (s *Server) handleHealth(req *RPCRequest) *RPCResponse {
	s.mu.RLock()
	uptime := time.Since(s.startTime)
	s.mu.RUnlock()

	result := map[string]interface{}{
		"status": "healthy",
		"uptime": uptime.String(),
	}
	data, _ := json.Marshal(result)
	return &RPCResponse{ID: req.ID, Result: data}
}

func (s *Server) handleStats(req *RPCRequest) *RPCResponse {
	s.mu.RLock()
	callCount := s.callCount
	uptime := time.Since(s.startTime)
	s.mu.RUnlock()

	result := map[string]interface{}{
		"calls":  callCount,
		"uptime": uptime.String(),
	}
	data, _ := json.Marshal(result)
	return &RPCResponse{ID: req.ID, Result: data}
}

// Stop stops the gRPC server
func (s *Server) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running {
		return nil
	}

	close(s.done)
	s.running = false

	if s.listener != nil {
		return s.listener.Close()
	}
	return nil
}

// IsRunning returns whether the server is running
func (s *Server) IsRunning() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.running
}

// Addr returns the server address
func (s *Server) Addr() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.listener != nil {
		return s.listener.Addr().String()
	}
	return s.config.Addr
}

// Stats returns server statistics
func (s *Server) Stats() (callCount int64, uptime time.Duration) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.callCount, time.Since(s.startTime)
}
