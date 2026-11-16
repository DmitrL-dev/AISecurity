package soc

import (
	"strings"
	"sync"
	"time"
)

// ThreatIntelEngine implements §6 — IOC (Indicator of Compromise) matching.
// Maintains feed subscriptions and in-memory IOC database for real-time matching.
type ThreatIntelEngine struct {
	mu    sync.RWMutex
	iocs  map[string]*IOC // key = value (IP, domain, hash)
	feeds []Feed
	hits  []IOCHit
	max   int
}

// IOCType categorizes the indicator.
type IOCType string

const (
	IOCIP     IOCType = "ip"
	IOCDomain IOCType = "domain"
	IOCHash   IOCType = "hash"
	IOCEmail  IOCType = "email"
	IOCURL    IOCType = "url"
)

// IOC is an individual indicator of compromise.
type IOC struct {
	Value       string    `json:"value"`
	Type        IOCType   `json:"type"`
	Severity    string    `json:"severity"` // CRITICAL, HIGH, MEDIUM, LOW
	Source      string    `json:"source"`   // Feed name
	Tags        []string  `json:"tags"`
	Description string    `json:"description"`
	FirstSeen   time.Time `json:"first_seen"`
	LastSeen    time.Time `json:"last_seen"`
	HitCount    int       `json:"hit_count"`
}

// Feed represents a threat intelligence source.
type Feed struct {
	Name        string    `json:"name"`
	URL         string    `json:"url"`
	Type        string    `json:"type"` // stix, csv, json
	Enabled     bool      `json:"enabled"`
	IOCCount    int       `json:"ioc_count"`
	LastSync    time.Time `json:"last_sync"`
	SyncInterval string  `json:"sync_interval"`
}

// IOCHit records a match between an event and an IOC.
type IOCHit struct {
	IOCValue  string    `json:"ioc_value"`
	IOCType   IOCType   `json:"ioc_type"`
	EventID   string    `json:"event_id"`
	Severity  string    `json:"severity"`
	Source    string    `json:"source"`
	Timestamp time.Time `json:"timestamp"`
}

// NewThreatIntelEngine creates the IOC matching engine with default feeds.
func NewThreatIntelEngine() *ThreatIntelEngine {
	t := &ThreatIntelEngine{
		iocs: make(map[string]*IOC),
		max:  1000,
	}
	t.loadDefaultFeeds()
	t.loadSampleIOCs()
	return t
}

func (t *ThreatIntelEngine) loadDefaultFeeds() {
	t.feeds = []Feed{
		{Name: "AlienVault OTX", URL: "https://otx.alienvault.com/api/v1/pulses/subscribed", Type: "json", Enabled: true, SyncInterval: "1h"},
		{Name: "Abuse.ch URLhaus", URL: "https://urlhaus.abuse.ch/downloads/csv_recent/", Type: "csv", Enabled: true, SyncInterval: "30m"},
		{Name: "CIRCL MISP", URL: "https://www.circl.lu/doc/misp/feed-osint/", Type: "stix", Enabled: false, SyncInterval: "6h"},
		{Name: "Internal STIX", URL: "file:///var/sentinel/iocs/internal.stix", Type: "stix", Enabled: true, SyncInterval: "5m"},
	}
}

func (t *ThreatIntelEngine) loadSampleIOCs() {
	samples := []IOC{
		{Value: "185.220.101.35", Type: IOCIP, Severity: "HIGH", Source: "AlienVault OTX", Tags: []string{"tor-exit", "scanner"}, Description: "Known Tor exit node / mass scanner"},
		{Value: "evil-ai-jailbreak.com", Type: IOCDomain, Severity: "CRITICAL", Source: "Internal STIX", Tags: []string{"jailbreak", "c2"}, Description: "Jailbreak prompt C2 domain"},
		{Value: "d41d8cd98f00b204e9800998ecf8427e", Type: IOCHash, Severity: "MEDIUM", Source: "Abuse.ch URLhaus", Tags: []string{"malware-hash"}, Description: "Known malware hash (MD5)"},
		{Value: "attacker@malicious-prompts.org", Type: IOCEmail, Severity: "HIGH", Source: "Internal STIX", Tags: []string{"phishing", "social-engineering"}, Description: "Known prompt injection author"},
	}
	now := time.Now()
	for _, ioc := range samples {
		ioc := ioc // shadow to capture per-iteration (safe for Go <1.22)
		ioc.FirstSeen = now.Add(-72 * time.Hour)
		ioc.LastSeen = now
		t.iocs[ioc.Value] = &ioc
	}
	for i := range t.feeds {
		if t.feeds[i].Enabled {
			t.feeds[i].IOCCount = len(samples) / 2
			t.feeds[i].LastSync = now.Add(-15 * time.Minute)
		}
	}
}

