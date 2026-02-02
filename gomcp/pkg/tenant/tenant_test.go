package tenant

import (
	"context"
	"testing"
)

func TestManager_CreateTenant(t *testing.T) {
	m := NewManager()

	tenant, err := m.CreateTenant("t1", "Test Tenant", DefaultQuotas())
	if err != nil {
		t.Fatalf("failed to create tenant: %v", err)
	}

	if tenant.ID != "t1" {
		t.Errorf("expected ID t1, got %s", tenant.ID)
	}
	if tenant.Name != "Test Tenant" {
		t.Errorf("expected name 'Test Tenant', got %s", tenant.Name)
	}
	if !tenant.Enabled {
		t.Error("expected tenant to be enabled")
	}
}

func TestManager_CreateTenant_Duplicate(t *testing.T) {
	m := NewManager()

	_, err := m.CreateTenant("t1", "First", DefaultQuotas())
	if err != nil {
		t.Fatalf("failed to create first tenant: %v", err)
	}

	_, err = m.CreateTenant("t1", "Second", DefaultQuotas())
	if err != ErrTenantExists {
		t.Errorf("expected ErrTenantExists, got %v", err)
	}
}

func TestManager_GetTenant(t *testing.T) {
	m := NewManager()
	m.CreateTenant("t1", "Test", DefaultQuotas())

	tenant, err := m.GetTenant("t1")
	if err != nil {
		t.Fatalf("failed to get tenant: %v", err)
	}
	if tenant.ID != "t1" {
		t.Errorf("expected ID t1, got %s", tenant.ID)
	}
}

func TestManager_GetTenant_NotFound(t *testing.T) {
	m := NewManager()

	_, err := m.GetTenant("nonexistent")
	if err != ErrTenantNotFound {
		t.Errorf("expected ErrTenantNotFound, got %v", err)
	}
}

func TestManager_DeleteTenant(t *testing.T) {
	m := NewManager()
	m.CreateTenant("t1", "Test", DefaultQuotas())

	err := m.DeleteTenant("t1")
	if err != nil {
		t.Fatalf("failed to delete tenant: %v", err)
	}

	_, err = m.GetTenant("t1")
	if err != ErrTenantNotFound {
		t.Errorf("expected ErrTenantNotFound after delete, got %v", err)
	}
}

func TestManager_ListTenants(t *testing.T) {
	m := NewManager()
	m.CreateTenant("t1", "Tenant 1", DefaultQuotas())
	m.CreateTenant("t2", "Tenant 2", DefaultQuotas())
	m.CreateTenant("t3", "Tenant 3", DefaultQuotas())

	tenants := m.ListTenants()
	if len(tenants) != 3 {
		t.Errorf("expected 3 tenants, got %d", len(tenants))
	}
}

func TestTenant_CheckQuota_ToolCalls(t *testing.T) {
	tenant := &Tenant{
		ID:      "t1",
		Enabled: true,
		Quotas:  Quotas{MaxToolCalls: 3},
	}

	// Should allow first 3 calls
	for i := 0; i < 3; i++ {
		if err := tenant.CheckQuota("tool_call"); err != nil {
			t.Errorf("call %d should be allowed", i+1)
		}
		tenant.IncrementToolCalls()
	}

	// 4th should fail
	if err := tenant.CheckQuota("tool_call"); err != ErrQuotaExceeded {
		t.Errorf("expected ErrQuotaExceeded, got %v", err)
	}
}

func TestTenant_CheckQuota_ConcurrentReqs(t *testing.T) {
	tenant := &Tenant{
		ID:      "t1",
		Enabled: true,
		Quotas:  Quotas{MaxConcurrentReqs: 2},
	}

	tenant.IncrementActiveReqs()
	tenant.IncrementActiveReqs()

	if err := tenant.CheckQuota("concurrent_req"); err != ErrQuotaExceeded {
		t.Errorf("expected ErrQuotaExceeded, got %v", err)
	}

	tenant.DecrementActiveReqs()

	if err := tenant.CheckQuota("concurrent_req"); err != nil {
		t.Errorf("should allow after decrement, got %v", err)
	}
}

func TestTenant_CheckQuota_Disabled(t *testing.T) {
	tenant := &Tenant{
		ID:      "t1",
		Enabled: false,
		Quotas:  DefaultQuotas(),
	}

	if err := tenant.CheckQuota("tool_call"); err != ErrAccessDenied {
		t.Errorf("expected ErrAccessDenied for disabled tenant, got %v", err)
	}
}

func TestTenant_IsToolAllowed_NoRestrictions(t *testing.T) {
	tenant := &Tenant{
		ID:           "t1",
		AllowedTools: nil, // No restrictions
	}

	if !tenant.IsToolAllowed("any_tool") {
		t.Error("should allow any tool when no restrictions")
	}
}

