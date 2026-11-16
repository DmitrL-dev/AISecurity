package soc

import (
	"testing"
	"time"
)

// Review 14.06 round-5: the IOC store had no bound and never evicted. Eviction
// drops the oldest-LastSeen indicators, keeping the live store bounded.
func TestEvictOldestIOCs(t *testing.T) {
	store := NewThreatIntelStore()
	now := time.Now()
	vals := []string{"10.0.0.0", "10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"}
	for i, v := range vals {
		store.AddIOC(IOC{
			Type:     IOCTypeIP,
			Value:    v,
			LastSeen: now.Add(time.Duration(i) * time.Hour), // index 0 = oldest
		})
	}

	store.evictOldestIOCs(2) // drop the two oldest (10.0.0.0, 10.0.0.1)

	if store.Lookup(IOCTypeIP, "10.0.0.0") != nil || store.Lookup(IOCTypeIP, "10.0.0.1") != nil {
		t.Fatal("the two oldest IOCs must be evicted")
	}
	if store.Lookup(IOCTypeIP, "10.0.0.4") == nil {
		t.Fatal("the newest IOC must survive")
	}
}

func TestThreatIntelStore_AddAndLookup(t *testing.T) {
	store := NewThreatIntelStore()

	ioc := IOC{
		Type:       IOCTypeIP,
		Value:      "192.168.1.100",
		Source:     "test-feed",
		Severity:   "high",
		FirstSeen:  time.Now(),
		LastSeen:   time.Now(),
		Confidence: 0.9,
	}

	store.AddIOC(ioc)

	if store.TotalIOCs != 1 {
		t.Errorf("expected 1 IOC, got %d", store.TotalIOCs)
	}

	found := store.Lookup(IOCTypeIP, "192.168.1.100")
	if found == nil {
		t.Fatal("expected to find IOC")
	}
	if found.Source != "test-feed" {
		t.Errorf("expected source test-feed, got %s", found.Source)
	}
}

func TestThreatIntelStore_LookupNotFound(t *testing.T) {
	store := NewThreatIntelStore()
	found := store.Lookup(IOCTypeIP, "10.0.0.1")
	if found != nil {
		t.Error("expected nil for unknown IOC")
	}
}

func TestThreatIntelStore_CaseInsensitiveLookup(t *testing.T) {
	store := NewThreatIntelStore()

	store.AddIOC(IOC{
		Type:       IOCTypeDomain,
		Value:      "evil.example.COM",
		Source:     "test",
		FirstSeen:  time.Now(),
		LastSeen:   time.Now(),
		Confidence: 0.8,
	})

	// Lookup with different case
	found := store.Lookup(IOCTypeDomain, "evil.example.com")
	if found == nil {
		t.Fatal("expected case-insensitive match")
	}
}

func TestThreatIntelStore_UpdateExisting(t *testing.T) {
	store := NewThreatIntelStore()
	now := time.Now()
	earlier := now.Add(-24 * time.Hour)

	store.AddIOC(IOC{
		Type:       IOCTypeIP,
		Value:      "10.0.0.1",
		Source:     "feed1",
		FirstSeen:  now,
		LastSeen:   now,
		Confidence: 0.5,
	})

	// Second add with earlier FirstSeen and higher confidence
	store.AddIOC(IOC{
		Type:       IOCTypeIP,
		Value:      "10.0.0.1",
		Source:     "feed2",
		FirstSeen:  earlier,
		LastSeen:   now,
		Confidence: 0.95,
	})

	// Should still be 1 IOC (merged)
	if store.TotalIOCs != 1 {
		t.Errorf("expected 1 IOC after merge, got %d", store.TotalIOCs)
	}

	found := store.Lookup(IOCTypeIP, "10.0.0.1")
	if found == nil {
		t.Fatal("expected to find merged IOC")
	}
	if found.Confidence != 0.95 {
		t.Errorf("expected confidence 0.95 after merge, got %.2f", found.Confidence)
	}
	if !found.FirstSeen.Equal(earlier) {
		t.Error("expected FirstSeen to be earlier timestamp after merge")
	}
}

