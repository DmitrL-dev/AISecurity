// Package main provides the SOC Respond process (SEC-001 Process Isolation).
//
// Responsibility: Receives incidents from soc-correlate via IPC,
// executes playbooks, dispatches webhooks, writes audit log.
//
// Network access: restricted to outbound HTTPS (webhook endpoints only).
//
// Usage:
//
//	go run ./cmd/soc-respond/
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"runtime/debug"
	"strings"
	"syscall"
	"time"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
	"github.com/syntrex/gomcp/internal/infrastructure/ipc"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
)

// responder bundles the live dependencies shared across incident connections.
type responder struct {
	engine     *domsoc.PlaybookEngine
	auditLog   *audit.DecisionLogger
	webhookURL string
	httpClient *http.Client
	logger     *slog.Logger
}

func main() {
	defer func() {
		if r := recover(); r != nil {
			buf := make([]byte, 4096)
			n := runtime.Stack(buf, false)
			fmt.Fprintf(os.Stderr, "SOC-RESPOND FATAL PANIC: %v\n%s\n", r, buf[:n])
			os.Exit(2)
		}
	}()

	logger := logging.New(env("SOC_LOG_FORMAT", "text"), env("SOC_LOG_LEVEL", "info"))
	slog.SetDefault(logger)

	// SEC-003: Memory safety — respond process uses minimal RAM.
	if limitStr := os.Getenv("GOMEMLIMIT"); limitStr == "" {
		debug.SetMemoryLimit(128 * 1024 * 1024) // 128 MiB
	}

	logger.Info("starting SOC-RESPOND (SEC-001 isolated process)",
		"upstream_pipe", "soc-correlate-to-respond",
	)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Playbook engine for automated response.
	playbookEngine := domsoc.NewPlaybookEngine()

	// WS6 #23: build the REAL executor registry (log/notify/quarantine/escalate/
	// webhook + a firewall-backed block_ip) from env config and install it as the
	// playbook handler — the responder previously kept the default LogHandler, so
	// nothing actually executed. The SAME BuildSOARRegistry helper the in-process
	// server uses keeps the two topologies in lockstep, incl. honest defaults
	// (block_ip log-only until SOC_FIREWALL_BACKEND is set).
	soarCfg := appsoc.SOARConfig{
		Firewall: domsoc.FirewallConfig{
			Backend:    env("SOC_FIREWALL_BACKEND", ""),
			ChainOrSet: env("SOC_FIREWALL_SET", env("SOC_FIREWALL_CHAIN", "")),
			Table:      env("SOC_FIREWALL_TABLE", ""),
			APIURL:     env("SOC_FIREWALL_API_URL", ""),
			APIToken:   env("SOC_FIREWALL_API_TOKEN", ""),
		},
		NotifyURL:   env("SOC_NOTIFY_URL", ""),
		EscalateURL: env("SOC_ESCALATE_URL", ""),
		WebhookURL:  env("SOC_WEBHOOK_URL", ""),
	}
	reg := appsoc.BuildSOARRegistry(soarCfg)
	playbookEngine.SetHandler(&domsoc.ExecutorActionHandler{Registry: reg})
	logger.Info("SOAR executors wired", "executors", reg.List())
	if soarCfg.Firewall.Backend == "" {
		logger.Warn("SOC_FIREWALL_BACKEND not set — block_ip is LOG-ONLY (will NOT block IPs); set it to enforce")
	}

	// WS6 #23: audit logger for the isolated responder. Fail CLOSED on a keyless
	// chain in the same way the in-process server does (the audit chain must be
	// HMAC-keyed to be tamper-evident); allow the unsigned dev chain only on
	// explicit opt-in.
	auditDir := env("SOC_AUDIT_DIR", ".")
	auditLog, err := audit.NewDecisionLogger(auditDir)
	if err != nil {
		logger.Error("decision logger init failed", "error", err)
		os.Exit(1)
	}
	if auditLog != nil && !auditLog.HMACEnabled() && os.Getenv("SOC_ALLOW_UNSIGNED_AUDIT") != "1" {
		logger.Error("SOC_HMAC_SECRET not set — the responder audit chain would be keyless (forgeable). " +
			"Set SOC_HMAC_SECRET (>=32 bytes), or SOC_ALLOW_UNSIGNED_AUDIT=1 for the unsigned dev chain.")
		os.Exit(1)
	}

	// WS6 #23: webhook dispatch — outbound HTTPS only (SEC-001). SSRF-guarded.
	webhookURL := env("SOC_RESPOND_WEBHOOK_URL", "")
	if webhookURL == "" {
		logger.Info("SOC_RESPOND_WEBHOOK_URL not set — incident webhook dispatch is a logged no-op (no fake sends)")
	}

	r := &responder{
		engine:     playbookEngine,
		auditLog:   auditLog,
		webhookURL: webhookURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				DialContext: domsoc.SafeDialContext,
			},
		},
		logger: logger,
	}

	// IPC: Listen for incidents from soc-correlate.
	listener, err := ipc.Listen("soc-correlate-to-respond")
	if err != nil {
		logger.Error("failed to listen", "error", err)
		os.Exit(1)
	}
	defer listener.Close()
	logger.Info("IPC listener ready", "pipe", "soc-correlate-to-respond")

	// Accept connections from correlate.
	go func() {
		for {
			conn, err := listener.Accept()
			if err != nil {
				if ctx.Err() != nil {
					return
				}
				logger.Error("accept failed", "error", err)
				continue
			}

			go r.handleCorrelateConnection(ctx, conn)
		}
	}()

	<-ctx.Done()
	logger.Info("SOC-RESPOND shutting down")
}

