package soc

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ActionExecutor defines the interface for playbook action handlers.
// Each executor implements a specific action type (webhook, block_ip, log, etc.)
type ActionExecutor interface {
	// Type returns the action type this executor handles (e.g., "webhook", "block_ip", "log").
	Type() string
	// Execute runs the action with the given parameters.
	// Returns a result summary or error.
	Execute(params ActionParams) (string, error)
}

// ActionParams contains the context passed to an action executor.
type ActionParams struct {
	IncidentID  string         `json:"incident_id"`
	Severity    EventSeverity  `json:"severity"`
	Category    string         `json:"category"`
	Description string         `json:"description"`
	EventCount  int            `json:"event_count"`
	RuleName    string         `json:"rule_name"`
	Extra       map[string]any `json:"extra,omitempty"`
}

// ExecutorRegistry manages registered action executors.
type ExecutorRegistry struct {
	mu        sync.RWMutex
	executors map[string]ActionExecutor
}

// NewExecutorRegistry creates a registry with the default LogExecutor.
func NewExecutorRegistry() *ExecutorRegistry {
	reg := &ExecutorRegistry{
		executors: make(map[string]ActionExecutor),
	}
	reg.Register(&LogExecutor{})
	return reg
}

// Register adds an executor to the registry.
func (r *ExecutorRegistry) Register(exec ActionExecutor) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.executors[exec.Type()] = exec
}

// Execute runs the named action. Returns error if executor not found.
func (r *ExecutorRegistry) Execute(actionType string, params ActionParams) (string, error) {
	r.mu.RLock()
	exec, ok := r.executors[actionType]
	r.mu.RUnlock()

	if !ok {
		return "", fmt.Errorf("executor not found: %s", actionType)
	}
	return exec.Execute(params)
}

// List returns all registered executor types.
func (r *ExecutorRegistry) List() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	types := make([]string, 0, len(r.executors))
	for t := range r.executors {
		types = append(types, t)
	}
	return types
}

// --- Built-in Executors ---

// LogExecutor logs the action (default, always available).
type LogExecutor struct{}

func (e *LogExecutor) Type() string { return "log" }

func (e *LogExecutor) Execute(params ActionParams) (string, error) {
	slog.Info("playbook action executed",
		"type", "log",
		"incident_id", params.IncidentID,
		"severity", params.Severity,
		"category", params.Category,
		"rule", params.RuleName,
	)
	return "logged", nil
}

// WebhookExecutor sends HTTP POST to a webhook URL (Slack, PagerDuty, etc.)
type WebhookExecutor struct {
	URL     string
	Headers map[string]string
	client  *http.Client
}

// NewWebhookExecutor creates a webhook executor for the given URL.
func NewWebhookExecutor(url string, headers map[string]string) *WebhookExecutor {
	return &WebhookExecutor{
		URL:     url,
		Headers: headers,
		client: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				DialContext: SafeDialContext,
			},
		},
	}
}

func (e *WebhookExecutor) Type() string { return "webhook" }

