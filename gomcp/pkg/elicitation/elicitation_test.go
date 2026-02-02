package elicitation

import (
	"context"
	"testing"
)

func TestRequest_Validate(t *testing.T) {
	tests := []struct {
		name    string
		req     *Request
		wantErr error
	}{
		{
			name: "valid request",
			req: &Request{
				RequestID: "req-1",
				Message:   "Enter your name",
			},
			wantErr: nil,
		},
		{
			name: "empty request ID",
			req: &Request{
				RequestID: "",
				Message:   "Enter name",
			},
			wantErr: ErrEmptyRequestID,
		},
		{
			name: "empty message",
			req: &Request{
				RequestID: "req-1",
				Message:   "",
			},
			wantErr: ErrEmptyMessage,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.req.Validate()
			if tc.wantErr == nil && err != nil {
				t.Errorf("expected no error, got %v", err)
			}
			if tc.wantErr != nil && err != tc.wantErr {
				t.Errorf("expected %v, got %v", tc.wantErr, err)
			}
		})
	}
}

func TestResponse_Validate(t *testing.T) {
	schema := &Schema{
		Type:     "object",
		Required: []string{"name"},
	}

	tests := []struct {
		name    string
		resp    *Response
		schema  *Schema
		wantErr bool
	}{
		{
			name: "valid submit",
			resp: &Response{
				RequestID: "req-1",
				Action:    ActionSubmit,
				Content:   map[string]any{"name": "John"},
			},
			schema:  schema,
			wantErr: false,
		},
		{
			name: "cancel action",
			resp: &Response{
				RequestID: "req-1",
				Action:    ActionCancel,
			},
			schema:  schema,
			wantErr: false,
		},
		{
			name: "missing required",
			resp: &Response{
				RequestID: "req-1",
				Action:    ActionSubmit,
				Content:   map[string]any{"age": 25},
			},
			schema:  schema,
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.resp.Validate(tc.schema)
			if tc.wantErr && err == nil {
				t.Error("expected error, got nil")
			}
			if !tc.wantErr && err != nil {
				t.Errorf("expected no error, got %v", err)
			}
		})
	}
}

