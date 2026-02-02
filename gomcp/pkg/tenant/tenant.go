// Package tenant provides multi-tenant namespace isolation for GoMCP.
package tenant

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"
)

var (
	// ErrTenantNotFound returned when tenant doesn't exist
	ErrTenantNotFound = errors.New("tenant not found")
	// ErrTenantExists returned when tenant already exists
	ErrTenantExists = errors.New("tenant already exists")
	// ErrQuotaExceeded returned when resource quota exceeded
	ErrQuotaExceeded = errors.New("resource quota exceeded")
	// ErrAccessDenied returned when tenant access is denied
	ErrAccessDenied = errors.New("access denied")
)

// Tenant represents an isolated tenant namespace
type Tenant struct {
	ID           string            `json:"id"`
	Name         string            `json:"name"`
	Enabled      bool              `json:"enabled"`
	CreatedAt    time.Time         `json:"created_at"`
	Quotas       Quotas            `json:"quotas"`
	Metadata     map[string]string `json:"metadata,omitempty"`
	AllowedTools []string          `json:"allowed_tools,omitempty"`

	// Runtime stats
	mu         sync.RWMutex
	toolCalls  int64
	activeReqs int
	dataUsage  int64
}

// Quotas defines resource limits for a tenant
type Quotas struct {
	MaxToolCalls      int64 `json:"max_tool_calls"`       // -1 for unlimited
	MaxConcurrentReqs int   `json:"max_concurrent_reqs"`  // -1 for unlimited
	MaxDataUsageBytes int64 `json:"max_data_usage_bytes"` // -1 for unlimited
	MaxWorkers        int   `json:"max_workers"`          // -1 for unlimited
	MaxToolsPerWorker int   `json:"max_tools_per_worker"` // -1 for unlimited
}

// DefaultQuotas returns sensible default quotas
func DefaultQuotas() Quotas {
	return Quotas{
		MaxToolCalls:      100000,     // 100K calls
		MaxConcurrentReqs: 100,        // 100 concurrent
		MaxDataUsageBytes: 1073741824, // 1GB
		MaxWorkers:        10,
		MaxToolsPerWorker: 50,
	}
}

// Manager handles tenant lifecycle and isolation
type Manager struct {
	mu      sync.RWMutex
	tenants map[string]*Tenant

	// Hooks for tenant events
	onTenantCreate func(*Tenant)
	onTenantDelete func(tenantID string)
}

// NewManager creates a new tenant manager
func NewManager() *Manager {
	return &Manager{
		tenants: make(map[string]*Tenant),
	}
}

// CreateTenant creates a new tenant with the given ID
func (m *Manager) CreateTenant(id, name string, quotas Quotas) (*Tenant, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.tenants[id]; exists {
		return nil, ErrTenantExists
	}

	tenant := &Tenant{
		ID:        id,
		Name:      name,
		Enabled:   true,
		CreatedAt: time.Now(),
		Quotas:    quotas,
		Metadata:  make(map[string]string),
	}

	m.tenants[id] = tenant

	if m.onTenantCreate != nil {
		m.onTenantCreate(tenant)
	}

	return tenant, nil
}

// GetTenant retrieves a tenant by ID
func (m *Manager) GetTenant(id string) (*Tenant, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	tenant, exists := m.tenants[id]
	if !exists {
		return nil, ErrTenantNotFound
	}

	return tenant, nil
}

// DeleteTenant removes a tenant
func (m *Manager) DeleteTenant(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.tenants[id]; !exists {
		return ErrTenantNotFound
	}

	delete(m.tenants, id)

	if m.onTenantDelete != nil {
		m.onTenantDelete(id)
	}

	return nil
}

// ListTenants returns all tenants
func (m *Manager) ListTenants() []*Tenant {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Tenant, 0, len(m.tenants))
	for _, t := range m.tenants {
		result = append(result, t)
	}
	return result
}

// OnTenantCreate sets a callback for tenant creation
func (m *Manager) OnTenantCreate(f func(*Tenant)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onTenantCreate = f
}

// OnTenantDelete sets a callback for tenant deletion
func (m *Manager) OnTenantDelete(f func(tenantID string)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onTenantDelete = f
}

// CheckQuota verifies if a tenant can perform an operation
func (t *Tenant) CheckQuota(operation string) error {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if !t.Enabled {
		return ErrAccessDenied
	}

	switch operation {
	case "tool_call":
		if t.Quotas.MaxToolCalls >= 0 && t.toolCalls >= t.Quotas.MaxToolCalls {
			return ErrQuotaExceeded
		}
	case "concurrent_req":
		if t.Quotas.MaxConcurrentReqs >= 0 && t.activeReqs >= t.Quotas.MaxConcurrentReqs {
			return ErrQuotaExceeded
		}
	case "data_usage":
		if t.Quotas.MaxDataUsageBytes >= 0 && t.dataUsage >= t.Quotas.MaxDataUsageBytes {
			return ErrQuotaExceeded
		}
	}

	return nil
}

