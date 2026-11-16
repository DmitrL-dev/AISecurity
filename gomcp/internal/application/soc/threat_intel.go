// Package soc provides a threat intelligence feed integration
// for enriching SOC events and correlation rules.
//
// Supports:
//   - STIX/TAXII 2.1 feeds (JSON)
//   - CSV IOC lists (hashes, IPs, domains)
//   - Local file-based IOC database
//   - Periodic background refresh
package soc

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"sort"
	"strings"
	"sync"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// ─── IOC Types ──────────────────────────────────────────

// IOCType represents the type of Indicator of Compromise.
type IOCType string

const (
	IOCTypeIP     IOCType = "ipv4-addr"
	IOCTypeDomain IOCType = "domain-name"
	IOCTypeHash   IOCType = "file:hashes"
	IOCTypeURL    IOCType = "url"
	IOCCVE        IOCType = "vulnerability"
	IOCPattern    IOCType = "pattern"
)

// IOC is an Indicator of Compromise.
type IOC struct {
	Type       IOCType   `json:"type"`
	Value      string    `json:"value"`
	Source     string    `json:"source"`     // Feed name
	Severity   string    `json:"severity"`   // critical/high/medium/low
	Tags       []string  `json:"tags"`       // MITRE ATT&CK, campaign, etc.
	FirstSeen  time.Time `json:"first_seen"`
	LastSeen   time.Time `json:"last_seen"`
	Confidence float64   `json:"confidence"` // 0.0-1.0
}

// ThreatFeed represents a configured threat intelligence source.
type ThreatFeed struct {
	Name        string        `json:"name"`
	URL         string        `json:"url"`
	Type        string        `json:"type"` // stix, csv, json
	Enabled     bool          `json:"enabled"`
	Interval    time.Duration `json:"interval"`
	APIKey      string        `json:"api_key,omitempty"`
	LastFetch   time.Time     `json:"last_fetch"`
	IOCCount    int           `json:"ioc_count"`
	LastError   string        `json:"last_error,omitempty"`
}

// ─── Threat Intel Store ─────────────────────────────────

// ThreatIntelStore manages IOCs from multiple feeds.
type ThreatIntelStore struct {
	mu    sync.RWMutex
	iocs  map[string]*IOC     // key: type:value
	feeds []ThreatFeed
	client *http.Client

	// Stats
	TotalIOCs    int `json:"total_iocs"`
	TotalFeeds   int `json:"total_feeds"`
	LastRefresh  time.Time `json:"last_refresh"`
	MatchesFound int64 `json:"matches_found"`
}

// NewThreatIntelStore creates an empty threat intel store.
//
// The HTTP client is SSRF-hardened: SafeDialContext re-resolves the target and
// rejects loopback/private/link-local/metadata IPs at dial time (DNS-rebinding
// safe), mirroring the SOAR webhook/notify/escalate executors. Feed URLs are
// additionally validated up front in fetchFeed via ValidateWebhookURL.
func NewThreatIntelStore() *ThreatIntelStore {
	return &ThreatIntelStore{
		iocs: make(map[string]*IOC),
		client: &http.Client{
			Timeout: 30 * time.Second,
			// DisableCompression: don't let the transport transparently inflate a
			// gzip feed body (a decompression bomb); paired with the per-feed
			// LimitReader in fetchFeed (Review 14.06 round-5).
			Transport: &http.Transport{
				DialContext:        domsoc.SafeDialContext,
				DisableCompression: true,
			},
		},
	}
}

// AddFeed registers a threat intel feed.
func (t *ThreatIntelStore) AddFeed(feed ThreatFeed) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.feeds = append(t.feeds, feed)
	t.TotalFeeds = len(t.feeds)
}

