// Package sidecar implements the Universal Sidecar (§5.5) — a zero-dependency
// Go binary that runs alongside SENTINEL sensors, tails their STDOUT/logs,
// and pushes parsed security events to the SOC Event Bus.
package sidecar

import (
	"log/slog"
	"regexp"
	"strconv"
	"strings"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// Parser converts a raw log line into a SOCEvent.
// Returns nil, false if the line is not a security event.
type Parser interface {
	Parse(line string) (*domsoc.SOCEvent, bool)
}

// ── sentinel-core Parser ─────────────────────────────────────────────────────

// SentinelCoreParser parses sentinel-core detection output.
// Expected format: [DETECT] engine=<name> confidence=<float> pattern=<desc> [severity=<sev>]
type SentinelCoreParser struct{}

var coreDetectRe = regexp.MustCompile(
	`\[DETECT\]\s+engine=(\S+)\s+confidence=([0-9.]+)\s+pattern=(.+?)(?:\s+severity=(\S+))?$`)

func (p *SentinelCoreParser) Parse(line string) (*domsoc.SOCEvent, bool) {
	m := coreDetectRe.FindStringSubmatch(strings.TrimSpace(line))
	if m == nil {
		return nil, false
	}

	engine := m[1]
	conf, _ := strconv.ParseFloat(m[2], 64)
	pattern := m[3]
	severity := mapConfidenceToSeverity(conf)
	// The optional severity= field is sensor-supplied text. Only honor it when
	// it names a known severity; otherwise keep the confidence-derived value.
	// An unrecognized override (e.g. "CRITICALX") would fail SOCEvent.Validate()
	// at ingest and silently drop the whole event — a malformed log line must
	// not erase a real detection.
	if m[4] != "" {
		if sev := domsoc.EventSeverity(strings.ToUpper(m[4])); domsoc.ValidSeverity(sev) {
			severity = sev
		}
	}

	evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, severity, engine,
		engine+": "+pattern)
	evt.Confidence = conf
	evt.Subcategory = pattern
	return &evt, true
}

// ── shield Parser ────────────────────────────────────────────────────────────

// ShieldParser parses shield network block logs.
// Expected format: BLOCKED protocol=<proto> reason=<reason> source_ip=<ip>
type ShieldParser struct{}

var shieldBlockRe = regexp.MustCompile(
	`BLOCKED\s+protocol=(\S+)\s+reason=(.+?)\s+source_ip=(\S+)`)

func (p *ShieldParser) Parse(line string) (*domsoc.SOCEvent, bool) {
	m := shieldBlockRe.FindStringSubmatch(strings.TrimSpace(line))
	if m == nil {
		return nil, false
	}

	protocol := m[1]
	reason := m[2]
	sourceIP := m[3]

	evt := domsoc.NewSOCEvent(domsoc.SourceShield, domsoc.SeverityMedium, "network_block",
		"Shield blocked "+protocol+" from "+sourceIP+": "+reason)
	evt.Subcategory = protocol
	evt.Metadata = map[string]string{
		"source_ip": sourceIP,
		"protocol":  protocol,
		"reason":    reason,
	}
	return &evt, true
}

// ── immune Parser ────────────────────────────────────────────────────────────

// ImmuneParser parses immune system anomaly/response logs.
// Expected format: [ANOMALY] type=<type> score=<float> detail=<text>
//
//	or: [RESPONSE] action=<action> target=<target> reason=<text>
type ImmuneParser struct{}

var immuneAnomalyRe = regexp.MustCompile(
	`\[ANOMALY\]\s+type=(\S+)\s+score=([0-9.]+)\s+detail=(.+)`)
var immuneResponseRe = regexp.MustCompile(
	`\[RESPONSE\]\s+action=(\S+)\s+target=(\S+)\s+reason=(.+)`)

