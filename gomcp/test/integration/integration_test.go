// Package integration provides end-to-end integration tests for GoMCP.
package integration

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sentinel-community/gomcp/pkg/batching"
	"github.com/sentinel-community/gomcp/pkg/health"
	"github.com/sentinel-community/gomcp/pkg/httpmode"
	"github.com/sentinel-community/gomcp/pkg/security"
	"github.com/sentinel-community/gomcp/pkg/supervisor"
	"github.com/sentinel-community/gomcp/pkg/tenant"
)

// MockToolHandler for integration tests
type MockToolHandler struct {
	tools   []httpmode.ToolInfo
	results map[string]json.RawMessage
}

func (m *MockToolHandler) Execute(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error) {
	if result, ok := m.results[tool]; ok {
		return result, nil
	}
	return json.RawMessage(`{"error": "not found"}`), nil
}

func (m *MockToolHandler) ListTools() []httpmode.ToolInfo {
	return m.tools
}

// Test: Supervisor + Security + Health together
func TestIntegration_SupervisorSecurityHealth(t *testing.T) {
	// Create supervisor
	sup := supervisor.New(supervisor.Config{
		DefaultTimeout:  30 * time.Second,
		MaxWorkers:      10,
		HeartbeatPeriod: 5 * time.Second,
	})

	// Create security validator
	validator := security.DefaultValidator()

	// Create health server
	healthSrv := health.NewServer("1.0.0")
	healthSrv.RegisterChecker(health.WorkerChecker(func() (int, int) {
		return 0, 0 // No workers yet
	}))

	// Verify all components work together
	if sup == nil || validator == nil || healthSrv == nil {
		t.Fatal("components should be initialized")
	}

	// Health check should work
	healthResp := healthSrv.GetHealth(context.Background())
	if healthResp.Status != health.StatusDegraded {
		t.Errorf("expected degraded status with no workers, got %s", healthResp.Status)
	}

	sup.Shutdown()
}

// Test: HTTPMode + Validator + TenantManager
func TestIntegration_HTTPModeWithSecurityAndTenant(t *testing.T) {
	// Setup tenant manager
	tm := tenant.NewManager()
	tenant1, _ := tm.CreateTenant("t1", "Tenant 1", tenant.DefaultQuotas())
	tenant1.SetAllowedTools([]string{"allowed_tool"})

	// Setup handler
	handler := &MockToolHandler{
		tools: []httpmode.ToolInfo{
			{Name: "allowed_tool", Description: "Allowed"},
			{Name: "blocked_tool", Description: "Blocked"},
		},
		results: map[string]json.RawMessage{
			"allowed_tool": json.RawMessage(`{"ok": true}`),
			"blocked_tool": json.RawMessage(`{"ok": true}`),
		},
	}

	// Create HTTP server with all integrations
	srv := httpmode.NewServer(httpmode.Config{
		Addr:          ":0",
		Handler:       handler,
		Validator:     security.DefaultValidator(),
		TenantManager: tm,
	})

	if srv == nil {
		t.Fatal("server should be created")
	}
}

// Test: Batching + Security validation pipeline
func TestIntegration_BatchingWithSecurity(t *testing.T) {
	validator := security.DefaultValidator()

	// Create executor with validation
	executor := batching.ExecutorFunc(func(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error) {
		// Validate input first
		result := validator.ValidateJSON(args)
		if !result.Valid {
			return nil, result.Errors[0]
		}
		return json.RawMessage(`{"ok": true}`), nil
	})

	proc := batching.NewProcessor(executor, batching.ProcessorConfig{
		DefaultTimeout: 10 * time.Second,
		MaxParallel:    5,
	})

	// Build batch with valid inputs
	batch := batching.NewBuilder().
		AddJSON("r1", "tool1", map[string]string{"key": "value"}).
		AddJSON("r2", "tool2", map[string]int{"count": 42}).
		Parallel(2).
		Build()

	result := proc.Process(context.Background(), batch)

	if result.SuccessCount != 2 {
		t.Errorf("expected 2 successes, got %d", result.SuccessCount)
	}
}

