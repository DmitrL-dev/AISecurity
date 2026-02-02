// Package batching provides batch processing for tool calls in GoMCP.
package batching

import (
	"context"
	"encoding/json"
	"sync"
	"time"
)

// Request represents a single tool call in a batch
type Request struct {
	ID        string          `json:"id"`
	ToolName  string          `json:"tool_name"`
	Arguments json.RawMessage `json:"arguments"`
}

// Response represents the result of a single tool call
type Response struct {
	ID       string          `json:"id"`
	Success  bool            `json:"success"`
	Output   json.RawMessage `json:"output,omitempty"`
	Error    *Error          `json:"error,omitempty"`
	Duration time.Duration   `json:"duration_ns"`
}

// Error represents a batch execution error
type Error struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// BatchRequest contains multiple tool calls to execute
type BatchRequest struct {
	Requests    []Request     `json:"requests"`
	Parallel    bool          `json:"parallel"`
	MaxParallel int           `json:"max_parallel,omitempty"`
	Timeout     time.Duration `json:"timeout,omitempty"`
}

// BatchResponse contains results for all tool calls
type BatchResponse struct {
	Responses     []Response    `json:"responses"`
	TotalDuration time.Duration `json:"total_duration_ns"`
	SuccessCount  int           `json:"success_count"`
	ErrorCount    int           `json:"error_count"`
}

// Executor interface for tool execution
type Executor interface {
	Execute(ctx context.Context, toolName string, args json.RawMessage) (json.RawMessage, error)
}

// ExecutorFunc wraps a function as Executor
type ExecutorFunc func(ctx context.Context, toolName string, args json.RawMessage) (json.RawMessage, error)

func (f ExecutorFunc) Execute(ctx context.Context, toolName string, args json.RawMessage) (json.RawMessage, error) {
	return f(ctx, toolName, args)
}

// Processor handles batch execution
type Processor struct {
	executor       Executor
	defaultTimeout time.Duration
	maxParallel    int
}

// ProcessorConfig configures the batch processor
type ProcessorConfig struct {
	DefaultTimeout time.Duration
	MaxParallel    int
}

// NewProcessor creates a new batch processor
func NewProcessor(executor Executor, cfg ProcessorConfig) *Processor {
	if cfg.DefaultTimeout == 0 {
		cfg.DefaultTimeout = 30 * time.Second
	}
	if cfg.MaxParallel == 0 {
		cfg.MaxParallel = 10
	}

	return &Processor{
		executor:       executor,
		defaultTimeout: cfg.DefaultTimeout,
		maxParallel:    cfg.MaxParallel,
	}
}

// Process executes a batch of tool calls
func (p *Processor) Process(ctx context.Context, batch BatchRequest) BatchResponse {
	start := time.Now()

	// Apply defaults
	timeout := batch.Timeout
	if timeout == 0 {
		timeout = p.defaultTimeout
	}

	maxParallel := batch.MaxParallel
	if maxParallel == 0 || maxParallel > p.maxParallel {
		maxParallel = p.maxParallel
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	var responses []Response

	if batch.Parallel && len(batch.Requests) > 1 {
		responses = p.executeParallel(ctx, batch.Requests, maxParallel)
	} else {
		responses = p.executeSequential(ctx, batch.Requests)
	}

	// Count results
	successCount := 0
	errorCount := 0
	for _, r := range responses {
		if r.Success {
			successCount++
		} else {
			errorCount++
		}
	}

	return BatchResponse{
		Responses:     responses,
		TotalDuration: time.Since(start),
		SuccessCount:  successCount,
		ErrorCount:    errorCount,
	}
}

func (p *Processor) executeSequential(ctx context.Context, requests []Request) []Response {
	responses := make([]Response, 0, len(requests))

	for _, req := range requests {
		resp := p.executeSingle(ctx, req)
		responses = append(responses, resp)

		// Check context cancellation
		if ctx.Err() != nil {
			// Mark remaining as cancelled
			for i := len(responses); i < len(requests); i++ {
				responses = append(responses, Response{
					ID:      requests[i].ID,
					Success: false,
					Error:   &Error{Code: -1, Message: "batch cancelled"},
				})
			}
			break
		}
	}

	return responses
}

func (p *Processor) executeParallel(ctx context.Context, requests []Request, maxParallel int) []Response {
	responses := make([]Response, len(requests))
	var wg sync.WaitGroup

	// Semaphore for limiting concurrency
	sem := make(chan struct{}, maxParallel)

	for i, req := range requests {
		wg.Add(1)
		go func(idx int, request Request) {
			defer wg.Done()

			sem <- struct{}{}        // Acquire
			defer func() { <-sem }() // Release

			responses[idx] = p.executeSingle(ctx, request)
		}(i, req)
	}

	wg.Wait()
	return responses
}

func (p *Processor) executeSingle(ctx context.Context, req Request) Response {
	start := time.Now()

	output, err := p.executor.Execute(ctx, req.ToolName, req.Arguments)
	duration := time.Since(start)

	if err != nil {
		return Response{
			ID:       req.ID,
			Success:  false,
			Error:    &Error{Code: -1, Message: err.Error()},
			Duration: duration,
		}
	}

	return Response{
		ID:       req.ID,
		Success:  true,
		Output:   output,
		Duration: duration,
	}
}

// Builder provides a fluent API for constructing batch requests
type Builder struct {
	requests    []Request
	parallel    bool
	maxParallel int
	timeout     time.Duration
}

// NewBuilder creates a new batch builder
func NewBuilder() *Builder {
	return &Builder{
		requests: make([]Request, 0),
	}
}

// Add adds a tool call to the batch
func (b *Builder) Add(id, toolName string, args json.RawMessage) *Builder {
	b.requests = append(b.requests, Request{
		ID:        id,
		ToolName:  toolName,
		Arguments: args,
	})
	return b
}

// AddJSON adds a tool call with JSON-encodable arguments
func (b *Builder) AddJSON(id, toolName string, args interface{}) *Builder {
	data, _ := json.Marshal(args)
	return b.Add(id, toolName, data)
}

// Parallel enables parallel execution
func (b *Builder) Parallel(max int) *Builder {
	b.parallel = true
	b.maxParallel = max
	return b
}

// Sequential enables sequential execution
func (b *Builder) Sequential() *Builder {
	b.parallel = false
	return b
}

// Timeout sets the batch timeout
func (b *Builder) Timeout(d time.Duration) *Builder {
	b.timeout = d
	return b
}

// Build constructs the BatchRequest
func (b *Builder) Build() BatchRequest {
	return BatchRequest{
		Requests:    b.requests,
		Parallel:    b.parallel,
		MaxParallel: b.maxParallel,
		Timeout:     b.timeout,
	}
}

// Size returns the number of requests in the batch
func (b *Builder) Size() int {
	return len(b.requests)
}

// Clear removes all requests from the builder
func (b *Builder) Clear() *Builder {
	b.requests = b.requests[:0]
	return b
}