// AddIOC adds or updates an indicator.
func (t *ThreatIntelStore) AddIOC(ioc IOC) {
	t.mu.Lock()
	defer t.mu.Unlock()
	key := fmt.Sprintf("%s:%s", ioc.Type, strings.ToLower(ioc.Value))
	if existing, ok := t.iocs[key]; ok {
		// Update — keep earliest first_seen, latest last_seen
		if ioc.FirstSeen.Before(existing.FirstSeen) {
			existing.FirstSeen = ioc.FirstSeen
		}
		existing.LastSeen = ioc.LastSeen
		if ioc.Confidence > existing.Confidence {
			existing.Confidence = ioc.Confidence
		}
	} else {
		// Cap the store with oldest-LastSeen eviction (Review 14.06 round-5): the
		// IOC map had no bound and never evicted, so large/churning feeds grew it
		// without limit → slow OOM of the long-lived SOC process. Evict a batch
		// when full (amortizes the O(n log n) sweep across ~iocEvictBatch inserts).
		if len(t.iocs) >= maxIOCs {
			t.evictOldestIOCs(iocEvictBatch)
		}
		t.iocs[key] = &ioc
		t.TotalIOCs = len(t.iocs)
	}
}

const (
	// maxIOCs bounds the live-feed indicator store (memory). EnrichEvent lookups
	// are O(1) map hits; the cap mainly guards memory + the ListIOCs copy.
	maxIOCs = 200_000
	// iocEvictBatch is dropped in one sweep when the store hits maxIOCs.
	iocEvictBatch = maxIOCs / 10
)

// evictOldestIOCs removes the n indicators with the oldest LastSeen. Caller holds
// t.mu. Runs only when the store is full, so the amortized per-AddIOC cost is small.
func (t *ThreatIntelStore) evictOldestIOCs(n int) {
	if n <= 0 || len(t.iocs) == 0 {
		return
	}
	type aged struct {
		key  string
		seen time.Time
	}
	all := make([]aged, 0, len(t.iocs))
	for k, ioc := range t.iocs {
		all = append(all, aged{k, ioc.LastSeen})
	}
	sort.Slice(all, func(i, j int) bool { return all[i].seen.Before(all[j].seen) })
	if n > len(all) {
		n = len(all)
	}
	for _, e := range all[:n] {
		delete(t.iocs, e.key)
	}
	t.TotalIOCs = len(t.iocs)
}

// Lookup checks if a value matches any known IOC.
// Returns nil if not found.
//
// Review 13.06 (audit D4 — data race): returns a COPY held under the lock, not
// the live map pointer. AddIOC mutates the stored *IOC in place under the lock,
// so callers (EnrichEvent) that dereferenced the returned pointer outside any
// lock could observe a torn read. Copying under the lock removes the race.
func (t *ThreatIntelStore) Lookup(iocType IOCType, value string) *IOC {
	t.mu.Lock()
	defer t.mu.Unlock()
	key := fmt.Sprintf("%s:%s", iocType, strings.ToLower(value))
	ioc, ok := t.iocs[key]
	if !ok {
		return nil
	}
	t.MatchesFound++
	cp := *ioc
	return &cp
}

// LookupAny checks value against all IOC types (broad search).
//
// Review pass 4 (error-handling/resource-safety): like Lookup, this returns
// COPIES held under the lock rather than the live map pointers. AddIOC mutates
// the stored *IOC in place under the lock, so a caller that dereferenced a
// returned live pointer after RUnlock could observe a torn read (data race).
// Copying under the lock removes the race, matching Lookup's contract.
func (t *ThreatIntelStore) LookupAny(value string) []*IOC {
	t.mu.RLock()
	defer t.mu.RUnlock()

	lowValue := strings.ToLower(value)
	var matches []*IOC
	for key, ioc := range t.iocs {
		if strings.HasSuffix(key, ":"+lowValue) {
			cp := *ioc
			matches = append(matches, &cp)
		}
	}
	return matches
}

// EnrichEvent checks event fields against IOC database and returns matches.
func (t *ThreatIntelStore) EnrichEvent(sourceIP, description string) []IOC {
	var matches []IOC

	// Check source IP
	if sourceIP != "" {
		if ioc := t.Lookup(IOCTypeIP, sourceIP); ioc != nil {
			matches = append(matches, *ioc)
		}
	}

	// Check description for domain/URL IOCs
	if description != "" {
		words := strings.Fields(description)
		for _, word := range words {
			word = strings.Trim(word, ".,;:\"'()[]{}!")
			if strings.Contains(word, ".") && len(word) > 4 {
				if ioc := t.Lookup(IOCTypeDomain, word); ioc != nil {
					matches = append(matches, *ioc)
				}
			}
		}
	}

	return matches
}

// ─── Feed Fetching ──────────────────────────────────────

