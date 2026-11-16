package shadow_ai

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync"
	"testing"
)

// testLogger returns a quiet slog logger for client tests (discard output).
func testLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

// newTestCookieJar returns a cookie jar for Zscaler session tests.
func newTestCookieJar() http.CookieJar {
	jar, _ := cookiejar.New(nil)
	return jar
}

func itoa(n int) string { return strconv.Itoa(n) }

// These tests exercise the REAL vendor HTTP clients against httptest mocks. They
// verify the auth handshake, request paths/headers/bodies, and non-2xx error
// mapping — i.e. the wire contract — without any real vendor creds or network.
//
// The clients are constructed directly (unexported fields set in-package) using
// ts.Client(), which reaches the loopback test server. This intentionally
// bypasses the production SafeDialContext SSRF guard (which would block 127.0.0.1)
// — the guard itself is covered by the domain/soc webhook tests; here we test the
// client logic layered on top of it.

func decodeBody(t *testing.T, r *http.Request) map[string]any {
	t.Helper()
	b, _ := io.ReadAll(r.Body)
	if len(b) == 0 {
		return map[string]any{}
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("decode request body: %v (raw=%q)", err, string(b))
	}
	return m
}

// --- Check Point ---

func TestCheckPoint_BlockDomain_LoginThenCommandsThenPublish(t *testing.T) {
	var paths []string
	var sawSID []string
	mu := sync.Mutex{}

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		paths = append(paths, r.URL.Path)
		sawSID = append(sawSID, r.Header.Get("X-chkp-sid"))
		mu.Unlock()

		if r.Header.Get("Content-Type") != "application/json" {
			t.Errorf("expected JSON content-type, got %q", r.Header.Get("Content-Type"))
		}
		switch r.URL.Path {
		case "/web_api/login":
			_ = json.NewEncoder(w).Encode(map[string]any{"sid": "SID-123", "session-timeout": 600})
		default:
			_ = json.NewEncoder(w).Encode(map[string]any{"uid": "ok"})
		}
	}))
	defer ts.Close()

	c := &CheckPointEnforcer{apiURL: ts.URL, apiKey: "k", client: ts.Client(), logger: testLogger()}

	if err := c.BlockDomain(context.Background(), "chat.openai.com", "shadow ai"); err != nil {
		t.Fatalf("BlockDomain: %v", err)
	}

	// Expected call order: login, add-application-site, publish, add-access-rule, publish.
	want := []string{
		"/web_api/login",
		"/web_api/add-application-site",
		"/web_api/publish",
		"/web_api/add-access-rule",
		"/web_api/publish",
	}
	if strings.Join(paths, ",") != strings.Join(want, ",") {
		t.Fatalf("call sequence mismatch:\n got=%v\nwant=%v", paths, want)
	}
	// login carries no SID; every subsequent call must carry the returned SID.
	if sawSID[0] != "" {
		t.Errorf("login should not send X-chkp-sid, got %q", sawSID[0])
	}
	for i := 1; i < len(sawSID); i++ {
		if sawSID[i] != "SID-123" {
			t.Errorf("call %d (%s) missing/wrong SID: %q", i, paths[i], sawSID[i])
		}
	}
}

func TestCheckPoint_SessionReused(t *testing.T) {
	logins := 0
	mu := sync.Mutex{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/web_api/login" {
			mu.Lock()
			logins++
			mu.Unlock()
			_ = json.NewEncoder(w).Encode(map[string]any{"sid": "SID-1", "session-timeout": 600})
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{})
	}))
	defer ts.Close()

	c := &CheckPointEnforcer{apiURL: ts.URL, apiKey: "k", client: ts.Client(), logger: testLogger()}
	if err := c.HealthCheck(context.Background()); err != nil {
		t.Fatalf("health 1: %v", err)
	}
	if err := c.HealthCheck(context.Background()); err != nil {
		t.Fatalf("health 2: %v", err)
	}
	if logins != 1 {
		t.Fatalf("expected session reuse (1 login), got %d logins", logins)
	}
}

