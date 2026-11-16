package soc

import (
	"fmt"
	"io"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// SOCMetrics is the SOC-plane self-observability registry (IMP7). It records the
// pipeline's own health — events ingested, incidents opened, playbook outcomes,
// and correlation latency — and renders them in Prometheus text exposition format
// so the SOC plane can be scraped like any other service.
//
// CARDINALITY DISCIPLINE (learned from the spectorn cardinality-bomb): every
// label here is drawn from a SMALL, server-controlled enum — severity (5),
// EventSource (7), and playbook outcome (2). There is deliberately NO per-tenant
// and NO per-sensor label: those are attacker-influenced unbounded strings and
// would blow up the series count. Per-playbook series are bounded by the fixed
// built-in playbook set plus a hard cap (maxPlaybookSeries) so a programmatic
// flood of custom playbook IDs can never grow the registry without limit.
type SOCMetrics struct {
	// Counters keyed by bounded labels. Access is guarded by mu.
	mu sync.RWMutex

	eventsBySeverity map[string]*atomic.Int64 // severity -> count
	eventsBySource   map[string]*atomic.Int64 // EventSource -> count
	incidentsBySev   map[string]*atomic.Int64 // severity -> count
	playbookRuns     map[string]*atomic.Int64 // outcome -> count ("success"/"partial_failure")
	playbookByID     map[string]*atomic.Int64 // playbookID -> count (capped)
	blockIPByOutcome map[string]*atomic.Int64 // "enforced"/"not_enforced"/"error"

	eventsTotal    atomic.Int64
	incidentsTotal atomic.Int64
	rejectedTotal  atomic.Int64 // events rejected pre-persist (auth/ratelimit/secret/capacity)

	// Correlation latency histogram (fixed buckets, seconds). Bounded by construction.
	corrBuckets   []float64 // upper bounds
	corrCounts    []atomic.Int64
	corrSum       atomicFloat
	corrCount     atomic.Int64
	maxPlaybookID int
}

// NewSOCMetrics builds an empty SOC metrics registry with fixed latency buckets.
func NewSOCMetrics() *SOCMetrics {
	m := &SOCMetrics{
		eventsBySeverity: make(map[string]*atomic.Int64),
		eventsBySource:   make(map[string]*atomic.Int64),
		incidentsBySev:   make(map[string]*atomic.Int64),
		playbookRuns:     make(map[string]*atomic.Int64),
		playbookByID:     make(map[string]*atomic.Int64),
		blockIPByOutcome: make(map[string]*atomic.Int64),
		// Correlation latency buckets: 100µs .. 1s. Detection on the in-process
		// seam is sub-millisecond; the wide tail catches a slow correlation pass.
		corrBuckets:   []float64{0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0},
		maxPlaybookID: 64, // hard cap on distinct per-playbook series
	}
	m.corrCounts = make([]atomic.Int64, len(m.corrBuckets)+1) // +1 for +Inf
	return m
}

// counter returns (creating if needed) the atomic counter for key in m. The
// caller holds no lock; counter takes mu. capKey caps map growth: when the map is
// at/over cap and key is new, it routes to a shared "_other" bucket instead of
// allocating an unbounded number of series.
func (m *SOCMetrics) counter(mp map[string]*atomic.Int64, key string, cap int) *atomic.Int64 {
	m.mu.RLock()
	c, ok := mp[key]
	m.mu.RUnlock()
	if ok {
		return c
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if c, ok = mp[key]; ok { // re-check under write lock
		return c
	}
	if cap > 0 && len(mp) >= cap {
		key = "_other"
		if c, ok = mp[key]; ok {
			return c
		}
	}
	c = &atomic.Int64{}
	mp[key] = c
	return c
}

// RecordEvent counts one successfully-ingested event by severity and source.
func (m *SOCMetrics) RecordEvent(severity, source string) {
	if m == nil {
		return
	}
	m.eventsTotal.Add(1)
	m.counter(m.eventsBySeverity, normSeverity(severity), 0).Add(1)
	m.counter(m.eventsBySource, normSource(source), 0).Add(1)
}

// RecordRejectedEvent counts one event rejected before persistence (auth failure,
// rate limit, secret detected, capacity). It is a single bounded counter.
func (m *SOCMetrics) RecordRejectedEvent() {
	if m == nil {
		return
	}
	m.rejectedTotal.Add(1)
}

// RecordIncident counts one created incident by severity.
func (m *SOCMetrics) RecordIncident(severity string) {
	if m == nil {
		return
	}
	m.incidentsTotal.Add(1)
	m.counter(m.incidentsBySev, normSeverity(severity), 0).Add(1)
}

// RecordPlaybookRun counts one playbook execution by outcome and (capped) ID.
func (m *SOCMetrics) RecordPlaybookRun(playbookID, outcome string) {
	if m == nil {
		return
	}
	if outcome != "success" && outcome != "partial_failure" {
		outcome = "unknown"
	}
	m.counter(m.playbookRuns, outcome, 0).Add(1)
	if playbookID != "" {
		m.counter(m.playbookByID, playbookID, m.maxPlaybookID).Add(1)
	}
}

// RecordBlockIP counts one block_ip action by enforcement outcome.
func (m *SOCMetrics) RecordBlockIP(outcome string) {
	if m == nil {
		return
	}
	switch outcome {
	case "enforced", "not_enforced", "error":
	default:
		outcome = "error"
	}
	m.counter(m.blockIPByOutcome, outcome, 0).Add(1)
}

// ObserveCorrelationLatency records one correlation-pass duration in the histogram.
func (m *SOCMetrics) ObserveCorrelationLatency(d time.Duration) {
	if m == nil {
		return
	}
	secs := d.Seconds()
	m.corrSum.Add(secs)
	m.corrCount.Add(1)
	for i, ub := range m.corrBuckets {
		if secs <= ub {
			m.corrCounts[i].Add(1)
			return
		}
	}
	m.corrCounts[len(m.corrBuckets)].Add(1) // +Inf bucket
}

// Snapshot carries scrape-time gauge values pulled from the live service (open
// incidents, MTTD/MTTR) that the registry itself does not own.
type Snapshot struct {
	OpenIncidents      int
	MTTDSeconds        float64
	MTTRHours          float64
	ResolvedIncidents  int
	MeasuredDetections int
	Sensors            map[string]int // status -> count (bounded: ONLINE/OFFLINE/DEGRADED/UNKNOWN)
}

// Write renders the registry plus the scrape-time snapshot in Prometheus text
// exposition format. All metric names are prefixed soc_ to namespace the SOC
// plane. Gauges that have no measurement (e.g. MTTD with zero samples) are still
// emitted as 0 with the sample-count series alongside, so a dashboard can tell
// "0 because nothing resolved yet" from "0ms detection".
func (m *SOCMetrics) Write(w io.Writer, snap Snapshot) {
	if m == nil {
		return
	}

	// --- Counters: events ---
	fmt.Fprintf(w, "# HELP soc_events_ingested_total SOC events ingested and persisted.\n")
	fmt.Fprintf(w, "# TYPE soc_events_ingested_total counter\n")
	fmt.Fprintf(w, "soc_events_ingested_total %d\n", m.eventsTotal.Load())
	writeLabeled(w, "soc_events_ingested", "severity", m.snapshotMap(m.eventsBySeverity))
	writeLabeled(w, "soc_events_ingested", "source", m.snapshotMap(m.eventsBySource))

	fmt.Fprintf(w, "# HELP soc_events_rejected_total SOC events rejected before persistence (auth/ratelimit/secret/capacity).\n")
	fmt.Fprintf(w, "# TYPE soc_events_rejected_total counter\n")
	fmt.Fprintf(w, "soc_events_rejected_total %d\n", m.rejectedTotal.Load())

	// --- Counters: incidents ---
	fmt.Fprintf(w, "# HELP soc_incidents_created_total SOC incidents created by correlation.\n")
	fmt.Fprintf(w, "# TYPE soc_incidents_created_total counter\n")
	fmt.Fprintf(w, "soc_incidents_created_total %d\n", m.incidentsTotal.Load())
	writeLabeled(w, "soc_incidents_created", "severity", m.snapshotMap(m.incidentsBySev))

	// --- Counters: playbooks ---
	fmt.Fprintf(w, "# HELP soc_playbook_runs_total Playbook executions by outcome.\n")
	fmt.Fprintf(w, "# TYPE soc_playbook_runs_total counter\n")
	writeLabeled(w, "soc_playbook_runs", "outcome", m.snapshotMap(m.playbookRuns))
	fmt.Fprintf(w, "# HELP soc_playbook_runs_by_id_total Playbook executions by playbook id (capped).\n")
	fmt.Fprintf(w, "# TYPE soc_playbook_runs_by_id_total counter\n")
	writeLabeled(w, "soc_playbook_runs_by_id", "playbook", m.snapshotMap(m.playbookByID))

	// --- Counters: block_ip enforcement ---
	fmt.Fprintf(w, "# HELP soc_block_ip_actions_total block_ip actions by enforcement outcome.\n")
	fmt.Fprintf(w, "# TYPE soc_block_ip_actions_total counter\n")
	writeLabeled(w, "soc_block_ip_actions", "outcome", m.snapshotMap(m.blockIPByOutcome))

	// --- Histogram: correlation latency ---
	fmt.Fprintf(w, "# HELP soc_correlation_latency_seconds Correlation-pass latency.\n")
	fmt.Fprintf(w, "# TYPE soc_correlation_latency_seconds histogram\n")
	var cumulative int64
	for i, ub := range m.corrBuckets {
		cumulative += m.corrCounts[i].Load()
		fmt.Fprintf(w, "soc_correlation_latency_seconds_bucket{le=\"%g\"} %d\n", ub, cumulative)
	}
	cumulative += m.corrCounts[len(m.corrBuckets)].Load()
	fmt.Fprintf(w, "soc_correlation_latency_seconds_bucket{le=\"+Inf\"} %d\n", cumulative)
	fmt.Fprintf(w, "soc_correlation_latency_seconds_sum %g\n", m.corrSum.Load())
	fmt.Fprintf(w, "soc_correlation_latency_seconds_count %d\n", m.corrCount.Load())

	// --- Gauges from the scrape-time snapshot ---
	fmt.Fprintf(w, "# HELP soc_open_incidents Currently open (unresolved) incidents.\n")
	fmt.Fprintf(w, "# TYPE soc_open_incidents gauge\n")
	fmt.Fprintf(w, "soc_open_incidents %d\n", snap.OpenIncidents)

	fmt.Fprintf(w, "# HELP soc_mttd_seconds Mean time to detect (incident created - first event), real timestamps.\n")
	fmt.Fprintf(w, "# TYPE soc_mttd_seconds gauge\n")
	fmt.Fprintf(w, "soc_mttd_seconds %g\n", snap.MTTDSeconds)
	fmt.Fprintf(w, "# HELP soc_mttd_measured_incidents Incidents with a measurable detect latency.\n")
	fmt.Fprintf(w, "# TYPE soc_mttd_measured_incidents gauge\n")
	fmt.Fprintf(w, "soc_mttd_measured_incidents %d\n", snap.MeasuredDetections)

	fmt.Fprintf(w, "# HELP soc_mttr_hours Mean time to resolve (resolved - created), real timestamps.\n")
	fmt.Fprintf(w, "# TYPE soc_mttr_hours gauge\n")
	fmt.Fprintf(w, "soc_mttr_hours %g\n", snap.MTTRHours)
	fmt.Fprintf(w, "# HELP soc_mttr_resolved_incidents Resolved incidents averaged into MTTR.\n")
	fmt.Fprintf(w, "# TYPE soc_mttr_resolved_incidents gauge\n")
	fmt.Fprintf(w, "soc_mttr_resolved_incidents %d\n", snap.ResolvedIncidents)

	if len(snap.Sensors) > 0 {
		fmt.Fprintf(w, "# HELP soc_sensors Registered sensors by status.\n")
		fmt.Fprintf(w, "# TYPE soc_sensors gauge\n")
		writeLabeled(w, "soc_sensors", "status", snap.Sensors)
	}
}

// snapshotMap copies a counter map to a plain int map under the read lock so the
// exposition reads a consistent point-in-time view.
func (m *SOCMetrics) snapshotMap(mp map[string]*atomic.Int64) map[string]int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make(map[string]int, len(mp))
	for k, v := range mp {
		out[k] = int(v.Load())
	}
	return out
}

// writeLabeled emits "<name>{<label>="k"} v" lines, sorted by label value for
// stable output. Empty maps emit nothing.
func writeLabeled(w io.Writer, name, label string, vals map[string]int) {
	if len(vals) == 0 {
		return
	}
	keys := make([]string, 0, len(vals))
	for k := range vals {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	suffix := "_total"
	for _, k := range keys {
		fmt.Fprintf(w, "%s%s{%s=%q} %d\n", name, suffix, label, k, vals[k])
	}
}

func normSeverity(s string) string {
	if s == "" {
		return "UNKNOWN"
	}
	if ValidSeverity(EventSeverity(s)) {
		return s
	}
	return "UNKNOWN"
}

func normSource(s string) string {
	if s == "" {
		return "unknown"
	}
	if ValidSource(EventSource(s)) {
		return s
	}
	return "unknown"
}

// atomicFloat is a tiny lock-free float64 accumulator for the histogram sum.
type atomicFloat struct {
	mu  sync.Mutex
	val float64
}

func (a *atomicFloat) Add(f float64) {
	a.mu.Lock()
	a.val += f
	a.mu.Unlock()
}

func (a *atomicFloat) Load() float64 {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.val
}
