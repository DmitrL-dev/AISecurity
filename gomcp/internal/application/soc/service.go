// Package soc provides application services for the SENTINEL AI SOC subsystem.
package soc

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/domain/oracle"
	"github.com/syntrex/gomcp/internal/domain/peer"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
)

const (
	// MaxEventsPerSecondPerSensor limits event ingest rate per sensor (§17.3).
	MaxEventsPerSecondPerSensor = 100

	// MaxSensors caps the in-memory sensor inventory (auto-discovery AND explicit
	// registration), bounding memory + the persisted sensors table against a
	// unique-SensorID flood (Review 14.06 round-5).
	MaxSensors = 10000
)

// Service orchestrates the SOC event pipeline:
// Step 0: Secret Scanner (INVARIANT) → DIP → Decision Logger → Persist → Correlation.
type Service struct {
	mu               sync.RWMutex
	repo             domsoc.SOCRepository
	logger           *audit.DecisionLogger
	rules            []domsoc.SOCCorrelationRule
	playbookEngine   *domsoc.PlaybookEngine
	executorRegistry *domsoc.ExecutorRegistry
	sensors          map[string]*domsoc.Sensor
	draining         bool // §15.7: graceful shutdown mode — rejects new events

	// Alert Clustering engine (§7.6): groups related alerts.
	clusterEngine *domsoc.ClusterEngine

	// Event bus for real-time SSE streaming.
	eventBus *domsoc.EventBus

	// Rate limiting per sensor (§17.3): sensorID → timestamps of recent events.
	sensorRates       map[string][]time.Time
	rateLimitDisabled bool

	// Sensor authentication (§17.3 T-01): sensorID → pre-shared key.
	sensorKeys map[string]string

	// Sensor→tenant binding (Review 14.06 round-4): sensorID → owning tenant.
	// Lets external-ingest events be attributed to the authenticated sensor's
	// tenant so alert clustering / correlation partition per tenant instead of
	// co-mingling every sensor's events under the empty tenant.
	sensorTenants map[string]string

	// SOAR webhook notifier (§P3): outbound HTTP POST on incidents.
	webhook *WebhookNotifier

	// Threat intelligence store (§P3+): IOC enrichment.
	threatIntel *ThreatIntelStore

	// Zero-G Mode (§13.4): manual approval workflow.
	zeroG *domsoc.ZeroGMode

	// P2P SOC Sync (§14): multi-site event synchronization.
	p2pSync *domsoc.P2PSyncService

	// Anomaly detection engine (§5): statistical baseline + Z-score.
	anomaly *domsoc.AnomalyDetector

	// Threat Intelligence IOC engine (§6): real-time IOC matching.
	threatIntelEngine *domsoc.ThreatIntelEngine

	// Data Retention Policy (§19): configurable lifecycle management.
	retention *domsoc.DataRetentionPolicy

	// P-1 FIX: In-memory sliding window for correlation (avoids DB query per ingest).
	// Keyed by TenantID and capped per-tenant (§7, Review 14.06 round-3) so one
	// tenant's volume cannot evict or co-mingle with another's events.
	recentEvents map[string][]domsoc.SOCEvent

	// Scan semaphore (§20.1): limits concurrent ingest processing to prevent OOM.
	// Non-blocking acquire → returns ErrCapacityFull if all slots in use.
	scanSemaphore chan struct{}

	// SOC-plane self-observability (IMP7): records the pipeline's own health
	// (events/incidents/playbook outcomes/correlation latency) for Prometheus.
	metrics *domsoc.SOCMetrics
}

// SOARConfig carries the runtime endpoints + firewall backend for the SOAR
// action executors. It is applied at construction (honest defaults: log-only
// firewall, empty webhook URLs that degrade to logging) and can be re-applied
// at boot via ConfigureSOAR once env config is read in cmd/soc.
type SOARConfig struct {
	// Firewall selects the block_ip enforcement backend (log-only by default).
	Firewall domsoc.FirewallConfig
	// NotifyURL is the default Slack/Telegram/webhook URL for the notify action.
	NotifyURL string
	// EscalateURL is the PagerDuty/webhook URL for the escalate action.
	EscalateURL string
	// WebhookURL is the destination for the generic webhook action (pb-c2-killchain
	// action #3). Empty → the webhook executor is still registered but every send
	// fails honestly (executor returns an error, recorded partial_failure).
	WebhookURL string
	// WebhookHeaders are optional headers (e.g. auth) sent with the webhook action.
	WebhookHeaders map[string]string
}

// BuildSOARRegistry constructs the full set of SOAR action executors from cfg.
// It is THE single source of truth for which executors exist, shared by
// NewService/ConfigureSOAR (in-process server) and cmd/soc-respond (the isolated
// SEC-001 responder) so both deployment topologies stay in lockstep — including
// the previously-missing "webhook" executor (audit #26). Honest defaults: a
// log-only firewall (block_ip reports NOT enforced) and empty notify/escalate/
// webhook URLs (degrade to logging) when cfg leaves them unset.
func BuildSOARRegistry(cfg SOARConfig) *domsoc.ExecutorRegistry {
	reg := domsoc.NewExecutorRegistry() // registers the default "log" executor
	reg.Register(domsoc.NewBlockIPExecutor(domsoc.NewFirewall(cfg.Firewall)))
	reg.Register(domsoc.NewNotifyExecutor(cfg.NotifyURL))
	reg.Register(domsoc.NewQuarantineExecutor())
	reg.Register(domsoc.NewEscalateExecutor(cfg.EscalateURL))
	reg.Register(domsoc.NewWebhookExecutor(cfg.WebhookURL, cfg.WebhookHeaders))
	return reg
}

// NewService creates a SOC service with persistence and decision logging.
func NewService(repo domsoc.SOCRepository, logger *audit.DecisionLogger) *Service {
	// Build executor registry with all SOAR action handlers. Honest defaults:
	// log-only firewall (block_ip reports NOT enforced until SOC_FIREWALL_BACKEND
	// is set) and empty notify/escalate/webhook URLs (degrade to logging). Real
	// endpoints are wired at boot via ConfigureSOAR in cmd/soc.
	reg := BuildSOARRegistry(SOARConfig{})

	// SOC self-observability registry (IMP7) — created first so the playbook
	// handler can record block_ip enforcement outcomes at the source.
	metrics := domsoc.NewSOCMetrics()

	// Create playbook engine with live executor handler (not just logging)
	pe := domsoc.NewPlaybookEngine()
	pe.SetHandler(&domsoc.ExecutorActionHandler{Registry: reg, Metrics: metrics})

	slog.Info("SOAR engine initialized",
		"executors", reg.List(),
		"playbooks", len(pe.ListPlaybooks()),
		"block_ip", "log-only (set SOC_FIREWALL_BACKEND to enforce)",
	)

	return &Service{
		repo:              repo,
		logger:            logger,
		rules:             domsoc.DefaultSOCCorrelationRules(),
		playbookEngine:    pe,
		executorRegistry:  reg,
		sensors:           make(map[string]*domsoc.Sensor),
		clusterEngine:     domsoc.NewClusterEngine(domsoc.DefaultClusterConfig()),
		eventBus:          domsoc.NewEventBus(256),
		sensorRates:       make(map[string][]time.Time),
		zeroG:             domsoc.NewZeroGMode(),
		p2pSync:           domsoc.NewP2PSyncService(),
		anomaly:           domsoc.NewAnomalyDetector(),
		threatIntelEngine: domsoc.NewThreatIntelEngine(),
		retention:         domsoc.NewDataRetentionPolicy(),
		scanSemaphore:     make(chan struct{}, 8), // §20.1: max 8 concurrent scans
		metrics:           metrics,
	}
}

// ConfigureSOAR rebuilds the executor registry with real endpoints + firewall
// backend and re-points the playbook handler at it. This is the single coherent
// entry point that supersedes the never-implemented SetNotifyURL/SetEscalateURL
// idea (audit: those setters were referenced in comments but never existed, so
// notify/escalate always ran with an empty URL). Call it once at boot after env
// config is read. Logs which executors are live vs honest-degraded.
func (s *Service) ConfigureSOAR(cfg SOARConfig) {
	reg := BuildSOARRegistry(cfg)

	s.mu.Lock()
	s.executorRegistry = reg
	s.mu.Unlock()

	// SetHandler takes the engine's own lock; call it outside s.mu.
	// Re-attach the metrics registry so block_ip enforcement outcomes keep being
	// recorded after a SOAR reconfigure (IMP7).
	s.playbookEngine.SetHandler(&domsoc.ExecutorActionHandler{Registry: reg, Metrics: s.metrics})

	fwBackend := cfg.Firewall.Backend
	if fwBackend == "" {
		fwBackend = "none/log-only"
	}
	slog.Info("SOAR reconfigured",
		"executors", reg.List(),
		"firewall_backend", fwBackend,
		"block_ip_enforces", isEnforcingFirewall(cfg.Firewall.Backend),
		"notify_live", cfg.NotifyURL != "",
		"escalate_live", cfg.EscalateURL != "",
		"webhook_live", cfg.WebhookURL != "",
	)
}

// isEnforcingFirewall reports whether the configured backend can actually drop
// packets (used only for the honest startup log).
func isEnforcingFirewall(backend string) bool {
	switch strings.ToLower(strings.TrimSpace(backend)) {
	case "nft", "nftables", "iptables", "ipt", "http", "https", "cloud", "webhook":
		return true
	default:
		return false
	}
}

// Repo returns the underlying SOC repository (used for demo seed injection).
func (s *Service) Repo() domsoc.SOCRepository {
	return s.repo
}

// AddCustomRules appends YAML-loaded custom correlation rules (§7.5).
func (s *Service) AddCustomRules(rules []domsoc.SOCCorrelationRule) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rules = append(s.rules, rules...)
}

// ClusterStats returns Alert Clustering engine statistics (§7.6).
func (s *Service) ClusterStats() map[string]any {
	if s.clusterEngine == nil {
		return map[string]any{"enabled": false}
	}
	stats := s.clusterEngine.Stats()
	stats["enabled"] = true
	return stats
}

// SetSensorKeys configures pre-shared keys for sensor authentication (§17.3 T-01).
// If keys is nil or empty, authentication is disabled (all events accepted).
func (s *Service) SetSensorKeys(keys map[string]string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sensorKeys = keys
}

// SetSensorTenants configures the sensorID→tenant binding (Review 14.06 round-4).
// When set, an authenticated sensor's events that carry no TenantID are
// attributed to its tenant in ingestEvent. nil/empty leaves events untenanted
// (the prior default).
func (s *Service) SetSensorTenants(tenants map[string]string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sensorTenants = tenants
}

