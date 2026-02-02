// Example: Sampling (LLM Inference Requests)
//
// This example demonstrates how to request LLM inference
// from a connected client using the sampling API.
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/sentinel-community/gomcp/pkg/sampling"
)

func main() {
	// Create sampling manager
	manager := sampling.NewManager()

	// Register a mock handler (in real app, this sends to client)
	manager.SetHandler(sampling.HandlerFunc(
		func(ctx context.Context, req *sampling.Request) (*sampling.Response, error) {
			log.Printf("Sampling request: model=%s, messages=%d",
				req.ModelPreferences.Hints[0].Name, len(req.Messages))

			// Simulate LLM response
			return &sampling.Response{
				Model:      "claude-3-sonnet",
				StopReason: "end_turn",
				Content: sampling.Content{
					Type: "text",
					Text: "The answer to your question is 42.",
				},
			}, nil
		},
	))

	ctx := context.Background()

	// Build a sampling request using the builder
	req := sampling.NewRequestBuilder().
		WithSystemPrompt("You are a helpful assistant.").
		AddUserMessage("What is the meaning of life?").
		WithModel("claude-3", "gpt-4").
		WithMaxTokens(100).
		Build()

	// Execute sampling
	resp, err := manager.Sample(ctx, req)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Model: %s\n", resp.Model)
	fmt.Printf("Response: %s\n", resp.Content.Text)
	fmt.Printf("Stop reason: %s\n", resp.StopReason)

	// Example with streaming (simulated)
	fmt.Println("\n--- Streaming example ---")

	streamReq := sampling.NewRequestBuilder().
		AddUserMessage("Write a haiku about coding.").
		WithModel("gpt-4").
		WithMaxTokens(50).
		Build()

	// In real implementation, this would stream tokens
	streamResp, _ := manager.Sample(ctx, streamReq)
	fmt.Printf("Streamed response: %s\n", streamResp.Content.Text)
}
