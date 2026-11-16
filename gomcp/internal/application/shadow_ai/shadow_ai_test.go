package shadow_ai

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"testing"
	"time"

 socdomain "github.com/syntrex/gomcp/internal/domain/soc"
)

// --- Mock Plugins ---

type mockFirewall struct {
	blockIPs     []string
	blockDomains []string
	healthy      bool
	mu           sync.Mutex
}

func newMockFirewall(healthy bool) *mockFirewall {
	return &mockFirewall{healthy: healthy}
}

func (m *mockFirewall) BlockIP(_ context.Context, ip string, _ time.Duration, _ string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.blockIPs = append(m.blockIPs, ip)
	return nil
}

func (m *mockFirewall) BlockDomain(_ context.Context, domain string, _ string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.blockDomains = append(m.blockDomains, domain)
	return nil
}

func (m *mockFirewall) UnblockIP(_ context.Context, _ string) error   { return nil }
func (m *mockFirewall) UnblockDomain(_ context.Context, _ string) error { return nil }

func (m *mockFirewall) HealthCheck(_ context.Context) error {
	if !m.healthy {
		return fmt.Errorf("firewall offline")
	}
	return nil
}

func (m *mockFirewall) Vendor() string { return "mock-firewall" }

type mockEDR struct {
	isolated []string
	healthy  bool
}

func newMockEDR(healthy bool) *mockEDR {
	return &mockEDR{healthy: healthy}
}

func (m *mockEDR) IsolateHost(_ context.Context, hostname string) error {
	m.isolated = append(m.isolated, hostname)
	return nil
}
func (m *mockEDR) ReleaseHost(_ context.Context, _ string) error          { return nil }
func (m *mockEDR) KillProcess(_ context.Context, _ string, _ int) error   { return nil }
func (m *mockEDR) QuarantineFile(_ context.Context, _ string, _ string) error { return nil }

func (m *mockEDR) HealthCheck(_ context.Context) error {
	if !m.healthy {
		return fmt.Errorf("EDR offline")
	}
	return nil
}

func (m *mockEDR) Vendor() string { return "mock-edr" }

type mockGateway struct {
	blockedURLs []string
	healthy     bool
}

func newMockGateway(healthy bool) *mockGateway {
	return &mockGateway{healthy: healthy}
}

func (m *mockGateway) BlockURL(_ context.Context, url string, _ string) error {
	m.blockedURLs = append(m.blockedURLs, url)
	return nil
}
func (m *mockGateway) UnblockURL(_ context.Context, _ string) error      { return nil }
func (m *mockGateway) BlockCategory(_ context.Context, _ string) error   { return nil }

func (m *mockGateway) HealthCheck(_ context.Context) error {
	if !m.healthy {
		return fmt.Errorf("gateway offline")
	}
	return nil
}

func (m *mockGateway) Vendor() string { return "mock-gateway" }

// --- Registry Tests ---

func TestRegistry_RegisterAndGet(t *testing.T) {
	reg := NewPluginRegistry()

	fw := newMockFirewall(true)
	reg.RegisterFactory(PluginTypeFirewall, "mock-firewall", func() interface{} {
		return fw
	})

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "mock-firewall", Enabled: true},
		},
	}

	if err := reg.LoadPlugins(cfg); err != nil {
		t.Fatalf("LoadPlugins: %v", err)
	}

	if reg.PluginCount() != 1 {
		t.Fatalf("expected 1 plugin, got %d", reg.PluginCount())
	}

	got, ok := reg.Get("mock-firewall")
	if !ok {
		t.Fatal("plugin not found")
	}

	ne, ok := got.(NetworkEnforcer)
	if !ok {
		t.Fatal("plugin does not implement NetworkEnforcer")
	}

	if ne.Vendor() != "mock-firewall" {
		t.Fatalf("expected vendor mock-firewall, got %s", ne.Vendor())
	}
}

func TestRegistry_DisabledPlugin(t *testing.T) {
	reg := NewPluginRegistry()
	reg.RegisterFactory(PluginTypeFirewall, "disabled-fw", func() interface{} {
		return newMockFirewall(true)
	})

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "disabled-fw", Enabled: false},
		},
	}

	_ = reg.LoadPlugins(cfg)

	if reg.PluginCount() != 0 {
		t.Fatalf("disabled plugin should not be loaded, got %d", reg.PluginCount())
	}
}

func TestRegistry_MissingFactory(t *testing.T) {
	reg := NewPluginRegistry()
	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "non-existent", Enabled: true},
		},
	}

	_ = reg.LoadPlugins(cfg)

	if reg.PluginCount() != 0 {
		t.Fatalf("expected 0 plugins, got %d", reg.PluginCount())
	}
}

