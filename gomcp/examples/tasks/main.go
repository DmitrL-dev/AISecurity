// Example: Async Tasks with Progress Tracking
//
// This example demonstrates creating and managing async tasks
// with progress updates and state transitions.
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/sentinel-community/gomcp/pkg/tasks"
)

func main() {
	// Create task manager
	manager := tasks.NewManager()

	// Start listening for updates
	go func() {
		for task := range manager.Updates() {
			log.Printf("[UPDATE] Task %s: state=%s progress=%v",
				task.ID, task.State, task.Progress)
		}
	}()

	// Create a long-running task
	task, err := manager.Create("data_processing", map[string]any{
		"input": "large_dataset.csv",
		"rows":  1000000,
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Created task: %s\n", task.ID)

	// Simulate processing with progress updates
	ctx := context.Background()
	go processTask(ctx, manager, task.ID)

	// Wait for completion
	for {
		t, _ := manager.Get(task.ID)
		if t.IsTerminal() {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}

	// Get final result
	finalTask, _ := manager.Get(task.ID)
	fmt.Printf("Task completed! State: %s, Result: %v\n",
		finalTask.State, finalTask.Result)
}

func processTask(ctx context.Context, m *tasks.Manager, taskID string) {
	// Simulate progress
	for i := 1; i <= 5; i++ {
		time.Sleep(200 * time.Millisecond)
		m.UpdateProgress(taskID, i*20, 100, fmt.Sprintf("Processing batch %d/5", i))
	}

	// Complete task
	m.Complete(taskID, map[string]any{
		"processed_rows": 1000000,
		"duration_ms":    1000,
	})
}