// ParseSensorKeys parses the SOC_SENSOR_KEYS env value into a sensorID→key map.
// Format: "sensorID:key[:tenantID],id2:key2[:tenant2]". Review 13.06 (audit A4):
// lets operators ENFORCE sensor authentication on /api/v1/soc/events ingest (the
// route is JWT-exempt by design for sensors). Empty input → nil = keyless (the
// current default), so this is opt-in and non-breaking; malformed pairs are
// skipped. The optional 3rd field (tenant) is parsed by ParseSensorTenants.
func ParseSensorKeys(env string) map[string]string {
	env = strings.TrimSpace(env)
	if env == "" {
		return nil
	}
	keys := make(map[string]string)
	for _, pair := range strings.Split(env, ",") {
		pair = strings.TrimSpace(pair)
		// SplitN into at most 3 so an "id:key:tenant" triple keeps the key intact
		// (a plain IndexByte would fold ":tenant" into the key).
		parts := strings.SplitN(pair, ":", 3)
		if len(parts) < 2 {
			continue // no key
		}
		id := strings.TrimSpace(parts[0])
		key := strings.TrimSpace(parts[1])
		if id != "" && key != "" {
			keys[id] = key
		}
	}
	return keys
}

// ParseSensorTenants extracts the optional sensorID→tenantID binding from the
// SAME SOC_SENSOR_KEYS value ("sensorID:key:tenantID"). Pairs without a 3rd
// field are omitted (no binding). Review 14.06 round-4: without this, external
// sensor-ingest events were never tenant-stamped, so every tenant's sensor
// events co-mingled (TenantID==""==""=true) in alert clusters and correlation.
func ParseSensorTenants(env string) map[string]string {
	env = strings.TrimSpace(env)
	if env == "" {
		return nil
	}
	tenants := make(map[string]string)
	for _, pair := range strings.Split(env, ",") {
		pair = strings.TrimSpace(pair)
		parts := strings.SplitN(pair, ":", 3)
		if len(parts) < 3 {
			continue // no tenant field
		}
		id := strings.TrimSpace(parts[0])
		tenant := strings.TrimSpace(parts[2])
		if id != "" && tenant != "" {
			tenants[id] = tenant
		}
	}
	if len(tenants) == 0 {
		return nil
	}
	return tenants
}

// SetWebhookConfig configures SOAR webhook notifications.
// If config has no endpoints, webhooks are disabled.
func (s *Service) SetWebhookConfig(config WebhookConfig) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.webhook = NewWebhookNotifier(config)
}

// SetThreatIntel configures the threat intelligence store for IOC enrichment.
func (s *Service) SetThreatIntel(store *ThreatIntelStore) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.threatIntel = store
}

// WebhookStats returns SOAR webhook delivery statistics (T3-5).
func (s *Service) WebhookStats() map[string]any {
	s.mu.RLock()
	wh := s.webhook
	s.mu.RUnlock()

	if wh == nil {
		return map[string]any{
			"enabled": false,
			"sent":    0,
			"failed":  0,
		}
	}
	sent, failed := wh.Stats()
	return map[string]any{
		"enabled": true,
		"sent":    sent,
		"failed":  failed,
	}
}

// GetWebhookConfig returns current webhook configuration.
func (s *Service) GetWebhookConfig() *WebhookConfig {
	s.mu.RLock()
	wh := s.webhook
	s.mu.RUnlock()
	if wh == nil {
		return nil
	}
	wh.mu.RLock()
	defer wh.mu.RUnlock()
	config := wh.config
	config.Endpoints = append([]string(nil), config.Endpoints...)
	config.Headers = nil
	return &config
}

// TestWebhook sends a test ping to all configured webhook endpoints.
func (s *Service) TestWebhook() []WebhookResult {
	s.mu.RLock()
	wh := s.webhook
	s.mu.RUnlock()
	if wh == nil || !wh.enabled {
		return nil
	}

	testIncident := &domsoc.Incident{
		ID:       "TEST-PING",
		Title:    "Webhook Test — SYNTREX SOC",
		Severity: domsoc.SeverityInfo,
		Status:   domsoc.StatusOpen,
	}
	return wh.NotifyIncident("webhook_test", testIncident)
}

// Drain puts the service into drain mode (§15.7 Stage 1).
// New events are rejected with ErrDraining; existing processing continues.
func (s *Service) Drain() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.draining = true
	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "DRAIN:ACTIVATED", "Zero-downtime update: ingest paused")
	}
}

// Resume exits drain mode, re-enabling event ingestion.
func (s *Service) Resume() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.draining = false
	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "DRAIN:DEACTIVATED", "Event ingestion resumed")
	}
}

// IsDraining returns true if the service is in drain mode.
func (s *Service) IsDraining() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.draining
}

// StartRetentionScheduler runs a background goroutine that periodically
// purges expired events and incidents (§19 Data Retention).
// Default interval: 1 hour. Stops when ctx is cancelled.
func (s *Service) StartRetentionScheduler(ctx context.Context, interval time.Duration) {
	if interval == 0 {
		interval = time.Hour
	}
	go func() {
		slog.Info("retention scheduler started", "interval", interval.String())
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				slog.Info("retention scheduler stopped")
				return
			case <-ticker.C:
				s.runRetentionPurge()
			}
		}
	}()
}

// runRetentionPurge executes one cycle of retention enforcement.
// A-3 FIX: Uses configurable retention durations instead of hardcoded defaults.
func (s *Service) runRetentionPurge() {
	evtDays := 90
	incDays := 365
	if s.retention != nil {
		if r, ok := s.retention.GetPolicy("events"); ok && r.RetainDays > 0 {
			evtDays = r.RetainDays
		}
		if r, ok := s.retention.GetPolicy("incidents"); ok && r.RetainDays > 0 {
			incDays = r.RetainDays
		}
	}

	evtCount, evtErr := s.repo.PurgeExpiredEvents(evtDays)
	incCount, incErr := s.repo.PurgeExpiredIncidents(incDays)
	// Safety purges (Review 14.06 round-5): a hard max-age for incidents that
	// never reached RESOLVED (PurgeExpiredIncidents only removes resolved ones, so
	// open/investigating incidents grew unbounded), and sensors not seen within
	// the stale window (sensor rows — incl. per-tenant "gateway:<tenant>" — were
	// never purged). Both close unbounded-growth + GDPR-residual gaps.
	staleIncCount, staleIncErr := s.repo.PurgeStaleIncidents(incDays * 2)
	staleSensorCount, staleSensorErr := s.repo.PurgeStaleSensors(sensorStaleDays)

	if evtErr != nil {
		slog.Error("retention purge: events", "error", evtErr)
	}
	if incErr != nil {
		slog.Error("retention purge: incidents", "error", incErr)
	}
	if staleIncErr != nil {
		slog.Error("retention purge: stale incidents", "error", staleIncErr)
	}
	if staleSensorErr != nil {
		slog.Error("retention purge: stale sensors", "error", staleSensorErr)
	}

	totalInc := incCount + staleIncCount
	if evtCount > 0 || totalInc > 0 || staleSensorCount > 0 {
		slog.Info("retention purge completed",
			"events_purged", evtCount,
			"incidents_purged", totalInc,
			"sensors_purged", staleSensorCount,
		)
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC, "RETENTION:PURGE",
				fmt.Sprintf("Purged %d events, %d incidents, %d sensors", evtCount, totalInc, staleSensorCount))
		}
	}
}

// sensorStaleDays: a sensor silent this long is treated as dead and purged.
const sensorStaleDays = 90

// EraseTenant fulfils a GDPR Art.17 right-to-erasure request for one tenant: it
// deletes ALL persisted SOC data (events/incidents/sensors) AND clears the
// tenant's in-memory state (correlation window, sensors, alert clusters), then
// records a TENANT_ERASED completion entry — counts only, no raw PII — as the
// compliance artifact. Idempotent; refuses an empty tenantID so it can never run
// store-wide. (The append-only decision/incident chains are RETAINED under GDPR
// Art.17(3) as a security record and carry no raw PII by design.)
func (s *Service) EraseTenant(tenantID string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("erase tenant: empty tenant_id refused")
	}

	rows, err := s.repo.DeleteByTenant(tenantID)
	if err != nil {
		return 0, fmt.Errorf("erase tenant: %w", err)
	}

	// Drop the tenant's in-memory state so nothing survives in RAM.
	s.mu.Lock()
	delete(s.recentEvents, tenantID)
	for id, sensor := range s.sensors {
		if sensor.TenantID == tenantID {
			delete(s.sensors, id)
		}
	}
	s.mu.Unlock()
	if s.clusterEngine != nil {
		s.clusterEngine.DeleteByTenant(tenantID)
	}

	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "TENANT_ERASED",
			fmt.Sprintf("tenant=%s rows_deleted=%d", tenantID, rows))
	}
	slog.Info("tenant SOC data erased (GDPR Art.17)", "tenant", tenantID, "rows_deleted", rows)
	return rows, nil
}

// IngestEvent processes an incoming security event through the SOC pipeline.
// Returns the event ID and any incident created by correlation.
//
// Pipeline (§5.2):
//
//	Step -1: Sensor Authentication — pre-shared key validation (§17.3 T-01)
//	Step 0: Secret Scanner — INVARIANT, cannot be disabled (§5.4)
//	Step 0.5: Rate Limiting — per sensor ≤100 events/sec (§17.3)
//	Step 1: Decision Logger — SHA-256 chain with Zero-G tagging (§5.6, §13.4)
//	Step 2: Persist event to SQLite
//	Step 3: Update sensor registry (§11.3)
//	Step 4: Run correlation engine (§7)
//	Step 5: Apply playbooks (§10)
func (s *Service) IngestEvent(event domsoc.SOCEvent) (string, *domsoc.Incident, error) {
	return s.ingestEvent(event, false)
}

// IngestInternalEvent processes a TRUSTED in-process event (e.g. the gateway scan
// path auto-feeding a tenant's SOC). It skips sensor-PSK authentication — which
// exists to authenticate EXTERNAL sensors over the network — while every other
// pipeline step (validate, secret-scan, rate-limit, dedup, persist, correlate,
// playbooks) runs identically. The caller is responsible for setting TenantID.
func (s *Service) IngestInternalEvent(event domsoc.SOCEvent) (string, *domsoc.Incident, error) {
	return s.ingestEvent(event, true)
}