func TestRegistry_GetByType(t *testing.T) {
	reg := NewPluginRegistry()

	reg.RegisterFactory(PluginTypeFirewall, "fw1", func() interface{} {
		return newMockFirewall(true)
	})
	reg.RegisterFactory(PluginTypeEDR, "edr1", func() interface{} {
		return newMockEDR(true)
	})

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw1", Enabled: true},
			{Type: PluginTypeEDR, Vendor: "edr1", Enabled: true},
		},
	}

	_ = reg.LoadPlugins(cfg)

	firewalls := reg.GetByType(PluginTypeFirewall)
	if len(firewalls) != 1 {
		t.Fatalf("expected 1 firewall, got %d", len(firewalls))
	}

	edrs := reg.GetByType(PluginTypeEDR)
	if len(edrs) != 1 {
		t.Fatalf("expected 1 edr, got %d", len(edrs))
	}
}

func TestRegistry_TypedGetters(t *testing.T) {
	reg := NewPluginRegistry()

	reg.RegisterFactory(PluginTypeFirewall, "fw1", func() interface{} {
		return newMockFirewall(true)
	})
	reg.RegisterFactory(PluginTypeEDR, "edr1", func() interface{} {
		return newMockEDR(true)
	})
	reg.RegisterFactory(PluginTypeProxy, "gw1", func() interface{} {
		return newMockGateway(true)
	})

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw1", Enabled: true},
			{Type: PluginTypeEDR, Vendor: "edr1", Enabled: true},
			{Type: PluginTypeProxy, Vendor: "gw1", Enabled: true},
		},
	}

	_ = reg.LoadPlugins(cfg)

	if len(reg.GetNetworkEnforcers()) != 1 {
		t.Fatal("expected 1 NetworkEnforcer")
	}
	if len(reg.GetEndpointControllers()) != 1 {
		t.Fatal("expected 1 EndpointController")
	}
	if len(reg.GetWebGateways()) != 1 {
		t.Fatal("expected 1 WebGateway")
	}
}

func TestRegistry_Vendors(t *testing.T) {
	reg := NewPluginRegistry()
	reg.RegisterFactory(PluginTypeFirewall, "a", func() interface{} {
		return newMockFirewall(true)
	})
	reg.RegisterFactory(PluginTypeEDR, "b", func() interface{} {
		return newMockEDR(true)
	})

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "a", Enabled: true},
			{Type: PluginTypeEDR, Vendor: "b", Enabled: true},
		},
	}

	_ = reg.LoadPlugins(cfg)

	vendors := reg.Vendors()
	if len(vendors) != 2 {
		t.Fatalf("expected 2 vendors, got %d", len(vendors))
	}
}

// --- Health Tests ---

func TestHealth_PluginHealthy(t *testing.T) {
	reg := NewPluginRegistry()
	fw := newMockFirewall(true)
	reg.RegisterFactory(PluginTypeFirewall, "fw", func() interface{} { return fw })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	hc := NewHealthChecker(reg, time.Second, nil)
	hc.CheckNow(context.Background())

	h, ok := reg.GetHealth("fw")
	if !ok || h.Status != PluginStatusHealthy {
		t.Fatalf("expected healthy, got %v", h)
	}
}

func TestHealth_PluginOffline(t *testing.T) {
	reg := NewPluginRegistry()
	fw := newMockFirewall(false) // unhealthy
	reg.RegisterFactory(PluginTypeFirewall, "fw", func() interface{} { return fw })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	hc := NewHealthChecker(reg, time.Second, nil)

	// Check 3 times to trigger offline.
	for i := 0; i < MaxConsecutivePluginFailures; i++ {
		hc.CheckNow(context.Background())
	}

	h, ok := reg.GetHealth("fw")
	if !ok {
		t.Fatal("health not found")
	}
	if h.Status != PluginStatusOffline {
		t.Fatalf("expected offline, got %s (consecutive=%d)", h.Status, h.Consecutive)
	}
}

func TestHealth_PluginRecovery(t *testing.T) {
	reg := NewPluginRegistry()
	fw := newMockFirewall(false) // start unhealthy
	reg.RegisterFactory(PluginTypeFirewall, "fw", func() interface{} { return fw })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	var alerts []string
	hc := NewHealthChecker(reg, time.Second, func(vendor string, status PluginStatus, msg string) {
		alerts = append(alerts, fmt.Sprintf("%s:%s", vendor, status))
	})

	// Make it go offline.
	for i := 0; i < MaxConsecutivePluginFailures; i++ {
		hc.CheckNow(context.Background())
	}

	// Now recover.
	fw.healthy = true
	hc.CheckNow(context.Background())

	h, _ := reg.GetHealth("fw")
	if h.Status != PluginStatusHealthy {
		t.Fatalf("expected healthy after recovery, got %s", h.Status)
	}

	if len(alerts) < 2 {
		t.Fatalf("expected at least 2 alerts (offline + recovery), got %d", len(alerts))
	}
}

