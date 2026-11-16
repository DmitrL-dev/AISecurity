package shadow_ai

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// ShadowAIController is the main orchestrator that ties together
// detection, enforcement, SOC event emission, and statistics.
type ShadowAIController struct {
	mu            sync.RWMutex
	registry      *PluginRegistry
	fallback      *FallbackManager
	healthChecker *HealthChecker
	netDetector   *NetworkDetector
	behavioral    *BehavioralDetector
	docBridge     *DocBridge
	approval      *ApprovalEngine
	events        []ShadowAIEvent // In-memory event store (bounded)
	maxEvents     int
	socEventFn    func(source, severity, category, description string, meta map[string]string) // Bridge to SOC event bus
	logger        *slog.Logger
}

// NewShadowAIController creates the main Shadow AI Control orchestrator.
func NewShadowAIController() *ShadowAIController {
	registry := NewPluginRegistry()
	RegisterDefaultPlugins(registry)
	return &ShadowAIController{
		registry:    registry,
		fallback:    NewFallbackManager(registry, "detect_only"),
		netDetector: NewNetworkDetector(),
		behavioral:  NewBehavioralDetector(100),
		docBridge:   NewDocBridge(),
		approval:    NewApprovalEngine(),
		events:      make([]ShadowAIEvent, 0, 1000),
		maxEvents:   10000,
		logger:      slog.Default().With("component", "shadow-ai-controller"),
	}
}

// SetSOCEventEmitter sets the function used to emit events into the SOC pipeline.
func (c *ShadowAIController) SetSOCEventEmitter(fn func(source, severity, category, description string, meta map[string]string)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.socEventFn = fn
}

// Configure loads plugin configuration and initializes the integration layer.
func (c *ShadowAIController) Configure(config *IntegrationConfig) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.registry.LoadPlugins(config); err != nil {
		return fmt.Errorf("failed to load plugins: %w", err)
	}

	c.fallback = NewFallbackManager(c.registry, config.FallbackStrategy)
	c.fallback.SetEventLogger(func(event ShadowAIEvent) {
		c.recordEvent(event)
	})

	interval := config.HealthCheckInterval
	if interval <= 0 {
		interval = 30 * time.Second
	}
	c.healthChecker = NewHealthChecker(c.registry, interval, func(vendor string, status PluginStatus, msg string) {
		c.emitSOCEvent("HIGH", "integration_health", msg, map[string]string{
			"vendor": vendor,
			"status": string(status),
		})
	})

	return nil
}

// StartHealthChecker starts continuous plugin health monitoring.
func (c *ShadowAIController) StartHealthChecker(ctx context.Context) {
	if c.healthChecker != nil {
		go c.healthChecker.Start(ctx)
	}
}

// ProcessNetworkEvent analyzes a network event and enforces policy.
func (c *ShadowAIController) ProcessNetworkEvent(ctx context.Context, event NetworkEvent) *ShadowAIEvent {
	detected := c.netDetector.Analyze(event)
	if detected == nil {
		return nil
	}

	// Record behavioral data.
	c.behavioral.RecordAccess(event.User, event.Destination, event.DataSize)

	// Attempt to block.
	enforcedBy, err := c.fallback.BlockDomain(ctx, event.Destination, fmt.Sprintf("Shadow AI: %s", detected.AIService))
	if err != nil {
		c.logger.Error("enforcement failed", "destination", event.Destination, "error", err)
	}

	if enforcedBy != "" {
		detected.Action = "blocked"
		detected.EnforcedBy = enforcedBy
	} else {
		detected.Action = "detected"
	}

	detected.ID = genEventID()
	c.recordEvent(*detected)

	// Emit to SOC event bus.
	c.emitSOCEvent("HIGH", "shadow_ai_usage",
		fmt.Sprintf("Shadow AI access detected: %s → %s", event.User, detected.AIService),
		map[string]string{
			"user":        event.User,
			"hostname":    event.Hostname,
			"destination": event.Destination,
			"ai_service":  detected.AIService,
			"action":      detected.Action,
			"enforced_by": detected.EnforcedBy,
		},
	)

	return detected
}

