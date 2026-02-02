package batching

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"testing"
	"time"
)

// Mock executor for testing
func mockExecutor(results map[string]json.RawMessage, delay time.Duration) Executor {
	return ExecutorFunc(func(ctx context.Context, toolName string, args json.RawMessage) (json.RawMessage, error) {
		if delay > 0 {
			select {
			case <-time.After(delay):
			case <-ctx.Done():
				return nil, ctx.Err()
			}
		}

		if result, ok := results[toolName]; ok {
			return result, nil
		}
		return nil, errors.New("tool not found: " + toolName)
	})
}

func TestProcessor_Process_Sequential(t *testing.T) {
	executor := mockExecutor(map[string]json.RawMessage{
		"tool1": json.RawMessage(`{"result": 1}`),
		"tool2": json.RawMessage(`{"result": 2}`),
	}, 0)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "tool1", Arguments: json.RawMessage(`{}`)},
			{ID: "r2", ToolName: "tool2", Arguments: json.RawMessage(`{}`)},
		},
		Parallel: false,
	}

	resp := p.Process(context.Background(), batch)

	if len(resp.Responses) != 2 {
		t.Fatalf("expected 2 responses, got %d", len(resp.Responses))
	}
	if resp.SuccessCount != 2 {
		t.Errorf("expected 2 successes, got %d", resp.SuccessCount)
	}
	if resp.ErrorCount != 0 {
		t.Errorf("expected 0 errors, got %d", resp.ErrorCount)
	}
}

func TestProcessor_Process_Parallel(t *testing.T) {
	executor := mockExecutor(map[string]json.RawMessage{
		"tool1": json.RawMessage(`{"result": 1}`),
		"tool2": json.RawMessage(`{"result": 2}`),
		"tool3": json.RawMessage(`{"result": 3}`),
	}, 10*time.Millisecond)

	p := NewProcessor(executor, ProcessorConfig{MaxParallel: 3})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "tool1"},
			{ID: "r2", ToolName: "tool2"},
			{ID: "r3", ToolName: "tool3"},
		},
		Parallel: true,
	}

	start := time.Now()
	resp := p.Process(context.Background(), batch)
	duration := time.Since(start)

	// Parallel execution should be faster than sequential
	// 3 tasks * 10ms sequentially = 30ms
	// 3 tasks in parallel = ~10ms
	if duration > 25*time.Millisecond {
		t.Logf("parallel execution took %v (expected < 25ms)", duration)
	}

	if resp.SuccessCount != 3 {
		t.Errorf("expected 3 successes, got %d", resp.SuccessCount)
	}
}

func TestProcessor_Process_WithErrors(t *testing.T) {
	executor := mockExecutor(map[string]json.RawMessage{
		"tool1": json.RawMessage(`{"ok": true}`),
		// tool2 not in map, will return error
	}, 0)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "tool1"},
			{ID: "r2", ToolName: "tool2"},
		},
	}

	resp := p.Process(context.Background(), batch)

	if resp.SuccessCount != 1 {
		t.Errorf("expected 1 success, got %d", resp.SuccessCount)
	}
	if resp.ErrorCount != 1 {
		t.Errorf("expected 1 error, got %d", resp.ErrorCount)
	}
	if resp.Responses[1].Error == nil {
		t.Error("expected error for tool2")
	}
}

func TestProcessor_Process_Timeout(t *testing.T) {
	executor := mockExecutor(map[string]json.RawMessage{
		"slow": json.RawMessage(`{}`),
	}, 100*time.Millisecond)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "slow"},
		},
		Timeout: 10 * time.Millisecond,
	}

	resp := p.Process(context.Background(), batch)

	if resp.ErrorCount != 1 {
		t.Errorf("expected 1 error due to timeout, got %d", resp.ErrorCount)
	}
}

func TestProcessor_Process_MaxParallel(t *testing.T) {
	callCount := 0
	maxConcurrent := 0
	currentConcurrent := 0
	var mu sync.Mutex

	executor := ExecutorFunc(func(ctx context.Context, toolName string, args json.RawMessage) (json.RawMessage, error) {
		mu.Lock()
		callCount++
		currentConcurrent++
		if currentConcurrent > maxConcurrent {
			maxConcurrent = currentConcurrent
		}
		mu.Unlock()

		time.Sleep(20 * time.Millisecond)

		mu.Lock()
		currentConcurrent--
		mu.Unlock()

		return json.RawMessage(`{}`), nil
	})

	p := NewProcessor(executor, ProcessorConfig{MaxParallel: 2})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "t"},
			{ID: "r2", ToolName: "t"},
			{ID: "r3", ToolName: "t"},
			{ID: "r4", ToolName: "t"},
		},
		Parallel:    true,
		MaxParallel: 2,
	}

	p.Process(context.Background(), batch)

	if maxConcurrent > 2 {
		t.Errorf("max concurrent exceeded limit: %d > 2", maxConcurrent)
	}
	if callCount != 4 {
		t.Errorf("expected 4 calls, got %d", callCount)
	}
}