func TestCheckPoint_NonOKMapsToError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/web_api/login" {
			_ = json.NewEncoder(w).Encode(map[string]any{"sid": "SID-1", "session-timeout": 600})
			return
		}
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(`{"message":"generic_err_object_not_found"}`))
	}))
	defer ts.Close()

	c := &CheckPointEnforcer{apiURL: ts.URL, apiKey: "k", client: ts.Client(), logger: testLogger()}
	err := c.BlockIP(context.Background(), "203.0.113.5", 0, "x")
	if err == nil {
		t.Fatal("expected error on 400, got nil")
	}
	if !strings.Contains(err.Error(), "400") {
		t.Errorf("error should mention status 400: %v", err)
	}
}

// --- CrowdStrike Falcon ---

func TestCrowdStrike_IsolateHost_OAuthResolveContain(t *testing.T) {
	var paths []string
	var bearer []string
	mu := sync.Mutex{}

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		paths = append(paths, r.URL.Path)
		bearer = append(bearer, r.Header.Get("Authorization"))
		mu.Unlock()

		switch {
		case r.URL.Path == "/oauth2/token":
			if ct := r.Header.Get("Content-Type"); ct != "application/x-www-form-urlencoded" {
				t.Errorf("token: expected form content-type, got %q", ct)
			}
			_ = r.ParseForm()
			if r.Form.Get("client_id") == "" || r.Form.Get("client_secret") == "" {
				t.Errorf("token: missing client_id/client_secret in form")
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"access_token": "TKN-1", "expires_in": 1800})
		case r.URL.Path == "/devices/queries/devices/v1":
			if got := r.URL.Query().Get("filter"); !strings.Contains(got, "hostname:'host-1'") {
				t.Errorf("device query filter wrong: %q", got)
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"resources": []string{"dev-abc"}})
		case r.URL.Path == "/devices/entities/devices-actions/v2":
			if got := r.URL.Query().Get("action_name"); got != "contain" {
				t.Errorf("expected action_name=contain, got %q", got)
			}
			body := decodeBody(t, r)
			ids, _ := body["ids"].([]any)
			if len(ids) != 1 || ids[0] != "dev-abc" {
				t.Errorf("contain body ids wrong: %v", body["ids"])
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"resources": []any{}})
		default:
			t.Errorf("unexpected path %s", r.URL.Path)
		}
	}))
	defer ts.Close()

	cs := &CrowdStrikeController{clientID: "id", clientSecret: "secret", baseURL: ts.URL, client: ts.Client(), logger: testLogger()}
	if err := cs.IsolateHost(context.Background(), "host-1"); err != nil {
		t.Fatalf("IsolateHost: %v", err)
	}

	want := []string{
		"/oauth2/token",
		"/devices/queries/devices/v1",
		"/devices/entities/devices-actions/v2",
	}
	if strings.Join(paths, ",") != strings.Join(want, ",") {
		t.Fatalf("call sequence mismatch:\n got=%v\nwant=%v", paths, want)
	}
	// Bearer must be present on the API calls (not the token call itself).
	if bearer[1] != "Bearer TKN-1" || bearer[2] != "Bearer TKN-1" {
		t.Errorf("expected Bearer TKN-1 on API calls, got %v", bearer)
	}
}

func TestCrowdStrike_TokenReusedAcrossCalls(t *testing.T) {
	tokenCalls := 0
	mu := sync.Mutex{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/oauth2/token":
			mu.Lock()
			tokenCalls++
			mu.Unlock()
			_ = json.NewEncoder(w).Encode(map[string]any{"access_token": "TKN", "expires_in": 1800})
		case "/sensors/queries/sensors/v1":
			_ = json.NewEncoder(w).Encode(map[string]any{"resources": []string{}})
		default:
			t.Errorf("unexpected path %s", r.URL.Path)
		}
	}))
	defer ts.Close()

	cs := &CrowdStrikeController{clientID: "id", clientSecret: "secret", baseURL: ts.URL, client: ts.Client(), logger: testLogger()}
	for i := 0; i < 3; i++ {
		if err := cs.HealthCheck(context.Background()); err != nil {
			t.Fatalf("health %d: %v", i, err)
		}
	}
	if tokenCalls != 1 {
		t.Fatalf("expected token cached (1 token call), got %d", tokenCalls)
	}
}