// ScanContent scans text content for AI API keys and prompt injections.
func (c *ShadowAIController) ScanContent(content string) (string, bool) {
	keyType := c.netDetector.SignatureDB().ScanForAPIKeys(content)
	isInjected := c.netDetector.SignatureDB().ScanForInjection(content)
	return keyType, isInjected
}

// ManualBlock manually blocks a domain or IP.
func (c *ShadowAIController) ManualBlock(ctx context.Context, req BlockRequest) error {
	var enforcedBy string
	var err error
	switch req.TargetType {
	case "domain":
		enforcedBy, err = c.fallback.BlockDomain(ctx, req.Target, req.Reason)
	case "ip":
		enforcedBy, err = c.fallback.BlockIP(ctx, req.Target, req.Duration, req.Reason)
	case "host":
		enforcedBy, err = c.fallback.IsolateHost(ctx, req.Target)
	default:
		return fmt.Errorf("unsupported target type: %s", req.TargetType)
	}
	if err != nil {
		return err
	}
	if enforcedBy == "" {
		return fmt.Errorf("manual containment unavailable: detection only")
	}
	return nil

}

// GetStats returns aggregate shadow AI statistics.
func (c *ShadowAIController) GetStats(timeRange string) ShadowAIStats {
	c.mu.RLock()
	defer c.mu.RUnlock()

	cutoff := parseCutoff(timeRange)
	stats := ShadowAIStats{
		TimeRange:    timeRange,
		ByService:    make(map[string]int),
		ByDepartment: make(map[string]int),
	}

	violatorMap := make(map[string]int)

	for _, e := range c.events {
		if e.Timestamp.Before(cutoff) {
			continue
		}
		stats.Total++
		switch e.Action {
		case "blocked":
			stats.Blocked++
		case "allowed", "approved":
			stats.Approved++
		case "pending":
			stats.Pending++
		}
		if e.AIService != "" {
			stats.ByService[e.AIService]++
		}
		if dept, ok := e.Metadata["department"]; ok {
			stats.ByDepartment[dept]++
		}
		if e.UserID != "" {
			violatorMap[e.UserID]++
		}
	}

	// Build top violators list (sorted desc).
	for uid, count := range violatorMap {
		stats.TopViolators = append(stats.TopViolators, Violator{UserID: uid, Attempts: count})
	}
	// Sort by attempts descending, limit to 10.
	for i := 0; i < len(stats.TopViolators); i++ {
		for j := i + 1; j < len(stats.TopViolators); j++ {
			if stats.TopViolators[j].Attempts > stats.TopViolators[i].Attempts {
				stats.TopViolators[i], stats.TopViolators[j] = stats.TopViolators[j], stats.TopViolators[i]
			}
		}
	}
	if len(stats.TopViolators) > 10 {
		stats.TopViolators = stats.TopViolators[:10]
	}

	return stats
}

// GetEvents returns recent shadow AI events (newest first).
func (c *ShadowAIController) GetEvents(limit int) []ShadowAIEvent {
	c.mu.RLock()
	defer c.mu.RUnlock()

	total := len(c.events)
	if total == 0 || limit <= 0 {
		// limit <= 0 guard: make([]ShadowAIEvent, 0, limit) panics on a
		// negative cap. A non-positive limit requests no events → return nil.
		return nil
	}
	start := total - limit
	if start < 0 {
		start = 0
	}

	// Return newest first.
	result := make([]ShadowAIEvent, 0, limit)
	for i := total - 1; i >= start; i-- {
		result = append(result, c.events[i])
	}
	return result
}

// GetEvent returns a single event by ID.
func (c *ShadowAIController) GetEvent(id string) (*ShadowAIEvent, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	for i := len(c.events) - 1; i >= 0; i-- {
		if c.events[i].ID == id {
			cp := c.events[i]
			return &cp, true
		}
	}
	return nil, false
}

// IntegrationHealth returns health status of all plugins.
func (c *ShadowAIController) IntegrationHealth() []PluginHealth {
	return c.registry.AllHealth()
}

// VendorHealth returns health for a specific vendor.
func (c *ShadowAIController) VendorHealth(vendor string) (*PluginHealth, bool) {
	return c.registry.GetHealth(vendor)
}

// Registry returns the plugin registry for direct access.
func (c *ShadowAIController) Registry() *PluginRegistry {
	return c.registry
}