// --- Fallback Tests ---

func TestFallback_BlockDomain_Healthy(t *testing.T) {
	reg := NewPluginRegistry()
	fw := newMockFirewall(true)
	reg.RegisterFactory(PluginTypeFirewall, "mock-firewall", func() interface{} { return fw })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "mock-firewall", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	fm := NewFallbackManager(reg, "detect_only")
	vendor, err := fm.BlockDomain(context.Background(), "api.openai.com", "test")
	if err != nil {
		t.Fatalf("BlockDomain: %v", err)
	}
	if vendor != "mock-firewall" {
		t.Fatalf("expected vendor 'mock-firewall', got '%s'", vendor)
	}

	fw.mu.Lock()
	if len(fw.blockDomains) != 1 || fw.blockDomains[0] != "api.openai.com" {
		t.Fatalf("expected blocked domain, got %v", fw.blockDomains)
	}
	fw.mu.Unlock()
}

func TestFallback_AllOffline_DetectOnly(t *testing.T) {
	reg := NewPluginRegistry()
	fw := newMockFirewall(false) // offline
	reg.RegisterFactory(PluginTypeFirewall, "fw", func() interface{} { return fw })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "fw", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	// Mark as offline.
	reg.SetHealth("fw", &PluginHealth{Vendor: "fw", Status: PluginStatusOffline})

	var detected []ShadowAIEvent
	fm := NewFallbackManager(reg, "detect_only")
	fm.SetEventLogger(func(e ShadowAIEvent) {
		detected = append(detected, e)
	})

	vendor, err := fm.BlockDomain(context.Background(), "api.openai.com", "test")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if vendor != "" {
		t.Fatalf("expected empty vendor for detect_only, got '%s'", vendor)
	}

	if len(detected) != 1 {
		t.Fatalf("expected 1 detect_only event, got %d", len(detected))
	}
	if detected[0].Action != "detect_only" {
		t.Fatalf("expected action 'detect_only', got '%s'", detected[0].Action)
	}
}

func TestFallback_IsolateHost(t *testing.T) {
	reg := NewPluginRegistry()
	edr := newMockEDR(true)
	reg.RegisterFactory(PluginTypeEDR, "mock-edr", func() interface{} { return edr })

	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeEDR, Vendor: "mock-edr", Enabled: true},
		},
	}
	_ = reg.LoadPlugins(cfg)

	fm := NewFallbackManager(reg, "detect_only")
	vendor, err := fm.IsolateHost(context.Background(), "workstation-1")
	if err != nil {
		t.Fatalf("IsolateHost: %v", err)
	}
	if vendor != "mock-edr" {
		t.Fatalf("expected vendor 'mock-edr', got '%s'", vendor)
	}
	if len(edr.isolated) != 1 || edr.isolated[0] != "workstation-1" {
		t.Fatalf("host not isolated: %v", edr.isolated)
	}
}

// --- Detection Tests ---

func TestDetection_MatchDomain(t *testing.T) {
	db := NewAISignatureDB()

	tests := []struct {
		domain  string
		service string
	}{
		{"chat.openai.com", "ChatGPT"},
		{"api.openai.com", "ChatGPT"},
		{"claude.ai", "Claude"},
		{"api.anthropic.com", "Claude"},
		{"gemini.google.com", "Gemini"},
		{"api.deepseek.com", "DeepSeek"},
		{"api.mistral.ai", "Mistral"},
		{"api.groq.com", "Groq"},
		{"example.com", ""},
		{"google.com", ""},
	}

	for _, tt := range tests {
		t.Run(tt.domain, func(t *testing.T) {
			result := db.MatchDomain(tt.domain)
			if result != tt.service {
				t.Errorf("MatchDomain(%q) = %q, want %q", tt.domain, result, tt.service)
			}
		})
	}
}

func TestDetection_ServiceCount(t *testing.T) {
	db := NewAISignatureDB()
	if db.ServiceCount() < 30 {
		t.Fatalf("expected at least 30 AI services, got %d", db.ServiceCount())
	}
	if db.DomainPatternCount() < 50 {
		t.Fatalf("expected at least 50 domain patterns, got %d", db.DomainPatternCount())
	}
}

func TestDetection_AddCustomService(t *testing.T) {
	db := NewAISignatureDB()
	initial := db.ServiceCount()

	db.AddService(AIServiceInfo{
		Name:    "InternalLLM",
		Vendor:  "Internal",
		Domains: []string{"llm.internal.corp"},
	})

	if db.ServiceCount() != initial+1 {
		t.Fatal("service not added")
	}

	result := db.MatchDomain("llm.internal.corp")
	if result != "InternalLLM" {
		t.Fatalf("custom service not matched: got %q", result)
	}
}