// Match checks a string against the IOC database.
// Returns matching IOC or nil.
func (t *ThreatIntelEngine) Match(value string) *IOC {
	t.mu.Lock()
	defer t.mu.Unlock()

	normalized := strings.ToLower(strings.TrimSpace(value))
	if ioc, ok := t.iocs[normalized]; ok {
		ioc.HitCount++
		ioc.LastSeen = time.Now()
		copy := *ioc // return safe copy, not mutable internal pointer
		return &copy
	}
	return nil
}

// MatchEvent checks all fields of an event description for IOC matches.
// Returns all hits.
func (t *ThreatIntelEngine) MatchEvent(eventID, text string) []IOCHit {
	lower := strings.ToLower(text)
	
	t.mu.RLock()
	var matched []*IOC
	// The keys in t.iocs are guaranteed strictly lowercase via AddIOC.
	// For loadSampleIOCs, they are also lower case. So we can use `key`.
	for key, ioc := range t.iocs {
		// substring fast-path directly bounds to the key
		if strings.Contains(lower, key) {
			matched = append(matched, ioc)
		}
	}
	t.mu.RUnlock()

	if len(matched) == 0 {
		return nil
	}

	var hits []IOCHit
	now := time.Now()

	t.mu.Lock()
	defer t.mu.Unlock()

	for _, ioc := range matched {
		hit := IOCHit{
			IOCValue:  ioc.Value,
			IOCType:   ioc.Type,
			EventID:   eventID,
			Severity:  ioc.Severity,
			Source:    ioc.Source,
			Timestamp: now,
		}
		ioc.HitCount++
		ioc.LastSeen = now
		hits = append(hits, hit)
	}

	// Batch append hits to the global ring buffer
	t.hits = append(t.hits, hits...)
	if len(t.hits) > t.max {
		overflow := len(t.hits) - t.max
		newHits := make([]IOCHit, t.max)
		copy(newHits, t.hits[overflow:])
		t.hits = newHits
	}

	return hits
}

// AddIOC adds a custom indicator of compromise.
func (t *ThreatIntelEngine) AddIOC(ioc IOC) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if ioc.FirstSeen.IsZero() {
		ioc.FirstSeen = time.Now()
	}
	ioc.LastSeen = time.Now()
	t.iocs[strings.ToLower(ioc.Value)] = &ioc
}

// ListIOCs returns all indicators.
func (t *ThreatIntelEngine) ListIOCs() []IOC {
	t.mu.RLock()
	defer t.mu.RUnlock()
	result := make([]IOC, 0, len(t.iocs))
	for _, ioc := range t.iocs {
		result = append(result, *ioc)
	}
	return result
}

// ListFeeds returns configured threat intel feeds.
func (t *ThreatIntelEngine) ListFeeds() []Feed {
	t.mu.RLock()
	defer t.mu.RUnlock()
	result := make([]Feed, len(t.feeds))
	copy(result, t.feeds)
	return result
}

// RecentHits returns recent IOC match hits.
func (t *ThreatIntelEngine) RecentHits(limit int) []IOCHit {
	t.mu.RLock()
	defer t.mu.RUnlock()
	if limit <= 0 || limit > len(t.hits) {
		limit = len(t.hits)
	}
	start := len(t.hits) - limit
	result := make([]IOCHit, limit)
	copy(result, t.hits[start:])
	return result
}

// Stats returns threat intel statistics.
func (t *ThreatIntelEngine) ThreatIntelStats() map[string]any {
	t.mu.RLock()
	defer t.mu.RUnlock()
	enabledFeeds := 0
	for _, f := range t.feeds {
		if f.Enabled {
			enabledFeeds++
		}
	}
	return map[string]any{
		"total_iocs":    len(t.iocs),
		"total_feeds":   len(t.feeds),
		"enabled_feeds": enabledFeeds,
		"total_hits":    len(t.hits),
	}
}
