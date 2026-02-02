// Example: Session Management
//
// This example demonstrates per-session tool registration
// and context propagation.
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/sentinel-community/gomcp/pkg/session"
)

func main() {
	// Create session manager
	manager := session.NewManager()

	// Set up lifecycle callbacks
	manager.OnSessionStart(func(s *session.Session) {
		log.Printf("[SESSION START] %s", s.ID)
	})

	manager.OnSessionEnd(func(s *session.Session) {
		log.Printf("[SESSION END] %s", s.ID)
	})

	// Create sessions for different clients
	client1, _ := manager.Create("client-1", &session.ClientInfo{
		Name:    "desktop-app",
		Version: "2.0.0",
	})

	client2, _ := manager.Create("client-2", &session.ClientInfo{
		Name:    "mobile-app",
		Version: "1.5.0",
	})

	// Register different tools for each session
	client1.RegisterTool("file_system")
	client1.RegisterTool("database")
	client1.RegisterTool("admin_tools")

	client2.RegisterTool("file_system")
	// Mobile doesn't get admin_tools

	// Set session context
	client1.SetContext("user_id", "admin-001")
	client1.SetContext("role", "admin")

	client2.SetContext("user_id", "user-002")
	client2.SetContext("role", "viewer")

	// Simulate request handling
	handleToolCall(manager, "client-1", "admin_tools")
	handleToolCall(manager, "client-2", "admin_tools")
	handleToolCall(manager, "client-2", "file_system")

	// List all sessions
	fmt.Printf("\nActive sessions: %d\n", manager.Count())
	for _, s := range manager.List() {
		fmt.Printf("  - %s (%s): %d tools\n",
			s.ID, s.ClientInfo.Name, len(s.GetTools()))
	}

	// Cleanup old sessions
	time.Sleep(10 * time.Millisecond)
	cleaned := manager.Cleanup(time.Hour) // Won't clean anything (sessions are fresh)
	fmt.Printf("\nCleaned %d old sessions\n", cleaned)

	// Delete session
	manager.Delete("client-1")
	fmt.Printf("After delete: %d sessions\n", manager.Count())
}

func handleToolCall(m *session.Manager, sessionID, tool string) {
	sess, err := m.Get(sessionID)
	if err != nil {
		log.Printf("[ERROR] Session not found: %s", sessionID)
		return
	}

	// Create context with session
	ctx := session.WithSession(context.Background(), sess)

	// Check tool access
	if s, ok := session.FromContext(ctx); ok {
		if s.HasTool(tool) {
			role, _ := s.GetContext("role")
			fmt.Printf("[ALLOWED] %s can use %s (role=%v)\n", sessionID, tool, role)
		} else {
			fmt.Printf("[DENIED] %s cannot use %s\n", sessionID, tool)
		}
	}

	sess.Touch() // Update last active
}