func TestDetection_ScanAPIKey_OpenAI(t *testing.T) {
	db := NewAISignatureDB()

	// Generate a mock key that matches the pattern.
	content := "My key is sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMN"
	result := db.ScanForAPIKeys(content)
	if result != "OpenAI Project Key" {
		t.Fatalf("expected OpenAI Project Key detection, got %q", result)
	}
}

func TestDetection_ScanAPIKey_NoMatch(t *testing.T) {
	db := NewAISignatureDB()

	result := db.ScanForAPIKeys("this is normal text without any API keys")
	if result != "" {
		t.Fatalf("expected no match, got %q", result)
	}
}

func TestDetection_MatchHTTPHeaders(t *testing.T) {
	db := NewAISignatureDB()

	headers := map[string]string{
		"Authorization": "Bearer sk-abc123",
	}
	result := db.MatchHTTPHeaders(headers)
	if result != "authorization: bearer sk-" {
		t.Fatalf("expected OpenAI header match, got %q", result)
	}
}

func TestDetection_MatchHTTPHeaders_NoMatch(t *testing.T) {
	db := NewAISignatureDB()

	headers := map[string]string{
		"Authorization": "Bearer jwt-token-xyz",
	}
	result := db.MatchHTTPHeaders(headers)
	if result != "" {
		t.Fatalf("expected no match, got %q", result)
	}
}

func TestDetection_NetworkDetector(t *testing.T) {
	nd := NewNetworkDetector()

	event := NetworkEvent{
		User:        "user1",
		Hostname:    "ws-001",
		Destination: "api.openai.com",
		DataSize:    1024,
		Timestamp:   time.Now(),
	}

	detected := nd.Analyze(event)
	if detected == nil {
		t.Fatal("expected detection for api.openai.com")
	}
	if detected.AIService != "ChatGPT" {
		t.Fatalf("expected ChatGPT, got %s", detected.AIService)
	}
	if detected.DetectionMethod != DetectNetwork {
		t.Fatalf("expected network detection, got %s", detected.DetectionMethod)
	}
}

func TestDetection_NetworkDetector_NoMatch(t *testing.T) {
	nd := NewNetworkDetector()

	event := NetworkEvent{
		User:        "user1",
		Destination: "example.com",
		Timestamp:   time.Now(),
	}

	if nd.Analyze(event) != nil {
		t.Fatal("should not detect non-AI domain")
	}
}

func TestDetection_HTTPSignature(t *testing.T) {
	nd := NewNetworkDetector()

	event := NetworkEvent{
		User:        "user1",
		Destination: "some-proxy.corp.internal",
		HTTPHeaders: map[string]string{
			"Authorization": "Bearer sk-abc123def456",
		},
		Timestamp: time.Now(),
	}

	detected := nd.Analyze(event)
	if detected == nil {
		t.Fatal("expected detection via HTTP sig")
	}
	if detected.DetectionMethod != DetectHTTP {
		t.Fatalf("expected HTTP detection, got %s", detected.DetectionMethod)
	}
}

// --- Behavioral Tests ---

func TestBehavioral_FirstAccess(t *testing.T) {
	bd := NewBehavioralDetector(10)

	bd.RecordAccess("user1", "api.openai.com", 1024)

	alerts := bd.DetectAnomalies()
	found := false
	for _, a := range alerts {
		if a.UserID == "user1" && a.AnomalyType == "first_ai_access" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected first_ai_access alert for user without baseline")
	}
}

func TestBehavioral_AccessSpike(t *testing.T) {
	bd := NewBehavioralDetector(10)

	bd.SetBaseline("user1", &UserBehaviorProfile{
		UserID:          "user1",
		AccessFrequency: 5,
	})

	// Record 50 accesses — 10x baseline.
	for i := 0; i < 50; i++ {
		bd.RecordAccess("user1", "api.openai.com", 100)
	}

	alerts := bd.DetectAnomalies()
	found := false
	for _, a := range alerts {
		if a.UserID == "user1" && a.AnomalyType == "access_spike" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected access_spike alert")
	}
}

func TestBehavioral_NewDestination(t *testing.T) {
	bd := NewBehavioralDetector(10)

	bd.SetBaseline("user1", &UserBehaviorProfile{
		UserID:            "user1",
		AccessFrequency:   5,
		KnownDestinations: []string{"api.openai.com"},
	})

	bd.RecordAccess("user1", "api.anthropic.com", 100)

	alerts := bd.DetectAnomalies()
	found := false
	for _, a := range alerts {
		if a.UserID == "user1" && a.AnomalyType == "new_ai_destination" {
			found = true
			if a.Destination != "api.anthropic.com" {
				t.Fatalf("expected destination api.anthropic.com, got %s", a.Destination)
			}
		}
	}
	if !found {
		t.Fatal("expected new_ai_destination alert")
	}
}