// NetworkDetector returns the network detector for configuration.
func (c *ShadowAIController) NetworkDetector() *NetworkDetector {
	return c.netDetector
}

// BehavioralDetector returns the behavioral detector.
func (c *ShadowAIController) BehavioralDetector() *BehavioralDetector {
	return c.behavioral
}

// DocBridge returns the document review bridge.
func (c *ShadowAIController) DocBridge() *DocBridge {
	return c.docBridge
}

// ApprovalEngine returns the approval workflow engine.
func (c *ShadowAIController) ApprovalEngine() *ApprovalEngine {
	return c.approval
}

// ReviewDocument scans a document and creates an approval request if needed.
func (c *ShadowAIController) ReviewDocument(docID, content, userID string) (*ScanResult, *ApprovalRequest) {
	result := c.docBridge.ScanDocument(docID, content, userID)

	// Create approval request based on data classification.
	var req *ApprovalRequest
	if result.Status != DocReviewBlocked {
		req = c.approval.SubmitRequest(userID, docID, result.DataClass)
	}

	// Emit SOC event for tracking.
	c.emitSOCEvent("MEDIUM", "shadow_ai_usage",
		fmt.Sprintf("Document review: %s by %s — %s (%s)",
			docID, userID, result.Status, result.DataClass),
		map[string]string{
			"user":       userID,
			"doc_id":     docID,
			"status":     string(result.Status),
			"data_class": string(result.DataClass),
			"pii_count":  fmt.Sprintf("%d", len(result.PIIFound)),
		},
	)

	return result, req
}

// GenerateComplianceReport generates a compliance report for the given period.
//
// AuditComplete is an HONEST signal, not a hardcoded true: the audit trail is
// only "complete" when detections are actually forwarded into the SOC event
// pipeline (the auditable, tamper-evident decision log). If no SOC event emitter
// is wired, detections are recorded only in this process's in-memory store and
// never reach the audit chain — so the report must say audit is NOT complete.
func (c *ShadowAIController) GenerateComplianceReport(period string) ComplianceReport {
	stats := c.GetStats(period)
	docStats := c.docBridge.Stats()

	c.mu.RLock()
	auditWired := c.socEventFn != nil
	c.mu.RUnlock()

	return ComplianceReport{
		GeneratedAt:       time.Now(),
		Period:            period,
		TotalInteractions: stats.Total,
		BlockedAttempts:   stats.Blocked,
		ApprovedReviews:   stats.Approved,
		PIIDetected:       docStats["redacted"] + docStats["blocked"],
		SecretsDetected:   docStats["blocked"],
		AuditComplete:     auditWired,
		Regulations:       []string{"GDPR", "SOC2", "EU AI Act Article 15"},
	}
}

// --- Internal helpers ---

func (c *ShadowAIController) recordEvent(event ShadowAIEvent) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.events = append(c.events, event)

	// Evict oldest events if over capacity.
	if len(c.events) > c.maxEvents {
		excess := len(c.events) - c.maxEvents
		c.events = c.events[excess:]
	}
}

func (c *ShadowAIController) emitSOCEvent(severity, category, description string, meta map[string]string) {
	c.mu.RLock()
	fn := c.socEventFn
	c.mu.RUnlock()

	if fn != nil {
		fn("shadow-ai", severity, category, description, meta)
	}
}

func parseCutoff(timeRange string) time.Time {
	switch timeRange {
	case "1h":
		return time.Now().Add(-1 * time.Hour)
	case "24h":
		return time.Now().Add(-24 * time.Hour)
	case "7d":
		return time.Now().Add(-7 * 24 * time.Hour)
	case "30d":
		return time.Now().Add(-30 * 24 * time.Hour)
	case "90d":
		return time.Now().Add(-90 * 24 * time.Hour)
	default:
		return time.Now().Add(-24 * time.Hour)
	}
}

var eventCounter uint64
var eventCounterMu sync.Mutex

func genEventID() string {
	eventCounterMu.Lock()
	eventCounter++
	id := eventCounter
	eventCounterMu.Unlock()
	return fmt.Sprintf("sai-%d-%d", time.Now().UnixMilli(), id)
}