func TestTenant_IsToolAllowed_WithRestrictions(t *testing.T) {
	tenant := &Tenant{
		ID:           "t1",
		AllowedTools: []string{"tool_a", "tool_b"},
	}

	if !tenant.IsToolAllowed("tool_a") {
		t.Error("tool_a should be allowed")
	}
	if !tenant.IsToolAllowed("tool_b") {
		t.Error("tool_b should be allowed")
	}
	if tenant.IsToolAllowed("tool_c") {
		t.Error("tool_c should not be allowed")
	}
}

func TestTenant_IsToolAllowed_Wildcard(t *testing.T) {
	tenant := &Tenant{
		ID:           "t1",
		AllowedTools: []string{"*"},
	}

	if !tenant.IsToolAllowed("any_tool") {
		t.Error("wildcard should allow any tool")
	}
}

func TestTenant_Metadata(t *testing.T) {
	tenant := &Tenant{
		ID:       "t1",
		Metadata: make(map[string]string),
	}

	tenant.SetMetadata("key1", "value1")

	val, ok := tenant.GetMetadata("key1")
	if !ok {
		t.Error("expected to find key1")
	}
	if val != "value1" {
		t.Errorf("expected value1, got %s", val)
	}

	_, ok = tenant.GetMetadata("nonexistent")
	if ok {
		t.Error("should not find nonexistent key")
	}
}

func TestTenant_EnableDisable(t *testing.T) {
	tenant := &Tenant{ID: "t1", Enabled: true}

	tenant.Disable()
	if tenant.Enabled {
		t.Error("should be disabled")
	}

	tenant.Enable()
	if !tenant.Enabled {
		t.Error("should be enabled")
	}
}

func TestTenant_Context(t *testing.T) {
	tenant := &Tenant{ID: "t1"}

	ctx := WithTenant(context.Background(), tenant)

	extractedTenant, ok := FromContext(ctx)
	if !ok {
		t.Fatal("expected to extract tenant from context")
	}
	if extractedTenant.ID != "t1" {
		t.Errorf("expected ID t1, got %s", extractedTenant.ID)
	}
}

func TestTenant_Context_Empty(t *testing.T) {
	ctx := context.Background()

	_, ok := FromContext(ctx)
	if ok {
		t.Error("should not find tenant in empty context")
	}
}

func TestTenant_GetStats(t *testing.T) {
	tenant := &Tenant{ID: "t1"}

	tenant.IncrementToolCalls()
	tenant.IncrementToolCalls()
	tenant.IncrementActiveReqs()
	tenant.AddDataUsage(1024)

	stats := tenant.GetStats()

	if stats.ToolCalls != 2 {
		t.Errorf("expected 2 tool calls, got %d", stats.ToolCalls)
	}
	if stats.ActiveReqs != 1 {
		t.Errorf("expected 1 active req, got %d", stats.ActiveReqs)
	}
	if stats.DataUsage != 1024 {
		t.Errorf("expected 1024 bytes, got %d", stats.DataUsage)
	}
}

func TestTenant_QuotaUsage(t *testing.T) {
	tenant := &Tenant{
		ID:      "t1",
		Enabled: true,
		Quotas: Quotas{
			MaxToolCalls: 100,
		},
	}

	for i := 0; i < 50; i++ {
		tenant.IncrementToolCalls()
	}

	usage := tenant.QuotaUsage()

	if usage["tool_calls"] != 50.0 {
		t.Errorf("expected 50%% usage, got %.2f", usage["tool_calls"])
	}
}

func TestTenant_Describe(t *testing.T) {
	tenant := &Tenant{
		ID:      "t1",
		Name:    "Test",
		Enabled: true,
	}

	desc := tenant.Describe()
	if desc == "" {
		t.Error("description should not be empty")
	}
}

func TestManager_Callbacks(t *testing.T) {
	m := NewManager()

	createCalled := false
	deleteCalled := false

	m.OnTenantCreate(func(tenant *Tenant) {
		createCalled = true
	})
	m.OnTenantDelete(func(id string) {
		deleteCalled = true
	})

	m.CreateTenant("t1", "Test", DefaultQuotas())
	if !createCalled {
		t.Error("create callback not called")
	}

	m.DeleteTenant("t1")
	if !deleteCalled {
		t.Error("delete callback not called")
	}
}

func TestDefaultQuotas(t *testing.T) {
	q := DefaultQuotas()

	if q.MaxToolCalls <= 0 {
		t.Error("MaxToolCalls should be positive")
	}
	if q.MaxConcurrentReqs <= 0 {
		t.Error("MaxConcurrentReqs should be positive")
	}
	if q.MaxDataUsageBytes <= 0 {
		t.Error("MaxDataUsageBytes should be positive")
	}
}

// Benchmark
func BenchmarkTenant_CheckQuota(b *testing.B) {
	tenant := &Tenant{
		ID:      "t1",
		Enabled: true,
		Quotas:  DefaultQuotas(),
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tenant.CheckQuota("tool_call")
	}
}

func BenchmarkManager_GetTenant(b *testing.B) {
	m := NewManager()
	for i := 0; i < 100; i++ {
		m.CreateTenant(string(rune('A'+i)), "Tenant", DefaultQuotas())
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		m.GetTenant("A")
	}
}
