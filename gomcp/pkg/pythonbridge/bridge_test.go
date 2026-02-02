package pythonbridge

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

func TestNew(t *testing.T) {
	cfg := Config{
		PythonPath:  "python",
		WorkerPath:  "worker.py",
		ProjectRoot: "/tmp",
	}

	b := New(cfg)

	if b.pythonPath != "python" {
		t.Error("pythonPath mismatch")
	}

	if b.workerPath != "worker.py" {
		t.Error("workerPath mismatch")
	}
}

func TestNew_DefaultPython(t *testing.T) {
	cfg := Config{
		WorkerPath: "worker.py",
	}

	b := New(cfg)

	if b.pythonPath != "python" {
		t.Error("should default to python")
	}
}

func TestBridge_NotStarted(t *testing.T) {
	b := New(Config{})

	_, err := b.Call(context.Background(), "test", nil)
	if err != ErrNotStarted {
		t.Errorf("expected ErrNotStarted, got %v", err)
	}
}

func TestBridge_IsRunning(t *testing.T) {
	b := New(Config{})

	if b.IsRunning() {
		t.Error("should not be running initially")
	}
}

func TestBridge_LastError(t *testing.T) {
	b := New(Config{})

	if b.LastError() != nil {
		t.Error("should have no error initially")
	}
}

func TestBridge_Stop_NotStarted(t *testing.T) {
	b := New(Config{})

	err := b.Stop()
	if err != nil {
		t.Errorf("stop should not error when not started: %v", err)
	}
}

func TestErrors(t *testing.T) {
	if ErrNotStarted.Error() == "" {
		t.Error("error should have message")
	}

	if ErrTimeout.Error() == "" {
		t.Error("error should have message")
	}
}

// Integration test - only runs if Python is available
func TestBridge_Integration(t *testing.T) {
	// Check if python is available
	if _, err := exec.LookPath("python"); err != nil {
		t.Skip("python not available")
	}

	// Create temp worker script
	tmpDir := t.TempDir()
	workerPath := filepath.Join(tmpDir, "worker.py")

	workerCode := `
import json
import sys

while True:
    try:
        line = input()
        req = json.loads(line)
        
        # Echo tool for testing
        if req['tool'] == 'echo':
            result = {'id': req['id'], 'success': True, 'result': {'echo': req['params'].get('msg', '')}}
        elif req['tool'] == 'add':
            a = req['params'].get('a', 0)
            b = req['params'].get('b', 0)
            result = {'id': req['id'], 'success': True, 'result': {'sum': a + b}}
        else:
            result = {'id': req['id'], 'success': False, 'error': 'Unknown tool'}
        
        print(json.dumps(result), flush=True)
    except EOFError:
        break
    except Exception as e:
        print(json.dumps({'id': 0, 'success': False, 'error': str(e)}), flush=True)
`

	if err := os.WriteFile(workerPath, []byte(workerCode), 0644); err != nil {
		t.Fatalf("failed to write worker: %v", err)
	}

	b := New(Config{
		PythonPath:  "python",
		WorkerPath:  workerPath,
		ProjectRoot: tmpDir,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Start bridge
	if err := b.Start(ctx); err != nil {
		t.Fatalf("failed to start: %v", err)
	}
	defer b.Stop()

	if !b.IsRunning() {
		t.Error("should be running after start")
	}

	// Test echo
	resp, err := b.Call(ctx, "echo", map[string]any{"msg": "hello"})
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}

	if !resp.Success {
		t.Errorf("call not successful: %s", resp.Error)
	}

	if resp.Result["echo"] != "hello" {
		t.Errorf("expected 'hello', got %v", resp.Result["echo"])
	}

	// Test add
	resp2, err := b.Call(ctx, "add", map[string]any{"a": 5, "b": 3})
	if err != nil {
		t.Fatalf("add call failed: %v", err)
	}

	if resp2.Result["sum"] != float64(8) {
		t.Errorf("expected 8, got %v", resp2.Result["sum"])
	}

	// Test unknown tool
	resp3, err := b.Call(ctx, "unknown", nil)
	if err != nil {
		t.Fatalf("unknown call failed: %v", err)
	}

	if resp3.Success {
		t.Error("unknown tool should not be successful")
	}
}

func TestBridge_ConcurrentCalls(t *testing.T) {
	if _, err := exec.LookPath("python"); err != nil {
		t.Skip("python not available")
	}

	tmpDir := t.TempDir()
	workerPath := filepath.Join(tmpDir, "worker.py")

	workerCode := `
import json
import time

while True:
    try:
        line = input()
        req = json.loads(line)
        time.sleep(0.01)  # Simulate work
        result = {'id': req['id'], 'success': True, 'result': {'id': req['id']}}
        print(json.dumps(result), flush=True)
    except EOFError:
        break
`

	if err := os.WriteFile(workerPath, []byte(workerCode), 0644); err != nil {
		t.Fatalf("failed to write worker: %v", err)
	}

	b := New(Config{
		PythonPath:  "python",
		WorkerPath:  workerPath,
		ProjectRoot: tmpDir,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := b.Start(ctx); err != nil {
		t.Fatalf("failed to start: %v", err)
	}
	defer b.Stop()

	// Launch 10 concurrent calls
	const numCalls = 10
	results := make(chan error, numCalls)

	for i := 0; i < numCalls; i++ {
		go func(id int) {
			_, err := b.Call(ctx, "test", map[string]any{"id": id})
			results <- err
		}(i)
	}

	// Collect results
	for i := 0; i < numCalls; i++ {
		if err := <-results; err != nil {
			t.Errorf("concurrent call %d failed: %v", i, err)
		}
	}
}
