package sampling

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
)

func TestTextContent(t *testing.T) {
	content := TextContent("hello")

	if content.Type != "text" {
		t.Errorf("expected text type, got %s", content.Type)
	}

	if content.Text != "hello" {
		t.Errorf("expected hello, got %s", content.Text)
	}
}

func TestImageContent(t *testing.T) {
	content := ImageContent("base64data", "image/png")

	if content.Type != "image" {
		t.Errorf("expected image type, got %s", content.Type)
	}

	if content.Data != "base64data" {
		t.Errorf("expected base64data, got %s", content.Data)
	}

	if content.MimeType != "image/png" {
		t.Errorf("expected image/png, got %s", content.MimeType)
	}
}

func TestRequest_Validate(t *testing.T) {
	tests := []struct {
		name    string
		req     *Request
		wantErr error
	}{
		{
			name: "valid request",
			req: &Request{
				Messages:  []Message{{Role: RoleUser, Content: TextContent("hello")}},
				MaxTokens: 100,
			},
			wantErr: nil,
		},
		{
			name: "no messages",
			req: &Request{
				Messages:  []Message{},
				MaxTokens: 100,
			},
			wantErr: ErrNoMessages,
		},
		{
			name: "invalid max tokens",
			req: &Request{
				Messages:  []Message{{Role: RoleUser, Content: TextContent("hello")}},
				MaxTokens: 0,
			},
			wantErr: ErrInvalidMaxTokens,
		},
		{
			name: "invalid role",
			req: &Request{
				Messages:  []Message{{Role: "invalid", Content: TextContent("hello")}},
				MaxTokens: 100,
			},
			wantErr: errors.New("invalid role"),
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.req.Validate()

			if tc.wantErr == nil {
				if err != nil {
					t.Errorf("expected no error, got %v", err)
				}
			} else {
				if err == nil {
					t.Error("expected error, got nil")
				}
			}
		})
	}
}

func TestManager_CreateMessage(t *testing.T) {
	handler := MockHandler("Hello, world!", "gpt-4")
	manager := NewManager(handler)

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	resp, err := manager.CreateMessage(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Content.Text != "Hello, world!" {
		t.Errorf("expected 'Hello, world!', got %s", resp.Content.Text)
	}

	if resp.Model != "gpt-4" {
		t.Errorf("expected gpt-4, got %s", resp.Model)
	}

	if resp.StopReason != StopReasonEndTurn {
		t.Errorf("expected endTurn, got %s", resp.StopReason)
	}
}

func TestManager_NoHandler(t *testing.T) {
	manager := NewManager(nil)

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	_, err := manager.CreateMessage(context.Background(), req)
	if err != ErrNoHandler {
		t.Errorf("expected ErrNoHandler, got %v", err)
	}
}

func TestManager_SetHandler(t *testing.T) {
	manager := NewManager(nil)

	handler := MockHandler("test", "model")
	manager.SetHandler(handler)

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	resp, err := manager.CreateMessage(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Content.Text != "test" {
		t.Errorf("expected 'test', got %s", resp.Content.Text)
	}
}

func TestManager_Middleware(t *testing.T) {
	callOrder := []string{}

	handler := HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
		callOrder = append(callOrder, "handler")
		return &Response{
			Role:    RoleAssistant,
			Content: TextContent("response"),
		}, nil
	})

	middleware1 := func(next Handler) Handler {
		return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
			callOrder = append(callOrder, "mw1-before")
			resp, err := next.CreateMessage(ctx, req)
			callOrder = append(callOrder, "mw1-after")
			return resp, err
		})
	}

	middleware2 := func(next Handler) Handler {
		return HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
			callOrder = append(callOrder, "mw2-before")
			resp, err := next.CreateMessage(ctx, req)
			callOrder = append(callOrder, "mw2-after")
			return resp, err
		})
	}

	manager := NewManager(handler)
	manager.Use(middleware1)
	manager.Use(middleware2)

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	_, err := manager.CreateMessage(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Middleware applied in reverse order
	expected := []string{"mw1-before", "mw2-before", "handler", "mw2-after", "mw1-after"}
	if len(callOrder) != len(expected) {
		t.Errorf("expected %d calls, got %d", len(expected), len(callOrder))
	}

	for i, exp := range expected {
		if i < len(callOrder) && callOrder[i] != exp {
			t.Errorf("call %d: expected %s, got %s", i, exp, callOrder[i])
		}
	}
}