func TestBehavioral_ResetCurrent(t *testing.T) {
	bd := NewBehavioralDetector(10)
	bd.RecordAccess("user1", "api.openai.com", 1024)
	bd.ResetCurrent()

	alerts := bd.DetectAnomalies()
	if len(alerts) != 0 {
		t.Fatalf("expected 0 alerts after reset, got %d", len(alerts))
	}
}

// --- Controller Tests ---

func TestController_ProcessNetworkEvent(t *testing.T) {
	ctrl := NewShadowAIController()

	var socEvents []string
	ctrl.SetSOCEventEmitter(func(source, severity, category, description string, meta map[string]string) {
		socEvents = append(socEvents, category+":"+description)
	})

	event := NetworkEvent{
		User:        "user1",
		Hostname:    "ws-001",
		Destination: "api.openai.com",
		DataSize:    2048,
		Timestamp:   time.Now(),
	}

	detected := ctrl.ProcessNetworkEvent(context.Background(), event)
	if detected == nil {
		t.Fatal("expected detection")
	}
	if detected.AIService != "ChatGPT" {
		t.Fatalf("expected ChatGPT, got %s", detected.AIService)
	}
	if len(socEvents) != 1 {
		t.Fatalf("expected 1 SOC event, got %d", len(socEvents))
	}
}

func TestController_GetStats(t *testing.T) {
	ctrl := NewShadowAIController()

	// Process a few events.
	for i := 0; i < 5; i++ {
		ctrl.ProcessNetworkEvent(context.Background(), NetworkEvent{
			User:        fmt.Sprintf("user%d", i%3),
			Destination: "api.openai.com",
			Timestamp:   time.Now(),
		})
	}

	stats := ctrl.GetStats("24h")
	if stats.Total != 5 {
		t.Fatalf("expected 5 total, got %d", stats.Total)
	}
	if stats.ByService["ChatGPT"] != 5 {
		t.Fatalf("expected 5 ChatGPT, got %d", stats.ByService["ChatGPT"])
	}
	if len(stats.TopViolators) == 0 {
		t.Fatal("expected at least 1 violator")
	}
}

func TestController_GetEvents(t *testing.T) {
	ctrl := NewShadowAIController()

	for i := 0; i < 10; i++ {
		ctrl.ProcessNetworkEvent(context.Background(), NetworkEvent{
			User:        "user1",
			Destination: "api.openai.com",
			Timestamp:   time.Now(),
		})
	}

	events := ctrl.GetEvents(5)
	if len(events) != 5 {
		t.Fatalf("expected 5 events, got %d", len(events))
	}
}

func TestController_ScanContent(t *testing.T) {
	ctrl := NewShadowAIController()

	result, isInjected := ctrl.ScanContent("nothing here")
	if result != "" || isInjected {
		t.Fatalf("expected no detection, got %q (injected: %v)", result, isInjected)
	}
}

func TestController_ComplianceReport(t *testing.T) {
	ctrl := NewShadowAIController()

	report := ctrl.GenerateComplianceReport("30d")
	if report.Period != "30d" {
		t.Fatalf("expected period 30d, got %s", report.Period)
	}
	// AuditComplete is HONEST (was previously hardcoded true): with no SOC event
	// bridge wired, detections never reach the auditable decision log, so audit
	// is NOT complete.
	if report.AuditComplete {
		t.Fatal("expected audit NOT complete without a SOC event emitter")
	}
	if len(report.Regulations) != 3 {
		t.Fatalf("expected 3 regulations, got %d", len(report.Regulations))
	}

	// Once the SOC bridge is wired, the audit path exists → AuditComplete true.
	ctrl.SetSOCEventEmitter(func(_, _, _, _ string, _ map[string]string) {})
	if !ctrl.GenerateComplianceReport("30d").AuditComplete {
		t.Fatal("expected audit complete once SOC emitter is wired")
	}
}

func TestController_IntegrationHealth(t *testing.T) {
	ctrl := NewShadowAIController()
	health := ctrl.IntegrationHealth()
	if health == nil {
		t.Fatal("expected non-nil health")
	}
}

func TestServicesByCategory(t *testing.T) {
	categories := ServicesByCategory()
	if len(categories) == 0 {
		t.Fatal("expected categories")
	}
	if _, ok := categories["llm"]; !ok {
		t.Fatal("expected 'llm' category")
	}
	if _, ok := categories["code_assist"]; !ok {
		t.Fatal("expected 'code_assist' category")
	}
}

