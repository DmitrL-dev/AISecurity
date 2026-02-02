// Example: Basic MCP Server with Hooks
//
// This example demonstrates creating an MCP server with
// lifecycle hooks for logging and monitoring.
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/sentinel-community/gomcp/pkg/hooks"
)

func main() {
	// Create hook registry
	registry := hooks.NewRegistry()

	// Add logging hook for all tool calls
	registry.Register(hooks.MethodToolsCall, hooks.PhaseBefore, hooks.HandlerFunc(
		func(ctx context.Context, e *hooks.Event) error {
			log.Printf("[BEFORE] Tool call: %s params=%v", e.Method, e.Params)
			return nil
		},
	))

	registry.Register(hooks.MethodToolsCall, hooks.PhaseAfter, hooks.HandlerFunc(
		func(ctx context.Context, e *hooks.Event) error {
			log.Printf("[AFTER] Tool call completed: result=%v", e.Result)
			return nil
		},
	))

	// Add timing hook
	var startTime time.Time
	registry.RegisterWithOrder(hooks.MethodToolsCall, hooks.PhaseBefore, hooks.HandlerFunc(
		func(ctx context.Context, e *hooks.Event) error {
			startTime = time.Now()
			return nil
		},
	), -1) // Run first (order -1)

	registry.RegisterWithOrder(hooks.MethodToolsCall, hooks.PhaseAfter, hooks.HandlerFunc(
		func(ctx context.Context, e *hooks.Event) error {
			duration := time.Since(startTime)
			log.Printf("[TIMING] Duration: %v", duration)
			return nil
		},
	), 100) // Run last (order 100)

	// Add error handling hook
	registry.Register(hooks.MethodToolsCall, hooks.PhaseError, hooks.HandlerFunc(
		func(ctx context.Context, e *hooks.Event) error {
			log.Printf("[ERROR] Tool failed: %v", e.Error)
			// Could send to monitoring, increment metrics, etc.
			return nil
		},
	))

	// Simulate tool execution with hooks
	ctx := context.Background()

	// Before hooks
	registry.ExecuteBefore(ctx, hooks.MethodToolsCall, map[string]any{
		"tool": "calculator",
		"args": map[string]any{"a": 1, "b": 2},
	})

	// Simulate tool work
	time.Sleep(10 * time.Millisecond)
	result := map[string]any{"sum": 3}

	// After hooks
	registry.ExecuteAfter(ctx, hooks.MethodToolsCall, result)

	fmt.Println("Hooks example completed!")
}