func TestBuilder_Add(t *testing.T) {
	b := NewBuilder().
		Add("r1", "tool1", json.RawMessage(`{"a": 1}`)).
		Add("r2", "tool2", json.RawMessage(`{"b": 2}`))

	if b.Size() != 2 {
		t.Errorf("expected size 2, got %d", b.Size())
	}

	batch := b.Build()
	if len(batch.Requests) != 2 {
		t.Errorf("expected 2 requests, got %d", len(batch.Requests))
	}
}

func TestBuilder_AddJSON(t *testing.T) {
	type Args struct {
		Value int `json:"value"`
	}

	b := NewBuilder().
		AddJSON("r1", "tool1", Args{Value: 42})

	batch := b.Build()
	if string(batch.Requests[0].Arguments) != `{"value":42}` {
		t.Errorf("unexpected arguments: %s", batch.Requests[0].Arguments)
	}
}

func TestBuilder_Parallel(t *testing.T) {
	batch := NewBuilder().
		Add("r1", "t", nil).
		Parallel(5).
		Build()

	if !batch.Parallel {
		t.Error("expected parallel to be true")
	}
	if batch.MaxParallel != 5 {
		t.Errorf("expected max parallel 5, got %d", batch.MaxParallel)
	}
}

func TestBuilder_Sequential(t *testing.T) {
	batch := NewBuilder().
		Add("r1", "t", nil).
		Parallel(5).
		Sequential().
		Build()

	if batch.Parallel {
		t.Error("expected parallel to be false after Sequential()")
	}
}

func TestBuilder_Timeout(t *testing.T) {
	batch := NewBuilder().
		Timeout(5 * time.Second).
		Build()

	if batch.Timeout != 5*time.Second {
		t.Errorf("expected 5s timeout, got %v", batch.Timeout)
	}
}

func TestBuilder_Clear(t *testing.T) {
	b := NewBuilder().
		Add("r1", "t1", nil).
		Add("r2", "t2", nil).
		Clear()

	if b.Size() != 0 {
		t.Errorf("expected size 0 after clear, got %d", b.Size())
	}
}

func TestProcessor_DefaultConfig(t *testing.T) {
	executor := mockExecutor(nil, 0)
	p := NewProcessor(executor, ProcessorConfig{})

	if p.defaultTimeout != 30*time.Second {
		t.Errorf("expected default timeout 30s, got %v", p.defaultTimeout)
	}
	if p.maxParallel != 10 {
		t.Errorf("expected default max parallel 10, got %d", p.maxParallel)
	}
}

func TestProcessor_ResponseOrder(t *testing.T) {
	executor := mockExecutor(map[string]json.RawMessage{
		"t1": json.RawMessage(`{"id": 1}`),
		"t2": json.RawMessage(`{"id": 2}`),
		"t3": json.RawMessage(`{"id": 3}`),
	}, 0)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "first", ToolName: "t1"},
			{ID: "second", ToolName: "t2"},
			{ID: "third", ToolName: "t3"},
		},
		Parallel: true,
	}

	resp := p.Process(context.Background(), batch)

	// Verify responses maintain order
	if resp.Responses[0].ID != "first" {
		t.Error("first response out of order")
	}
	if resp.Responses[1].ID != "second" {
		t.Error("second response out of order")
	}
	if resp.Responses[2].ID != "third" {
		t.Error("third response out of order")
	}
}

// Benchmark
func BenchmarkProcessor_Sequential(b *testing.B) {
	executor := mockExecutor(map[string]json.RawMessage{
		"t": json.RawMessage(`{}`),
	}, 0)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "t"},
			{ID: "r2", ToolName: "t"},
			{ID: "r3", ToolName: "t"},
		},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		p.Process(context.Background(), batch)
	}
}

func BenchmarkProcessor_Parallel(b *testing.B) {
	executor := mockExecutor(map[string]json.RawMessage{
		"t": json.RawMessage(`{}`),
	}, 0)

	p := NewProcessor(executor, ProcessorConfig{})

	batch := BatchRequest{
		Requests: []Request{
			{ID: "r1", ToolName: "t"},
			{ID: "r2", ToolName: "t"},
			{ID: "r3", ToolName: "t"},
		},
		Parallel: true,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		p.Process(context.Background(), batch)
	}
}
