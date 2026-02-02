// Example: Auto-completions for Prompts
//
// This example demonstrates setting up completion providers
// for prompt arguments and resource URIs.
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/sentinel-community/gomcp/pkg/completions"
)

func main() {
	// Create completion manager
	manager := completions.NewManager()

	// Register static provider for model names
	manager.RegisterProvider(
		completions.RefTypePrompt,
		"generate_code",
		completions.NewStaticProvider([]string{
			"gpt-4",
			"gpt-4-turbo",
			"gpt-3.5-turbo",
			"claude-3-opus",
			"claude-3-sonnet",
			"gemini-pro",
		}),
	)

	// Register dynamic provider for file paths
	manager.RegisterProvider(
		completions.RefTypeResource,
		"", // All resources
		completions.NewPrefixProvider(func() []string {
			// In real app, would scan filesystem
			return []string{
				"file:///src/main.go",
				"file:///src/utils.go",
				"file:///src/config.yaml",
				"file:///tests/main_test.go",
			}
		}),
	)

	ctx := context.Background()

	// Test completion for model names starting with "gpt"
	resp, err := manager.Complete(ctx, &completions.Request{
		Ref: completions.CompletionRef{
			Type: completions.RefTypePrompt,
			Name: "generate_code",
		},
		Argument: completions.CompletionArg{
			Name:  "model",
			Value: "gpt",
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("Model completions for 'gpt':")
	for _, v := range resp.Completion.Values {
		fmt.Printf("  - %s\n", v)
	}

	// Test completion for file paths starting with "file:///src"
	resp2, err := manager.Complete(ctx, &completions.Request{
		Ref: completions.CompletionRef{
			Type: completions.RefTypeResource,
		},
		Argument: completions.CompletionArg{
			Name:  "uri",
			Value: "file:///src",
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("\nFile completions for 'file:///src':")
	for _, v := range resp2.Completion.Values {
		fmt.Printf("  - %s\n", v)
	}
}
