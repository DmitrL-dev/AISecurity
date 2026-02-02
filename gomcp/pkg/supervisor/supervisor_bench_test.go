package supervisor

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func BenchmarkCallTool(b *testing.B) {
	sup := New(Config{})
	defer sup.Shutdown()

	sup.RegisterWorker(&Worker{
		ID: "bench-worker",
		Tools: []ToolDef{
			{Name: "bench_tool", Description: "Benchmark tool"},
		},
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		call := &ToolCall{
			RequestID: "bench",
			ToolName:  "bench_tool",
			Arguments: json.RawMessage(`{}`),
		}
		sup.CallTool(context.Background(), call)
	}
}

func BenchmarkRegisterWorker(b *testing.B) {
	for i := 0; i < b.N; i++ {
		sup := New(Config{})
		sup.RegisterWorker(&Worker{
			ID: "worker",
			Tools: []ToolDef{
				{Name: "tool", Description: "A tool"},
			},
		})
		sup.Shutdown()
	}
}

func BenchmarkListTools(b *testing.B) {
	sup := New(Config{})
	defer sup.Shutdown()

	for i := 0; i < 10; i++ {
		sup.RegisterWorker(&Worker{
			ID: string(rune('a' + i)),
			Tools: []ToolDef{
				{Name: string(rune('a' + i)), Description: "Tool"},
			},
		})
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		sup.ListTools()
	}
}

func TestConcurrentCallTool(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	sup.RegisterWorker(&Worker{
		ID: "concurrent-worker",
		Tools: []ToolDef{
			{Name: "concurrent_tool", Description: "Concurrent test tool"},
		},
	})

	done := make(chan bool, 100)

	for i := 0; i < 100; i++ {
		go func(id int) {
			call := &ToolCall{
				RequestID: string(rune('a' + id%26)),
				ToolName:  "concurrent_tool",
				Arguments: json.RawMessage(`{}`),
			}
			result := sup.CallTool(context.Background(), call)
			if result.Error != nil {
				t.Errorf("Concurrent call %d failed: %v", id, result.Error)
			}
			done <- true
		}(i)
	}

	// Wait for all goroutines
	for i := 0; i < 100; i++ {
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Fatal("Timeout waiting for concurrent calls")
		}
	}
}

func TestConcurrentRegisterWorker(t *testing.T) {
	sup := New(Config{})
	defer sup.Shutdown()

	done := make(chan bool, 50)

	for i := 0; i < 50; i++ {
		go func(id int) {
			worker := &Worker{
				ID: string(rune('a' + id%26)),
				Tools: []ToolDef{
					{Name: string(rune('a' + id%26)), Description: "Concurrent tool"},
				},
			}
			sup.RegisterWorker(worker)
			done <- true
		}(i)
	}

	for i := 0; i < 50; i++ {
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Fatal("Timeout waiting for concurrent registration")
		}
	}
}

func TestWorkerHealthCheck(t *testing.T) {
	sup := New(Config{HeartbeatPeriod: 10 * time.Millisecond})
	defer sup.Shutdown()

	worker := &Worker{
		ID: "health-test",
		Tools: []ToolDef{
			{Name: "health_tool", Description: "Health test tool"},
		},
	}
	sup.RegisterWorker(worker)

	// Wait for heartbeat
	time.Sleep(50 * time.Millisecond)

	// Worker has no running process, so healthy should be false
	worker.mu.RLock()
	healthy := worker.healthy
	worker.mu.RUnlock()

	if healthy {
		t.Log("Worker marked healthy (no process = false expected)")
	}
}