// ingestEvent runs the SOC ingest pipeline; trusted=true bypasses sensor auth.
func (s *Service) ingestEvent(event domsoc.SOCEvent, trusted bool) (string, *domsoc.Incident, error) {
	// Step -3: Drain guard (§15.7)
	if s.IsDraining() {
		return "", nil, domsoc.ErrDraining
	}

	// Step -2: Input Validation
	if err := event.Validate(); err != nil {
		return "", nil, err
	}

	// Step -1: Sensor Authentication (§17.3 T-01)
	// S-1 FIX: When sensor keys are configured, ALL events must authenticate.
	// Events without SensorID are rejected (prevents auth bypass via empty SensorID).
	if !trusted {
		if err := s.authenticateSensor(event.SensorID, event.SensorKey); err != nil {
			return "", nil, err
		}
		// Attribute the event to the authenticated sensor's tenant when the caller
		// supplied none (Review 14.06 round-4). External sensor ingest never set
		// TenantID, so all tenants' events co-mingled (""=="") in alert clusters
		// and correlation. With a sensorID→tenant binding provisioned, stamp it
		// here — the single chokepoint before dedup/persist/cluster/correlate —
		// so they all partition per tenant. Unprovisioned sensors stay untenanted
		// (unchanged behavior).
		if event.TenantID == "" {
			s.mu.RLock()
			tenant := s.sensorTenants[event.SensorID]
			s.mu.RUnlock()
			if tenant != "" {
				event.TenantID = tenant
			}
		}
	}

	// S-2 FIX: Clear sensitive key material after auth check.
	event.SensorKey = ""

	// Step 0: Secret Scanner — INVARIANT (§5.4)
	// always_active: true, cannot_disable: true
	if event.Payload != "" {
		scanResult := oracle.ScanForSecrets(event.Payload)
		if scanResult.HasSecrets {
			if s.logger != nil {
				s.logger.Record(audit.ModuleSOC,
					"SECRET_DETECTED:REJECT",
					fmt.Sprintf("source=%s event_id=%s detections=%s",
						event.Source, event.ID, strings.Join(scanResult.Detections, "; ")))
			}
			s.metrics.RecordRejectedEvent()
			return "", nil, fmt.Errorf("%w: %d detections found", domsoc.ErrSecretDetected, len(scanResult.Detections))
		}
	}

	// Step 0.5: Rate Limiting per sensor (§17.3 T-02 DoS Protection)
	sensorID := event.SensorID
	if sensorID == "" {
		sensorID = string(event.Source)
	}
	if s.isRateLimited(sensorID) {
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC,
				"RATE_LIMIT_EXCEEDED:REJECT",
				fmt.Sprintf("sensor=%s limit=%d/sec", sensorID, MaxEventsPerSecondPerSensor))
		}
		s.metrics.RecordRejectedEvent()
		return "", nil, fmt.Errorf("%w: sensor %s (max %d events/sec)", domsoc.ErrRateLimited, sensorID, MaxEventsPerSecondPerSensor)
	}

	// Step 0.6: Scan semaphore — backpressure guard (§20.1)
	select {
	case s.scanSemaphore <- struct{}{}:
		defer func() { <-s.scanSemaphore }()
	default:
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC,
				"CAPACITY_FULL:REJECT",
				fmt.Sprintf("concurrent_scans=%d", cap(s.scanSemaphore)))
		}
		s.metrics.RecordRejectedEvent()
		return "", nil, fmt.Errorf("%w: max %d concurrent scans", domsoc.ErrCapacityFull, cap(s.scanSemaphore))
	}

	// Step 1: Log decision with Zero-G tagging (§13.4)
	if s.logger != nil {
		zeroGTag := ""
		if event.ZeroGMode {
			zeroGTag = " zero_g_mode=true"
		}
		if err := s.logger.Record(audit.ModuleSOC,
			fmt.Sprintf("INGEST:%s", event.Verdict),
			fmt.Sprintf("source=%s category=%s severity=%s confidence=%.2f%s",
				event.Source, event.Category, event.Severity, event.Confidence, zeroGTag)); err != nil {
			return "", nil, ErrDecisionAuditUnavailable
		}
	}

	// Step 1.5: Content deduplication (§5.2 step 2)
	event.ComputeContentHash()
	if event.ContentHash != "" {
		exists, err := s.repo.EventExistsByHash(event.TenantID, event.ContentHash)
		if err != nil {
			slog.Warn("dedup check failed, proceeding", "error", err)
		} else if exists {
			return event.ID, nil, nil // Silently deduplicate
		}
	}

	// Step 2: Persist event
	if err := s.repo.InsertEvent(event); err != nil {
		return "", nil, fmt.Errorf("soc: persist event: %w", err)
	}

	// Step 2.5: Publish to event bus for real-time SSE streaming.
	if s.eventBus != nil {
		s.eventBus.Publish(event)
	}

	// SOC self-observability (IMP7): the event is persisted, count it by
	// severity+source (bounded enums — never per-tenant/per-sensor).
	s.metrics.RecordEvent(string(event.Severity), string(event.Source))

	// Step 3: Update sensor registry (§11.3)
	s.updateSensor(event)

	// Step 3.1: Alert Clustering (§7.6)
	if s.clusterEngine != nil {
		s.clusterEngine.AddEvent(event)
	}

	// Step 3.5: Threat Intel IOC enrichment (§P3+)
	if s.threatIntel != nil {
		iocMatches := s.threatIntel.EnrichEvent(event.SensorID, event.Description)
		if len(iocMatches) > 0 {
			// Boost confidence and log IOC match
			if event.Confidence < 0.9 {
				event.Confidence = 0.9
			}
			if s.logger != nil {
				s.logger.Record(audit.ModuleSOC,
					fmt.Sprintf("IOC_MATCH:%d", len(iocMatches)),
					fmt.Sprintf("event=%s ioc_type=%s ioc_value=%s source=%s",
						event.ID, iocMatches[0].Type, iocMatches[0].Value, iocMatches[0].Source))
			}
		}
	}

	// Step 4: Run correlation against recent events (§7)
	// Zero-G events are excluded from auto-response but still correlated.
	corrStart := time.Now()
	incident := s.correlate(event)
	s.metrics.ObserveCorrelationLatency(time.Since(corrStart))
	if incident != nil {
		s.metrics.RecordIncident(string(incident.Severity))
	}

	// Step 5: Apply playbooks if incident created (§10)
	// Skip auto-response for Zero-G events (§13.4: require_manual_approval: true)
	if incident != nil && !event.ZeroGMode {
		s.applyPlaybooks(event, incident)
	} else if incident != nil && event.ZeroGMode {
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC,
				"PLAYBOOK_SKIPPED:ZERO_G",
				fmt.Sprintf("incident=%s reason=zero_g_mode_requires_manual_approval", incident.ID))
		}
	}

	// Step 6: SOAR webhook notification (§P3)
	// Skip webhook for Zero-G events — must go through manual approval (§13.4).
	if incident != nil && s.webhook != nil && !event.ZeroGMode {
		go s.webhook.NotifyIncident("incident_created", incident)
	}

	return event.ID, incident, nil
}

// DisableRateLimit disables per-sensor rate limiting (for benchmarks only).
func (s *Service) DisableRateLimit() {
	s.mu.Lock()
	s.rateLimitDisabled = true
	s.mu.Unlock()
}

// isRateLimited checks if sensor exceeds MaxEventsPerSecondPerSensor (§17.3).
// P-2 FIX: Also cleans up dead sensor entries to prevent memory leak.
func (s *Service) isRateLimited(sensorID string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.rateLimitDisabled {
		return false
	}

	now := time.Now()
	cutoff := now.Add(-time.Second)

	// P-2 FIX: Periodically clean up dead sensors (every ~100 calls).
	// Removes sensors with no activity in the last 10 seconds.
	if len(s.sensorRates) > 10 {
		deadCutoff := now.Add(-10 * time.Second)
		for id, timestamps := range s.sensorRates {
			if id == sensorID {
				continue
			}
			if len(timestamps) > 0 && timestamps[len(timestamps)-1].Before(deadCutoff) {
				delete(s.sensorRates, id)
			}
		}
	}

	// Prune old timestamps.
	timestamps := s.sensorRates[sensorID]
	pruned := timestamps[:0]
	for _, ts := range timestamps {
		if ts.After(cutoff) {
			pruned = append(pruned, ts)
		}
	}

	rateLimited := len(pruned) >= MaxEventsPerSecondPerSensor
	if !rateLimited {
		pruned = append(pruned, now)
	}
	s.sensorRates[sensorID] = pruned

	return rateLimited
}

// updateSensor registers/updates sentinel sensor on event ingest (§11.3 auto-discovery).
// E-2 FIX: Logs UpsertSensor errors instead of silently ignoring them.
func (s *Service) updateSensor(event domsoc.SOCEvent) {
	sensorID := event.SensorID
	if sensorID == "" {
		sensorID = string(event.Source)
	}

	// Mutate the in-memory sensor under the lock, snapshot it, then persist the
	// copy OUTSIDE the lock (Review 14.06 round-4): UpsertSensor is a SQLite write
	// serialized behind a single connection, and holding the service-wide s.mu
	// across it on the hot ingest path throttled all ingest/correlation and
	// blocked dashboard reads. UpsertSensor is independently serialized, so
	// persisting the snapshot off-lock is still correct.
	s.mu.Lock()
	sensor, exists := s.sensors[sensorID]
	if !exists {
		// Cardinality cap on auto-discovery (Review 14.06 round-5): a flood of
		// unique SensorIDs would otherwise grow s.sensors + the SQLite sensors
		// table without bound (memory/disk DoS). Above the cap, still ingest the
		// EVENT (handled by the caller) but do NOT register a new sensor row.
		// RegisterSensor enforces the same cap on the explicit path.
		if len(s.sensors) >= MaxSensors {
			s.mu.Unlock()
			return
		}
		newSensor := domsoc.NewSensor(sensorID, domsoc.SensorType(event.Source))
		// Attribute the sensor to its tenant so per-tenant sensor inventory /
		// health queries see it (Review 14.06 round-3: sensor rows were never
		// tenant-tagged, so a tenant's fleet view was always empty).
		newSensor.TenantID = event.TenantID
		sensor = &newSensor
		s.sensors[sensorID] = sensor
	} else if sensor.TenantID == "" && event.TenantID != "" {
		// Backfill a sensor discovered before tenant attribution existed.
		sensor.TenantID = event.TenantID
	}
	sensor.RecordEvent()
	snapshot := *sensor
	s.mu.Unlock()

	if err := s.repo.UpsertSensor(snapshot); err != nil {
		slog.Error("sensor upsert failed", "sensor_id", sensorID, "error", err)
	}
}

// correlate runs correlation rules against recent events (§7).
// P-1 FIX: Uses in-memory sliding window instead of DB query per ingest.
func (s *Service) correlate(event domsoc.SOCEvent) *domsoc.Incident {
	s.mu.Lock()
	if s.recentEvents == nil {
		s.recentEvents = make(map[string][]domsoc.SOCEvent)
	}
	// PER-TENANT sliding window (Review 14.06 round-2 + round-3): keying by
	// TenantID — and capping PER TENANT — both (a) stops one tenant's events
	// co-mingling into another's incident, and (b) stops a noisy tenant from
	// evicting a quiet tenant's events out of a shared globally-capped buffer
	// (which silently suppressed the quiet tenant's multi-stage correlation).
	// Each tenant correlates only its own events. The R3 gateway→SOC seam feeds
	// real per-tenant scan traffic through here.
	tid := event.TenantID
	cutoff := time.Now().Add(-time.Hour)
	win := s.recentEvents[tid][:0]
	for _, e := range s.recentEvents[tid] {
		if e.Timestamp.After(cutoff) {
			win = append(win, e)
		}
	}
	win = append(win, event)
	if len(win) > 500 { // cap PER TENANT, not globally
		win = win[len(win)-500:]
	}
	s.recentEvents[tid] = win
	events := make([]domsoc.SOCEvent, len(win))
	copy(events, win)
	s.mu.Unlock()

	if len(events) < 2 {
		return nil
	}

	matches := domsoc.CorrelateSOCEvents(events, s.rules)
	if len(matches) == 0 {
		return nil
	}

	match := matches[0]
	incident := domsoc.NewIncident(match.Rule.Name, match.Rule.Severity, match.Rule.ID)
	// Attribute the incident to its tenant (Review 14.06 round-2): the window is
	// tenant-partitioned above, so all matched events share event.TenantID.
	// Without this, auto-correlated incidents had TenantID="" and were invisible
	// to the owning tenant (and a cross-tenant evidence co-mingling risk).
	incident.TenantID = event.TenantID
	incident.KillChainPhase = match.Rule.KillChainPhase
	incident.MITREMapping = match.Rule.MITREMapping

	for _, e := range match.Events {
		incident.AddEvent(e.ID, e.Severity)
		// Track the earliest correlated-event time as the MTTD anchor (IMP6).
		incident.RecordFirstEventTime(e.Timestamp)
	}

	// Set decision chain anchor (§5.6)
	if s.logger != nil {
		anchor := s.logger.PrevHash()
		incident.SetAnchor(anchor, s.logger.Count())
		s.logger.Record(audit.ModuleCorrelation,
			fmt.Sprintf("INCIDENT_CREATED:%s", incident.ID),
			fmt.Sprintf("rule=%s severity=%s anchor=%s chain_length=%d",
				match.Rule.ID, match.Rule.Severity, anchor, s.logger.Count()))
	}

	// E-1 FIX: Handle InsertIncident error.
	if err := s.repo.InsertIncident(incident); err != nil {
		slog.Error("failed to persist incident", "incident_id", incident.ID, "error", err)
		return nil
	}
	return &incident
}