func TestController_EventBounded(t *testing.T) {
	ctrl := NewShadowAIController()
	// Override maxEvents for testing.
	ctrl.mu.Lock()
	ctrl.maxEvents = 10
	ctrl.mu.Unlock()

	for i := 0; i < 20; i++ {
		ctrl.ProcessNetworkEvent(context.Background(), NetworkEvent{
			User:        "user1",
			Destination: "api.openai.com",
			Timestamp:   time.Now(),
		})
	}

	events := ctrl.GetEvents(100)
	if len(events) > 10 {
		t.Fatalf("expected max 10 events, got %d", len(events))
	}
}

// =====================================================
// Phase 3: Document Review Bridge Tests
// =====================================================

func TestDocBridge_CleanContent(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-1", "This is clean text without any PII or secrets.", "user1")
	if result.Status != DocReviewClean {
		t.Fatalf("expected clean, got %s", result.Status)
	}
	if result.DataClass != DataPublic {
		t.Fatalf("expected PUBLIC, got %s", result.DataClass)
	}
	if len(result.PIIFound) != 0 {
		t.Fatalf("expected 0 PII, got %d", len(result.PIIFound))
	}
}

func TestDocBridge_DetectEmail(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-2", "Please contact john.doe@example.com for details.", "user1")
	if len(result.PIIFound) == 0 {
		t.Fatal("expected PII detection for email")
	}
	found := false
	for _, pii := range result.PIIFound {
		if pii.Type == "email" {
			found = true
			if pii.Masked == "" {
				t.Fatal("expected masked email")
			}
		}
	}
	if !found {
		t.Fatal("expected email PII type")
	}
}

func TestDocBridge_DetectSSN(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-3", "SSN: 123-45-6789", "user1")
	found := false
	for _, pii := range result.PIIFound {
		if pii.Type == "ssn" {
			found = true
			if pii.Masked != "***-**-****" {
				t.Fatalf("expected masked SSN, got %q", pii.Masked)
			}
		}
	}
	if !found {
		t.Fatal("expected SSN detection")
	}
	if result.DataClass != DataCritical {
		t.Fatalf("SSN should classify as CRITICAL, got %s", result.DataClass)
	}
}

func TestDocBridge_DetectCreditCard(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-4", "Card: 4111 1111 1111 1111", "user1")
	found := false
	for _, pii := range result.PIIFound {
		if pii.Type == "credit_card" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected credit_card detection")
	}
	if result.DataClass != DataCritical {
		t.Fatalf("credit card should classify as CRITICAL, got %s", result.DataClass)
	}
}

func TestDocBridge_DetectAWSKey(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-5", "AWS key: AKIAIOSFODNN7EXAMPLE", "user1")
	if len(result.SecretsFound) == 0 {
		t.Fatal("expected AWS key detection")
	}
	found := false
	for _, s := range result.SecretsFound {
		if s.Provider == "AWS" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected AWS provider")
	}
	if result.Status != DocReviewBlocked {
		t.Fatalf("secrets should block, got %s", result.Status)
	}
}

func TestDocBridge_DetectGitHubToken(t *testing.T) {
	db := NewDocBridge()
	result := db.ScanDocument("doc-6", "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij", "user1")
	found := false
	for _, s := range result.SecretsFound {
		if s.Provider == "GitHub" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected GitHub token detection")
	}
}

func TestDocBridge_RedactContent(t *testing.T) {
	db := NewDocBridge()
	content := "Email: john@example.com, SSN: 123-45-6789, Key: AKIAIOSFODNN7EXAMPLE"
	redacted := db.RedactContent(content)

	if redacted == content {
		t.Fatal("expected content to be modified")
	}
	// Email should be partially masked.
	if strings.Contains(redacted, "john@example.com") {
		t.Fatal("email should be redacted")
	}
	// SSN should be fully masked.
	if strings.Contains(redacted, "123-45-6789") {
		t.Fatal("SSN should be redacted")
	}
	// AWS key should be replaced.
	if strings.Contains(redacted, "AKIAIOSFODNN7EXAMPLE") {
		t.Fatal("AWS key should be redacted")
	}
}

func TestDocBridge_GetReview(t *testing.T) {
	db := NewDocBridge()
	db.ScanDocument("doc-7", "clean text", "user1")

	r, ok := db.GetReview("doc-7")
	if !ok || r == nil {
		t.Fatal("review not found")
	}
	if r.DocumentID != "doc-7" {
		t.Fatalf("expected doc-7, got %s", r.DocumentID)
	}
}

func TestDocBridge_Stats(t *testing.T) {
	db := NewDocBridge()
	db.ScanDocument("d1", "clean text", "u1")
	db.ScanDocument("d2", "email: a@b.com", "u1")
	db.ScanDocument("d3", "key: AKIAIOSFODNN7EXAMPLE", "u1")

	stats := db.Stats()
	if stats["total"] != 3 {
		t.Fatalf("expected 3 total, got %d", stats["total"])
	}
	if stats["clean"] != 1 {
		t.Fatalf("expected 1 clean, got %d", stats["clean"])
	}
}

