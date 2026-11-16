// Package soc provides SOC analytics: event trends, severity distribution,
// top sources, MITRE ATT&CK coverage, and time-series aggregation.
package soc

import (
	"sort"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// ─── Analytics Types ──────────────────────────────────────

// TimeSeriesPoint represents a single data point in time series.
type TimeSeriesPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Count     int       `json:"count"`
}

// SeverityDistribution counts events by severity.
type SeverityDistribution struct {
	Critical int `json:"critical"`
	High     int `json:"high"`
	Medium   int `json:"medium"`
	Low      int `json:"low"`
	Info     int `json:"info"`
}

// SourceBreakdown counts events per source.
type SourceBreakdown struct {
	Source string `json:"source"`
	Count  int    `json:"count"`
}

// CategoryBreakdown counts events per category.
type CategoryBreakdown struct {
	Category string `json:"category"`
	Count    int    `json:"count"`
}

// IncidentTimeline shows incident trend.
type IncidentTimeline struct {
	Created  []TimeSeriesPoint `json:"created"`
	Resolved []TimeSeriesPoint `json:"resolved"`
}

// AnalyticsReport is the full SOC analytics output.
type AnalyticsReport struct {
	GeneratedAt time.Time `json:"generated_at"`
	TimeRange   struct {
		From time.Time `json:"from"`
		To   time.Time `json:"to"`
	} `json:"time_range"`

	// Event analytics
	EventTrend           []TimeSeriesPoint    `json:"event_trend"`
	SeverityDistribution SeverityDistribution `json:"severity_distribution"`
	TopSources           []SourceBreakdown    `json:"top_sources"`
	TopCategories        []CategoryBreakdown  `json:"top_categories"`

	// Incident analytics
	IncidentTimeline IncidentTimeline `json:"incident_timeline"`
	// MTTR (Mean Time To Resolve) is computed from REAL timestamps — the span
	// ResolvedAt−CreatedAt averaged over resolved incidents (IMP6). 0 when no
	// incident has been resolved yet (honest: no measurement, not "instant").
	MTTR float64 `json:"mttr_hours"`
	// MTTD (Mean Time To Detect) is the detect latency CreatedAt−FirstEventAt
	// averaged over incidents that carry a first-event timestamp (IMP6). Surfaced
	// in seconds (detection is typically sub-minute on the in-process seam) and
	// minutes for the dashboard. 0 / null when no incident has a measurable anchor.
	MTTDSeconds float64 `json:"mttd_seconds"`
	MTTDMinutes float64 `json:"mttd_minutes"`
	// ResolvedIncidents / MeasuredDetections expose the SAMPLE SIZE behind the two
	// means so a single fast resolution can't be mistaken for a stable SLA.
	ResolvedIncidents  int `json:"resolved_incidents"`
	MeasuredDetections int `json:"measured_detections"`

	// Derived KPIs
	EventsPerHour float64 `json:"events_per_hour"`
	IncidentRate  float64 `json:"incident_rate"` // incidents / 100 events
}

// ─── Analytics Functions ──────────────────────────────────

// MaxAnalyticsWindowHours bounds the analytics window to ~10 years. The window
// flows in from an untrusted ?window= query param (handleAnalytics → Analytics →
// GenerateReport) with only a >0 check upstream. Without an upper bound two
// boundary failures are reachable:
//   - integer overflow: time.Duration(windowHours)*time.Hour overflows int64 for
//     windowHours ≳ 2.5e6, wrapping windowStart into the future so to.Sub(from)
//     is negative and the make([]int, hours) calls below panic (len out of range);
//   - memory amplification: a merely large (non-overflowing) window allocates
//     three hours-sized slices, e.g. ?window=10000000 → ~240MB per request.
//
// 10 years is far beyond any meaningful SOC window (events are retention-purged
// at 90 days by default) and keeps the bucket slices to a few MB.
const MaxAnalyticsWindowHours = 24 * 366 * 10

// GenerateReport builds a full analytics report from events and incidents.
func GenerateReport(events []domsoc.SOCEvent, incidents []domsoc.Incident, windowHours int) *AnalyticsReport {
	if windowHours <= 0 {
		windowHours = 24
	}
	if windowHours > MaxAnalyticsWindowHours {
		windowHours = MaxAnalyticsWindowHours
	}

	now := time.Now()
	windowStart := now.Add(-time.Duration(windowHours) * time.Hour)

	report := &AnalyticsReport{
		GeneratedAt: now,
	}
	report.TimeRange.From = windowStart
	report.TimeRange.To = now

	// Filter events within window
	var windowEvents []domsoc.SOCEvent
	for _, e := range events {
		if e.Timestamp.After(windowStart) {
			windowEvents = append(windowEvents, e)
		}
	}

	// Severity distribution
	report.SeverityDistribution = calcSeverityDist(windowEvents)

	// Event trend (hourly buckets)
	report.EventTrend = calcEventTrend(windowEvents, windowStart, now)

	// Top sources
	report.TopSources = calcTopSources(windowEvents, 10)

	// Top categories
	report.TopCategories = calcTopCategories(windowEvents, 10)

	// Incident timeline
	report.IncidentTimeline = calcIncidentTimeline(incidents, windowStart, now)

	// MTTR / MTTD — real, timestamp-derived (IMP6). Computed over ALL incidents
	// passed in (the caller scopes them per tenant), not just the windowed slice,
	// so a resolution that lands outside the event window still counts.
	report.MTTR, report.ResolvedIncidents = calcMTTR(incidents)
	report.MTTDSeconds, report.MeasuredDetections = calcMTTD(incidents)
	report.MTTDMinutes = report.MTTDSeconds / 60.0

	// KPIs
	hours := now.Sub(windowStart).Hours()
	if hours > 0 {
		report.EventsPerHour = float64(len(windowEvents)) / hours
	}
	if len(windowEvents) > 0 {
		report.IncidentRate = float64(len(incidents)) / float64(len(windowEvents)) * 100
	}

	return report
}

