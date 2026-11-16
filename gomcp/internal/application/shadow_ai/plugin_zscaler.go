package shadow_ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/cookiejar"
	"strconv"
	"strings"
	"sync"
	"time"
)

// shadowAIBlockCategory is the custom Zscaler URL category this plugin manages.
const shadowAIBlockCategory = "SHADOW_AI_BLOCK"

// ZscalerGateway is a real Zscaler Internet Access (ZIA) API client implementing
// the WebGateway interface.
//
// Auth model: obfuscated-API-key session login. The plugin obfuscates the API
// key against the current millisecond timestamp (Zscaler's documented algorithm)
// and POSTs username+password+obfuscated-key+timestamp to /authenticatedSession.
// ZIA returns a JSESSIONID cookie held in a cookie jar and replayed on every
// subsequent call. Config changes are staged then committed with /status/activate.
//
// Base host is https://zsapi.{cloud_name}/api/v1 derived from cloud_name. A
// `base_url` config key overrides this (used only for tests against httptest).
// With no creds the plugin is never loaded, so the controller stays detect_only.
type ZscalerGateway struct {
	cloudName string
	apiKey    string
	username  string
	password  string
	baseURL   string

	client *http.Client
	logger *slog.Logger

	mu            sync.Mutex
	authenticated bool
}

// NewZscalerGateway constructs an uninitialized ZIA client. Call Initialize first.
func NewZscalerGateway() *ZscalerGateway {
	return &ZscalerGateway{
		logger: slog.Default().With("component", "shadow-ai-plugin-zscaler"),
	}
}

func (z *ZscalerGateway) Initialize(config map[string]interface{}) error {
	z.cloudName = cfgString(config, "cloud_name")
	z.apiKey = cfgString(config, "api_key")
	z.username = cfgString(config, "username")
	z.password = cfgString(config, "password")
	z.baseURL = strings.TrimRight(cfgString(config, "base_url"), "/") // test override

	if z.baseURL == "" {
		if z.cloudName == "" {
			return fmt.Errorf("zscaler: cloud_name required")
		}
		z.baseURL = fmt.Sprintf("https://zsapi.%s/api/v1", z.cloudName)
	}
	if z.apiKey == "" || z.username == "" || z.password == "" {
		return fmt.Errorf("zscaler: api_key, username and password required")
	}
	if err := validateVendorURL(z.logger, z.baseURL); err != nil {
		return fmt.Errorf("zscaler: base_url rejected: %w", err)
	}

	// Cookie jar carries the JSESSIONID across requests. Build the SSRF-hardened
	// client with the jar attached.
	jar, err := cookiejar.New(nil)
	if err != nil {
		return fmt.Errorf("zscaler: cookie jar: %w", err)
	}
	z.client = newVendorHTTPClient()
	z.client.Jar = jar

	z.logger.Info("initialized", "cloud", z.cloudName)
	return nil
}

// obfuscateAPIKey implements Zscaler's documented API-key obfuscation: split the
// millisecond timestamp string, index the key by the digits of the high and low
// halves, and concatenate. Returns the obfuscated key for the given timestamp.
func obfuscateAPIKey(apiKey, timestamp string) (string, error) {
	if len(timestamp) < 6 {
		return "", fmt.Errorf("zscaler: timestamp too short")
	}
	high := timestamp[len(timestamp)-6:]
	n, err := strconv.Atoi(high)
	if err != nil {
		return "", fmt.Errorf("zscaler: bad timestamp high: %w", err)
	}
	low := fmt.Sprintf("%06d", n>>1)

	var b strings.Builder
	for i := 0; i < len(high); i++ {
		idx := int(high[i] - '0')
		if idx < 0 || idx >= len(apiKey) {
			return "", fmt.Errorf("zscaler: api_key too short for obfuscation")
		}
		b.WriteByte(apiKey[idx])
	}
	for i := 0; i < len(low); i++ {
		idx := int(low[i]-'0') + 2
		if idx < 0 || idx >= len(apiKey) {
			return "", fmt.Errorf("zscaler: api_key too short for obfuscation")
		}
		b.WriteByte(apiKey[idx])
	}
	return b.String(), nil
}

// authenticate establishes a session (JSESSIONID stored in the jar). Caller must
// hold z.mu.
func (z *ZscalerGateway) authenticate(ctx context.Context) error {
	timestamp := strconv.FormatInt(time.Now().UnixMilli(), 10)
	obf, err := obfuscateAPIKey(z.apiKey, timestamp)
	if err != nil {
		return err
	}
	body := map[string]interface{}{
		"username":  z.username,
		"password":  z.password,
		"apiKey":    obf,
		"timestamp": timestamp,
	}
	if err := z.do(ctx, http.MethodPost, "/authenticatedSession", body, nil, true); err != nil {
		return fmt.Errorf("zscaler: authenticate: %w", err)
	}
	z.authenticated = true
	return nil
}

// session ensures an authenticated session exists.
func (z *ZscalerGateway) session(ctx context.Context) error {
	z.mu.Lock()
	defer z.mu.Unlock()
	if z.authenticated {
		return nil
	}
	return z.authenticate(ctx)
}