// =====================================================
// Phase 3: Approval Engine Tests
// =====================================================

func TestApproval_AutoApprove_Public(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-1", DataPublic)
	if req.Status != string(ApprovalAutoApproved) {
		t.Fatalf("expected auto_approved for PUBLIC, got %s", req.Status)
	}
	if req.ApprovedBy != "system" {
		t.Fatalf("expected approved by system, got %s", req.ApprovedBy)
	}
}

func TestApproval_PendingInternal(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-2", DataInternal)
	if req.Status != string(ApprovalPending) {
		t.Fatalf("expected pending for INTERNAL, got %s", req.Status)
	}
	if req.ExpiresAt.IsZero() {
		t.Fatal("expected non-zero expiry for INTERNAL")
	}
}

func TestApproval_ApproveFlow(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-3", DataConfidential)

	if err := ae.Approve(req.ID, "manager1"); err != nil {
		t.Fatalf("approve: %v", err)
	}

	got, ok := ae.GetRequest(req.ID)
	if !ok {
		t.Fatal("request not found after approval")
	}
	if got.Status != string(ApprovalApproved) {
		t.Fatalf("expected approved, got %s", got.Status)
	}
	if got.ApprovedBy != "manager1" {
		t.Fatalf("expected manager1, got %s", got.ApprovedBy)
	}
}

func TestApproval_DenyFlow(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-4", DataCritical)

	if err := ae.Deny(req.ID, "ciso", "data too sensitive"); err != nil {
		t.Fatalf("deny: %v", err)
	}

	got, _ := ae.GetRequest(req.ID)
	if got.Status != string(ApprovalDenied) {
		t.Fatalf("expected denied, got %s", got.Status)
	}
	if got.Reason != "data too sensitive" {
		t.Fatalf("expected reason, got %q", got.Reason)
	}
}

func TestApproval_DoubleApprove(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-5", DataInternal)
	_ = ae.Approve(req.ID, "mgr")

	err := ae.Approve(req.ID, "mgr2")
	if err == nil {
		t.Fatal("expected error on double approve")
	}
}

func TestApproval_ExpireOverdue(t *testing.T) {
	ae := NewApprovalEngine()
	req := ae.SubmitRequest("user1", "doc-6", DataInternal)

	// Manually set ExpiresAt to the past.
	ae.mu.Lock()
	ae.requests[req.ID].ExpiresAt = time.Now().Add(-1 * time.Hour)
	ae.mu.Unlock()

	expired := ae.ExpireOverdue()
	if expired != 1 {
		t.Fatalf("expected 1 expired, got %d", expired)
	}

	got, _ := ae.GetRequest(req.ID)
	if got.Status != string(ApprovalExpired) {
		t.Fatalf("expected expired, got %s", got.Status)
	}
}

func TestApproval_Stats(t *testing.T) {
	ae := NewApprovalEngine()
	ae.SubmitRequest("u1", "d1", DataPublic)   // auto
	ae.SubmitRequest("u2", "d2", DataInternal)  // pending
	req := ae.SubmitRequest("u3", "d3", DataConfidential) // pending
	_ = ae.Deny(req.ID, "ciso", "no")

	stats := ae.Stats()
	if stats["auto_approved"] != 1 {
		t.Fatalf("expected 1 auto_approved, got %d", stats["auto_approved"])
	}
	if stats["pending"] != 1 {
		t.Fatalf("expected 1 pending, got %d", stats["pending"])
	}
	if stats["denied"] != 1 {
		t.Fatalf("expected 1 denied, got %d", stats["denied"])
	}
}

func TestApproval_Tiers(t *testing.T) {
	ae := NewApprovalEngine()
	tiers := ae.Tiers()
	if len(tiers) != 4 {
		t.Fatalf("expected 4 tiers, got %d", len(tiers))
	}
}

// =====================================================
// Phase 3: Vendor Plugin Stubs
// =====================================================

