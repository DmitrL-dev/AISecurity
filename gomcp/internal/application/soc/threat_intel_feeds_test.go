package soc

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// ── ParseThreatFeeds (pure, env-config) ──────────────────────────────────────

func TestParseThreatFeeds(t *testing.T) {
	if got := ParseThreatFeeds(""); got != nil {
		t.Fatalf("empty input must be nil, got %v", got)
	}
	if got := ParseThreatFeeds("   "); got != nil {
		t.Fatalf("blank input must be nil, got %v", got)
	}

	spec := "OTX|https://otx.example/v1|json|30m|secretkey" +
		";URLhaus|https://urlhaus.example/csv|csv" + // no interval/key → defaults
		";Bad" + // too few fields → skipped
		";NoURL||json" + // empty url → skipped
		";BadType|https://x.example|xml" // unsupported type → skipped
	got := ParseThreatFeeds(spec)
	if len(got) != 2 {
		t.Fatalf("want 2 valid feeds, got %d (%+v)", len(got), got)
	}

	otx := got[0]
	if otx.Name != "OTX" || otx.URL != "https://otx.example/v1" || otx.Type != "json" {
		t.Fatalf("otx feed parsed wrong: %+v", otx)
	}
	if otx.Interval != 30*time.Minute {
		t.Fatalf("otx interval want 30m, got %v", otx.Interval)
	}
	if otx.APIKey != "secretkey" {
		t.Fatalf("otx apikey want secretkey, got %q", otx.APIKey)
	}
	if !otx.Enabled {
		t.Fatal("a feed with a URL must be Enabled")
	}

	uh := got[1]
	if uh.Type != "csv" || uh.Interval != time.Hour {
		t.Fatalf("urlhaus defaults wrong: %+v", uh)
	}
}

// ── SSRF protection on the fetch path ────────────────────────────────────────

func TestFetchFeed_SSRFBlocked(t *testing.T) {
	store := NewThreatIntelStore() // real client (SafeDialContext) + real ValidateWebhookURL
	blocked := []string{
		"http://127.0.0.1/feed.json",                       // loopback
		"http://169.254.169.254/latest/meta-data/",          // cloud metadata (link-local)
		"http://10.0.0.5/feed.json",                          // private
		"http://[::1]/feed.json",                             // ipv6 loopback
		"file:///etc/passwd",                                 // non-http scheme
	}
	for _, u := range blocked {
		if _, err := store.fetchFeed(ThreatFeed{Name: "x", URL: u, Type: "json", Enabled: true}); err == nil {
			t.Fatalf("expected SSRF block for %s, got nil error", u)
		}
	}
}

// ── End-to-end fetch + parse (loopback test server) ──────────────────────────

// withLoopbackFetch bypasses the SSRF guard for a loopback httptest server: it
// stubs ValidateWebhookURL and points the store's client at the test server.
func withLoopbackFetch(t *testing.T, store *ThreatIntelStore, ts *httptest.Server) {
	t.Helper()
	orig := domsoc.ValidateWebhookURL
	domsoc.ValidateWebhookURL = func(string) error { return nil }
	t.Cleanup(func() { domsoc.ValidateWebhookURL = orig })
	store.client = ts.Client()
}

func TestRefreshAll_JSONFeed(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`[
			{"type":"ipv4-addr","value":"203.0.113.7","severity":"high","source":"unit"},
			{"type":"domain-name","value":"evil.example","severity":"critical","source":"unit"}
		]`))
	}))
	defer ts.Close()

	store := NewThreatIntelStore()
	withLoopbackFetch(t, store, ts)
	store.AddFeed(ThreatFeed{Name: "json-test", URL: ts.URL, Type: "json", Enabled: true})

	if err := store.RefreshAll(); err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	if store.IOCCount() != 2 {
		t.Fatalf("want 2 IOCs imported, got %d", store.IOCCount())
	}
	if m := store.LookupAny("203.0.113.7"); len(m) == 0 {
		t.Fatal("imported IP IOC not found via LookupAny")
	}
}

func TestRefreshAll_CSVFeed(t *testing.T) {
	// URLhaus-style: '#' comments + columns; the URL column is the primary IOC.
	csvBody := "# comment line, ignored\n" +
		"id,dateadded,url,url_status,threat\n" + // header row: 'url' col is the IOC
		"1,2026-06-14,http://malware.example/payload.bin,online,malware_download\n" +
		"2,2026-06-14,http://c2.example/beacon,online,botnet_cc\n"
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/csv")
		w.Write([]byte(csvBody))
	}))
	defer ts.Close()

	store := NewThreatIntelStore()
	withLoopbackFetch(t, store, ts)
	store.AddFeed(ThreatFeed{Name: "csv-test", URL: ts.URL, Type: "csv", Enabled: true})

	if err := store.RefreshAll(); err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	// 2 data rows → 2 URL IOCs (the header row's 'url' is a non-IOC string, skipped).
	if store.IOCCount() != 2 {
		t.Fatalf("want 2 CSV IOCs, got %d (%+v)", store.IOCCount(), store.ListIOCs())
	}
	if m := store.LookupAny("http://malware.example/payload.bin"); len(m) == 0 {
		t.Fatal("CSV URL IOC not found")
	}
}

// ── classifyIOC unit ─────────────────────────────────────────────────────────

func TestClassifyIOC(t *testing.T) {
	cases := []struct {
		in   string
		typ  IOCType
		want bool
	}{
		{"http://evil.example/x", IOCTypeURL, true},
		{"https://c2.example", IOCTypeURL, true},
		{"8.8.8.8", IOCTypeIP, true},
		{"2001:db8::1", IOCTypeIP, true},
		{"d41d8cd98f00b204e9800998ecf8427e", IOCTypeHash, true}, // md5 (32 hex)
		{"evil.example", IOCTypeDomain, true},
		{"not an ioc", "", false}, // has space
		{"2026", "", false},       // no dot, not hash-len
		{"", "", false},
		{"plainword", "", false},
	}
	for _, c := range cases {
		got, ok := classifyIOC(c.in)
		if ok != c.want || (ok && got != c.typ) {
			t.Errorf("classifyIOC(%q) = (%q,%v), want (%q,%v)", c.in, got, ok, c.typ, c.want)
		}
	}
}

// ── StartConfiguredThreatFeeds wiring (count + feed registration) ─────────────

func TestStartConfiguredThreatFeeds(t *testing.T) {
	store := NewThreatIntelStore()
	done := make(chan struct{})
	defer close(done)

	// Loopback URLs: the background RefreshAll will be SSRF-blocked instantly
	// (no network), so this stays hermetic; we assert wiring, not fetch success.
	spec := "F1|http://127.0.0.1:9/a.json|json|1h;F2|http://127.0.0.1:9/b.csv|csv"
	n := StartConfiguredThreatFeeds(store, spec, "", done)
	if n != 2 {
		t.Fatalf("want 2 feeds started, got %d", n)
	}

	feeds := store.GetFeeds()
	if len(feeds) != 2 {
		t.Fatalf("want 2 feeds registered, got %d", len(feeds))
	}

	// No spec and no OTX key → nothing started.
	store2 := NewThreatIntelStore()
	if n := StartConfiguredThreatFeeds(store2, "", "", done); n != 0 {
		t.Fatalf("unconfigured must start 0 feeds, got %d", n)
	}
}