// applyPlaybooks matches playbooks against the event and incident (§10).
//
// Audit #26: the kill-chain phase MUST be passed through so pb-c2-killchain
// (trigger KillChainPhase=="command_control") is reachable on the automatic
// ingest→incident→playbook path. Passing "" made it structurally unreachable.
// The phase is populated at correlate time (incident.KillChainPhase).
func (s *Service) applyPlaybooks(event domsoc.SOCEvent, incident *domsoc.Incident) {
	// ExecuteForIncident threads the full incident context (severity, rule,
	// description, event count) into the action handler so notify/webhook/escalate
	// emit real alert payloads (IMP6). The triggering event's category selects
	// category-scoped playbooks (the incident has no single category field).
	execs := s.playbookEngine.ExecuteForIncident(incident, event.Category)
	// SOC self-observability (IMP7): count every playbook run by outcome+id so
	// the dashboard sees auto-response volume and partial_failure rate.
	for _, ex := range execs {
		s.metrics.RecordPlaybookRun(ex.PlaybookID, ex.Status)
	}
	if len(execs) > 0 {
		incident.PlaybookApplied = execs[0].PlaybookID
		if s.logger != nil {
			// Surface per-action outcome (status + error) so an operator can see a
			// partial_failure — e.g. block_ip NOT enforced (log-only backend) — rather
			// than assuming every playbook step succeeded.
			detail := fmt.Sprintf("incident=%s actions=%d status=%s",
				incident.ID, execs[0].ActionsRun, execs[0].Status)
			if execs[0].Error != "" {
				detail += " error=" + execs[0].Error
			}
			s.logger.Record(audit.ModuleSOC,
				fmt.Sprintf("PLAYBOOK_APPLIED:%s", execs[0].PlaybookID),
				detail)
		}
	}
}

// authenticateSensor enforces the per-sensor pre-shared key (§17.3 T-01) when
// SOC_SENSOR_KEYS is configured. Shared by event ingest AND heartbeat so every
// sensor-facing route is gated uniformly — Review 14.06 round-4: heartbeat had
// lost its only authentication when requireSOC was removed (round-2) and had no
// PSK backstop, leaving it reachable by anonymous callers.
//
// Pre-launch audit 18.06: fails CLOSED when no PSKs are configured (was: open).
// External sensor ingest/heartbeat now requires SOC_SENSOR_KEYS, matching the
// product's fail-closed posture (scan engine, audit chain). Dev can opt back into
// the open default with SOC_ALLOW_UNAUTH_INGEST=1. The internal gateway->SOC feed
// is unaffected — it ingests via the trusted path, which never calls this.
func (s *Service) authenticateSensor(sensorID, sensorKey string) error {
	s.mu.RLock()
	sensorKeys := s.sensorKeys
	s.mu.RUnlock()
	if len(sensorKeys) == 0 {
		if os.Getenv("SOC_ALLOW_UNAUTH_INGEST") == "1" {
			return nil
		}
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC, "AUTH_FAILED:REJECT", "reason=no_sensor_keys_configured")
		}
		return fmt.Errorf("%w: external sensor ingest requires SOC_SENSOR_KEYS (set SOC_ALLOW_UNAUTH_INGEST=1 for dev only)", domsoc.ErrAuthFailed)
	}
	if sensorID == "" {
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC, "AUTH_FAILED:REJECT", "reason=missing_sensor_id")
		}
		return fmt.Errorf("%w: sensor_id required when authentication is enabled", domsoc.ErrAuthFailed)
	}
	expected, exists := sensorKeys[sensorID]
	// S-3: Constant-time comparison prevents timing side-channel attacks on PSK.
	if !exists || subtle.ConstantTimeCompare([]byte(expected), []byte(sensorKey)) != 1 {
		if s.logger != nil {
			s.logger.Record(audit.ModuleSOC, "AUTH_FAILED:REJECT",
				fmt.Sprintf("sensor_id=%s reason=invalid_key", sensorID))
		}
		return fmt.Errorf("%w: sensor %s", domsoc.ErrAuthFailed, sensorID)
	}
	return nil
}

// RecordHeartbeat processes a sensor heartbeat (§11.3). Authenticates with the
// same PSK as event ingest (Review 14.06 round-4) before touching state.
func (s *Service) RecordHeartbeat(sensorID, sensorKey string) (bool, error) {
	if err := s.authenticateSensor(sensorID, sensorKey); err != nil {
		return false, err
	}

	s.mu.Lock()
	sensor, exists := s.sensors[sensorID]
	if !exists {
		s.mu.Unlock()
		return false, fmt.Errorf("sensor not found: %s", sensorID)
	}
	sensor.RecordHeartbeat()
	snapshot := *sensor // persist off-lock (Review 14.06 round-4) — see updateSensor
	s.mu.Unlock()

	if err := s.repo.UpsertSensor(snapshot); err != nil {
		return false, fmt.Errorf("soc: upsert sensor: %w", err)
	}
	return true, nil
}

// CheckSensors runs heartbeat check on all sensors (§11.3).
// Returns sensors that transitioned to OFFLINE (need SOC alert).
func (s *Service) CheckSensors() []domsoc.Sensor {
	// Mark past-due sensors under the lock, collecting snapshots; persist and log
	// OUTSIDE the lock (Review 14.06 round-4: don't hold s.mu across the SQLite
	// writes + audit-log I/O for every offline sensor).
	s.mu.Lock()
	var toUpsert []domsoc.Sensor
	var offlineSensors []domsoc.Sensor
	for _, sensor := range s.sensors {
		if sensor.TimeSinceLastSeen() > time.Duration(domsoc.HeartbeatIntervalSec)*time.Second {
			alertNeeded := sensor.MissHeartbeat()
			toUpsert = append(toUpsert, *sensor)
			if alertNeeded {
				offlineSensors = append(offlineSensors, *sensor)
			}
		}
	}
	s.mu.Unlock()

	for _, snap := range toUpsert {
		if err := s.repo.UpsertSensor(snap); err != nil {
			slog.Error("sensor heartbeat check: upsert failed", "sensor_id", snap.SensorID, "error", err)
		}
	}
	if s.logger != nil {
		for _, snap := range offlineSensors {
			s.logger.Record(audit.ModuleSOC,
				"SENSOR_OFFLINE:ALERT",
				fmt.Sprintf("sensor=%s type=%s missed=%d", snap.SensorID, snap.SensorType, snap.MissedHeartbeats))
		}
	}
	return offlineSensors
}

// ListEvents returns recent events with optional limit, scoped to tenant.
func (s *Service) ListEvents(tenantID string, limit int) ([]domsoc.SOCEvent, error) {
	return s.repo.ListEvents(tenantID, limit)
}

// ListIncidents returns incidents, optionally filtered by status, scoped to tenant.
func (s *Service) ListIncidents(tenantID string, status string, limit int) ([]domsoc.Incident, error) {
	return s.repo.ListIncidents(tenantID, status, limit)
}

// ListRules returns all active correlation rules (built-in + custom).
func (s *Service) ListRules() []domsoc.SOCCorrelationRule {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]domsoc.SOCCorrelationRule, len(s.rules))
	copy(out, s.rules)
	return out
}

// EventBus returns the real-time event bus for SSE subscribers.
func (s *Service) EventBus() *domsoc.EventBus {
	return s.eventBus
}

// ZeroG returns the Zero-G Mode approval engine (§13.4).
func (s *Service) ZeroG() *domsoc.ZeroGMode {
	return s.zeroG
}

// DecisionLogPath returns the decision log file path for chain verification.
func (s *Service) DecisionLogPath() string {
	if s.logger == nil {
		return ""
	}
	return s.logger.Path()
}

// P2PSync returns the P2P SOC sync engine (§14).
func (s *Service) P2PSync() *domsoc.P2PSyncService {
	return s.p2pSync
}

// AnomalyDetector returns the anomaly detection engine (§5).
func (s *Service) AnomalyDetector() *domsoc.AnomalyDetector {
	return s.anomaly
}

// PlaybookEngine returns the playbook execution engine (§10).
func (s *Service) PlaybookEngine() *domsoc.PlaybookEngine {
	return s.playbookEngine
}

// ThreatIntelEngine returns the IOC matching engine (§6).
func (s *Service) ThreatIntelEngine() *domsoc.ThreatIntelEngine {
	return s.threatIntelEngine
}

// RetentionPolicy returns the data retention policy engine (§19).
func (s *Service) RetentionPolicy() *domsoc.DataRetentionPolicy {
	return s.retention
}

// GetKillChain reconstructs the Kill Chain for a given incident (§8).
func (s *Service) GetKillChain(incidentID string) (*domsoc.KillChain, error) {
	inc, err := s.repo.GetIncident(incidentID)
	if err != nil {
		return nil, err
	}

	// Fetch events associated with the incident
	var events []domsoc.SOCEvent
	for _, eid := range inc.Events {
		ev, err := s.repo.GetEvent(eid)
		if err == nil {
			events = append(events, *ev)
		}
	}

	s.mu.RLock()
	rules := s.rules
	s.mu.RUnlock()

	kc := domsoc.ReconstructKillChain(*inc, events, rules)
	if kc == nil {
		return nil, fmt.Errorf("soc: no kill chain for incident %s", incidentID)
	}
	return kc, nil
}

// GetRecentDecisions returns audit metadata for the decision log (§9).
// Note: Full decision retrieval requires extending DecisionLogger in a future phase.
func (s *Service) GetRecentDecisions(limit int) []map[string]any {
	if s.logger == nil {
		return nil
	}
	// Return summary from available DecisionLogger API
	return []map[string]any{
		{
			"total_decisions": s.logger.Count(),
			"hash_chain":      s.logger.PrevHash(),
			"log_path":        s.logger.Path(),
			"status":          "operational",
		},
	}
}

// GetIncident returns an incident by ID.
func (s *Service) GetIncident(id string) (*domsoc.Incident, error) {
	return s.repo.GetIncident(id)
}

// ErrDecisionAuditUnavailable indicates an unconfirmed decision audit write.
var ErrDecisionAuditUnavailable = errors.New("decision audit unavailable")

