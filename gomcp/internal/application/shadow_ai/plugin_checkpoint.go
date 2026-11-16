package shadow_ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"

	socdomain "github.com/syntrex/gomcp/internal/domain/soc"
)

// CheckPointEnforcer is a real Check Point Management Web API client implementing
// the NetworkEnforcer interface.
//
// Auth model: session-based. login() POSTs credentials (api-key, or
// user+password) to {api_url}/web_api/login and receives a session id ("sid").
// Every subsequent command carries the SID in the X-chkp-sid header. The SID is
// cached until shortly before its session-timeout and re-minted on demand. Each
// mutating command is followed by /web_api/publish to commit the change.
//
// Enforcement requires real Check Point creds + a reachable Management server.
// With no creds the plugin is never loaded (Initialize errors on a missing
// api_url), so the controller stays in honest detect_only mode.
type CheckPointEnforcer struct {
	apiURL   string
	apiKey   string
	username string
	password string

	client *http.Client
	logger *slog.Logger

	mu        sync.Mutex
	sid       string
	sidExpiry time.Time
}

// NewCheckPointEnforcer constructs an uninitialized Check Point client. Call
// Initialize before use.
func NewCheckPointEnforcer() *CheckPointEnforcer {
	return &CheckPointEnforcer{
		logger: slog.Default().With("component", "shadow-ai-plugin-checkpoint"),
		client: newVendorHTTPClient(),
	}
}

// newVendorHTTPClient builds an HTTP client hardened against SSRF (it pins the
// resolved IP at dial time and rejects loopback/private/link-local targets).
func newVendorHTTPClient() *http.Client {
	return &http.Client{
		Timeout: 20 * time.Second,
		Transport: &http.Transport{
			DialContext:         socdomain.SafeDialContext,
			TLSHandshakeTimeout: 10 * time.Second,
			MaxIdleConns:        10,
			IdleConnTimeout:     90 * time.Second,
		},
	}
}

func (c *CheckPointEnforcer) Initialize(config map[string]interface{}) error {
	c.apiURL = strings.TrimRight(cfgString(config, "api_url"), "/")
	c.apiKey = cfgString(config, "api_key")
	c.username = cfgString(config, "username")
	c.password = cfgString(config, "password")

	if c.apiURL == "" {
		return fmt.Errorf("checkpoint: api_url required")
	}
	if c.apiKey == "" && (c.username == "" || c.password == "") {
		return fmt.Errorf("checkpoint: api_key OR username+password required")
	}
	// SSRF guard: reject Management URLs that resolve to internal/loopback hosts.
	if err := validateVendorURL(c.logger, c.apiURL); err != nil {
		return fmt.Errorf("checkpoint: api_url rejected: %w", err)
	}
	if c.client == nil {
		c.client = newVendorHTTPClient()
	}
	c.logger.Info("initialized", "api_url", c.apiURL)
	return nil
}

// login authenticates and caches the session id. Callers must hold c.mu.
func (c *CheckPointEnforcer) login(ctx context.Context) (string, error) {
	body := map[string]interface{}{}
	if c.apiKey != "" {
		body["api-key"] = c.apiKey
	} else {
		body["user"] = c.username
		body["password"] = c.password
	}

	var out struct {
		SID            string `json:"sid"`
		SessionTimeout int    `json:"session-timeout"`
	}
	if err := c.do(ctx, "/web_api/login", "", body, &out); err != nil {
		return "", fmt.Errorf("checkpoint: login: %w", err)
	}
	if out.SID == "" {
		return "", fmt.Errorf("checkpoint: login returned empty sid")
	}

	timeout := out.SessionTimeout
	if timeout <= 0 {
		timeout = 600 // Check Point default session-timeout is 600s.
	}
	c.sid = out.SID
	// Refresh ~30s before expiry to avoid mid-command session loss.
	c.sidExpiry = time.Now().Add(time.Duration(timeout-30) * time.Second)
	return c.sid, nil
}

// session returns a valid SID, logging in (or re-logging in) as needed.
func (c *CheckPointEnforcer) session(ctx context.Context) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.sid != "" && time.Now().Before(c.sidExpiry) {
		return c.sid, nil
	}
	return c.login(ctx)
}