// handleCorrelateConnection processes incidents from soc-correlate.
func (r *responder) handleCorrelateConnection(ctx context.Context, conn net.Conn) {
	defer conn.Close()
	receiver := ipc.NewReceiver(conn, "correlate")

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		msg, err := receiver.Next()
		if err == io.EOF {
			r.logger.Info("correlate connection closed")
			return
		}
		if err != nil {
			r.logger.Error("read incident", "error", err)
			continue
		}

		if msg.Type != ipc.SOCMsgIncident {
			continue
		}

		var incident domsoc.Incident
		if err := json.Unmarshal(msg.Payload, &incident); err != nil {
			r.logger.Error("unmarshal incident", "error", err)
			continue
		}

		r.processIncident(ctx, incident)
	}
}

// processIncident runs matching playbooks, dispatches the webhook, and writes
// the audit record for a single incident.
func (r *responder) processIncident(ctx context.Context, incident domsoc.Incident) {
	r.logger.Info("incident received for response",
		"id", incident.ID,
		"severity", incident.Severity,
		"correlation_rule", incident.CorrelationRule,
		"kill_chain_phase", incident.KillChainPhase,
	)

	// WS6 #23: actually MATCH + EXECUTE via the engine (was: log every enabled
	// playbook without matching). Execute() runs matches() internally so only
	// triggering playbooks fire, and they run the real executors. The Incident
	// has no Category field, so derive it from the correlation rule (the same
	// signal the in-process path uses via event.Category).
	category := deriveCategory(incident)
	execs := r.engine.Execute(incident.ID, string(incident.Severity), category, incident.KillChainPhase)

	for _, ex := range execs {
		r.logger.Info("playbook executed",
			"playbook", ex.PlaybookID,
			"incident", incident.ID,
			"status", ex.Status,
			"actions_run", ex.ActionsRun,
			"error", ex.Error,
		)
	}
	if len(execs) == 0 {
		r.logger.Info("no playbook matched incident", "incident", incident.ID)
	}

	// WS6 #23: webhook dispatch (outbound HTTPS only).
	r.notifyIncident(ctx, incident, execs)

	// WS6 #23: audit write.
	r.writeAudit(incident, execs)
}

// deriveCategory extracts a category signal from the incident for playbook
// matching. The correlation rule name typically encodes the threat class
// (e.g. "jailbreak", "exfiltration"); fall back to lowercased rule text.
func deriveCategory(incident domsoc.Incident) string {
	rule := strings.ToLower(incident.CorrelationRule)
	for _, cat := range []string{"jailbreak", "exfiltration", "injection", "c2", "command_control"} {
		if strings.Contains(rule, cat) {
			return cat
		}
	}
	return rule
}

// notifyIncident POSTs an incident summary to SOC_RESPOND_WEBHOOK_URL if set.
// SSRF-guarded; when unset it is an honest logged no-op (never a fake send).
func (r *responder) notifyIncident(ctx context.Context, incident domsoc.Incident, execs []domsoc.PlaybookExecution) {
	if r.webhookURL == "" {
		r.logger.Info("webhook dispatch skipped (SOC_RESPOND_WEBHOOK_URL unset)", "incident", incident.ID)
		return
	}
	if err := domsoc.ValidateWebhookURL(r.webhookURL); err != nil {
		r.logger.Error("webhook dispatch blocked (SSRF)", "url", r.webhookURL, "error", err)
		return
	}

	playbooks := make([]map[string]any, 0, len(execs))
	for _, ex := range execs {
		playbooks = append(playbooks, map[string]any{
			"playbook": ex.PlaybookID,
			"status":   ex.Status,
			"actions":  ex.ActionsRun,
			"error":    ex.Error,
		})
	}
	payload, err := json.Marshal(map[string]any{
		"event_type":       "incident_response",
		"incident_id":      incident.ID,
		"severity":         incident.Severity,
		"correlation_rule": incident.CorrelationRule,
		"kill_chain_phase": incident.KillChainPhase,
		"playbooks":        playbooks,
		"timestamp":        time.Now().Format(time.RFC3339),
		"source":           "soc-respond",
	})
	if err != nil {
		r.logger.Error("webhook marshal failed", "error", err)
		return
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.webhookURL, bytes.NewReader(payload))
	if err != nil {
		r.logger.Error("webhook request build failed", "error", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "SYNTREX-SOC-Respond/1.0")

	resp, err := r.httpClient.Do(req)
	if err != nil {
		r.logger.Error("webhook delivery failed", "url", r.webhookURL, "error", err)
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		r.logger.Warn("webhook returned error", "url", r.webhookURL, "status", resp.StatusCode)
		return
	}
	r.logger.Info("incident webhook delivered", "incident", incident.ID, "status", resp.StatusCode)
}

// writeAudit records the response outcome to the (HMAC-keyed) decision chain.
func (r *responder) writeAudit(incident domsoc.Incident, execs []domsoc.PlaybookExecution) {
	if r.auditLog == nil {
		return
	}
	parts := make([]string, 0, len(execs))
	for _, ex := range execs {
		s := fmt.Sprintf("%s=%s", ex.PlaybookID, ex.Status)
		if ex.Error != "" {
			s += "(" + ex.Error + ")"
		}
		parts = append(parts, s)
	}
	summary := strings.Join(parts, ",")
	if summary == "" {
		summary = "no_playbook_matched"
	}
	if err := r.auditLog.Record(audit.ModuleSOC,
		"RESPOND_EXECUTED:"+incident.ID,
		fmt.Sprintf("severity=%s rule=%s playbooks=%s",
			incident.Severity, incident.CorrelationRule, summary)); err != nil {
		r.logger.Error("audit write failed", "incident", incident.ID, "error", err)
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