// UpdateVerdict updates an incident's status (manual verdict).
func (s *Service) UpdateVerdict(id string, status domsoc.IncidentStatus) error {
	if s.logger != nil {
		if err := s.logger.Record(audit.ModuleSOC, fmt.Sprintf("VERDICT:%s", status), fmt.Sprintf("incident=%s", id)); err != nil {
			return ErrDecisionAuditUnavailable
		}
	}
	return s.repo.UpdateIncidentStatus(id, status)
}

// Copy the mutable slices before making an uncommitted case mutation. A repo
// may return a shared pointer; no caller-visible state changes on audit failure.
func copyIncidentForCaseUpdate(inc *domsoc.Incident) *domsoc.Incident {
	copy := *inc
	copy.Notes = append([]domsoc.IncidentNote(nil), inc.Notes...)
	copy.Timeline = append([]domsoc.TimelineEntry(nil), inc.Timeline...)
	return &copy
}

// AssignIncident assigns an analyst to an incident.
func (s *Service) AssignIncident(id, analyst string) error {
	inc, err := s.repo.GetIncident(id)
	if err != nil {
		return fmt.Errorf("incident not found: %s", id)
	}
	candidate := copyIncidentForCaseUpdate(inc)
	candidate.Assign(analyst)
	if s.logger != nil {
		if err := s.logger.Record(audit.ModuleSOC, "ASSIGN", fmt.Sprintf("incident=%s analyst=%s", id, analyst)); err != nil {
			return ErrDecisionAuditUnavailable
		}
	}
	return s.repo.UpdateIncident(candidate)
}

// ChangeIncidentStatus changes the status of an incident with actor tracking.
func (s *Service) ChangeIncidentStatus(id string, status domsoc.IncidentStatus, actor string) error {
	inc, err := s.repo.GetIncident(id)
	if err != nil {
		return fmt.Errorf("incident not found: %s", id)
	}
	candidate := copyIncidentForCaseUpdate(inc)
	candidate.ChangeStatus(status, actor)
	if s.logger != nil {
		if err := s.logger.Record(audit.ModuleSOC, fmt.Sprintf("STATUS_CHANGE:%s", status), fmt.Sprintf("incident=%s actor=%s", id, actor)); err != nil {
			return ErrDecisionAuditUnavailable
		}
	}
	return s.repo.UpdateIncident(candidate)
}

// AddIncidentNote adds an investigation note to an incident.
func (s *Service) AddIncidentNote(id, author, content string) (*domsoc.IncidentNote, error) {
	inc, err := s.repo.GetIncident(id)
	if err != nil {
		return nil, fmt.Errorf("incident not found: %s", id)
	}
	candidate := copyIncidentForCaseUpdate(inc)
	note := candidate.AddNote(author, content)
	if s.logger != nil {
		if err := s.logger.Record(audit.ModuleSOC, "NOTE_ADDED", fmt.Sprintf("incident=%s author=%s note_id=%s", id, author, note.ID)); err != nil {
			return nil, ErrDecisionAuditUnavailable
		}
	}
	if err := s.repo.UpdateIncident(candidate); err != nil {
		return nil, err
	}
	return &note, nil
}

// GetIncidentDetail returns full incident with notes and timeline.
func (s *Service) GetIncidentDetail(id string) (*domsoc.Incident, error) {
	return s.repo.GetIncident(id)
}

// ── Sprint 2: Incident Management Enhancements ─────────────────────────

// IncidentFilter defines advanced filter criteria for incidents.
type IncidentFilter struct {
	// TenantID scopes the query to one tenant. Review 13.06 (audit CRITICAL):
	// this MUST be set from the caller's tenant by the HTTP handlers — empty
	// means "all tenants" and is reserved for superadmin. Without it, advanced
	// list / export leaked every tenant's incidents.
	TenantID   string `json:"-"`
	Status     string `json:"status"`
	Severity   string `json:"severity"`
	AssignedTo string `json:"assigned_to"`
	Search     string `json:"search"`
	Source     string `json:"source"` // correlation_rule
	DateFrom   string `json:"date_from"`
	DateTo     string `json:"date_to"`
	Page       int    `json:"page"`
	Limit      int    `json:"limit"`
	SortBy     string `json:"sort_by"`
	SortOrder  string `json:"sort_order"` // asc, desc
}

// IncidentFilterResult is paginated incidents response.
type IncidentFilterResult struct {
	Incidents  []domsoc.Incident `json:"incidents"`
	Total      int               `json:"total"`
	Page       int               `json:"page"`
	Limit      int               `json:"limit"`
	TotalPages int               `json:"total_pages"`
}

// ListIncidentsAdvanced filters incidents with multi-field criteria and pagination.
// Review 13.06 (audit CRITICAL): scope to f.TenantID at the repo layer so a
// caller never sees other tenants' incidents (empty TenantID = superadmin/all).
func (s *Service) ListIncidentsAdvanced(f IncidentFilter) (*IncidentFilterResult, error) {
	// Get the tenant's incidents (repo doesn't support advanced filtering).
	all, err := s.repo.ListIncidents(f.TenantID, "", 10000)
	if err != nil {
		return nil, err
	}

	// Apply filters in memory
	var filtered []domsoc.Incident
	for _, inc := range all {
		if f.Status != "" && string(inc.Status) != f.Status {
			continue
		}
		if f.Severity != "" && string(inc.Severity) != f.Severity {
			continue
		}
		if f.AssignedTo != "" && inc.AssignedTo != f.AssignedTo {
			continue
		}
		if f.Source != "" && inc.CorrelationRule != f.Source {
			continue
		}
		if f.Search != "" {
			found := false
			search := strings.ToLower(f.Search)
			if strings.Contains(strings.ToLower(inc.Title), search) ||
				strings.Contains(strings.ToLower(inc.Description), search) ||
				strings.Contains(strings.ToLower(inc.ID), search) {
				found = true
			}
			if !found {
				continue
			}
		}
		if f.DateFrom != "" {
			if from, err := time.Parse(time.RFC3339, f.DateFrom); err == nil {
				if inc.CreatedAt.Before(from) {
					continue
				}
			}
		}
		if f.DateTo != "" {
			if to, err := time.Parse(time.RFC3339, f.DateTo); err == nil {
				if inc.CreatedAt.After(to) {
					continue
				}
			}
		}
		filtered = append(filtered, inc)
	}

	// Sort
	if f.SortBy == "" {
		f.SortBy = "created_at"
	}
	sort.Slice(filtered, func(i, j int) bool {
		ascending := f.SortOrder != "desc"
		switch f.SortBy {
		case "severity":
			if ascending {
				return filtered[i].Severity.Rank() < filtered[j].Severity.Rank()
			}
			return filtered[i].Severity.Rank() > filtered[j].Severity.Rank()
		case "status":
			if ascending {
				return string(filtered[i].Status) < string(filtered[j].Status)
			}
			return string(filtered[i].Status) > string(filtered[j].Status)
		default: // created_at
			if ascending {
				return filtered[i].CreatedAt.Before(filtered[j].CreatedAt)
			}
			return filtered[i].CreatedAt.After(filtered[j].CreatedAt)
		}
	})

	total := len(filtered)
	if f.Limit <= 0 {
		f.Limit = 20
	}
	if f.Page <= 0 {
		f.Page = 1
	}
	totalPages := (total + f.Limit - 1) / f.Limit
	start := (f.Page - 1) * f.Limit
	if start >= total {
		return &IncidentFilterResult{
			Incidents: []domsoc.Incident{},
			Total:     total, Page: f.Page, Limit: f.Limit, TotalPages: totalPages,
		}, nil
	}
	end := start + f.Limit
	if end > total {
		end = total
	}

	return &IncidentFilterResult{
		Incidents:  filtered[start:end],
		Total:      total,
		Page:       f.Page,
		Limit:      f.Limit,
		TotalPages: totalPages,
	}, nil
}

// BulkAction defines a batch operation on incidents.
type BulkAction struct {
	Action      string   `json:"action"` // assign, status, close, delete
	IncidentIDs []string `json:"incident_ids"`
	Value       string   `json:"value"` // analyst email, new status
	Actor       string   `json:"actor"` // who initiated
}

// BulkActionResult is the result of a batch operation.
type BulkActionResult struct {
	Affected int      `json:"affected"`
	Failed   int      `json:"failed"`
	Errors   []string `json:"errors,omitempty"`
}

// BulkUpdateIncidents performs batch operations on multiple incidents.
func (s *Service) BulkUpdateIncidents(action BulkAction) (*BulkActionResult, error) {
	result := &BulkActionResult{}
	for _, id := range action.IncidentIDs {
		var err error
		switch action.Action {
		case "assign":
			err = s.AssignIncident(id, action.Value)
		case "status":
			err = s.ChangeIncidentStatus(id, domsoc.IncidentStatus(action.Value), action.Actor)
		case "close":
			err = s.ChangeIncidentStatus(id, domsoc.StatusResolved, action.Actor)
		default:
			err = fmt.Errorf("unknown bulk action: %s", action.Action)
		}
		if err != nil {
			result.Failed++
			result.Errors = append(result.Errors, fmt.Sprintf("%s: %s", id, err.Error()))
		} else {
			result.Affected++
		}
	}
	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "BULK_"+strings.ToUpper(action.Action),
			fmt.Sprintf("affected=%d failed=%d ids=%d actor=%s", result.Affected, result.Failed, len(action.IncidentIDs), action.Actor))
	}
	return result, nil
}

// SLAThreshold defines response/resolution time targets per severity.
type SLAThreshold struct {
	Severity       string        `json:"severity"`
	ResponseTime   time.Duration `json:"response_time"`   // max time to assign
	ResolutionTime time.Duration `json:"resolution_time"` // max time to resolve
}

// SLAStatus represents an incident's SLA compliance state.
type SLAStatus struct {
	ResponseBreached    bool    `json:"response_breached"`
	ResolutionBreached  bool    `json:"resolution_breached"`
	ResponseRemaining   float64 `json:"response_remaining_min"` // minutes remaining (negative = breached)
	ResolutionRemaining float64 `json:"resolution_remaining_min"`
	ResponseTarget      float64 `json:"response_target_min"`
	ResolutionTarget    float64 `json:"resolution_target_min"`
}

// DefaultSLAThresholds returns SLA targets per severity.
func DefaultSLAThresholds() map[string]SLAThreshold {
	return map[string]SLAThreshold{
		"CRITICAL": {Severity: "CRITICAL", ResponseTime: 15 * time.Minute, ResolutionTime: 4 * time.Hour},
		"HIGH":     {Severity: "HIGH", ResponseTime: 30 * time.Minute, ResolutionTime: 8 * time.Hour},
		"MEDIUM":   {Severity: "MEDIUM", ResponseTime: 2 * time.Hour, ResolutionTime: 24 * time.Hour},
		"LOW":      {Severity: "LOW", ResponseTime: 8 * time.Hour, ResolutionTime: 72 * time.Hour},
		"INFO":     {Severity: "INFO", ResponseTime: 24 * time.Hour, ResolutionTime: 168 * time.Hour},
	}
}