// IncrementToolCalls increments the tool call counter
func (t *Tenant) IncrementToolCalls() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.toolCalls++
}

// IncrementActiveReqs increments active requests
func (t *Tenant) IncrementActiveReqs() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.activeReqs++
}

// DecrementActiveReqs decrements active requests
func (t *Tenant) DecrementActiveReqs() {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.activeReqs > 0 {
		t.activeReqs--
	}
}

// AddDataUsage adds to data usage counter
func (t *Tenant) AddDataUsage(bytes int64) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.dataUsage += bytes
}

// GetStats returns tenant runtime statistics
func (t *Tenant) GetStats() TenantStats {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return TenantStats{
		ToolCalls:  t.toolCalls,
		ActiveReqs: t.activeReqs,
		DataUsage:  t.dataUsage,
	}
}

// TenantStats contains runtime statistics for a tenant
type TenantStats struct {
	ToolCalls  int64 `json:"tool_calls"`
	ActiveReqs int   `json:"active_reqs"`
	DataUsage  int64 `json:"data_usage_bytes"`
}

// IsToolAllowed checks if a tool is allowed for this tenant
func (t *Tenant) IsToolAllowed(toolName string) bool {
	t.mu.RLock()
	defer t.mu.RUnlock()

	// If no restrictions, allow all
	if len(t.AllowedTools) == 0 {
		return true
	}

	for _, allowed := range t.AllowedTools {
		if allowed == toolName || allowed == "*" {
			return true
		}
	}
	return false
}

// SetMetadata sets a metadata value
func (t *Tenant) SetMetadata(key, value string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.Metadata[key] = value
}

// GetMetadata gets a metadata value
func (t *Tenant) GetMetadata(key string) (string, bool) {
	t.mu.RLock()
	defer t.mu.RUnlock()
	v, ok := t.Metadata[key]
	return v, ok
}

// Context key for tenant
type contextKey string

const tenantContextKey contextKey = "tenant"

// WithTenant adds a tenant to the context
func WithTenant(ctx context.Context, t *Tenant) context.Context {
	return context.WithValue(ctx, tenantContextKey, t)
}

// FromContext extracts tenant from context
func FromContext(ctx context.Context) (*Tenant, bool) {
	t, ok := ctx.Value(tenantContextKey).(*Tenant)
	return t, ok
}

// MarshalJSON implements json.Marshaler
func (t *Tenant) MarshalJSON() ([]byte, error) {
	t.mu.RLock()
	defer t.mu.RUnlock()

	type Alias Tenant
	return json.Marshal(&struct {
		*Alias
		Stats TenantStats `json:"stats"`
	}{
		Alias: (*Alias)(t),
		Stats: TenantStats{
			ToolCalls:  t.toolCalls,
			ActiveReqs: t.activeReqs,
			DataUsage:  t.dataUsage,
		},
	})
}

// Enable enables the tenant
func (t *Tenant) Enable() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.Enabled = true
}

// Disable disables the tenant
func (t *Tenant) Disable() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.Enabled = false
}

// UpdateQuotas updates tenant quotas
func (t *Tenant) UpdateQuotas(quotas Quotas) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.Quotas = quotas
}

// SetAllowedTools sets the list of allowed tools
func (t *Tenant) SetAllowedTools(tools []string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.AllowedTools = tools
}

// QuotaUsage returns current quota usage as percentages
func (t *Tenant) QuotaUsage() map[string]float64 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	usage := make(map[string]float64)

	if t.Quotas.MaxToolCalls > 0 {
		usage["tool_calls"] = float64(t.toolCalls) / float64(t.Quotas.MaxToolCalls) * 100
	}
	if t.Quotas.MaxDataUsageBytes > 0 {
		usage["data_usage"] = float64(t.dataUsage) / float64(t.Quotas.MaxDataUsageBytes) * 100
	}
	if t.Quotas.MaxConcurrentReqs > 0 {
		usage["concurrent_reqs"] = float64(t.activeReqs) / float64(t.Quotas.MaxConcurrentReqs) * 100
	}

	return usage
}

// Describe returns a human-readable description
func (t *Tenant) Describe() string {
	t.mu.RLock()
	defer t.mu.RUnlock()

	status := "enabled"
	if !t.Enabled {
		status = "disabled"
	}

	return fmt.Sprintf("Tenant[%s] %s (%s) - %d tool calls, %d active reqs",
		t.ID, t.Name, status, t.toolCalls, t.activeReqs)
}
