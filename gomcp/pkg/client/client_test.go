package client

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.Name == "" {
		t.Error("expected default name")
	}

	if cfg.ConnectTimeout == 0 {
		t.Error("expected default connect timeout")
	}

	if cfg.RequestTimeout == 0 {
		t.Error("expected default request timeout")
	}
}

func TestBaseClient_IsConnected(t *testing.T) {
	bc := NewBaseClient(DefaultConfig())

	if bc.IsConnected() {
		t.Error("expected not connected initially")
	}

	bc.setConnected(true, &ServerInfo{Name: "test"}, &ServerCapabilities{})

	if !bc.IsConnected() {
		t.Error("expected connected after setConnected")
	}

	if bc.ServerInfo() == nil || bc.ServerInfo().Name != "test" {
		t.Error("expected server info to be set")
	}
}

func TestBaseClient_NotificationHandlers(t *testing.T) {
	bc := NewBaseClient(DefaultConfig())

	received := make(chan string, 1)

	bc.OnNotification(func(method string, params json.RawMessage) {
		received <- method
	})

	bc.notifyHandlers("test/notification", nil)

	select {
	case method := <-received:
		if method != "test/notification" {
			t.Errorf("expected test/notification, got %s", method)
		}
	case <-time.After(time.Second):
		t.Error("timeout waiting for notification")
	}
}

func TestHTTPClient_New(t *testing.T) {
	client := NewHTTPClient(HTTPConfig{
		BaseURL:   "http://localhost:8080",
		AuthToken: "test-token",
		TenantID:  "tenant-1",
	})

	if client == nil {
		t.Fatal("expected client to be created")
	}

	if client.baseURL != "http://localhost:8080" {
		t.Errorf("unexpected baseURL: %s", client.baseURL)
	}
}

func TestStdioClient_New(t *testing.T) {
	client := NewStdioClient(StdioConfig{})

	if client == nil {
		t.Fatal("expected client to be created")
	}

	if client.IsConnected() {
		t.Error("should not be connected initially")
	}
}

func TestGRPCClient_New(t *testing.T) {
	client := NewGRPCClient(GRPCConfig{
		Address:   "localhost:50051",
		AuthToken: "test-token",
	})

	if client == nil {
		t.Fatal("expected client to be created")
	}
}

func TestClient_Errors(t *testing.T) {
	tests := []struct {
		name string
		err  error
	}{
		{"NotConnected", ErrNotConnected},
		{"AlreadyConnected", ErrAlreadyConnected},
		{"ConnectionFailed", ErrConnectionFailed},
		{"Timeout", ErrTimeout},
		{"ToolNotFound", ErrToolNotFound},
		{"ResourceNotFound", ErrResourceNotFound},
		{"PromptNotFound", ErrPromptNotFound},
		{"InvalidResponse", ErrInvalidResponse},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if tc.err == nil {
				t.Error("expected error to be defined")
			}
			if tc.err.Error() == "" {
				t.Error("expected error message")
			}
		})
	}
}

func TestHTTPClient_NotConnectedErrors(t *testing.T) {
	client := NewHTTPClient(HTTPConfig{BaseURL: "http://localhost:8080"})
	ctx := context.Background()

	_, err := client.ListTools(ctx)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.CallTool(ctx, "test", nil)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.ListResources(ctx)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.ReadResource(ctx, "test://uri")
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.ListPrompts(ctx)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.GetPrompt(ctx, "test", nil)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.CreateSample(ctx, &SamplingRequest{})
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}
}

func TestStdioClient_NotConnectedErrors(t *testing.T) {
	client := NewStdioClient(StdioConfig{})
	ctx := context.Background()

	_, err := client.ListTools(ctx)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}

	_, err = client.CallTool(ctx, "test", nil)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}
}

func TestGRPCClient_NotConnectedErrors(t *testing.T) {
	client := NewGRPCClient(GRPCConfig{Address: "localhost:50051"})
	ctx := context.Background()

	_, err := client.ListTools(ctx)
	if err != ErrNotConnected {
		t.Errorf("expected ErrNotConnected, got %v", err)
	}
}

func TestTypes_Serialization(t *testing.T) {
	// Test Tool serialization
	tool := Tool{
		Name:        "test_tool",
		Description: "A test tool",
		InputSchema: map[string]any{
			"type": "object",
			"properties": map[string]any{
				"input": map[string]any{"type": "string"},
			},
		},
	}

	data, err := json.Marshal(tool)
	if err != nil {
		t.Fatalf("failed to marshal tool: %v", err)
	}

	var decoded Tool
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal tool: %v", err)
	}

	if decoded.Name != tool.Name {
		t.Error("tool name mismatch")
	}

	// Test SamplingRequest serialization
	req := SamplingRequest{
		Messages: []SamplingMessage{
			{
				Role:    "user",
				Content: ContentItem{Type: "text", Text: "Hello"},
			},
		},
		MaxTokens: 100,
		ModelPreferences: &ModelPreferences{
			CostPriority:  0.5,
			SpeedPriority: 0.3,
		},
	}

	data, err = json.Marshal(req)
	if err != nil {
		t.Fatalf("failed to marshal sampling request: %v", err)
	}

	var decodedReq SamplingRequest
	if err := json.Unmarshal(data, &decodedReq); err != nil {
		t.Fatalf("failed to unmarshal sampling request: %v", err)
	}

	if decodedReq.MaxTokens != req.MaxTokens {
		t.Error("max tokens mismatch")
	}
}

func TestHTTPClient_SetAuth(t *testing.T) {
	client := NewHTTPClient(HTTPConfig{BaseURL: "http://localhost:8080"})

	client.SetAuthToken("new-token")
	if client.authToken != "new-token" {
		t.Error("auth token not set")
	}

	client.SetTenantID("new-tenant")
	if client.tenantID != "new-tenant" {
		t.Error("tenant ID not set")
	}
}

func TestGRPCClient_SetAuth(t *testing.T) {
	client := NewGRPCClient(GRPCConfig{Address: "localhost:50051"})

	client.SetAuthToken("new-token")
	if client.authToken != "new-token" {
		t.Error("auth token not set")
	}

	client.SetTenantID("new-tenant")
	if client.tenantID != "new-tenant" {
		t.Error("tenant ID not set")
	}
}

// Integration test placeholders (would need running server)

func TestHTTPClient_Integration(t *testing.T) {
	t.Skip("requires running HTTP server")

	client := NewHTTPClient(HTTPConfig{
		BaseURL: "http://localhost:8080",
	})

	ctx := context.Background()
	if err := client.Connect(ctx); err != nil {
		t.Fatalf("failed to connect: %v", err)
	}
	defer client.Close()

	tools, err := client.ListTools(ctx)
	if err != nil {
		t.Fatalf("failed to list tools: %v", err)
	}

	t.Logf("Found %d tools", len(tools))
}

func TestStdioClient_Integration(t *testing.T) {
	t.Skip("requires MCP server binary")

	client := NewStdioClient(StdioConfig{
		ClientConfig: DefaultConfig(),
	})

	ctx := context.Background()
	if err := client.Connect(ctx); err != nil {
		t.Fatalf("failed to connect: %v", err)
	}
	defer client.Close()
}