// CalculateSLA computes SLA status for an incident.
func CalculateSLA(inc *domsoc.Incident) *SLAStatus {
	thresholds := DefaultSLAThresholds()
	t, ok := thresholds[string(inc.Severity)]
	if !ok {
		return nil
	}

	now := time.Now()
	sla := &SLAStatus{
		ResponseTarget:   t.ResponseTime.Minutes(),
		ResolutionTarget: t.ResolutionTime.Minutes(),
	}

	// Response SLA — breached if not assigned within threshold
	if inc.AssignedTo == "" {
		elapsed := now.Sub(inc.CreatedAt)
		sla.ResponseRemaining = (t.ResponseTime - elapsed).Minutes()
		sla.ResponseBreached = elapsed > t.ResponseTime
	} else {
		sla.ResponseRemaining = t.ResponseTime.Minutes() // assigned, so OK
	}

	// Resolution SLA
	if inc.IsOpen() {
		elapsed := now.Sub(inc.CreatedAt)
		sla.ResolutionRemaining = (t.ResolutionTime - elapsed).Minutes()
		sla.ResolutionBreached = elapsed > t.ResolutionTime
	} else if inc.ResolvedAt != nil {
		elapsed := inc.ResolvedAt.Sub(inc.CreatedAt)
		sla.ResolutionRemaining = (t.ResolutionTime - elapsed).Minutes()
		sla.ResolutionBreached = elapsed > t.ResolutionTime
	}

	return sla
}

// ExportIncidentsCSV generates CSV data for incidents.
func (s *Service) ExportIncidentsCSV(f IncidentFilter) ([]byte, error) {
	result, err := s.ListIncidentsAdvanced(f)
	if err != nil {
		return nil, err
	}
	var buf bytes.Buffer
	w := csv.NewWriter(&buf)
	// Header
	w.Write([]string{"ID", "Title", "Status", "Severity", "Assigned To", "Correlation Rule",
		"Kill Chain Phase", "Event Count", "Created At", "Updated At", "Resolved At", "MTTR (min)",
		"SLA Response Breached", "SLA Resolution Breached"})

	for _, inc := range result.Incidents {
		resolvedAt := ""
		mttr := ""
		if inc.ResolvedAt != nil {
			resolvedAt = inc.ResolvedAt.Format(time.RFC3339)
			mttr = fmt.Sprintf("%.1f", inc.MTTR().Minutes())
		}
		sla := CalculateSLA(&inc)
		slaResp, slaResol := "N/A", "N/A"
		if sla != nil {
			if sla.ResponseBreached {
				slaResp = "BREACHED"
			} else {
				slaResp = "OK"
			}
			if sla.ResolutionBreached {
				slaResol = "BREACHED"
			} else {
				slaResol = "OK"
			}
		}
		w.Write([]string{
			inc.ID, inc.Title, string(inc.Status), string(inc.Severity),
			inc.AssignedTo, inc.CorrelationRule, inc.KillChainPhase,
			strconv.Itoa(inc.EventCount),
			inc.CreatedAt.Format(time.RFC3339),
			inc.UpdatedAt.Format(time.RFC3339),
			resolvedAt, mttr, slaResp, slaResol,
		})
	}
	w.Flush()
	return buf.Bytes(), nil
}

// ListSensors returns registered sensors, scoped to tenant.
func (s *Service) ListSensors(tenantID string) ([]domsoc.Sensor, error) {
	return s.repo.ListSensors(tenantID)
}

// RegisterSensor adds or updates a sensor in the SOC.
func (s *Service) RegisterSensor(id, name, sensorType string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.sensors) >= MaxSensors {
		return domsoc.ErrCapacityFull
	}

	if _, exists := s.sensors[id]; exists {
		return fmt.Errorf("sensor %s already registered", id)
	}

	sensor := domsoc.NewSensor(id, domsoc.SensorType(sensorType))
	sensor.Hostname = name
	s.sensors[id] = &sensor
	return nil
}

// DeregisterSensor removes a sensor from the SOC.
func (s *Service) DeregisterSensor(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.sensors, id)
}

// Dashboard returns SOC KPI metrics, scoped to tenant.
func (s *Service) Dashboard(tenantID string) (*DashboardData, error) {
	totalEvents, err := s.repo.CountEvents(tenantID)
	if err != nil {
		return nil, err
	}

	lastHourEvents, err := s.repo.CountEventsSince(tenantID, time.Now().Add(-1*time.Hour))
	if err != nil {
		return nil, err
	}

	openIncidents, err := s.repo.CountOpenIncidents(tenantID)
	if err != nil {
		return nil, err
	}

	sensorCounts, err := s.repo.CountSensorsByStatus(tenantID)
	if err != nil {
		return nil, err
	}

	// Chain validation (§5.6, §12.2) — full SHA-256 chain verification.
	chainValid := false
	chainLength := 0
	chainHeadHash := ""
	chainBrokenLine := 0
	if s.logger != nil {
		chainLength = s.logger.Count()
		chainHeadHash = s.logger.PrevHash()
		// Full chain verification via VerifyChainFromFile (§5.6)
		validCount, brokenLine, verifyErr := audit.VerifyChainFromFile(s.logger.Path(), s.logger.Keyset())
		if verifyErr == nil && brokenLine == 0 {
			chainValid = true
			chainLength = validCount // Use file-verified count
		} else {
			chainBrokenLine = brokenLine
		}
	}

	return &DashboardData{
		TotalEvents:      totalEvents,
		EventsLastHour:   lastHourEvents,
		OpenIncidents:    openIncidents,
		SensorStatus:     sensorCounts,
		ChainValid:       chainValid,
		ChainLength:      chainLength,
		ChainHeadHash:    chainHeadHash,
		ChainBrokenLine:  chainBrokenLine,
		CorrelationRules: len(s.rules),
		ActivePlaybooks:  len(s.playbookEngine.ListPlaybooks()),
	}, nil
}

// MaxAnalyticsEvents caps the event fetch for analytics reports to prevent OOM.
const MaxAnalyticsEvents = 100000

// Analytics generates a SOC analytics report for the given time window, scoped
// to tenantID. An empty tenantID means all tenants (superadmin only — the caller
// is responsible for passing the request's tenant scope). Review 14.06 round-2:
// previously hardcoded "" here, leaking all-tenant aggregates to any viewer.
func (s *Service) Analytics(tenantID string, windowHours int) (*AnalyticsReport, error) {
	if windowHours <= 0 {
		windowHours = 24
	}

	events, err := s.repo.ListEvents(tenantID, MaxAnalyticsEvents)
	if err != nil {
		return nil, fmt.Errorf("soc: analytics events: %w", err)
	}

	incidents, err := s.repo.ListIncidents(tenantID, "", 10000)
	if err != nil {
		return nil, fmt.Errorf("soc: analytics incidents: %w", err)
	}

	return GenerateReport(events, incidents, windowHours), nil
}

// WriteMetrics renders the SOC-plane Prometheus exposition (IMP7): the counters/
// histogram owned by the registry PLUS scrape-time gauges (open incidents, real
// MTTD/MTTR, sensor status) pulled here from the store. It is GLOBAL/all-tenant
// by design — /metrics is an operator endpoint, and (critically) it carries NO
// per-tenant label, so scraping it cannot leak tenant identities or blow up
// cardinality. Errors reading the store degrade to zero gauges rather than
// failing the scrape (the counters are still emitted).
func (s *Service) WriteMetrics(w io.Writer) {
	if s.metrics == nil {
		return
	}
	snap := domsoc.Snapshot{}

	// Open incidents (global). Best-effort: a store error leaves the gauge at 0.
	if open, err := s.repo.CountOpenIncidents(""); err == nil {
		snap.OpenIncidents = open
	}

	// Real MTTD/MTTR over all incidents (the same computation the analytics
	// endpoint surfaces, so /metrics and the dashboard agree).
	if incidents, err := s.repo.ListIncidents("", "", MaxAnalyticsEvents); err == nil {
		mttr, resolved := calcMTTR(incidents)
		mttdSecs, measured := calcMTTD(incidents)
		snap.MTTRHours = mttr
		snap.ResolvedIncidents = resolved
		snap.MTTDSeconds = mttdSecs
		snap.MeasuredDetections = measured
	}

	// Sensor status counts (bounded labels: ONLINE/OFFLINE/DEGRADED/UNKNOWN).
	if counts, err := s.repo.CountSensorsByStatus(""); err == nil && len(counts) > 0 {
		snap.Sensors = make(map[string]int, len(counts))
		for status, n := range counts {
			snap.Sensors[string(status)] = n
		}
	}

	s.metrics.Write(w, snap)
}

// DashboardData holds SOC KPI metrics (§12.2).
type DashboardData struct {
	TotalEvents      int                         `json:"total_events"`
	EventsLastHour   int                         `json:"events_last_hour"`
	OpenIncidents    int                         `json:"open_incidents"`
	SensorStatus     map[domsoc.SensorStatus]int `json:"sensor_status"`
	ChainValid       bool                        `json:"chain_valid"`
	ChainLength      int                         `json:"chain_length"`
	ChainHeadHash    string                      `json:"chain_head_hash"`
	ChainBrokenLine  int                         `json:"chain_broken_line,omitempty"`
	CorrelationRules int                         `json:"correlation_rules"`
	ActivePlaybooks  int                         `json:"active_playbooks"`
}

// JSON returns the dashboard as JSON string.
func (d *DashboardData) JSON() string {
	data, _ := json.MarshalIndent(d, "", "  ")
	return string(data)
}

// RunPlaybook manually executes a playbook against an incident (§10, §12.1).
func (s *Service) RunPlaybook(playbookID, incidentID string) (*PlaybookResult, error) {
	// Find playbook.
	var pb *domsoc.Playbook
	for _, p := range s.playbookEngine.ListPlaybooks() {
		if p.ID == playbookID {
			pCopy := p
			pb = &pCopy
			break
		}
	}
	if pb == nil {
		return nil, fmt.Errorf("playbook not found: %s", playbookID)
	}

	// Find incident.
	incident, err := s.repo.GetIncident(incidentID)
	if err != nil {
		return nil, fmt.Errorf("incident not found: %s", incidentID)
	}

	_ = incident
	// The manual path has no authenticated action executor. Never mutate the
	// incident or claim actions happened merely because the request was valid.
	return nil, ErrManualPlaybookUnavailable

}

var ErrManualPlaybookUnavailable = errors.New("manual playbook execution unavailable")

// PlaybookResult represents the result of a manual playbook run.
type PlaybookResult struct {
	PlaybookID string                  `json:"playbook_id"`
	IncidentID string                  `json:"incident_id"`
	Actions    []domsoc.PlaybookAction `json:"actions"`
	Status     string                  `json:"status"`
}

// complianceEvidence is the bundle of LIVE, machine-verifiable signals the
// compliance reports bind their requirement statuses to (IMP8). Every field is
// computed from the running system — the tamper-evident decision chain, the SOC
// incident store, and the real registry sizes — NOT from static strings. The
// reports degrade truthfully when these signals are absent (e.g. no decision
// logger ⇒ ChainValid=false ⇒ the chain-backed requirements report NON_COMPLIANT).
type complianceEvidence struct {
	// Decision-chain integrity (the HMAC-SHA256 tamper-evident audit log).
	ChainValid      bool
	ChainLength     int
	ChainHeadHash   string
	ChainBrokenLine int
	ChainKeyed      bool // true ⇒ links are HMAC-keyed (unforgeable), not bare SHA-256

	// Live SOC operational metrics (IMP7), real timestamps.
	TotalEvents        int
	OpenIncidents      int
	MTTRHours          float64
	ResolvedIncidents  int
	MTTDSeconds        float64
	MeasuredDetections int

	// Real registry sizes.
	CorrelationRules int
	Sensors          int
	Playbooks        int
}

