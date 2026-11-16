package soc

import (
	"testing"
	"time"
)

func TestThreatIntel_SampleIOCs(t *testing.T) {
	ti := NewThreatIntelEngine()
	iocs := ti.ListIOCs()
	if len(iocs) != 4 {
		t.Fatalf("expected 4 sample IOCs, got %d", len(iocs))
	}
}

func TestThreatIntel_Match(t *testing.T) {
	ti := NewThreatIntelEngine()
	ioc := ti.Match("185.220.101.35")
	if ioc == nil {
		t.Fatal("should match known IP IOC")
	}
	if ioc.Severity != "HIGH" {
		t.Fatalf("expected HIGH severity, got %s", ioc.Severity)
	}
}

func TestThreatIntel_NoMatch(t *testing.T) {
	ti := NewThreatIntelEngine()
	ioc := ti.Match("192.168.1.1")
	if ioc != nil {
		t.Fatal("should not match unknown IP")
	}
}

func TestThreatIntel_MatchEvent(t *testing.T) {
	ti := NewThreatIntelEngine()
	hits := ti.MatchEvent("evt-001", "Detected connection to evil-ai-jailbreak.com from internal host")
	if len(hits) != 1 {
		t.Fatalf("expected 1 hit, got %d", len(hits))
	}
	if hits[0].Severity != "CRITICAL" {
		t.Fatalf("expected CRITICAL, got %s", hits[0].Severity)
	}
}

func TestThreatIntel_AddCustomIOC(t *testing.T) {
	ti := NewThreatIntelEngine()
	ti.AddIOC(IOC{
		Value:    "bad-prompt.ai",
		Type:     IOCDomain,
		Severity: "HIGH",
		Source:   "manual",
	})
	ioc := ti.Match("bad-prompt.ai")
	if ioc == nil {
		t.Fatal("should match custom IOC")
	}
}

func TestThreatIntel_Feeds(t *testing.T) {
	ti := NewThreatIntelEngine()
	feeds := ti.ListFeeds()
	if len(feeds) != 4 {
		t.Fatalf("expected 4 feeds, got %d", len(feeds))
	}
}

func TestThreatIntel_Stats(t *testing.T) {
	ti := NewThreatIntelEngine()
	stats := ti.ThreatIntelStats()
	if stats["total_iocs"].(int) != 4 {
		t.Fatal("expected 4 IOCs")
	}
}

func TestThreatIntel_HitTracking(t *testing.T) {
	ti := NewThreatIntelEngine()
	ti.MatchEvent("evt-001", "Connection to 185.220.101.35")
	ti.MatchEvent("evt-002", "Request from 185.220.101.35")

	hits := ti.RecentHits(10)
	if len(hits) != 2 {
		t.Fatalf("expected 2 hits, got %d", len(hits))
	}
}

func TestRetention_DefaultPolicies(t *testing.T) {
	rp := NewDataRetentionPolicy()
	policies := rp.ListPolicies()
	if len(policies) != 5 {
		t.Fatalf("expected 5 default policies, got %d", len(policies))
	}
}

func TestRetention_Expiration(t *testing.T) {
	rp := NewDataRetentionPolicy()
	old := time.Now().AddDate(0, 0, -100) // 100 days ago
	fresh := time.Now().Add(-1 * time.Hour)

	if !rp.IsExpired("events", old) {
		t.Fatal("100-day old event should be expired (90d policy)")
	}
	if rp.IsExpired("events", fresh) {
		t.Fatal("1-hour old event should not be expired")
	}
}

func TestRetention_Enforce(t *testing.T) {
	rp := NewDataRetentionPolicy()
	timestamps := []time.Time{
		time.Now().AddDate(0, 0, -100),
		time.Now().AddDate(0, 0, -95),
		time.Now().Add(-1 * time.Hour),
	}
	expired := rp.Enforce("events", timestamps)
	if expired != 2 {
		t.Fatalf("expected 2 expired, got %d", expired)
	}
}

func TestRetention_CustomPolicy(t *testing.T) {
	rp := NewDataRetentionPolicy()
	rp.SetPolicy("custom", 7, "delete")
	r, ok := rp.GetPolicy("custom")
	if !ok {
		t.Fatal("custom policy should exist")
	}
	if r.RetainDays != 7 {
		t.Fatalf("expected 7 days, got %d", r.RetainDays)
	}
}