func TestManager_RequestInput(t *testing.T) {
	handler := MockHandler(ActionSubmit, map[string]any{"value": "test"})
	manager := NewManager(handler)

	req := &Request{
		RequestID: "req-1",
		Message:   "Enter value",
	}

	resp, err := manager.RequestInput(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Action != ActionSubmit {
		t.Errorf("expected submit, got %s", resp.Action)
	}

	if resp.Content["value"] != "test" {
		t.Error("unexpected content")
	}
}

func TestManager_NoHandler(t *testing.T) {
	manager := NewManager(nil)

	_, err := manager.RequestInput(context.Background(), &Request{
		RequestID: "req-1",
		Message:   "Enter value",
	})

	if err != ErrNoHandler {
		t.Errorf("expected ErrNoHandler, got %v", err)
	}
}

func TestManager_SetHandler(t *testing.T) {
	manager := NewManager(nil)

	handler := MockHandler(ActionSubmit, nil)
	manager.SetHandler(handler)

	resp, err := manager.RequestInput(context.Background(), &Request{
		RequestID: "req-1",
		Message:   "Enter value",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Action != ActionSubmit {
		t.Errorf("expected submit, got %s", resp.Action)
	}
}

func TestManager_PendingRequests(t *testing.T) {
	manager := NewManager(nil)

	// Register pending
	ch := manager.RegisterPending("req-1")

	if manager.PendingCount() != 1 {
		t.Errorf("expected 1 pending, got %d", manager.PendingCount())
	}

	// Resolve pending
	go func() {
		manager.ResolvePending(&Response{
			RequestID: "req-1",
			Action:    ActionSubmit,
			Content:   map[string]any{"value": "test"},
		})
	}()

	resp := <-ch
	if resp.Action != ActionSubmit {
		t.Errorf("expected submit, got %s", resp.Action)
	}

	if manager.PendingCount() != 0 {
		t.Errorf("expected 0 pending, got %d", manager.PendingCount())
	}
}

func TestManager_CancelPending(t *testing.T) {
	manager := NewManager(nil)

	ch := manager.RegisterPending("req-1")

	go func() {
		manager.CancelPending("req-1")
	}()

	resp := <-ch
	if resp.Action != ActionCancel {
		t.Errorf("expected cancel, got %s", resp.Action)
	}
}

func TestManager_ResolvePending_NotFound(t *testing.T) {
	manager := NewManager(nil)

	err := manager.ResolvePending(&Response{RequestID: "unknown"})
	if err != ErrRequestNotFound {
		t.Errorf("expected ErrRequestNotFound, got %v", err)
	}
}

func TestTextInput(t *testing.T) {
	schema := TextInput("Name", "Enter your name")

	if schema.Type != "string" {
		t.Errorf("expected string, got %s", schema.Type)
	}

	if schema.Title != "Name" {
		t.Errorf("expected Name, got %s", schema.Title)
	}
}

func TestNumberInput(t *testing.T) {
	min := 0.0
	max := 100.0
	schema := NumberInput("Age", "Your age", &min, &max)

	if schema.Type != "number" {
		t.Errorf("expected number, got %s", schema.Type)
	}

	if *schema.Minimum != 0 {
		t.Error("unexpected minimum")
	}

	if *schema.Maximum != 100 {
		t.Error("unexpected maximum")
	}
}

func TestSelectInput(t *testing.T) {
	schema := SelectInput("Color", "Choose color", []string{"red", "green", "blue"})

	if schema.Type != "string" {
		t.Errorf("expected string, got %s", schema.Type)
	}

	if len(schema.Enum) != 3 {
		t.Errorf("expected 3 options, got %d", len(schema.Enum))
	}
}

func TestBooleanInput(t *testing.T) {
	schema := BooleanInput("Agree", "Do you agree?", true)

	if schema.Type != "boolean" {
		t.Errorf("expected boolean, got %s", schema.Type)
	}

	if schema.Default != true {
		t.Error("expected default true")
	}
}

func TestObjectInput(t *testing.T) {
	properties := map[string]Property{
		"name": {Type: "string"},
		"age":  {Type: "number"},
	}

	schema := ObjectInput("User", "User info", properties, []string{"name"})

	if schema.Type != "object" {
		t.Errorf("expected object, got %s", schema.Type)
	}

	if len(schema.Properties) != 2 {
		t.Error("expected 2 properties")
	}

	if len(schema.Required) != 1 {
		t.Error("expected 1 required")
	}
}

func TestHandlerFunc(t *testing.T) {
	called := false

	hf := HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
		called = true
		return &Response{Action: ActionSubmit}, nil
	})

	_, err := hf.RequestInput(context.Background(), &Request{
		RequestID: "req-1",
		Message:   "Test",
	})

	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	if !called {
		t.Error("handler not called")
	}
}

func TestMockHandler(t *testing.T) {
	handler := MockHandler(ActionSubmit, map[string]any{"key": "value"})

	resp, err := handler.RequestInput(context.Background(), &Request{
		RequestID: "req-1",
		Message:   "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Action != ActionSubmit {
		t.Errorf("expected submit, got %s", resp.Action)
	}

	if resp.Content["key"] != "value" {
		t.Error("unexpected content")
	}
}

func TestErrors(t *testing.T) {
	if ErrNoHandler == nil {
		t.Error("ErrNoHandler should be defined")
	}

	if ErrRequestNotFound == nil {
		t.Error("ErrRequestNotFound should be defined")
	}

	if ErrEmptyRequestID == nil {
		t.Error("ErrEmptyRequestID should be defined")
	}

	if ErrEmptyMessage == nil {
		t.Error("ErrEmptyMessage should be defined")
	}
}

func TestConstants(t *testing.T) {
	if MethodElicit != "elicitation/create" {
		t.Error("invalid method name")
	}

	if ActionSubmit != "submit" {
		t.Error("invalid action")
	}

	if ActionCancel != "cancel" {
		t.Error("invalid action")
	}

	if ActionTimeout != "timeout" {
		t.Error("invalid action")
	}
}
