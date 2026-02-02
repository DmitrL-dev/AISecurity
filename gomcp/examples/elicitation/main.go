// Example: Elicitation (User Input Requests)
//
// This example demonstrates requesting user input
// for confirmations, selections, and data entry.
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/sentinel-community/gomcp/pkg/elicitation"
)

func main() {
	// Create mock handler (simulates user responses)
	handler := elicitation.NewMockHandler(map[string]any{
		"confirm":       true,
		"project_name":  "my-awesome-project",
		"language":      "go",
		"include_tests": true,
		"max_file_size": 1024,
	})

	ctx := context.Background()

	// 1. Boolean confirmation
	confirmReq := elicitation.BooleanInput("confirm",
		"Delete all temporary files?",
		"This action cannot be undone.")

	confirmResult, err := handler.Handle(ctx, confirmReq)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("User confirmed: %v\n", confirmResult.Value)

	// 2. Text input
	nameReq := elicitation.TextInput("project_name",
		"Enter project name:",
		"Choose a unique identifier").
		WithValidation(`^[a-z][a-z0-9-]*$`)

	nameResult, _ := handler.Handle(ctx, nameReq)
	fmt.Printf("Project name: %v\n", nameResult.Value)

	// 3. Select from options
	langReq := elicitation.SelectInput("language",
		"Choose programming language:",
		[]string{"go", "python", "typescript", "rust"}).
		WithDefault("go")

	langResult, _ := handler.Handle(ctx, langReq)
	fmt.Printf("Selected language: %v\n", langResult.Value)

	// 4. Number input with range
	sizeReq := elicitation.NumberInput("max_file_size",
		"Maximum file size (KB):",
		"Files larger than this will be skipped").
		WithRange(1, 10240).
		WithDefault(1024)

	sizeResult, _ := handler.Handle(ctx, sizeReq)
	fmt.Printf("Max file size: %vKB\n", sizeResult.Value)

	// 5. Complex object input
	configReq := elicitation.ObjectInput("config",
		"Configure project settings:",
		map[string]any{
			"name":        "string",
			"description": "string",
			"version":     "string",
		})

	configResult, _ := handler.Handle(ctx, configReq)
	fmt.Printf("Config: %v\n", configResult.Value)

	fmt.Println("\nAll inputs collected successfully!")
}