// gatherComplianceEvidence collects the live evidence bundle from the running
// system. It reuses the exact same computations as the SOC dashboard and the
// /metrics scrape (chain verification, calcMTTR/calcMTTD) so a compliance report
// never disagrees with what an operator sees on the dashboard. A store error is
// returned (the report must not silently fabricate evidence); a MISSING logger is
// NOT an error — it degrades ChainValid to false, which the requirements then
// report honestly as NON_COMPLIANT.
func (s *Service) gatherComplianceEvidence() (*complianceEvidence, error) {
	dashboard, err := s.Dashboard("") // global view; verifies the chain on the wire
	if err != nil {
		return nil, err
	}
	sensors, err := s.repo.ListSensors("")
	if err != nil {
		return nil, err
	}

	ev := &complianceEvidence{
		ChainValid:       dashboard.ChainValid,
		ChainLength:      dashboard.ChainLength,
		ChainHeadHash:    dashboard.ChainHeadHash,
		ChainBrokenLine:  dashboard.ChainBrokenLine,
		TotalEvents:      dashboard.TotalEvents,
		OpenIncidents:    dashboard.OpenIncidents,
		CorrelationRules: len(s.rules),
		Sensors:          len(sensors),
		Playbooks:        len(s.playbookEngine.ListPlaybooks()),
	}
	if s.logger != nil {
		ev.ChainKeyed = s.logger.HMACEnabled()
	}

	// Real MTTD/MTTR over all incidents — the same numbers /metrics emits.
	if incidents, err := s.repo.ListIncidents("", "", MaxAnalyticsEvents); err == nil {
		ev.MTTRHours, ev.ResolvedIncidents = calcMTTR(incidents)
		ev.MTTDSeconds, ev.MeasuredDetections = calcMTTD(incidents)
	}
	return ev, nil
}

// ComplianceReport generates an EU AI Act Article 15 compliance report (§12.3).
//
// HONESTY (WS8 + IMP8): this report is a SELF-ASSESSMENT, not an attestation of
// conformity. A requirement is only reported COMPLIANT when it is backed by a
// LIVE, machine-verifiable signal — concretely, the tamper-evident decision-chain
// integrity holding over a non-empty chain. Every requirement carries the actual
// evidence it was judged on (chain head hash, entry count, real MTTR/incident
// counts, registry sizes) as structured EvidenceItems, so a reader can audit the
// verdict rather than trust a label. Controls that genuinely exist but are NOT
// externally audited report SELF_ATTESTED; controls with no programmatic evidence
// report NOT_ASSESSED. We never hardcode COMPLIANT from static strings, and the
// report DEGRADES truthfully: if the chain is broken or empty, the chain-backed
// requirements report NON_COMPLIANT (never COMPLIANT) and say so in their gap.
func (s *Service) ComplianceReport() (*ComplianceData, error) {
	ev, err := s.gatherComplianceEvidence()
	if err != nil {
		return nil, err
	}

	chainEv := ev.chainEvidence()
	recordKeeping := ev.recordKeepingStatus()

	requirements := []ComplianceRequirement{
		{
			ID:          "15.1",
			Description: "Risk Management System",
			// A correlation engine + playbooks genuinely exist (live counts), but
			// no external audit has validated the risk-management PROCESS.
			Status: ComplianceSelfAttested,
			Evidence: []EvidenceItem{
				{Source: "soc_correlation_engine", Detail: fmt.Sprintf("correlation_rules=%d", ev.CorrelationRules), Verifiable: true},
				{Source: "soc_playbooks", Detail: fmt.Sprintf("playbooks=%d", ev.Playbooks), Verifiable: true},
				{Source: "soc_metrics", Detail: fmt.Sprintf("open_incidents=%d resolved=%d", ev.OpenIncidents, ev.ResolvedIncidents), Verifiable: true},
			},
			Gap: "No independent audit of the risk-management system — self-attested.",
		},
		{
			ID:          "15.2",
			Description: "Data Governance",
			// Machine-verifiable: the decision-chain hash integrity is checked live.
			Status:   boolToCompliance(ev.ChainValid),
			Evidence: chainEv,
			Gap:      ev.chainGap(),
		},
		{
			ID:          "15.3",
			Description: "Technical Documentation",
			// This service holds no programmatic evidence of technical docs; the
			// previously-cited SENTINEL_AI_SOC_SPEC.md is not verifiable here.
			Status: ComplianceNotAssessed,
			Gap:    "Technical documentation is not verifiable by this service — assess out-of-band.",
		},
		{
			ID:          "15.4",
			Description: "Record-keeping",
			// Machine-verifiable: the chain must be valid AND non-empty.
			Status:   recordKeeping,
			Evidence: chainEv,
			Gap:      ev.recordKeepingGap(),
		},
		{
			ID:          "15.5",
			Description: "Transparency",
			Status:      CompliancePartial,
			Evidence: []EvidenceItem{
				{Source: "soc_dashboard", Detail: fmt.Sprintf("events_total=%d open_incidents=%d", ev.TotalEvents, ev.OpenIncidents), Verifiable: true},
				{Source: "incident_explain_endpoint", Detail: "GET /api/soc/incidents/{id}/explain", Verifiable: false},
			},
			Gap: "Real-time explainability of correlation decisions is incomplete.",
		},
		{
			ID:          "15.6",
			Description: "Human Oversight",
			// RBAC + manual verdict/playbook tooling genuinely exist (live sensor
			// count), but the oversight PROCESS is not externally audited.
			Status: ComplianceSelfAttested,
			Evidence: []EvidenceItem{
				{Source: "soc_verdict_tool", Detail: "manual analyst verdict endpoint", Verifiable: false},
				{Source: "soc_sensors", Detail: fmt.Sprintf("registered_sensors=%d", ev.Sensors), Verifiable: true},
			},
			Gap: "Human-oversight process is not independently audited — self-attested.",
		},
	}

	return &ComplianceData{
		Framework:    "EU AI Act Article 15",
		GeneratedAt:  time.Now(),
		Assessment:   "self-assessment (no external audit)",
		Requirements: requirements,
		Overall:      overallStatus(requirements),
	}, nil
}

// SOC2ComplianceReport generates an evidence-backed SOC 2 Common Criteria
// self-assessment (IMP8). Like the EU AI Act report it is honest by construction:
// a control is COMPLIANT only when a live, machine-verifiable signal backs it.
//
//   - CC4.1 (Monitoring): the entity monitors the system. Backed by the live SOC
//     metrics (events ingested, open incidents, MTTD/MTTR) — COMPLIANT when the
//     pipeline has actually observed events; NOT_ASSESSED when it has seen none
//     (no evidence of monitoring activity yet, so we do NOT claim the control).
//   - CC4.2 (Evaluation of deficiencies): incidents are detected, tracked and
//     resolved. SELF_ATTESTED — the incident lifecycle exists and carries real
//     MTTR, but remediation effectiveness is not externally audited.
//   - CC7.2 (System monitoring for anomalies): correlation rules + anomaly engine
//     genuinely exist (live rule count). SELF_ATTESTED.
//   - CC7.3 (Security event audit trail integrity): the tamper-evident decision
//     chain. COMPLIANT only when chain integrity VERIFIES over a non-empty chain;
//     NON_COMPLIANT when the chain is broken or empty (degrades truthfully).
func (s *Service) SOC2ComplianceReport() (*ComplianceData, error) {
	ev, err := s.gatherComplianceEvidence()
	if err != nil {
		return nil, err
	}

	chainEv := ev.chainEvidence()

	// CC4.1: COMPLIANT requires evidence the system is ACTUALLY being monitored —
	// at least one ingested event. With zero observed events we hold no evidence of
	// monitoring activity, so we report NOT_ASSESSED rather than claim the control.
	monitoringStatus := ComplianceNotAssessed
	monitoringGap := "No events observed yet — no evidence of active monitoring to assess."
	if ev.TotalEvents > 0 {
		monitoringStatus = ComplianceCompliant
		monitoringGap = ""
	}

	requirements := []ComplianceRequirement{
		{
			ID:          "CC4.1",
			Description: "Monitoring of Controls",
			Status:      monitoringStatus,
			Evidence: []EvidenceItem{
				{Source: "soc_metrics", Detail: fmt.Sprintf("events_total=%d open_incidents=%d", ev.TotalEvents, ev.OpenIncidents), Verifiable: true},
				{Source: "soc_metrics", Detail: fmt.Sprintf("mttd_seconds=%.0f measured=%d", ev.MTTDSeconds, ev.MeasuredDetections), Verifiable: true},
			},
			Gap: monitoringGap,
		},
		{
			ID:          "CC4.2",
			Description: "Evaluation and Communication of Deficiencies",
			// Incident lifecycle with real MTTR exists, but remediation
			// effectiveness is not externally audited.
			Status: ComplianceSelfAttested,
			Evidence: []EvidenceItem{
				{Source: "soc_metrics", Detail: fmt.Sprintf("resolved_incidents=%d mttr_hours=%.2f", ev.ResolvedIncidents, ev.MTTRHours), Verifiable: true},
				{Source: "soc_metrics", Detail: fmt.Sprintf("open_incidents=%d", ev.OpenIncidents), Verifiable: true},
			},
			Gap: "Remediation effectiveness is not independently audited — self-attested.",
		},
		{
			ID:          "CC7.2",
			Description: "System Monitoring for Anomalies",
			// Correlation + anomaly detection engines genuinely exist (live counts),
			// but the detection coverage is not externally audited.
			Status: ComplianceSelfAttested,
			Evidence: []EvidenceItem{
				{Source: "soc_correlation_engine", Detail: fmt.Sprintf("correlation_rules=%d", ev.CorrelationRules), Verifiable: true},
				{Source: "soc_sensors", Detail: fmt.Sprintf("registered_sensors=%d", ev.Sensors), Verifiable: true},
			},
			Gap: "Anomaly-detection coverage is not independently audited — self-attested.",
		},
		{
			ID:          "CC7.3",
			Description: "Security Event Audit Trail Integrity",
			// Machine-verifiable: tamper-evident decision chain must verify AND be
			// non-empty. THE evidence-backed control of this report.
			Status:   ev.recordKeepingStatus(),
			Evidence: chainEv,
			Gap:      ev.recordKeepingGap(),
		},
	}

	return &ComplianceData{
		Framework:    "SOC 2 Common Criteria (self-assessment)",
		GeneratedAt:  time.Now(),
		Assessment:   "self-assessment (no external audit)",
		Requirements: requirements,
		Overall:      overallStatus(requirements),
	}, nil
}