// ─── Internal Computations ────────────────────────────────

func calcSeverityDist(events []domsoc.SOCEvent) SeverityDistribution {
	var d SeverityDistribution
	for _, e := range events {
		switch e.Severity {
		case domsoc.SeverityCritical:
			d.Critical++
		case domsoc.SeverityHigh:
			d.High++
		case domsoc.SeverityMedium:
			d.Medium++
		case domsoc.SeverityLow:
			d.Low++
		case domsoc.SeverityInfo:
			d.Info++
		}
	}
	return d
}

func calcEventTrend(events []domsoc.SOCEvent, from, to time.Time) []TimeSeriesPoint {
	hours := int(to.Sub(from).Hours()) + 1
	buckets := make([]int, hours)

	for _, e := range events {
		idx := int(e.Timestamp.Sub(from).Hours())
		if idx >= 0 && idx < len(buckets) {
			buckets[idx]++
		}
	}

	points := make([]TimeSeriesPoint, hours)
	for i := range points {
		points[i] = TimeSeriesPoint{
			Timestamp: from.Add(time.Duration(i) * time.Hour),
			Count:     buckets[i],
		}
	}
	return points
}

func calcTopSources(events []domsoc.SOCEvent, limit int) []SourceBreakdown {
	counts := make(map[string]int)
	for _, e := range events {
		counts[string(e.Source)]++
	}

	result := make([]SourceBreakdown, 0, len(counts))
	for src, cnt := range counts {
		result = append(result, SourceBreakdown{Source: src, Count: cnt})
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Count > result[j].Count
	})

	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

func calcTopCategories(events []domsoc.SOCEvent, limit int) []CategoryBreakdown {
	counts := make(map[string]int)
	for _, e := range events {
		counts[string(e.Category)]++
	}

	result := make([]CategoryBreakdown, 0, len(counts))
	for cat, cnt := range counts {
		result = append(result, CategoryBreakdown{Category: cat, Count: cnt})
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Count > result[j].Count
	})

	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

func calcIncidentTimeline(incidents []domsoc.Incident, from, to time.Time) IncidentTimeline {
	hours := int(to.Sub(from).Hours()) + 1
	created := make([]int, hours)
	resolved := make([]int, hours)

	for _, inc := range incidents {
		idx := int(inc.CreatedAt.Sub(from).Hours())
		if idx >= 0 && idx < hours {
			created[idx]++
		}
		if inc.Status == domsoc.StatusResolved {
			ridx := int(inc.UpdatedAt.Sub(from).Hours())
			if ridx >= 0 && ridx < hours {
				resolved[ridx]++
			}
		}
	}

	timeline := IncidentTimeline{
		Created:  make([]TimeSeriesPoint, hours),
		Resolved: make([]TimeSeriesPoint, hours),
	}
	for i := range timeline.Created {
		t := from.Add(time.Duration(i) * time.Hour)
		timeline.Created[i] = TimeSeriesPoint{Timestamp: t, Count: created[i]}
		timeline.Resolved[i] = TimeSeriesPoint{Timestamp: t, Count: resolved[i]}
	}
	return timeline
}

// calcMTTR returns mean-time-to-resolve in HOURS and the number of resolved
// incidents it averaged over. It prefers the honest ResolvedAt timestamp (set by
// Incident.Resolve/ChangeStatus); for legacy/imported rows that are RESOLVED but
// carry no ResolvedAt it falls back to UpdatedAt so historical data still counts.
// Incidents that are not resolved, or whose span is non-positive (clock skew),
// are skipped — never folded in as a 0h resolution.
func calcMTTR(incidents []domsoc.Incident) (float64, int) {
	var total float64
	var count int
	for _, inc := range incidents {
		if inc.Status != domsoc.StatusResolved && inc.Status != domsoc.StatusFalsePositive {
			continue
		}
		end := inc.UpdatedAt
		if inc.ResolvedAt != nil && !inc.ResolvedAt.IsZero() {
			end = *inc.ResolvedAt
		}
		if end.IsZero() || inc.CreatedAt.IsZero() {
			continue
		}
		duration := end.Sub(inc.CreatedAt).Hours()
		if duration > 0 {
			total += duration
			count++
		}
	}
	if count == 0 {
		return 0, 0
	}
	return total / float64(count), count
}

// calcMTTD returns mean-time-to-detect in SECONDS and the number of incidents it
// averaged over. Detect latency for one incident is CreatedAt−FirstEventAt
// (Incident.DetectLatency), which is only defined when the incident carries a
// first-event anchor — incidents without one (e.g. P2P-imported) are skipped so
// the mean reflects real measurements rather than a flood of false 0s.
func calcMTTD(incidents []domsoc.Incident) (float64, int) {
	var total float64
	var count int
	for _, inc := range incidents {
		d, ok := inc.DetectLatency()
		if !ok {
			continue
		}
		total += d.Seconds()
		count++
	}
	if count == 0 {
		return 0, 0
	}
	return total / float64(count), count
}