func TestLoggingMiddleware(t *testing.T) {
	var logs []string
	logger := func(format string, args ...any) {
		logs = append(logs, "logged")
	}

	handler := MockHandler("response", "model")
	manager := NewManager(handler)
	manager.Use(LoggingMiddleware(logger))

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	_, err := manager.CreateMessage(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(logs) != 2 { // request + response
		t.Errorf("expected 2 log entries, got %d", len(logs))
	}
}

func TestRateLimitMiddleware(t *testing.T) {
	handler := MockHandler("response", "model")
	manager := NewManager(handler)
	manager.Use(RateLimitMiddleware(2)) // 2 requests per minute

	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	}

	// First two should succeed
	for i := 0; i < 2; i++ {
		_, err := manager.CreateMessage(context.Background(), req)
		if err != nil {
			t.Fatalf("request %d: unexpected error: %v", i, err)
		}
	}

	// Third should fail
	_, err := manager.CreateMessage(context.Background(), req)
	if err != ErrRateLimited {
		t.Errorf("expected ErrRateLimited, got %v", err)
	}
}

func TestRequest_JSON(t *testing.T) {
	req := &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hello")}},
		MaxTokens: 100,
		ModelPreferences: &ModelPreferences{
			CostPriority:  0.5,
			SpeedPriority: 0.3,
		},
	}

	data, err := req.ToJSON()
	if err != nil {
		t.Fatalf("failed to marshal: %v", err)
	}

	var decoded Request
	if err := decoded.FromJSON(data); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if len(decoded.Messages) != 1 {
		t.Error("expected 1 message")
	}

	if decoded.MaxTokens != 100 {
		t.Errorf("expected maxTokens 100, got %d", decoded.MaxTokens)
	}
}

func TestResponse_Serialization(t *testing.T) {
	resp := &Response{
		Role:       RoleAssistant,
		Content:    TextContent("Hello!"),
		Model:      "gpt-4",
		StopReason: StopReasonEndTurn,
	}

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("failed to marshal: %v", err)
	}

	var decoded Response
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if decoded.Role != RoleAssistant {
		t.Errorf("expected assistant role, got %s", decoded.Role)
	}

	if decoded.Model != "gpt-4" {
		t.Errorf("expected gpt-4, got %s", decoded.Model)
	}
}

func TestHandlerFunc(t *testing.T) {
	called := false

	hf := HandlerFunc(func(ctx context.Context, req *Request) (*Response, error) {
		called = true
		return &Response{}, nil
	})

	_, err := hf.CreateMessage(context.Background(), &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	})

	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	if !called {
		t.Error("handler not called")
	}
}

func TestMockHandler(t *testing.T) {
	handler := MockHandler("custom response", "custom-model")

	resp, err := handler.CreateMessage(context.Background(), &Request{
		Messages:  []Message{{Role: RoleUser, Content: TextContent("Hi")}},
		MaxTokens: 100,
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.Content.Text != "custom response" {
		t.Errorf("expected 'custom response', got %s", resp.Content.Text)
	}

	if resp.Model != "custom-model" {
		t.Errorf("expected custom-model, got %s", resp.Model)
	}
}

func TestErrors(t *testing.T) {
	if ErrNoHandler == nil {
		t.Error("ErrNoHandler should be defined")
	}

	if ErrNoMessages == nil {
		t.Error("ErrNoMessages should be defined")
	}

	if ErrInvalidMaxTokens == nil {
		t.Error("ErrInvalidMaxTokens should be defined")
	}

	if ErrRateLimited == nil {
		t.Error("ErrRateLimited should be defined")
	}
}

func TestConstants(t *testing.T) {
	if MethodCreateMessage != "sampling/createMessage" {
		t.Error("invalid method name")
	}

	if StopReasonEndTurn != "endTurn" {
		t.Error("invalid stop reason")
	}

	if StopReasonStopSequence != "stopSequence" {
		t.Error("invalid stop reason")
	}

	if StopReasonMaxTokens != "maxTokens" {
		t.Error("invalid stop reason")
	}
}