func (e *WebhookExecutor) Execute(params ActionParams) (string, error) {
	payload, err := json.Marshal(map[string]any{
		"incident_id": params.IncidentID,
		"severity":    params.Severity,
		"category":    params.Category,
		"description": params.Description,
		"event_count": params.EventCount,
		"rule_name":   params.RuleName,
		"timestamp":   time.Now().Format(time.RFC3339),
		"source":      "sentinel-soc",
	})
	if err != nil {
		return "", fmt.Errorf("webhook: marshal: %w", err)
	}

	if err := ValidateWebhookURL(e.URL); err != nil {
		slog.Error("webhook delivery blocked (SSRF attempt)", "url", e.URL, "error", err)
		return "", fmt.Errorf("webhook ssrf blocked: %w", err)
	}

	req, err := http.NewRequest(http.MethodPost, e.URL, bytes.NewReader(payload))
	if err != nil {
		return "", fmt.Errorf("webhook: create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	for k, v := range e.Headers {
		req.Header.Set(k, v)
	}

	resp, err := e.client.Do(req)
	if err != nil {
		slog.Error("webhook delivery failed", "url", e.URL, "error", err)
		return "", fmt.Errorf("webhook: send: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		slog.Warn("webhook returned error", "url", e.URL, "status", resp.StatusCode)
		return "", fmt.Errorf("webhook: HTTP %d", resp.StatusCode)
	}

	slog.Info("webhook delivered", "url", e.URL, "status", resp.StatusCode,
		"incident_id", params.IncidentID)
	return fmt.Sprintf("webhook: HTTP %d", resp.StatusCode), nil
}

// BlockIPExecutor enforces a firewall block by delegating to a Firewall backend.
//
// HONESTY (audit #38): the previous stub returned "success" without blocking.
// This executor returns a SUCCESS string only when the backend reports
// enforced=true (a kernel rule was installed or a cloud-FW API accepted it).
// When the backend is log-only or cannot enforce (e.g. Windows dev, missing
// NET_ADMIN), Execute returns an ERROR so PlaybookEngine records the run as
// partial_failure — the SOC never claims a block it did not perform.
type BlockIPExecutor struct {
	fw Firewall
}

// NewBlockIPExecutor builds a block_ip executor backed by fw. A nil fw defaults
// to the honest LogOnlyFirewall (reports not-enforced) for backward compat.
func NewBlockIPExecutor(fw Firewall) *BlockIPExecutor {
	if fw == nil {
		fw = &LogOnlyFirewall{}
	}
	return &BlockIPExecutor{fw: fw}
}

func (e *BlockIPExecutor) Type() string { return "block_ip" }

func (e *BlockIPExecutor) Execute(params ActionParams) (string, error) {
	// Backward compat: a zero-value &BlockIPExecutor{} has no backend.
	if e.fw == nil {
		e.fw = &LogOnlyFirewall{}
	}

	ip, _ := params.Extra["ip"].(string)
	if ip == "" {
		return "", fmt.Errorf("block_ip: missing ip in extra params")
	}

	// duration is in seconds (matches playbook.go pb defaults: 3600 / 86400).
	ttl := time.Hour
	if durStr, ok := params.Extra["duration"].(string); ok && durStr != "" {
		if secs, err := strconv.Atoi(strings.TrimSpace(durStr)); err == nil && secs > 0 {
			ttl = time.Duration(secs) * time.Second
		}
	}

	reason := params.Category
	if reason == "" {
		reason = params.RuleName
	}

	enforced, detail, err := e.fw.Block(ip, ttl, reason)
	if err != nil {
		slog.Error("block_ip: backend error", "ip", ip, "backend", e.fw.Type(),
			"incident_id", params.IncidentID, "error", err)
		return "", fmt.Errorf("block_ip: %s backend failed for %s: %w", e.fw.Type(), ip, err)
	}
	if !enforced {
		// Not a fake success: surface as an error so the playbook run is recorded
		// partial_failure and an operator sees block_ip did NOT take effect.
		return "", fmt.Errorf("block_ip: NOT enforced (%s): %s", e.fw.Type(), detail)
	}

	slog.Warn("block_ip: enforced", "ip", ip, "backend", e.fw.Type(),
		"ttl", ttl.String(), "incident_id", params.IncidentID, "detail", detail)
	return fmt.Sprintf("block_ip: %s BLOCKED via %s for %s", ip, e.fw.Type(), ttl), nil
}

// NotifyExecutor sends a formatted alert notification via HTTP POST.
// Supports Slack, Telegram, PagerDuty, or any webhook-compatible endpoint.
type NotifyExecutor struct {
	DefaultURL string
	Headers    map[string]string
	client     *http.Client
}

// NewNotifyExecutor creates a notification executor with a default webhook URL.
func NewNotifyExecutor(url string) *NotifyExecutor {
	return &NotifyExecutor{
		DefaultURL: url,
		client: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				DialContext: SafeDialContext,
			},
		},
	}
}

func (e *NotifyExecutor) Type() string { return "notify" }