func TestCrowdStrike_401TriggersReauth(t *testing.T) {
	tokenCalls := 0
	healthCalls := 0
	mu := sync.Mutex{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/oauth2/token":
			mu.Lock()
			tokenCalls++
			n := tokenCalls
			mu.Unlock()
			_ = json.NewEncoder(w).Encode(map[string]any{"access_token": "TKN-" + itoa(n), "expires_in": 1800})
		case "/sensors/queries/sensors/v1":
			mu.Lock()
			healthCalls++
			n := healthCalls
			mu.Unlock()
			if n == 1 {
				w.WriteHeader(http.StatusUnauthorized) // first call: expired token
				_, _ = w.Write([]byte(`{"errors":[{"message":"access denied"}]}`))
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"resources": []string{}})
		default:
			t.Errorf("unexpected path %s", r.URL.Path)
		}
	}))
	defer ts.Close()

	cs := &CrowdStrikeController{clientID: "id", clientSecret: "secret", baseURL: ts.URL, client: ts.Client(), logger: testLogger()}
	if err := cs.HealthCheck(context.Background()); err != nil {
		t.Fatalf("HealthCheck after re-auth should succeed: %v", err)
	}
	if tokenCalls != 2 {
		t.Errorf("expected 2 token mints (initial + re-auth), got %d", tokenCalls)
	}
	if healthCalls != 2 {
		t.Errorf("expected 2 health attempts (401 then retry), got %d", healthCalls)
	}
}

// fqlEscape must neutralize the single-quote (and backslash) so attacker-influenced
// hostname data cannot break out of the hostname:'...' FQL literal and retarget a
// contain/kill/RTR action at an unintended device.
func TestCrowdStrike_FQLEscape(t *testing.T) {
	cases := []struct{ in, want string }{
		{"host-1", "host-1"},
		{"host' OR hostname:'*", `host\' OR hostname:\'*`},
		{`a\b`, `a\\b`},
		{`x'\`, `x\'\\`},
	}
	for _, c := range cases {
		if got := fqlEscape(c.in); got != c.want {
			t.Errorf("fqlEscape(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// validHostname is the defense-in-depth gate: anything outside the RFC-1123 charset
// (notably the quotes/spaces that enable FQL injection) is rejected before the
// filter is ever built.
func TestCrowdStrike_ValidHostname(t *testing.T) {
	valid := []string{"host-1", "web01.corp.example.com", "A-B-C", "1.2.3.4"}
	for _, h := range valid {
		if !validHostname(h) {
			t.Errorf("validHostname(%q) = false, want true", h)
		}
	}
	invalid := []string{
		"",
		"host' OR hostname:'*",  // injection attempt (quote + space)
		`evil\host`,             // backslash
		"-leadinghyphen",        // label can't start with hyphen
		"trailinghyphen-",       // label can't end with hyphen
		"a..b",                  // empty label
		"has space",             // space
		strings.Repeat("a", 64), // label > 63
	}
	for _, h := range invalid {
		if validHostname(h) {
			t.Errorf("validHostname(%q) = true, want false", h)
		}
	}
}

// resolveDeviceID must reject an injection-bearing hostname before any HTTP call —
// proving the malformed value never reaches the device-query filter.
func TestCrowdStrike_ResolveDeviceID_RejectsInjection(t *testing.T) {
	called := false
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		_ = json.NewEncoder(w).Encode(map[string]any{"access_token": "T", "expires_in": 1800})
	}))
	defer ts.Close()

	cs := &CrowdStrikeController{clientID: "id", clientSecret: "secret", baseURL: ts.URL, client: ts.Client(), logger: testLogger()}
	_, err := cs.resolveDeviceID(context.Background(), "host' OR hostname:'*")
	if err == nil {
		t.Fatal("expected error for injection-bearing hostname, got nil")
	}
	if !strings.Contains(err.Error(), "invalid hostname") {
		t.Errorf("error should mention invalid hostname: %v", err)
	}
	if called {
		t.Error("no HTTP request should be made for a rejected hostname")
	}
}

// --- Zscaler Internet Access ---

func TestZscaler_BlockURL_AuthCookieCategoryActivate(t *testing.T) {
	var paths []string
	mu := sync.Mutex{}
	const cookie = "JSESSIONID=ABC123"

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		paths = append(paths, r.Method+" "+r.URL.Path)
		mu.Unlock()

		switch r.URL.Path {
		case "/authenticatedSession":
			body := decodeBody(t, r)
			if body["username"] == "" || body["password"] == "" || body["apiKey"] == "" || body["timestamp"] == "" {
				t.Errorf("auth body missing fields: %v", body)
			}
			w.Header().Set("Set-Cookie", cookie)
			_ = json.NewEncoder(w).Encode(map[string]any{"authType": "ADMIN_LOGIN"})
		default:
			// All post-auth calls must replay the JSESSIONID cookie.
			if c, err := r.Cookie("JSESSIONID"); err != nil || c.Value != "ABC123" {
				t.Errorf("path %s missing JSESSIONID cookie (err=%v)", r.URL.Path, err)
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"ok": true})
		}
	}))
	defer ts.Close()

	z := newZscalerTestClient(ts)
	if err := z.BlockURL(context.Background(), "https://chat.openai.com/", "shadow ai"); err != nil {
		t.Fatalf("BlockURL: %v", err)
	}

	// auth -> add URL to category -> create block rule -> activate.
	want := []string{
		"POST /authenticatedSession",
		"PUT /urlCategories/" + shadowAIBlockCategory,
		"POST /urlFilteringRules",
		"POST /status/activate",
	}
	if strings.Join(paths, " | ") != strings.Join(want, " | ") {
		t.Fatalf("call sequence mismatch:\n got=%v\nwant=%v", paths, want)
	}
}