// Test: Tenant quota enforcement in batch processing
func TestIntegration_TenantQuotaInBatch(t *testing.T) {
	tm := tenant.NewManager()
	tenant1, _ := tm.CreateTenant("t1", "Tenant 1", tenant.Quotas{
		MaxToolCalls: 3,
	})

	executor := batching.ExecutorFunc(func(ctx context.Context, tool string, args json.RawMessage) (json.RawMessage, error) {
		// Check tenant quota
		if err := tenant1.CheckQuota("tool_call"); err != nil {
			return nil, err
		}
		tenant1.IncrementToolCalls()
		return json.RawMessage(`{"ok": true}`), nil
	})

	proc := batching.NewProcessor(executor, batching.ProcessorConfig{})

	batch := batching.NewBuilder().
		Add("r1", "t", nil).
		Add("r2", "t", nil).
		Add("r3", "t", nil).
		Add("r4", "t", nil). // This should fail quota
		Build()

	result := proc.Process(context.Background(), batch)

	if result.SuccessCount != 3 {
		t.Errorf("expected 3 successes before quota exceeded, got %d", result.SuccessCount)
	}
	if result.ErrorCount != 1 {
		t.Errorf("expected 1 error after quota exceeded, got %d", result.ErrorCount)
	}
}

// Test: Health endpoints with live components
func TestIntegration_HealthEndpointsWithHTTPServer(t *testing.T) {
	healthSrv := health.NewServer("integration-test")

	// Add database checker (simulated)
	healthSrv.RegisterChecker(health.CheckerFunc(func(ctx context.Context) health.ComponentHealth {
		return health.ComponentHealth{
			Name:   "database",
			Status: health.StatusHealthy,
		}
	}))

	// Add cache checker (simulated degraded)
	healthSrv.RegisterChecker(health.CheckerFunc(func(ctx context.Context) health.ComponentHealth {
		return health.ComponentHealth{
			Name:    "cache",
			Status:  health.StatusDegraded,
			Message: "high latency",
		}
	}))

	// Test health endpoint
	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()
	healthSrv.HandleHealth().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp health.HealthResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.Status != health.StatusDegraded {
		t.Errorf("expected degraded due to cache, got %s", resp.Status)
	}
}

// Test: Security audit logging with tenant context
func TestIntegration_AuditLoggingWithTenant(t *testing.T) {
	// Setup audit logger
	auditLog := security.NewInMemoryAuditLogger(100)

	// Setup tenant
	tm := tenant.NewManager()
	tenant1, _ := tm.CreateTenant("t1", "Audit Tenant", tenant.DefaultQuotas())

	// Create context with tenant
	ctx := tenant.WithTenant(context.Background(), tenant1)

	// Log event with tenant context
	extractedTenant, ok := tenant.FromContext(ctx)
	if !ok {
		t.Fatal("should extract tenant from context")
	}

	metadata, _ := json.Marshal(map[string]string{
		"tenant_id":   extractedTenant.ID,
		"tenant_name": extractedTenant.Name,
		"tool":        "test_tool",
	})

	auditLog.Log(&security.AuditEvent{
		Timestamp: time.Now(),
		EventType: security.AuditToolCall,
		ClientID:  extractedTenant.ID,
		Metadata:  metadata,
	})

	events := auditLog.Events()
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}

	if events[0].ClientID != "t1" {
		t.Error("tenant ID not logged correctly")
	}
}

// Test: Full request flow
func TestIntegration_FullRequestFlow(t *testing.T) {
	// 1. Create all components
	tm := tenant.NewManager()
	tm.CreateTenant("customer1", "Customer 1", tenant.DefaultQuotas())

	validator := security.DefaultValidator()
	auditLog := security.NewInMemoryAuditLogger(50)
	healthSrv := health.NewServer("1.0.0")

	// 2. Simulate request
	input := json.RawMessage(`{"query": "SELECT * FROM users"}`)

	// 3. Validate input
	result := validator.ValidateJSON(input)
	if !result.Valid {
		t.Error("valid input should pass validation")
	}

	// 4. Log the request
	auditLog.Log(&security.AuditEvent{
		Timestamp: time.Now(),
		EventType: security.AuditToolCall,
		ClientID:  "customer1",
		Success:   true,
	})

	// 5. Check health
	healthResp := healthSrv.GetHealth(context.Background())
	if healthResp.Status != health.StatusHealthy {
		t.Error("system should be healthy")
	}

	// Verify audit log captured request
	events := auditLog.Events()
	if len(events) != 1 {
		t.Error("audit should capture one event")
	}
}

// Benchmark: Integration overhead
func BenchmarkIntegration_FullPipeline(b *testing.B) {
	validator := security.DefaultValidator()
	auditLog := security.NewInMemoryAuditLogger(1000)

	input := json.RawMessage(`{"key": "value", "count": 42}`)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Validate
		validator.ValidateJSON(input)

		// Audit
		auditLog.Log(&security.AuditEvent{
			Timestamp: time.Now(),
			EventType: security.AuditToolCall,
		})
	}
}