func (e *NotifyExecutor) Execute(params ActionParams) (string, error) {
	channel, _ := params.Extra["channel"].(string)
	if channel == "" {
		channel = "soc-alerts"
	}

	url := e.DefaultURL
	if customURL, ok := params.Extra["webhook_url"].(string); ok && customURL != "" {
		url = customURL
	}

	// Build structured alert payload (Slack-compatible format)
	sevEmoji := map[EventSeverity]string{
		SeverityCritical: "🔴", SeverityHigh: "🟠",
		SeverityMedium: "🟡", SeverityLow: "🔵", SeverityInfo: "⚪",
	}
	emoji := sevEmoji[params.Severity]
	if emoji == "" {
		emoji = "⚠️"
	}

	payload := map[string]any{
		"text": fmt.Sprintf("%s *[%s] %s*\nIncident: `%s` | Events: %d\n%s",
			emoji, params.Severity, params.Category,
			params.IncidentID, params.EventCount, params.Description),
		"channel":  channel,
		"username": "SYNTREX SOC",
		// Slack blocks for rich formatting
		"blocks": []map[string]any{
			{
				"type": "section",
				"text": map[string]string{
					"type": "mrkdwn",
					"text": fmt.Sprintf("%s *%s Alert — %s*", emoji, params.Severity, params.Category),
				},
			},
			{
				"type": "section",
				"fields": []map[string]string{
					{"type": "mrkdwn", "text": fmt.Sprintf("*Incident:*\n`%s`", params.IncidentID)},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Events:*\n%d", params.EventCount)},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Rule:*\n%s", params.RuleName)},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Severity:*\n%s", params.Severity)},
				},
			},
		},
	}

	if url == "" {
		// No webhook configured — log and succeed (graceful degradation)
		slog.Info("notify: no webhook URL configured, logging alert",
			"channel", channel, "incident_id", params.IncidentID, "severity", params.Severity)
		return fmt.Sprintf("notify: logged to channel=%s (no webhook URL)", channel), nil
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("notify: marshal: %w", err)
	}

	if err := ValidateWebhookURL(url); err != nil {
		slog.Error("notify: delivery blocked (SSRF attempt)", "url", url, "error", err)
		return "", fmt.Errorf("notify ssrf blocked: %w", err)
	}

	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("notify: create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	for k, v := range e.Headers {
		req.Header.Set(k, v)
	}

	resp, err := e.client.Do(req)
	if err != nil {
		slog.Error("notify: delivery failed", "url", url, "error", err)
		return "", fmt.Errorf("notify: send: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("notify: HTTP %d from %s", resp.StatusCode, url)
	}

	slog.Info("notify: alert delivered",
		"channel", channel, "url", url, "status", resp.StatusCode,
		"incident_id", params.IncidentID)
	return fmt.Sprintf("notify: delivered to %s (HTTP %d)", channel, resp.StatusCode), nil
}

// QuarantineExecutor marks a session or IP as quarantined.
// Maintains an in-memory blocklist and logs quarantine actions.
type QuarantineExecutor struct {
	mu        sync.RWMutex
	blocklist map[string]time.Time // IP/session → quarantine expiry
}

func NewQuarantineExecutor() *QuarantineExecutor {
	return &QuarantineExecutor{
		blocklist: make(map[string]time.Time),
	}
}

func (e *QuarantineExecutor) Type() string { return "quarantine" }

func (e *QuarantineExecutor) Execute(params ActionParams) (string, error) {
	scope, _ := params.Extra["scope"].(string)
	if scope == "" {
		scope = "session"
	}

	target, _ := params.Extra["target"].(string)
	if target == "" {
		target, _ = params.Extra["ip"].(string)
	}
	if target == "" {
		target = params.IncidentID // Quarantine by incident
	}

	duration := 1 * time.Hour
	if durStr, ok := params.Extra["duration"].(string); ok {
		if d, err := time.ParseDuration(durStr); err == nil {
			duration = d
		}
	}

	e.mu.Lock()
	e.blocklist[target] = time.Now().Add(duration)
	e.mu.Unlock()

	slog.Warn("quarantine: target isolated",
		"scope", scope,
		"target", target,
		"duration", duration,
		"incident_id", params.IncidentID,
		"severity", params.Severity,
	)
	return fmt.Sprintf("quarantine: %s=%s isolated for %s", scope, target, duration), nil
}

// IsQuarantined checks if a target is currently quarantined.
func (e *QuarantineExecutor) IsQuarantined(target string) bool {
	e.mu.RLock()
	defer e.mu.RUnlock()
	expiry, ok := e.blocklist[target]
	if !ok {
		return false
	}
	if time.Now().After(expiry) {
		return false
	}
	return true
}

// QuarantinedTargets returns all currently active quarantines.
func (e *QuarantineExecutor) QuarantinedTargets() map[string]time.Time {
	e.mu.RLock()
	defer e.mu.RUnlock()
	now := time.Now()
	active := make(map[string]time.Time)
	for target, expiry := range e.blocklist {
		if now.Before(expiry) {
			active[target] = expiry
		}
	}
	return active
}

// EscalateExecutor auto-assigns incidents and fires escalation webhooks.
type EscalateExecutor struct {
	EscalationURL string // Webhook URL for escalation alerts (PagerDuty, etc.)
	client        *http.Client
}