func TestZscaler_DuplicateRuleIsBenign(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/authenticatedSession":
			w.Header().Set("Set-Cookie", "JSESSIONID=X")
			_ = json.NewEncoder(w).Encode(map[string]any{})
		case "/urlFilteringRules":
			w.WriteHeader(http.StatusConflict) // rule already exists
			_, _ = w.Write([]byte(`{"message":"resource already exists"}`))
		default:
			_ = json.NewEncoder(w).Encode(map[string]any{})
		}
	}))
	defer ts.Close()

	z := newZscalerTestClient(ts)
	// A 409 on the rule-create must NOT fail the block (rule already present).
	if err := z.BlockURL(context.Background(), "openai.com", "x"); err != nil {
		t.Fatalf("BlockURL should treat duplicate rule as benign: %v", err)
	}
}

func TestZscaler_ObfuscateAPIKey_Deterministic(t *testing.T) {
	key := "abcdefghijklmnopqrstuvwxyz0123456789"
	out, err := obfuscateAPIKey(key, "1609459200123")
	if err != nil {
		t.Fatalf("obfuscate: %v", err)
	}
	// Deterministic for a fixed timestamp; length = 6 (high) + 6 (low) = 12.
	if len(out) != 12 {
		t.Fatalf("expected 12-char obfuscated key, got %d (%q)", len(out), out)
	}
	out2, _ := obfuscateAPIKey(key, "1609459200123")
	if out != out2 {
		t.Fatalf("obfuscation not deterministic: %q vs %q", out, out2)
	}
}

func TestZscaler_HealthCheck_ReauthOn401(t *testing.T) {
	auths := 0
	statusCalls := 0
	mu := sync.Mutex{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/authenticatedSession":
			mu.Lock()
			auths++
			mu.Unlock()
			w.Header().Set("Set-Cookie", "JSESSIONID=S")
			_ = json.NewEncoder(w).Encode(map[string]any{})
		case "/status":
			mu.Lock()
			statusCalls++
			n := statusCalls
			mu.Unlock()
			if n == 1 {
				w.WriteHeader(http.StatusUnauthorized)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"ok": true})
		default:
			t.Errorf("unexpected path %s", r.URL.Path)
		}
	}))
	defer ts.Close()

	z := newZscalerTestClient(ts)
	if err := z.HealthCheck(context.Background()); err != nil {
		t.Fatalf("HealthCheck after re-auth should succeed: %v", err)
	}
	if auths != 2 {
		t.Errorf("expected 2 authentications (initial + re-auth), got %d", auths)
	}
	if statusCalls != 2 {
		t.Errorf("expected 2 status attempts (401 then retry), got %d", statusCalls)
	}
}

// newZscalerTestClient builds a Zscaler client wired to a test server with a
// cookie jar (so JSESSIONID is captured + replayed), bypassing Initialize.
func newZscalerTestClient(ts *httptest.Server) *ZscalerGateway {
	client := ts.Client()
	client.Jar = newTestCookieJar()
	return &ZscalerGateway{
		cloudName: "test", apiKey: "abcdefghijklmnopqrstuvwxyz0123456789",
		username: "u", password: "p", baseURL: ts.URL,
		client: client, logger: testLogger(),
	}
}
