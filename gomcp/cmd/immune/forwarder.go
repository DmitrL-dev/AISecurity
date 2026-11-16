package main

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/syntrex/gomcp/internal/application/sidecar"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// socForwarder forwards guard violations to the SOC Event Bus as real SOC events.
//
// HONESTY CONTRACT: when no bus URL is configured the forwarder is an explicit
// no-op that WARNS once at startup and never silently drops violations into a
// void. It NEVER fabricates delivery — a failed POST is logged, not swallowed as
// success. The wire format is identical to every other sensor (the shared
// sidecar.BusClient → POST /api/v1/soc/events), so immune violations land in the
// same pipeline (auth → secret scan → correlate → playbook) as core/shield.
type socForwarder struct {
	client  *sidecar.BusClient // nil when no bus URL configured
	busURL  string
	logger  *slog.Logger
	enabled bool
}

// newSOCForwarder builds a forwarder. If busURL is empty the forwarder is
// disabled (honest no-op). sensorID/sensorKey are sent so the SOC can attribute
// and (optionally) PSK-authenticate the immune sensor.
func newSOCForwarder(busURL, sensorID, sensorKey string, logger *slog.Logger) *socForwarder {
	f := &socForwarder{busURL: busURL, logger: logger}
	if busURL == "" {
		logger.Warn("SOC forwarding DISABLED: SOC_BUS_URL not set — guard violations are logged locally only, NOT sent to the SOC. " +
			"Set SOC_BUS_URL=http://<soc-host>:9100 to forward violations as SOC events.")
		return f
	}
	f.client = sidecar.NewBusClient(busURL, sensorID, sensorKey)
	f.enabled = true
	logger.Info("SOC forwarding enabled", "bus_url", busURL, "sensor_id", sensorID, "endpoint", "/api/v1/soc/events")
	return f
}

// Forward sends a single violation to the SOC. It is safe to call from the
// violation handler (called inline from recordViolation). On the disabled path
// it returns immediately. Errors are logged — the agent keeps running.
func (f *socForwarder) Forward(v guard.Violation) {
	if !f.enabled || f.client == nil {
		return
	}
	evt := violationToEvent(v)
	ctx, cancel := context.WithTimeout(context.Background(), 12*time.Second)
	defer cancel()
	if err := f.client.SendEvent(ctx, evt); err != nil {
		f.logger.Error("SOC forward FAILED — violation not delivered to SOC",
			"process", v.ProcessName, "pid", v.PID, "type", v.Type, "error", err)
		return
	}
	f.logger.Debug("violation forwarded to SOC", "process", v.ProcessName, "type", v.Type)
}

// violationToEvent maps a guard.Violation onto the SOC domain event. The mapping
// is honest: Action is reported verbatim in metadata so the SOC sees whether the
// violation was actually blocked vs only logged.
func violationToEvent(v guard.Violation) *domsoc.SOCEvent {
	evt := domsoc.NewSOCEvent(
		domsoc.SourceImmune,
		mapSeverity(v.Severity),
		categoryFor(v.Type),
		fmt.Sprintf("runtime guard: %s", v.Detail),
	)
	evt.Subcategory = v.Type
	evt.Confidence = 0.9 // procfs/eBPF observation of a policy match is high-confidence.
	evt.Metadata = map[string]string{
		"guard_process": v.ProcessName,
		"guard_pid":     fmt.Sprintf("%d", v.PID),
		"guard_type":    v.Type,
		"guard_action":  v.Action, // "logged" | "blocked" | "alerted" — verbatim, never overstated.
		"policy_mode":   string(v.PolicyMode),
		"sensor":        "sec-002-runtime-guard",
	}
	return &evt
}

// mapSeverity converts guard severity strings to SOC event severities.
func mapSeverity(s string) domsoc.EventSeverity {
	switch s {
	case "CRITICAL":
		return domsoc.SeverityCritical
	case "HIGH":
		return domsoc.SeverityHigh
	case "MEDIUM":
		return domsoc.SeverityMedium
	case "LOW":
		return domsoc.SeverityLow
	default:
		return domsoc.SeverityMedium
	}
}

// categoryFor maps a guard violation type to a SOC event category so the
// correlation engine can group runtime-guard signal with related telemetry.
func categoryFor(violationType string) string {
	switch violationType {
	case "syscall":
		return "runtime_syscall_violation"
	case "file":
		return "runtime_file_violation"
	case "network":
		return "exfiltration"
	case "resource":
		return "runtime_resource_violation"
	default:
		return "runtime_guard_violation"
	}
}