// RefreshAll fetches all enabled feeds and updates IOC database.
func (t *ThreatIntelStore) RefreshAll() error {
	t.mu.RLock()
	feeds := make([]ThreatFeed, len(t.feeds))
	copy(feeds, t.feeds)
	t.mu.RUnlock()

	var errs []string
	for i, feed := range feeds {
		if !feed.Enabled {
			continue
		}

		iocs, err := t.fetchFeed(feed)
		if err != nil {
			feeds[i].LastError = err.Error()
			errs = append(errs, fmt.Sprintf("%s: %v", feed.Name, err))
			continue
		}

		for _, ioc := range iocs {
			t.AddIOC(ioc)
		}

		feeds[i].LastFetch = time.Now()
		feeds[i].IOCCount = len(iocs)
		feeds[i].LastError = ""
	}

	// Update feed states
	t.mu.Lock()
	t.feeds = feeds
	t.LastRefresh = time.Now()
	t.mu.Unlock()

	if len(errs) > 0 {
		return fmt.Errorf("feed errors: %s", strings.Join(errs, "; "))
	}
	return nil
}

// fetchFeed retrieves IOCs from a single feed.
// maxFeedBytes caps the (decompressed) bytes read from a threat-intel feed
// response, bounding memory against a decompression-bomb / oversized feed.
const maxFeedBytes = 128 << 20 // 128 MiB

func (t *ThreatIntelStore) fetchFeed(feed ThreatFeed) ([]IOC, error) {
	// SSRF guard: reject loopback/private/link-local/metadata targets before we
	// dial. SafeDialContext on the client re-checks at dial time (DNS-rebinding
	// safe); this up-front check gives a clean error and blocks file:// etc.
	if err := domsoc.ValidateWebhookURL(feed.URL); err != nil {
		return nil, fmt.Errorf("ssrf blocked: %w", err)
	}

	req, err := http.NewRequest("GET", feed.URL, nil)
	if err != nil {
		return nil, err
	}

	if feed.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+feed.APIKey)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "SENTINEL-ThreatIntel/1.0")

	resp, err := t.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	// Bound the body before any parser reads it (Review 14.06 round-5). Feed
	// content is externally controlled and the parsers had NO size limit, so a
	// small (optionally gzip) body could inflate to GBs and OOM the long-lived SOC
	// process — recurring on every background refresh = persistent SOC outage.
	// LimitReader caps the bytes the parser sees; a truncated bomb makes JSON/STIX
	// fail to decode (rejected) and CSV drop only its partial tail. The original
	// body is still closed by the defer above.
	resp.Body = io.NopCloser(io.LimitReader(resp.Body, maxFeedBytes))

	switch feed.Type {
	case "stix":
		return t.parseSTIX(resp)
	case "json":
		return t.parseJSON(resp)
	case "csv":
		return t.parseCSV(resp.Body)
	default:
		return nil, fmt.Errorf("unsupported feed type: %s", feed.Type)
	}
}

// parseCSV parses a CSV IOC feed (e.g. abuse.ch URLhaus). Lines beginning with
// '#' are treated as comments. For each row the first recognizable indicator
// (URL > IP > hash > domain) is imported, so one row yields one IOC.
func (t *ThreatIntelStore) parseCSV(r io.Reader) ([]IOC, error) {
	cr := csv.NewReader(r)
	cr.Comment = '#'
	cr.FieldsPerRecord = -1 // variable column counts
	cr.LazyQuotes = true

	now := time.Now()
	var iocs []IOC
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed rows rather than abort the whole feed
		}
		for _, field := range rec {
			f := strings.TrimSpace(strings.Trim(field, `"`))
			if typ, ok := classifyIOC(f); ok {
				iocs = append(iocs, IOC{
					Type:       typ,
					Value:      f,
					Source:     "csv",
					Severity:   "medium",
					FirstSeen:  now,
					LastSeen:   now,
					Confidence: 0.6,
				})
				break // one (primary) indicator per row
			}
		}
	}
	return iocs, nil
}