// call runs an authenticated request, re-authenticating once on a 401.
func (z *ZscalerGateway) call(ctx context.Context, method, path string, body map[string]interface{}, out interface{}) error {
	if err := z.session(ctx); err != nil {
		return err
	}
	err := z.do(ctx, method, path, body, out, false)
	if isAuthError(err) {
		z.mu.Lock()
		z.authenticated = false
		if aerr := z.authenticate(ctx); aerr != nil {
			z.mu.Unlock()
			return aerr
		}
		z.mu.Unlock()
		err = z.do(ctx, method, path, body, out, false)
	}
	return err
}

func (z *ZscalerGateway) BlockURL(ctx context.Context, rawURL, reason string) error {
	// Append the URL to the managed custom category, then ensure a blocking rule
	// references it, then activate.
	if err := z.call(ctx, http.MethodPut, "/urlCategories/"+shadowAIBlockCategory+"?action=ADD_TO_LIST",
		map[string]interface{}{
			"configuredName": shadowAIBlockCategory,
			"urls":           []string{normalizeURLHost(rawURL)},
		}, nil); err != nil {
		return fmt.Errorf("zscaler: block url %q: %w", rawURL, err)
	}
	if err := z.ensureBlockRule(ctx, reason); err != nil {
		return err
	}
	return z.activate(ctx)
}

func (z *ZscalerGateway) UnblockURL(ctx context.Context, rawURL string) error {
	if err := z.call(ctx, http.MethodPut, "/urlCategories/"+shadowAIBlockCategory+"?action=REMOVE_FROM_LIST",
		map[string]interface{}{
			"configuredName": shadowAIBlockCategory,
			"urls":           []string{normalizeURLHost(rawURL)},
		}, nil); err != nil {
		return fmt.Errorf("zscaler: unblock url %q: %w", rawURL, err)
	}
	return z.activate(ctx)
}

func (z *ZscalerGateway) BlockCategory(ctx context.Context, category string) error {
	if err := z.call(ctx, http.MethodPost, "/urlFilteringRules", map[string]interface{}{
		"name":          "ShadowAI-Block-" + sanitizeName(category),
		"action":        "BLOCK",
		"state":         "ENABLED",
		"order":         1,
		"rank":          7,
		"urlCategories": []string{category},
	}, nil); err != nil {
		return fmt.Errorf("zscaler: block category %q: %w", category, err)
	}
	return z.activate(ctx)
}

// ensureBlockRule creates the URL-filtering rule that blocks the managed
// category. ZIA rejects duplicate rule names; a 409/400 on re-create is benign.
func (z *ZscalerGateway) ensureBlockRule(ctx context.Context, reason string) error {
	err := z.call(ctx, http.MethodPost, "/urlFilteringRules", map[string]interface{}{
		"name":          "ShadowAI-Block",
		"action":        "BLOCK",
		"state":         "ENABLED",
		"order":         1,
		"rank":          7,
		"urlCategories": []string{shadowAIBlockCategory},
		"description":   reason,
	}, nil)
	var ve *vendorHTTPError
	if err != nil && asVendorErr(err, &ve) && (ve.status == http.StatusConflict || ve.status == http.StatusBadRequest) {
		// Rule already exists — not an error.
		return nil
	}
	return err
}

// activate commits staged ZIA configuration changes.
func (z *ZscalerGateway) activate(ctx context.Context) error {
	if err := z.call(ctx, http.MethodPost, "/status/activate", map[string]interface{}{}, nil); err != nil {
		return fmt.Errorf("zscaler: activate: %w", err)
	}
	return nil
}

func (z *ZscalerGateway) HealthCheck(ctx context.Context) error {
	if z.cloudName == "" && z.baseURL == "" {
		return fmt.Errorf("zscaler: not configured")
	}
	return z.call(ctx, http.MethodGet, "/status", nil, nil)
}

func (z *ZscalerGateway) Vendor() string { return "zscaler" }

// do performs a single JSON request against the ZIA API. When isAuth is true the
// caller is the login path (no session precondition). A non-2xx status maps to a
// *vendorHTTPError.
func (z *ZscalerGateway) do(ctx context.Context, method, path string, body map[string]interface{}, out interface{}, isAuth bool) error {
	var rdr io.Reader
	if body != nil {
		payload, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal: %w", err)
		}
		rdr = bytes.NewReader(payload)
	}
	req, err := http.NewRequestWithContext(ctx, method, z.baseURL+path, rdr)
	if err != nil {
		return fmt.Errorf("request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := z.client.Do(req)
	if err != nil {
		return fmt.Errorf("send: %w", err)
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return &vendorHTTPError{status: resp.StatusCode, body: string(respBody)}
	}
	if out != nil && len(respBody) > 0 {
		if err := json.Unmarshal(respBody, out); err != nil {
			return fmt.Errorf("decode response: %w", err)
		}
	}
	return nil
}

// normalizeURLHost reduces a URL to the host[/path] form ZIA expects in URL
// category lists (it does not accept scheme prefixes).
func normalizeURLHost(raw string) string {
	s := raw
	if i := strings.Index(s, "://"); i >= 0 {
		s = s[i+3:]
	}
	return strings.TrimSuffix(s, "/")
}