// Compliance status values (WS8). Only ComplianceCompliant is backed by a live,
// machine-verifiable signal; the others honestly mark the absence of independent
// validation (SELF_ATTESTED) or of any programmatic evidence (NOT_ASSESSED).
const (
	ComplianceCompliant    = "COMPLIANT"
	CompliancePartial      = "PARTIAL"
	ComplianceNonCompliant = "NON_COMPLIANT"
	// ComplianceSelfAttested: the control genuinely exists but has NOT been
	// validated by an external audit. Not a claim of conformity.
	ComplianceSelfAttested = "SELF_ATTESTED"
	// ComplianceNotAssessed: this service holds no evidence to evaluate the control.
	ComplianceNotAssessed = "NOT_ASSESSED"
)

// ComplianceData holds an EU AI Act compliance report (§12.3).
type ComplianceData struct {
	Framework    string                  `json:"framework"`
	GeneratedAt  time.Time               `json:"generated_at"`
	Assessment   string                  `json:"assessment"` // honesty disclaimer (WS8)
	Requirements []ComplianceRequirement `json:"requirements"`
	Overall      string                  `json:"overall"`
}

// ComplianceRequirement is a single compliance check. Evidence (IMP8) is the
// list of live signals the Status was judged on, so a reader can audit the
// verdict instead of trusting the label.
type ComplianceRequirement struct {
	ID          string         `json:"id"`
	Description string         `json:"description"`
	Status      string         `json:"status"` // COMPLIANT, PARTIAL, NON_COMPLIANT, SELF_ATTESTED, NOT_ASSESSED
	Evidence    []EvidenceItem `json:"evidence,omitempty"`
	Gap         string         `json:"gap,omitempty"`
}

// EvidenceItem is one piece of machine-derived evidence attached to a compliance
// requirement (IMP8). Source names the live subsystem it came from (e.g.
// "decision_chain", "soc_metrics"); Detail carries the actual measured value
// (e.g. "integrity=VERIFIED entries=42 head=ab12…"); Verifiable is true when the
// detail is a value this service derived from the running system right now (as
// opposed to a static pointer to an out-of-band artifact such as an endpoint URL).
type EvidenceItem struct {
	Source     string `json:"source"`
	Detail     string `json:"detail"`
	Verifiable bool   `json:"verifiable"`
}

// chainEvidence renders the decision-chain integrity signals as structured
// evidence items. The head-hash is truncated to a short prefix — enough to anchor
// the report to a specific chain state without dumping the full digest.
func (ev *complianceEvidence) chainEvidence() []EvidenceItem {
	integrity := "BROKEN"
	if ev.ChainValid {
		integrity = "VERIFIED"
	}
	keyed := "sha256"
	if ev.ChainKeyed {
		keyed = "hmac-sha256"
	}
	detail := fmt.Sprintf("integrity=%s entries=%d head=%s keying=%s",
		integrity, ev.ChainLength, shortHash(ev.ChainHeadHash), keyed)
	if !ev.ChainValid && ev.ChainBrokenLine > 0 {
		detail += fmt.Sprintf(" broken_at_line=%d", ev.ChainBrokenLine)
	}
	return []EvidenceItem{
		{Source: "decision_chain", Detail: detail, Verifiable: true},
		{Source: "decisions.log", Detail: fmt.Sprintf("chain_valid=%t chain_length=%d", ev.ChainValid, ev.ChainLength), Verifiable: true},
	}
}

// recordKeepingStatus is COMPLIANT only when the chain VERIFIES over a non-empty
// log; otherwise NON_COMPLIANT. This is the truthful-degradation contract: a
// broken OR empty chain can never report COMPLIANT.
func (ev *complianceEvidence) recordKeepingStatus() string {
	return boolToCompliance(ev.ChainValid && ev.ChainLength > 0)
}

// chainGap explains a non-VERIFIED chain for the data-governance requirement.
func (ev *complianceEvidence) chainGap() string {
	if ev.ChainValid {
		return ""
	}
	if ev.ChainLength == 0 {
		return "Decision chain is empty — no tamper-evident record to verify."
	}
	return fmt.Sprintf("Decision-chain integrity check FAILED at line %d — record may be tampered.", ev.ChainBrokenLine)
}

// recordKeepingGap explains a non-COMPLIANT record-keeping verdict.
func (ev *complianceEvidence) recordKeepingGap() string {
	if ev.ChainValid && ev.ChainLength > 0 {
		return ""
	}
	if ev.ChainLength == 0 {
		return "No append-only decision records exist yet — record-keeping cannot be evidenced."
	}
	return fmt.Sprintf("Decision-chain integrity FAILED at line %d — record-keeping integrity not assured.", ev.ChainBrokenLine)
}

// shortHash returns a stable short prefix of a chain hash for display, preserving
// any "<keyID>:" prefix so a keyed chain is recognizable. Empty/GENESIS pass through.
func shortHash(h string) string {
	if h == "" {
		return "none"
	}
	prefix := ""
	if i := strings.IndexByte(h, ':'); i > 0 && i < len(h)-1 {
		prefix = h[:i+1] // keep "k1:" so keyed heads are distinguishable
		h = h[i+1:]
	}
	if len(h) > 12 {
		h = h[:12]
	}
	return prefix + h
}

func boolToCompliance(ok bool) string {
	if ok {
		return ComplianceCompliant
	}
	return ComplianceNonCompliant
}

// overallStatus rolls up requirement statuses HONESTLY (WS8): the overall result
// is only COMPLIANT when EVERY requirement is COMPLIANT (machine-verified). Any
// NON_COMPLIANT dominates; otherwise the presence of PARTIAL / SELF_ATTESTED /
// NOT_ASSESSED degrades the overall to the most honest non-conformant label so we
// never assert blanket compliance that isn't backed by evidence.
func overallStatus(reqs []ComplianceRequirement) string {
	allCompliant := true
	hasPartial := false
	hasUnbacked := false // SELF_ATTESTED or NOT_ASSESSED
	for _, r := range reqs {
		switch r.Status {
		case ComplianceNonCompliant:
			return ComplianceNonCompliant
		case ComplianceCompliant:
			// evidence-backed; no degradation
		case CompliancePartial:
			hasPartial = true
			allCompliant = false
		default: // SELF_ATTESTED, NOT_ASSESSED, or any unknown status
			hasUnbacked = true
			allCompliant = false
		}
	}
	switch {
	case allCompliant:
		return ComplianceCompliant
	case hasUnbacked:
		// Not externally validated end-to-end — report the honest aggregate.
		return ComplianceSelfAttested
	case hasPartial:
		return CompliancePartial
	default:
		return ComplianceCompliant
	}
}

// ExportIncidents converts all current incidents into portable SyncIncident format
// for P2P synchronization (§10 T-01).
func (s *Service) ExportIncidents(sourcePeerID string) []peer.SyncIncident {
	s.mu.RLock()
	defer s.mu.RUnlock()

	incidents, err := s.repo.ListIncidents("", "", 1000)
	if err != nil || len(incidents) == 0 {
		return nil
	}

	result := make([]peer.SyncIncident, 0, len(incidents))
	for _, inc := range incidents {
		result = append(result, peer.SyncIncident{
			ID:              inc.ID,
			Status:          string(inc.Status),
			Severity:        string(inc.Severity),
			Title:           inc.Title,
			Description:     inc.Description,
			EventCount:      inc.EventCount,
			CorrelationRule: inc.CorrelationRule,
			KillChainPhase:  inc.KillChainPhase,
			MITREMapping:    inc.MITREMapping,
			CreatedAt:       inc.CreatedAt,
			SourcePeerID:    sourcePeerID,
		})
	}
	return result
}

// ImportIncidents ingests incidents from a trusted peer (§10 T-01).
// Uses UPDATE-or-INSERT semantics: new incidents are created, existing IDs are skipped.
// Returns the number of newly imported incidents.
func (s *Service) ImportIncidents(incidents []peer.SyncIncident) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	imported := 0
	for _, si := range incidents {
		// Skip incidents that already exist locally — the documented
		// "existing IDs are skipped" semantics. Without this, re-importing
		// an overlapping batch (the normal case on every P2P sync cycle)
		// hits a UNIQUE-constraint error in InsertIncident and aborts the
		// whole remaining batch.
		if existing, err := s.repo.GetIncident(si.ID); err == nil && existing != nil {
			continue
		}

		// Convert back to domain incident.
		inc := domsoc.Incident{
			ID:              si.ID,
			Status:          domsoc.IncidentStatus(si.Status),
			Severity:        domsoc.EventSeverity(si.Severity),
			Title:           fmt.Sprintf("[P2P:%s] %s", si.SourcePeerID, si.Title),
			Description:     si.Description,
			EventCount:      si.EventCount,
			CorrelationRule: si.CorrelationRule,
			KillChainPhase:  si.KillChainPhase,
			MITREMapping:    si.MITREMapping,
			CreatedAt:       si.CreatedAt,
			UpdatedAt:       time.Now(),
		}
		err := s.repo.InsertIncident(inc)
		if err != nil {
			return imported, fmt.Errorf("import incident %s: %w", si.ID, err)
		}
		imported++
	}

	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "P2P_INCIDENT_SYNC",
			fmt.Sprintf("imported=%d total=%d", imported, len(incidents)))
	}
	return imported, nil
}

// waitlistHashSalt provides domain separation for the waitlist-email hash that
// goes into the immutable audit chain (Review 14.06 round-5). Not a secret; it
// just keeps the chain hashes from matching generic email rainbow tables.
const waitlistHashSalt = "syntrex-waitlist-v1"

// AddWaitlistEntry records a pre-signup registration interest. The cleartext (email
// + company + use_case) is persisted to the DELETABLE soc_waitlist store so the
// business can contact signups while the PII stays erasable (GDPR Art.17, see
// DeleteWaitlistEntry). The IMMUTABLE decision chain gets only a salted hash (it
// attests a signup occurred without the cleartext), and the application log gets NO
// cleartext — closing the round-6 B-2 PII-in-logs gap. Returns a persist error (the
// caller still has the audit-chain hash) so lost leads are visible.
func (s *Service) AddWaitlistEntry(email, company, useCase string) error {
	h := sha256.Sum256([]byte(waitlistHashSalt + email))
	emailHash := hex.EncodeToString(h[:])
	if s.logger != nil {
		s.logger.Record(audit.ModuleSOC, "WAITLIST:NEW",
			fmt.Sprintf("email_sha256=%s", emailHash))
	}
	var err error
	if s.repo != nil {
		err = s.repo.AddWaitlistEntry(domsoc.NewWaitlistEntry(email, company, useCase, time.Now()))
	}
	// No cleartext PII in the application log — only a non-PII correlation prefix.
	slog.Info("waitlist entry recorded", "email_sha256_prefix", emailHash[:12])
	return err
}

// ListWaitlist returns waitlist entries newest-first so the business can contact
// signups. The result contains cleartext PII — callers must handle it accordingly.
func (s *Service) ListWaitlist(limit int) ([]domsoc.WaitlistEntry, error) {
	if s.repo == nil {
		return nil, nil
	}
	return s.repo.ListWaitlist(limit)
}

// DeleteWaitlistEntry erases every waitlist row for an email — the GDPR Art.17
// erasure path for a pre-signup subject. Returns the number of rows deleted.
func (s *Service) DeleteWaitlistEntry(email string) (int64, error) {
	if s.repo == nil {
		return 0, nil
	}
	return s.repo.DeleteWaitlistByEmail(email)
}