func NewEscalateExecutor(url string) *EscalateExecutor {
	return &EscalateExecutor{
		EscalationURL: url,
		client: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				DialContext: SafeDialContext,
			},
		},
	}
}

func (e *EscalateExecutor) Type() string { return "escalate" }

func (e *EscalateExecutor) Execute(params ActionParams) (string, error) {
	team, _ := params.Extra["team"].(string)
	if team == "" {
		team = "soc-team"
	}

	slog.Warn("escalate: incident escalated",
		"team", team,
		"incident_id", params.IncidentID,
		"severity", params.Severity,
		"category", params.Category,
	)

	// Fire escalation webhook if configured
	if e.EscalationURL != "" {
		// SEC-V12: Prevent SSRF via the Escalate Executor
		if err := ValidateWebhookURL(e.EscalationURL); err != nil {
			slog.Error("escalate: delivery blocked (SSRF attempt)", "url", e.EscalationURL, "error", err)
			return "", fmt.Errorf("escalate ssrf blocked: %w", err)
		}

		payload, _ := json.Marshal(map[string]any{
			"event_type":  "escalation",
			"incident_id": params.IncidentID,
			"severity":    params.Severity,
			"category":    params.Category,
			"team":        team,
			"description": params.Description,
			"timestamp":   time.Now().Format(time.RFC3339),
			"source":      "syntrex-soc",
		})

		req, err := http.NewRequest(http.MethodPost, e.EscalationURL, bytes.NewReader(payload))
		if err == nil {
			req.Header.Set("Content-Type", "application/json")
			if resp, err := e.client.Do(req); err == nil {
				resp.Body.Close()
				slog.Info("escalate: webhook delivered", "url", e.EscalationURL, "status", resp.StatusCode)
			} else {
				slog.Error("escalate: webhook failed", "url", e.EscalationURL, "error", err)
			}
		}
	}

	return fmt.Sprintf("escalate: assigned to team=%s", team), nil
}

// --- ExecutorActionHandler bridges PlaybookEngine → ExecutorRegistry ---

// ExecutorActionHandler implements ActionHandler by delegating to ExecutorRegistry.
// This is the bridge that makes playbook actions actually execute real handlers.
type ExecutorActionHandler struct {
	Registry *ExecutorRegistry
	// Metrics, when set, records block_ip enforcement outcomes at the source
	// (IMP7) — enforced vs not_enforced vs error — so the SOC plane reports
	// whether automated blocks actually take effect, not just that they ran.
	Metrics *SOCMetrics
}

func (h *ExecutorActionHandler) Handle(action PlaybookAction, ctx ActionContext) error {
	// IMP6: carry the incident context into ActionParams so notify/webhook/escalate
	// emit the REAL severity/category/rule/description/count instead of blank
	// fields, and block_ip can read the target IP threaded via the action params.
	params := ActionParams{
		IncidentID:  ctx.IncidentID,
		Severity:    EventSeverity(ctx.Severity),
		Category:    ctx.Category,
		Description: ctx.Description,
		EventCount:  ctx.EventCount,
		RuleName:    ctx.RuleName,
		Extra:       make(map[string]any),
	}
	// Action-level params (e.g. duration, channel, team, ip) override/augment via Extra.
	for k, v := range action.Params {
		params.Extra[k] = v
	}

	result, err := h.Registry.Execute(action.Type, params)
	if action.Type == "block_ip" && h.Metrics != nil {
		h.Metrics.RecordBlockIP(blockIPOutcome(result, err))
	}
	if err != nil {
		slog.Error("playbook action failed",
			"type", action.Type,
			"incident_id", ctx.IncidentID,
			"error", err,
		)
		return err
	}
	slog.Info("playbook action executed",
		"type", action.Type,
		"incident_id", ctx.IncidentID,
		"result", result,
	)
	return nil
}

// blockIPOutcome maps a block_ip executor result/error to a bounded metric label.
// The BlockIPExecutor returns a "...BLOCKED..." string only when the firewall
// backend actually enforced; a not-enforced log-only backend returns an error
// containing "NOT enforced"; any other error is a backend failure.
func blockIPOutcome(result string, err error) string {
	if err == nil && strings.Contains(result, "BLOCKED") {
		return "enforced"
	}
	if err != nil && strings.Contains(err.Error(), "NOT enforced") {
		return "not_enforced"
	}
	return "error"
}