// classifyIOC heuristically determines the IOC type of a CSV token. Returns
// ok=false for tokens that are not recognizable indicators.
func classifyIOC(s string) (IOCType, bool) {
	if s == "" || strings.ContainsAny(s, " \t") {
		return "", false
	}
	if strings.Contains(s, "://") {
		return IOCTypeURL, true
	}
	if ip := net.ParseIP(s); ip != nil {
		return IOCTypeIP, true
	}
	if l := len(s); (l == 32 || l == 40 || l == 64) && isHex(s) {
		return IOCTypeHash, true
	}
	// Hostname-ish: has a dot and a letter, no path/credential markers.
	if strings.Contains(s, ".") && strings.ContainsAny(s, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") && !strings.ContainsAny(s, "/@:") {
		return IOCTypeDomain, true
	}
	return "", false
}

func isHex(s string) bool {
	for _, c := range s {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

// parseSTIX parses STIX 2.1 bundle response.
func (t *ThreatIntelStore) parseSTIX(resp *http.Response) ([]IOC, error) {
	var bundle struct {
		Type    string          `json:"type"`
		ID      string          `json:"id"`
		Objects json.RawMessage `json:"objects"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&bundle); err != nil {
		return nil, fmt.Errorf("stix parse: %w", err)
	}

	var objects []struct {
		Type    string `json:"type"`
		Pattern string `json:"pattern"`
		Name    string `json:"name"`
	}
	if err := json.Unmarshal(bundle.Objects, &objects); err != nil {
		return nil, fmt.Errorf("stix objects: %w", err)
	}

	var iocs []IOC
	now := time.Now()
	for _, obj := range objects {
		if obj.Type != "indicator" {
			continue
		}
		iocs = append(iocs, IOC{
			Type:       IOCPattern,
			Value:      obj.Pattern,
			Source:     "stix",
			FirstSeen:  now,
			LastSeen:   now,
			Confidence: 0.8,
		})
	}
	return iocs, nil
}

// parseJSON parses a simple JSON IOC list.
func (t *ThreatIntelStore) parseJSON(resp *http.Response) ([]IOC, error) {
	var iocs []IOC
	if err := json.NewDecoder(resp.Body).Decode(&iocs); err != nil {
		return nil, fmt.Errorf("json parse: %w", err)
	}
	return iocs, nil
}

// ─── Background Refresh ─────────────────────────────────

// StartBackgroundRefresh runs periodic feed refresh in a goroutine.
func (t *ThreatIntelStore) StartBackgroundRefresh(interval time.Duration, stop <-chan struct{}) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		// Initial fetch
		if err := t.RefreshAll(); err != nil {
			log.Printf("[ThreatIntel] initial refresh error: %v", err)
		}

		for {
			select {
			case <-ticker.C:
				if err := t.RefreshAll(); err != nil {
					log.Printf("[ThreatIntel] refresh error: %v", err)
				} else {
					// Read the stat counters under the lock — AddIOC/AddFeed
					// mutate them under t.mu from other goroutines (e.g. FeedSync
					// pollers), so an unlocked read here is a data race.
					t.mu.RLock()
					totalIOCs, totalFeeds := t.TotalIOCs, t.TotalFeeds
					t.mu.RUnlock()
					log.Printf("[ThreatIntel] refreshed: %d IOCs from %d feeds",
						totalIOCs, totalFeeds)
				}
			case <-stop:
				return
			}
		}
	}()
}

// Stats returns threat intel statistics.
func (t *ThreatIntelStore) Stats() map[string]interface{} {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return map[string]interface{}{
		"total_iocs":    t.TotalIOCs,
		"total_feeds":   t.TotalFeeds,
		"last_refresh":  t.LastRefresh,
		"matches_found": t.MatchesFound,
		"feeds":         redactedFeeds(t.feeds),
	}
}

// GetFeeds returns all configured feeds with their status.
func (t *ThreatIntelStore) GetFeeds() []ThreatFeed {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return redactedFeeds(t.feeds)
}

// Both public projections redact on a copy; internal refresh retains credentials.
func redactedFeeds(source []ThreatFeed) []ThreatFeed {
	feeds := append([]ThreatFeed(nil), source...)
	for i := range feeds {
		feeds[i].APIKey = ""
	}
	return feeds
}

// ListIOCs returns a snapshot of all stored indicators (for API exposure).
func (t *ThreatIntelStore) ListIOCs() []IOC {
	t.mu.RLock()
	defer t.mu.RUnlock()
	out := make([]IOC, 0, len(t.iocs))
	for _, ioc := range t.iocs {
		out = append(out, *ioc)
	}
	return out
}

// IOCCount returns the number of stored indicators (cheap; no snapshot).
func (t *ThreatIntelStore) IOCCount() int {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return len(t.iocs)
}

// AddDefaultFeeds registers SENTINEL-native threat feeds.
func (t *ThreatIntelStore) AddDefaultFeeds() {
	t.AddFeed(ThreatFeed{
		Name:     "OWASP LLM Top 10",
		Type:     "json",
		Enabled:  false, // Enable when URL configured
		Interval: 24 * time.Hour,
	})
	t.AddFeed(ThreatFeed{
		Name:     "MITRE ATLAS",
		Type:     "stix",
		Enabled:  false,
		Interval: 12 * time.Hour,
	})
	t.AddFeed(ThreatFeed{
		Name:     "SENTINEL Community IOCs",
		Type:     "json",
		Enabled:  false,
		Interval: 1 * time.Hour,
	})
}

// ─── Operator configuration (env-driven) ────────────────

// ParseThreatFeeds parses the SOC_THREATINTEL_FEEDS env value into feed configs.
//
// Format — feeds separated by ';', fields by '|':
//
//	Name|https://host/feed|type|interval|apikey
//
// where type ∈ {json,csv,stix}, interval is a Go duration (default 1h, optional),
// and apikey is optional (sent as a Bearer token by ThreatIntelStore.fetchFeed).
// A feed with a non-empty URL is Enabled. Malformed/unsupported entries are
// skipped; empty input → nil.
//
// SSRF validation deliberately happens at fetch time (SafeDialContext +
// ValidateWebhookURL), not here, so this stays pure and unit-testable without
// network access.
func ParseThreatFeeds(env string) []ThreatFeed {
	env = strings.TrimSpace(env)
	if env == "" {
		return nil
	}
	var feeds []ThreatFeed
	for _, spec := range strings.Split(env, ";") {
		spec = strings.TrimSpace(spec)
		if spec == "" {
			continue
		}
		parts := strings.Split(spec, "|")
		if len(parts) < 3 {
			continue
		}
		name := strings.TrimSpace(parts[0])
		rawURL := strings.TrimSpace(parts[1])
		ftype := strings.ToLower(strings.TrimSpace(parts[2]))
		if name == "" || rawURL == "" {
			continue
		}
		switch ftype {
		case "json", "csv", "stix":
		default:
			continue // unsupported feed type
		}
		interval := time.Hour
		if len(parts) >= 4 {
			if d, err := time.ParseDuration(strings.TrimSpace(parts[3])); err == nil && d > 0 {
				interval = d
			}
		}
		apiKey := ""
		if len(parts) >= 5 {
			apiKey = strings.TrimSpace(parts[4])
		}
		feeds = append(feeds, ThreatFeed{
			Name:     name,
			URL:      rawURL,
			Type:     ftype,
			Enabled:  true,
			Interval: interval,
			APIKey:   apiKey,
		})
	}
	return feeds
}

// StartConfiguredThreatFeeds wires operator-configured threat-intel feeds into
// the store and starts SSRF-protected background fetching. feedsSpec is the
// SOC_THREATINTEL_FEEDS value (generic json/csv/stix feeds, fetched by
// ThreatIntelStore.RefreshAll); otxKey is the optional SOC_OTX_API_KEY shortcut
// for AlienVault OTX (fetched by FeedSync, which sets the X-OTX-API-KEY header).
// Both paths import into the same store, so live IOCs become visible via the API
// and used in ingest-time enrichment. Returns the number of feeds started.
func StartConfiguredThreatFeeds(store *ThreatIntelStore, feedsSpec, otxKey string, done <-chan struct{}) int {
	started := 0

	feeds := ParseThreatFeeds(feedsSpec)
	refresh := 6 * time.Hour
	enabled := 0
	for _, f := range feeds {
		store.AddFeed(f)
		if f.Enabled {
			enabled++
			if f.Interval > 0 && f.Interval < refresh {
				refresh = f.Interval
			}
		}
	}
	if enabled > 0 {
		store.StartBackgroundRefresh(refresh, done)
		started += enabled
	}

	if strings.TrimSpace(otxKey) != "" {
		NewFeedSync(store, []STIXFeedConfig{DefaultOTXFeed(otxKey)}).Start(done)
		started++
	}

	return started
}
