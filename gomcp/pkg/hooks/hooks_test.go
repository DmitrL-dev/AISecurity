package hooks

import (
	"context"
	"errors"
	"testing"
)

func TestRegistry_Register(t *testing.T) {
	r := NewRegistry()

	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		return nil
	}))

	if r.Count() != 1 {
		t.Errorf("expected 1 hook, got %d", r.Count())
	}
}

func TestRegistry_Has(t *testing.T) {
	r := NewRegistry()

	r.Register("tools/call", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		return nil
	}))

	if !r.Has("tools/call", PhaseBefore) {
		t.Error("should have before hook")
	}

	if r.Has("tools/call", PhaseAfter) {
		t.Error("should not have after hook")
	}
}

func TestRegistry_Execute(t *testing.T) {
	r := NewRegistry()

	called := false
	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		called = true
		return nil
	}))

	err := r.Execute(context.Background(), "test", PhaseBefore, &Event{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !called {
		t.Error("handler should be called")
	}
}

func TestRegistry_Execute_NoHooks(t *testing.T) {
	r := NewRegistry()

	err := r.Execute(context.Background(), "nomethod", PhaseBefore, &Event{})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestRegistry_Execute_Error(t *testing.T) {
	r := NewRegistry()

	testErr := errors.New("test error")
	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		return testErr
	}))

	err := r.Execute(context.Background(), "test", PhaseBefore, &Event{})
	if err != testErr {
		t.Errorf("expected test error, got %v", err)
	}
}

func TestRegistry_ExecuteBefore(t *testing.T) {
	r := NewRegistry()

	var capturedParams any
	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		capturedParams = e.Params
		return nil
	}))

	params := map[string]string{"key": "value"}
	err := r.ExecuteBefore(context.Background(), "test", params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if capturedParams == nil {
		t.Error("params should be captured")
	}
}

func TestRegistry_ExecuteAfter(t *testing.T) {
	r := NewRegistry()

	var capturedResult any
	r.Register("test", PhaseAfter, HandlerFunc(func(ctx context.Context, e *Event) error {
		capturedResult = e.Result
		return nil
	}))

	result := "success"
	err := r.ExecuteAfter(context.Background(), "test", result)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if capturedResult != result {
		t.Error("result should be captured")
	}
}

func TestRegistry_ExecuteError(t *testing.T) {
	r := NewRegistry()

	var capturedErr error
	r.Register("test", PhaseError, HandlerFunc(func(ctx context.Context, e *Event) error {
		capturedErr = e.Error
		return nil
	}))

	origErr := errors.New("original error")
	err := r.ExecuteError(context.Background(), "test", origErr)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if capturedErr != origErr {
		t.Error("error should be captured")
	}
}

func TestRegistry_Clear(t *testing.T) {
	r := NewRegistry()

	r.Register("a", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error { return nil }))
	r.Register("b", PhaseAfter, HandlerFunc(func(ctx context.Context, e *Event) error { return nil }))

	r.Clear()

	if r.Count() != 0 {
		t.Errorf("expected 0 hooks after clear, got %d", r.Count())
	}
}

func TestRegistry_MultipleHooks(t *testing.T) {
	r := NewRegistry()

	callOrder := make([]int, 0)

	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		callOrder = append(callOrder, 1)
		return nil
	}))

	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		callOrder = append(callOrder, 2)
		return nil
	}))

	r.Execute(context.Background(), "test", PhaseBefore, &Event{})

	if len(callOrder) != 2 {
		t.Errorf("expected 2 calls, got %d", len(callOrder))
	}

	if callOrder[0] != 1 || callOrder[1] != 2 {
		t.Error("hooks should be called in order")
	}
}

func TestHandlerFunc(t *testing.T) {
	called := false
	hf := HandlerFunc(func(ctx context.Context, e *Event) error {
		called = true
		return nil
	})

	err := hf.Handle(context.Background(), &Event{})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	if !called {
		t.Error("handler not called")
	}
}

func TestEvent_ToJSON(t *testing.T) {
	e := &Event{
		Phase:  PhaseBefore,
		Method: "test",
		Params: map[string]string{"key": "value"},
	}

	data, err := e.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestConstants(t *testing.T) {
	if PhaseBefore != "before" {
		t.Error("invalid phase")
	}

	if PhaseAfter != "after" {
		t.Error("invalid phase")
	}

	if PhaseError != "error" {
		t.Error("invalid phase")
	}

	if MethodToolsCall != "tools/call" {
		t.Error("invalid method")
	}
}

func TestBeforeToolCall_Fields(t *testing.T) {
	btc := &BeforeToolCall{
		ToolName:  "myTool",
		Arguments: map[string]any{"arg": "val"},
	}

	if btc.ToolName != "myTool" {
		t.Error("toolName mismatch")
	}
}

func TestAfterToolCall_Fields(t *testing.T) {
	atc := &AfterToolCall{
		ToolName: "myTool",
		Result:   "success",
		Duration: 1000,
	}

	if atc.Duration != 1000 {
		t.Error("duration mismatch")
	}
}

func TestMiddleware(t *testing.T) {
	r := NewRegistry()

	beforeCalled := false
	afterCalled := false

	r.Register("test", PhaseBefore, HandlerFunc(func(ctx context.Context, e *Event) error {
		beforeCalled = true
		return nil
	}))

	r.Register("test", PhaseAfter, HandlerFunc(func(ctx context.Context, e *Event) error {
		afterCalled = true
		return nil
	}))

	inner := HandlerFunc(func(ctx context.Context, e *Event) error {
		return nil
	})

	wrapped := Middleware(r)(inner)

	err := wrapped.Handle(context.Background(), &Event{Method: "test"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !beforeCalled {
		t.Error("before hook should be called")
	}

	if !afterCalled {
		t.Error("after hook should be called")
	}
}