func TestPlugins_RegisterDefault(t *testing.T) {
	// This constructor-only fixture deliberately uses reserved documentation IPs.
	// Admit them only here; production validation and connection pinning keep
	// rejecting them. No plugin request is dispatched by this test.
	validate := socdomain.ValidateWebhookURL
	socdomain.ValidateWebhookURL = func(raw string) error {
		if strings.HasPrefix(raw, "https://203.0.113.") {
			return nil
		}
		return validate(raw)
	}
	t.Cleanup(func() { socdomain.ValidateWebhookURL = validate })

	reg := NewPluginRegistry()
	RegisterDefaultPlugins(reg)

	// Provide COMPLETE config for each vendor client. The real clients require
	// full credentials (a half-configured plugin must NOT load — it would be a
	// silent non-enforcer), so each entry carries every required field.
	//
	// URLs use literal public IPs from the TEST-NET-3 documentation range
	// (203.0.113.0/24, RFC 5737): the SSRF guard parses them as IPs (no DNS
	// lookup, so the test is fast + hermetic) and are admitted only by this constructor fixture override.
	// Production correctly rejects these reserved addresses. Zscaler is given an explicit base_url for the
	// same reason (otherwise it would derive zsapi.<cloud> and do a DNS lookup).
	cfg := &IntegrationConfig{
		Plugins: []PluginConfig{
			{Type: PluginTypeFirewall, Vendor: "checkpoint", Enabled: true, Config: map[string]interface{}{
				"api_url": "https://203.0.113.10", "api_key": "cp-api-key",
			}},
			{Type: PluginTypeEDR, Vendor: "crowdstrike", Enabled: true, Config: map[string]interface{}{
				"client_id": "test-id", "client_secret": "test-secret", "base_url": "https://203.0.113.11",
			}},
			{Type: PluginTypeProxy, Vendor: "zscaler", Enabled: true, Config: map[string]interface{}{
				"cloud_name": "zscalertwo", "base_url": "https://203.0.113.12/api/v1",
				"api_key": "z-api-key-0123456789", "username": "svc@example.com", "password": "pw",
			}},
		},
	}
	_ = reg.LoadPlugins(cfg)

	if reg.PluginCount() != 3 {
		t.Fatalf("expected 3 plugins, got %d", reg.PluginCount())
	}
}

func TestPlugins_CheckPoint_Vendor(t *testing.T) {
	cp := NewCheckPointEnforcer()
	if cp.Vendor() != "checkpoint" {
		t.Fatalf("expected 'checkpoint', got %s", cp.Vendor())
	}
}

func TestPlugins_CrowdStrike_Vendor(t *testing.T) {
	cs := NewCrowdStrikeController()
	if cs.Vendor() != "crowdstrike" {
		t.Fatalf("expected 'crowdstrike', got %s", cs.Vendor())
	}
}

func TestPlugins_Zscaler_Vendor(t *testing.T) {
	z := NewZscalerGateway()
	if z.Vendor() != "zscaler" {
		t.Fatalf("expected 'zscaler', got %s", z.Vendor())
	}
}

// =====================================================
// Phase 3: Correlation Rules
// =====================================================

func TestCorrelation_RuleCount(t *testing.T) {
	rules := ShadowAICorrelationRules()
	if len(rules) != 9 {
		t.Fatalf("expected 9 correlation rules, got %d", len(rules))
	}
}

func TestCorrelation_RuleIDs(t *testing.T) {
	rules := ShadowAICorrelationRules()
	ids := make(map[string]bool)
	for _, r := range rules {
		if ids[r.ID] {
			t.Fatalf("duplicate rule ID: %s", r.ID)
		}
		ids[r.ID] = true
	}
}

func TestCorrelation_CriticalRules(t *testing.T) {
	rules := ShadowAICorrelationRules()
	critical := 0
	for _, r := range rules {
		if r.Severity == "CRITICAL" {
			critical++
		}
	}
	if critical < 3 {
		t.Fatalf("expected at least 3 CRITICAL rules, got %d", critical)
	}
}

// =====================================================
// Phase 3: Controller Integration (DocBridge + Approval)
// =====================================================

func TestController_ReviewDocument_Clean(t *testing.T) {
	ctrl := NewShadowAIController()
	result, approval := ctrl.ReviewDocument("doc-1", "clean content", "user1")
	if result.Status != DocReviewClean {
		t.Fatalf("expected clean, got %s", result.Status)
	}
	if approval == nil {
		t.Fatal("expected auto-approval for clean doc")
	}
	if approval.Status != string(ApprovalAutoApproved) {
		t.Fatalf("expected auto_approved, got %s", approval.Status)
	}
}

func TestController_ReviewDocument_WithPII(t *testing.T) {
	ctrl := NewShadowAIController()
	result, approval := ctrl.ReviewDocument("doc-2", "Contact: alice@corp.com", "user1")
	if result.Status != DocReviewRedacted {
		t.Fatalf("expected redacted, got %s", result.Status)
	}
	if approval == nil {
		t.Fatal("expected approval request for PII")
	}
	if approval.Status != string(ApprovalPending) {
		t.Fatalf("expected pending, got %s", approval.Status)
	}
}

func TestController_ReviewDocument_WithSecrets(t *testing.T) {
	ctrl := NewShadowAIController()
	result, approval := ctrl.ReviewDocument("doc-3", "key: AKIAIOSFODNN7EXAMPLE", "user1")
	if result.Status != DocReviewBlocked {
		t.Fatalf("expected blocked, got %s", result.Status)
	}
	// Should NOT create approval for blocked docs.
	if approval != nil {
		t.Fatal("blocked docs should not create approval")
	}
}

