// Example: Filesystem Roots Management
//
// This example demonstrates managing client filesystem roots
// for sandboxed file access.
package main

import (
	"fmt"
	"log"

	"github.com/sentinel-community/gomcp/pkg/roots"
)

func main() {
	// Create roots manager
	manager := roots.NewManager()

	// Set up change notification
	manager.OnChange(func(rootList []*roots.Root) {
		log.Printf("[ROOTS CHANGED] Now have %d roots", len(rootList))
	})

	// Add project roots
	manager.Add("file:///home/user/project", "Main Project")
	manager.Add("file:///home/user/libs", "Shared Libraries")
	manager.Add("file:///tmp/workspace", "Temp Workspace")

	// List all roots
	fmt.Println("Registered roots:")
	for _, root := range manager.List() {
		fmt.Printf("  - %s (%s)\n", root.Name, root.URI)
	}

	// Check if paths are within roots
	testPaths := []string{
		"file:///home/user/project/src/main.go",
		"file:///home/user/project",
		"file:///home/user/other/secret.txt",
		"file:///tmp/workspace/build/out.bin",
	}

	fmt.Println("\nPath containment check:")
	for _, path := range testPaths {
		allowed := manager.Contains(path)
		status := "❌ DENIED"
		if allowed {
			status = "✅ ALLOWED"
		}
		fmt.Printf("  %s: %s\n", path, status)
	}

	// Remove a root
	manager.Remove("file:///tmp/workspace")
	fmt.Printf("\nAfter removal: %d roots\n", manager.Count())

	// Export as JSON (for MCP protocol)
	json, err := manager.ToJSON()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("\nJSON export:\n%s\n", string(json))
}