// command runs an authenticated Management command, retrying once on a 401
// (expired session). On success it publishes the change.
func (c *CheckPointEnforcer) command(ctx context.Context, path string, body map[string]interface{}) error {
	sid, err := c.session(ctx)
	if err != nil {
		return err
	}
	err = c.do(ctx, path, sid, body, nil)
	if isAuthError(err) {
		// Session expired between session() and do(); force a re-login and retry.
		c.mu.Lock()
		c.sid = ""
		c.mu.Unlock()
		if sid, err = c.session(ctx); err != nil {
			return err
		}
		err = c.do(ctx, path, sid, body, nil)
	}
	if err != nil {
		return err
	}
	// Commit the change. Publish failures are surfaced (a silent unpublished
	// rule is not enforcement).
	return c.do(ctx, "/web_api/publish", sid, map[string]interface{}{}, nil)
}

func (c *CheckPointEnforcer) BlockDomain(ctx context.Context, domain string, reason string) error {
	// Create an application-site for the domain, then a Drop rule referencing it.
	name := "ShadowAI-" + sanitizeName(domain)
	if err := c.command(ctx, "/web_api/add-application-site", map[string]interface{}{
		"name":             name,
		"url-list":         []string{domain},
		"primary-category": "Custom_Application_Site",
		"comments":         reason,
	}); err != nil {
		return fmt.Errorf("checkpoint: block domain %q: %w", domain, err)
	}
	return c.command(ctx, "/web_api/add-access-rule", map[string]interface{}{
		"layer":       "Network",
		"position":    "top",
		"name":        name,
		"action":      "Drop",
		"destination": name,
		"comments":    reason,
	})
}

func (c *CheckPointEnforcer) BlockIP(ctx context.Context, ip string, duration time.Duration, reason string) error {
	name := "ShadowAI-" + sanitizeName(ip)
	if err := c.command(ctx, "/web_api/add-host", map[string]interface{}{
		"name":       name,
		"ip-address": ip,
		"comments":   reason,
	}); err != nil {
		return fmt.Errorf("checkpoint: block ip %q: %w", ip, err)
	}
	return c.command(ctx, "/web_api/add-access-rule", map[string]interface{}{
		"layer":       "Network",
		"position":    "top",
		"name":        name,
		"action":      "Drop",
		"destination": name,
		"comments":    reason,
	})
}

func (c *CheckPointEnforcer) UnblockDomain(ctx context.Context, domain string) error {
	name := "ShadowAI-" + sanitizeName(domain)
	if err := c.command(ctx, "/web_api/delete-access-rule", map[string]interface{}{
		"layer": "Network",
		"name":  name,
	}); err != nil {
		return fmt.Errorf("checkpoint: unblock domain %q: %w", domain, err)
	}
	return c.command(ctx, "/web_api/delete-application-site", map[string]interface{}{
		"name": name,
	})
}

func (c *CheckPointEnforcer) UnblockIP(ctx context.Context, ip string) error {
	name := "ShadowAI-" + sanitizeName(ip)
	if err := c.command(ctx, "/web_api/delete-access-rule", map[string]interface{}{
		"layer": "Network",
		"name":  name,
	}); err != nil {
		return fmt.Errorf("checkpoint: unblock ip %q: %w", ip, err)
	}
	return c.command(ctx, "/web_api/delete-host", map[string]interface{}{
		"name": name,
	})
}

func (c *CheckPointEnforcer) HealthCheck(ctx context.Context) error {
	if c.apiURL == "" {
		return fmt.Errorf("checkpoint: not configured")
	}
	sid, err := c.session(ctx)
	if err != nil {
		return err
	}
	if err := c.do(ctx, "/web_api/show-session", sid, map[string]interface{}{}, nil); err != nil {
		if isAuthError(err) {
			c.mu.Lock()
			c.sid = ""
			c.mu.Unlock()
		}
		return err
	}
	return nil
}

func (c *CheckPointEnforcer) Vendor() string { return "checkpoint" }

// do performs a single JSON POST against the Management API. When sid != "" it is
// sent as the X-chkp-sid header. A non-2xx status is mapped to an error carrying
// the (truncated) response body.
func (c *CheckPointEnforcer) do(ctx context.Context, path, sid string, body map[string]interface{}, out interface{}) error {
	payload, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.apiURL+path, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if sid != "" {
		req.Header.Set("X-chkp-sid", sid)
	}

	resp, err := c.client.Do(req)
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
