package httpserver

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"log/slog"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/oracle"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// buildScanSOCEvent constructs the tenant-scoped SOCEvent for a blocked gateway
// scan. The raw prompt is NEVER stored — only a redacted fingerprint (sha256
// prefix + length) — to avoid persisting customer PII/secrets and to avoid the
// ingest secret-scanner rejecting the event. Pure/sync so it is unit-testable.
func buildScanSOCEvent(tenantID, threatType string, confidence float64, prompt string, indicators []string) domsoc.SOCEvent {
	severity := domsoc.SeverityHigh
	if confidence >= 0.9 {
		severity = domsoc.SeverityCritical
	}
	category := threatType
	if category == "" {
		category = "threat_detected"
	}

	sum := sha256.Sum256([]byte(prompt))
	desc := fmt.Sprintf("gateway scan blocked: %s (confidence %.2f, prompt sha256=%s len=%d)",
		category, confidence, hex.EncodeToString(sum[:8]), len(prompt))

	evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, severity, category, desc)
	evt.TenantID = tenantID
	// Per-tenant sensor ID: the ingest pipeline rate-limits per SensorID
	// (§17.3). A single shared "gateway" bucket let a noisy tenant's blocked
	// scans exhaust the rate limit and starve every other tenant's gateway->SOC
	// feed (Review 14.06 round-3). Scoping the sensor to the tenant gives each
	// tenant its own bucket, so one tenant's volume can only throttle itself.
	evt.SensorID = "gateway:" + tenantID
	evt.Confidence = confidence
	if len(indicators) > 0 {
		joined := strings.Join(indicators, ",")
		// SEC defense-in-depth (mega-review 17.06): indicators are engine-derived
		// LABELS today (no raw input), but the ingest secret-scanner INVARIANT only
		// covers Payload — Description/Metadata are never scanned. Guard the metadata
		// here so a future engine that ever echoes raw input into an indicator cannot
		// silently persist a customer secret into the tenant SOC + exports.
		if oracle.ScanForSecrets(joined).HasSecrets {
			slog.Warn("gateway->SOC: an indicator tripped the secret scanner; redacting metadata", "tenant", tenantID)
			joined = "[redacted: indicator matched a secret pattern]"
		}
		evt.Metadata = map[string]string{"indicators": joined}
	}
	// Intentionally NOT setting evt.Payload (the raw prompt) — redaction only.
	return evt
}

// emitScanSOCEvent makes "the gateway IS the sensor" true (MASTER_PLAN R3): a
// blocked scan from an AUTHENTICATED tenant auto-populates that tenant's SOC
// through the full ingest pipeline, fired async so scan latency is unchanged.
// Anonymous (no-tenant) demo scans are a no-op — scan-derived events must never
// land in a real tenant's SOC.
func (s *Server) emitScanSOCEvent(tenantID, threatType string, confidence float64, prompt string, indicators []string) {
	if s.socSvc == nil || tenantID == "" {
		return
	}
	evt := buildScanSOCEvent(tenantID, threatType, confidence, prompt, indicators)
	go func() {
		// A panic in the ingest pipeline must never crash the gateway (this is a
		// detached fire-and-forget goroutine — an unrecovered panic is fatal).
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("gateway->SOC emit panicked", "tenant", tenantID, "panic", rec)
			}
		}()
		if _, _, err := s.socSvc.IngestInternalEvent(evt); err != nil {
			slog.Warn("gateway->SOC auto-feed failed", "tenant", tenantID, "error", err)
		}
	}()
}