func TestThreatIntelStore_LookupAny(t *testing.T) {
	store := NewThreatIntelStore()

	store.AddIOC(IOC{Type: IOCTypeIP, Value: "10.0.0.1", FirstSeen: time.Now(), LastSeen: time.Now()})
	store.AddIOC(IOC{Type: IOCTypeDomain, Value: "10.0.0.1", FirstSeen: time.Now(), LastSeen: time.Now()})

	matches := store.LookupAny("10.0.0.1")
	if len(matches) != 2 {
		t.Errorf("expected 2 matches (IP + domain), got %d", len(matches))
	}
}

func TestThreatIntelStore_EnrichEvent(t *testing.T) {
	store := NewThreatIntelStore()

	store.AddIOC(IOC{
		Type:       IOCTypeIP,
		Value:      "malicious-sensor",
		Source:     "intel",
		Severity:   "critical",
		FirstSeen:  time.Now(),
		LastSeen:   time.Now(),
		Confidence: 0.99,
	})

	// Enrich event with matching sensorID as sourceIP
	matches := store.EnrichEvent("malicious-sensor", "normal traffic")
	if len(matches) != 1 {
		t.Errorf("expected 1 IOC match, got %d", len(matches))
	}
}

func TestThreatIntelStore_EnrichEvent_DomainInDescription(t *testing.T) {
	store := NewThreatIntelStore()

	store.AddIOC(IOC{
		Type:      IOCTypeDomain,
		Value:     "evil.example.com",
		Source:    "stix",
		FirstSeen: time.Now(),
		LastSeen:  time.Now(),
	})

	matches := store.EnrichEvent("", "Request to evil.example.com detected")
	if len(matches) != 1 {
		t.Errorf("expected 1 domain match in description, got %d", len(matches))
	}
}

func TestThreatIntelStore_AddDefaultFeeds(t *testing.T) {
	store := NewThreatIntelStore()
	store.AddDefaultFeeds()

	if store.TotalFeeds != 3 {
		t.Errorf("expected 3 default feeds, got %d", store.TotalFeeds)
	}

	feeds := store.GetFeeds()
	for _, f := range feeds {
		if f.Enabled {
			t.Errorf("default feed %s should be disabled", f.Name)
		}
	}
}

func TestThreatIntelStore_Stats(t *testing.T) {
	store := NewThreatIntelStore()
	store.AddIOC(IOC{Type: IOCTypeIP, Value: "1.2.3.4", FirstSeen: time.Now(), LastSeen: time.Now()})
	store.AddDefaultFeeds()

	stats := store.Stats()
	if stats["total_iocs"] != 1 {
		t.Errorf("expected total_iocs=1, got %v", stats["total_iocs"])
	}
	if stats["total_feeds"] != 3 {
		t.Errorf("expected total_feeds=3, got %v", stats["total_feeds"])
	}
}

func TestAuditThreatFeedProjectionsRedactCredentialsOnCopies(t *testing.T) {
	store := NewThreatIntelStore()
	store.feeds = []ThreatFeed{{Name: "fixture", APIKey: "synthetic-private-value"}}
	for _, feeds := range [][]ThreatFeed{store.GetFeeds(), store.Stats()["feeds"].([]ThreatFeed)} {
		if feeds[0].APIKey != "" {
			t.Fatal("public feed projection includes credentials")
		}
		feeds[0].Name = "mutated"
	}
	if store.feeds[0].APIKey == "" || store.feeds[0].Name != "fixture" {
		t.Fatal("projection mutated refresh config")
	}
}

func TestAuditWebhookProjectionOmitsAuthorizationHeaders(t *testing.T) {
	service := newTestService(t)
	service.SetWebhookConfig(WebhookConfig{Endpoints: []string{"https://synthetic.invalid/hook"}, Headers: map[string]string{"Authorization": "synthetic-private-value"}})
	projected := service.GetWebhookConfig()
	if len(projected.Headers) != 0 {
		t.Fatal("webhook config exposes authorization headers")
	}
	projected.Endpoints[0] = "changed"
	if service.webhook.config.Headers["Authorization"] == "" || service.webhook.config.Endpoints[0] == "changed" {
		t.Fatal("projection mutated internal delivery config")
	}
}
