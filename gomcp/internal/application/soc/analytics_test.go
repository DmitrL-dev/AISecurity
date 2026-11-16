package soc

import (
	"testing"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

func TestGenerateReport_EmptyEvents(t *testing.T) {
	report := GenerateReport(nil, nil, 24)
	if report == nil {
		t.Fatal("expected non-nil report")
	}
	if report.EventsPerHour != 0 {
		t.Errorf("expected 0 events/hour, got %.2f", report.EventsPerHour)
	}
	if report.MTTR != 0 {
		t.Errorf("expected 0 MTTR, got %.2f", report.MTTR)
	}
}

func TestGenerateReport_SeverityDistribution(t *testing.T) {
	now := time.Now()
	events := []domsoc.SOCEvent{
		{Severity: domsoc.SeverityCritical, Timestamp: now},
		{Severity: domsoc.SeverityCritical, Timestamp: now},
		{Severity: domsoc.SeverityHigh, Timestamp: now},
		{Severity: domsoc.SeverityMedium, Timestamp: now},
		{Severity: domsoc.SeverityLow, Timestamp: now},
		{Severity: domsoc.SeverityInfo, Timestamp: now},
		{Severity: domsoc.SeverityInfo, Timestamp: now},
		{Severity: domsoc.SeverityInfo, Timestamp: now},
	}

	report := GenerateReport(events, nil, 1)

	if report.SeverityDistribution.Critical != 2 {
		t.Errorf("expected 2 critical, got %d", report.SeverityDistribution.Critical)
	}
	if report.SeverityDistribution.High != 1 {
		t.Errorf("expected 1 high, got %d", report.SeverityDistribution.High)
	}
	if report.SeverityDistribution.Info != 3 {
		t.Errorf("expected 3 info, got %d", report.SeverityDistribution.Info)
	}
}

func TestGenerateReport_TopSources(t *testing.T) {
	now := time.Now()
	events := []domsoc.SOCEvent{
		{Source: domsoc.SourceSentinelCore, Timestamp: now},
		{Source: domsoc.SourceSentinelCore, Timestamp: now},
		{Source: domsoc.SourceSentinelCore, Timestamp: now},
		{Source: domsoc.SourceShield, Timestamp: now},
		{Source: domsoc.SourceShield, Timestamp: now},
		{Source: domsoc.SourceExternal, Timestamp: now},
	}

	report := GenerateReport(events, nil, 1)

	if len(report.TopSources) == 0 {
		t.Fatal("expected non-empty top sources")
	}

	// First source should be sentinel-core (3 events)
	if report.TopSources[0].Source != string(domsoc.SourceSentinelCore) {
		t.Errorf("expected top source sentinel-core, got %s", report.TopSources[0].Source)
	}
	if report.TopSources[0].Count != 3 {
		t.Errorf("expected top source count 3, got %d", report.TopSources[0].Count)
	}
}

func TestGenerateReport_MTTR(t *testing.T) {
	now := time.Now()
	incidents := []domsoc.Incident{
		{
			Status:    domsoc.StatusResolved,
			CreatedAt: now.Add(-3 * time.Hour),
			UpdatedAt: now.Add(-1 * time.Hour),
		},
		{
			Status:    domsoc.StatusResolved,
			CreatedAt: now.Add(-5 * time.Hour),
			UpdatedAt: now.Add(-4 * time.Hour),
		},
	}

	report := GenerateReport(nil, incidents, 24)

	// MTTR = (2h + 1h) / 2 = 1.5h
	if report.MTTR < 1.4 || report.MTTR > 1.6 {
		t.Errorf("expected MTTR ~1.5h, got %.2f", report.MTTR)
	}
}

func TestGenerateReport_IncidentRate(t *testing.T) {
	now := time.Now()
	events := make([]domsoc.SOCEvent, 100)
	for i := range events {
		events[i] = domsoc.SOCEvent{Timestamp: now, Severity: domsoc.SeverityLow}
	}

	incidents := make([]domsoc.Incident, 5)
	for i := range incidents {
		incidents[i] = domsoc.Incident{CreatedAt: now, Status: domsoc.StatusOpen}
	}

	report := GenerateReport(events, incidents, 1)

	// 5 incidents / 100 events * 100 = 5%
	if report.IncidentRate < 4.9 || report.IncidentRate > 5.1 {
		t.Errorf("expected incident rate ~5%%, got %.2f%%", report.IncidentRate)
	}
}
