// Example: MCP Client SDK
//
// This example demonstrates using the Go client to connect
// to an MCP server and interact with tools, resources, and prompts.
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/sentinel-community/gomcp/pkg/client"
)

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Create stdio client to connect to MCP server
	cfg := client.Config{
		Name:    "example-client",
		Version: "1.0.0",
		Capabilities: map[string]any{
			"sampling": map[string]any{},
		},
	}

	// Connect via stdio (would normally spawn server process)
	// cli, err := client.NewStdioClient(ctx, cfg, "mcp-server", "--stdio")

	// For demo, we'll show the API patterns:
	fmt.Println("=== MCP Client SDK Example ===")
	fmt.Println()

	// 1. List available tools
	fmt.Println("1. Listing tools...")
	fmt.Println("   client.ListTools(ctx)")
	fmt.Println("   → Returns: []ToolInfo{name, description, inputSchema}")
	fmt.Println()

	// 2. Call a tool
	fmt.Println("2. Calling a tool...")
	fmt.Println("   result, err := client.CallTool(ctx, \"calculator\", map[string]any{")
	fmt.Println("       \"operation\": \"add\",")
	fmt.Println("       \"a\": 5,")
	fmt.Println("       \"b\": 3,")
	fmt.Println("   })")
	fmt.Println("   → Returns: ToolResult{content, isError}")
	fmt.Println()

	// 3. List resources
	fmt.Println("3. Reading resources...")
	fmt.Println("   resources, _ := client.ListResources(ctx)")
	fmt.Println("   content, _ := client.ReadResource(ctx, \"file:///config.yaml\")")
	fmt.Println("   → Returns: ResourceContent{uri, mimeType, text}")
	fmt.Println()

	// 4. Get prompts
	fmt.Println("4. Getting prompts...")
	fmt.Println("   prompts, _ := client.ListPrompts(ctx)")
	fmt.Println("   result, _ := client.GetPrompt(ctx, \"code_review\", map[string]any{")
	fmt.Println("       \"language\": \"go\",")
	fmt.Println("       \"code\": \"func main() {}\")")
	fmt.Println("   })")
	fmt.Println("   → Returns: PromptResult{messages}")
	fmt.Println()

	// 5. Notifications
	fmt.Println("5. Handling notifications...")
	fmt.Println("   client.OnNotification(func(method string, params any) {")
	fmt.Println("       log.Printf(\"Notification: %s\", method)")
	fmt.Println("   })")
	fmt.Println()

	// Example of actual client creation (commented for demo)
	fmt.Println("=== Real Usage ===")
	fmt.Println(`
	cli, err := client.NewStdioClient(ctx, cfg, "npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp")
	if err != nil {
		log.Fatal(err)
	}
	defer cli.Close()

	tools, _ := cli.ListTools(ctx)
	for _, tool := range tools {
		fmt.Printf("Tool: %s - %s\n", tool.Name, tool.Description)
	}
	`)

	log.Printf("Example completed at %v", time.Now())
}