func (p *ImmuneParser) Parse(line string) (*domsoc.SOCEvent, bool) {
	trimmed := strings.TrimSpace(line)

	if m := immuneAnomalyRe.FindStringSubmatch(trimmed); m != nil {
		anomalyType := m[1]
		score, _ := strconv.ParseFloat(m[2], 64)
		detail := m[3]

		evt := domsoc.NewSOCEvent(domsoc.SourceImmune, mapConfidenceToSeverity(score),
			"anomaly", "Immune anomaly: "+anomalyType+": "+detail)
		evt.Confidence = score
		evt.Subcategory = anomalyType
		return &evt, true
	}

	if m := immuneResponseRe.FindStringSubmatch(trimmed); m != nil {
		action := m[1]
		target := m[2]
		reason := m[3]

		evt := domsoc.NewSOCEvent(domsoc.SourceImmune, domsoc.SeverityHigh,
			"immune_response", "Immune response: "+action+" on "+target+": "+reason)
		evt.Subcategory = action
		evt.Metadata = map[string]string{
			"action": action,
			"target": target,
			"reason": reason,
		}
		return &evt, true
	}

	return nil, false
}

// ── Generic Parser ───────────────────────────────────────────────────────────

// GenericParser uses a configurable regex with named groups.
// Named groups: "category", "severity", "description", "confidence".
type GenericParser struct {
	Pattern *regexp.Regexp
	Source  domsoc.EventSource
}

func NewGenericParser(pattern string, source domsoc.EventSource) (*GenericParser, error) {
	re, err := regexp.Compile(pattern)
	if err != nil {
		return nil, err
	}
	return &GenericParser{Pattern: re, Source: source}, nil
}

func (p *GenericParser) Parse(line string) (*domsoc.SOCEvent, bool) {
	m := p.Pattern.FindStringSubmatch(strings.TrimSpace(line))
	if m == nil {
		return nil, false
	}

	names := p.Pattern.SubexpNames()
	groups := map[string]string{}
	for i, name := range names {
		if i > 0 && name != "" {
			groups[name] = m[i]
		}
	}

	category := groups["category"]
	if category == "" {
		category = "generic"
	}
	description := groups["description"]
	if description == "" {
		description = line
	}
	severity := domsoc.SeverityMedium
	// Only honor a recognized severity from the named group; an unknown value
	// would fail SOCEvent.Validate() at ingest and drop the event. Fall back to
	// MEDIUM rather than discarding a real detection over a bad label.
	if s, ok := groups["severity"]; ok && s != "" {
		if sev := domsoc.EventSeverity(strings.ToUpper(s)); domsoc.ValidSeverity(sev) {
			severity = sev
		}
	}
	confidence := 0.5
	if c, ok := groups["confidence"]; ok {
		if f, err := strconv.ParseFloat(c, 64); err == nil {
			confidence = f
		}
	}

	evt := domsoc.NewSOCEvent(p.Source, severity, category, description)
	evt.Confidence = confidence
	return &evt, true
}

// ── Helpers ──────────────────────────────────────────────────────────────────

// ParserForSensor returns the appropriate parser for a sensor type.
func ParserForSensor(sensorType string) Parser {
	switch strings.ToLower(sensorType) {
	case "sentinel-core":
		return &SentinelCoreParser{}
	case "shield":
		return &ShieldParser{}
	case "immune":
		return &ImmuneParser{}
	default:
		slog.Warn("sidecar: unknown sensor type, using sentinel-core parser as fallback",
			"sensor_type", sensorType)
		return &SentinelCoreParser{} // fallback
	}
}

func mapConfidenceToSeverity(conf float64) domsoc.EventSeverity {
	switch {
	case conf >= 0.9:
		return domsoc.SeverityCritical
	case conf >= 0.7:
		return domsoc.SeverityHigh
	case conf >= 0.5:
		return domsoc.SeverityMedium
	case conf >= 0.3:
		return domsoc.SeverityLow
	default:
		return domsoc.SeverityInfo
	}
}
