package shadow_ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"
)

// CrowdStrikeController is a real CrowdStrike Falcon API client implementing the
// EndpointController interface.
//
// Auth model: OAuth2 client-credentials. token() POSTs client_id+client_secret
// (form-encoded) to {base_url}/oauth2/token and receives a bearer token + TTL,
// cached and refreshed shortly before expiry. Every request carries
// "Authorization: Bearer <token>".
//
// Falcon actions target a device_id, not a hostname, so IsolateHost/ReleaseHost
// first resolve hostname -> device_id via the devices query API. Process control
// uses Real-Time-Response (RTR) sessions.
//
// base_url MUST match the tenant's cloud region (us-1/us-2/eu-1/us-gov). With no
// creds the plugin is never loaded, so the controller stays in detect_only mode.
type CrowdStrikeController struct {
	clientID     string
	clientSecret string
	baseURL      string

	client *http.Client
	logger *slog.Logger

	mu          sync.Mutex
	token       string
	tokenExpiry time.Time
}

// NewCrowdStrikeController constructs an uninitialized Falcon client. Call
// Initialize before use.
func NewCrowdStrikeController() *CrowdStrikeController {
	return &CrowdStrikeController{
		baseURL: "https://api.crowdstrike.com",
		logger:  slog.Default().With("component", "shadow-ai-plugin-crowdstrike"),
		client:  newVendorHTTPClient(),
	}
}

func (cs *CrowdStrikeController) Initialize(config map[string]interface{}) error {
	cs.clientID = cfgString(config, "client_id")
	cs.clientSecret = cfgString(config, "client_secret")
	if u := cfgString(config, "base_url"); u != "" {
		cs.baseURL = strings.TrimRight(u, "/")
	}

	if cs.clientID == "" || cs.clientSecret == "" {
		return fmt.Errorf("crowdstrike: client_id and client_secret required")
	}
	if err := validateVendorURL(cs.logger, cs.baseURL); err != nil {
		return fmt.Errorf("crowdstrike: base_url rejected: %w", err)
	}
	if cs.client == nil {
		cs.client = newVendorHTTPClient()
	}
	cs.logger.Info("initialized", "base_url", cs.baseURL)
	return nil
}

// bearer returns a valid OAuth2 token, minting/refreshing as needed.
func (cs *CrowdStrikeController) bearer(ctx context.Context) (string, error) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	if cs.token != "" && time.Now().Before(cs.tokenExpiry) {
		return cs.token, nil
	}

	form := url.Values{}
	form.Set("client_id", cs.clientID)
	form.Set("client_secret", cs.clientSecret)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, cs.baseURL+"/oauth2/token",
		strings.NewReader(form.Encode()))
	if err != nil {
		return "", fmt.Errorf("crowdstrike: token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")

	resp, err := cs.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("crowdstrike: token send: %w", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("crowdstrike: token: %w", &vendorHTTPError{status: resp.StatusCode, body: string(body)})
	}

	var out struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int    `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &out); err != nil {
		return "", fmt.Errorf("crowdstrike: decode token: %w", err)
	}
	if out.AccessToken == "" {
		return "", fmt.Errorf("crowdstrike: token response missing access_token")
	}
	ttl := out.ExpiresIn
	if ttl <= 0 {
		ttl = 1800 // Falcon tokens default to 30 min.
	}
	cs.token = out.AccessToken
	cs.tokenExpiry = time.Now().Add(time.Duration(ttl-60) * time.Second)
	return cs.token, nil
}

// fqlEscape escapes a string for safe interpolation inside a single-quoted FQL
// literal (Falcon Query Language). A bare "'" in attacker-influenceable hostname
// data would otherwise break out of hostname:'...' and let the filter match an
// unintended device (which contain/kill/RTR then acts on). Backslash MUST be
// escaped first, then the single quote, so "\'" can't be un-escaped by the engine.
func fqlEscape(s string) string {
	s = strings.ReplaceAll(s, `\`, `\\`)
	s = strings.ReplaceAll(s, `'`, `\'`)
	return s
}

// validHostname reports whether s is a plausible RFC-1123 hostname (labels of
// [A-Za-z0-9-] separated by dots, total <= 253). Defense-in-depth: a hostname
// sourced from SOC event/incident data that fails this is rejected outright,
// before fqlEscape, so it can never reach the device-action paths.
func validHostname(s string) bool {
	if s == "" || len(s) > 253 {
		return false
	}
	for _, label := range strings.Split(s, ".") {
		if label == "" || len(label) > 63 {
			return false
		}
		if strings.HasPrefix(label, "-") || strings.HasSuffix(label, "-") {
			return false
		}
		for _, r := range label {
			if !((r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-') {
				return false
			}
		}
	}
	return true
}

// resolveDeviceID looks up the first device_id matching the given hostname.
func (cs *CrowdStrikeController) resolveDeviceID(ctx context.Context, hostname string) (string, error) {
	// Reject malformed/injection-bearing hostnames before they reach the filter:
	// a stray quote here could otherwise retarget contain/kill at an unintended device.
	if !validHostname(hostname) {
		return "", fmt.Errorf("crowdstrike: invalid hostname %q", hostname)
	}
	q := url.Values{}
	q.Set("filter", fmt.Sprintf("hostname:'%s'", fqlEscape(hostname)))
	q.Set("limit", "1")

	var out struct {
		Resources []string `json:"resources"`
	}
	if err := cs.do(ctx, http.MethodGet, "/devices/queries/devices/v1?"+q.Encode(), nil, &out); err != nil {
		return "", fmt.Errorf("crowdstrike: resolve device %q: %w", hostname, err)
	}
	if len(out.Resources) == 0 {
		return "", fmt.Errorf("crowdstrike: no device found for hostname %q", hostname)
	}
	return out.Resources[0], nil
}

// deviceAction posts a contain/lift_containment action for a device_id.
func (cs *CrowdStrikeController) deviceAction(ctx context.Context, deviceID, action string) error {
	body := map[string]interface{}{"ids": []string{deviceID}}
	return cs.do(ctx, http.MethodPost,
		"/devices/entities/devices-actions/v2?action_name="+url.QueryEscape(action), body, nil)
}

func (cs *CrowdStrikeController) IsolateHost(ctx context.Context, hostname string) error {
	deviceID, err := cs.resolveDeviceID(ctx, hostname)
	if err != nil {
		return err
	}
	if err := cs.deviceAction(ctx, deviceID, "contain"); err != nil {
		return fmt.Errorf("crowdstrike: isolate %q: %w", hostname, err)
	}
	return nil
}

func (cs *CrowdStrikeController) ReleaseHost(ctx context.Context, hostname string) error {
	deviceID, err := cs.resolveDeviceID(ctx, hostname)
	if err != nil {
		return err
	}
	if err := cs.deviceAction(ctx, deviceID, "lift_containment"); err != nil {
		return fmt.Errorf("crowdstrike: release %q: %w", hostname, err)
	}
	return nil
}

func (cs *CrowdStrikeController) KillProcess(ctx context.Context, hostname string, pid int) error {
	deviceID, err := cs.resolveDeviceID(ctx, hostname)
	if err != nil {
		return err
	}

	// Open an RTR session on the device.
	var sess struct {
		Resources []struct {
			SessionID string `json:"session_id"`
		} `json:"resources"`
	}
	if err := cs.do(ctx, http.MethodPost, "/real-time-response/entities/sessions/v1",
		map[string]interface{}{"device_id": deviceID}, &sess); err != nil {
		return fmt.Errorf("crowdstrike: open RTR session on %q: %w", hostname, err)
	}
	if len(sess.Resources) == 0 || sess.Resources[0].SessionID == "" {
		return fmt.Errorf("crowdstrike: RTR session not created for %q", hostname)
	}
	sessionID := sess.Resources[0].SessionID

	// Issue the kill admin-command.
	if err := cs.do(ctx, http.MethodPost, "/real-time-response/entities/admin-command/v1",
		map[string]interface{}{
			"session_id":     sessionID,
			"base_command":   "kill",
			"command_string": "kill " + strconv.Itoa(pid),
		}, nil); err != nil {
		return fmt.Errorf("crowdstrike: kill pid %d on %q: %w", pid, hostname, err)
	}
	return nil
}

func (cs *CrowdStrikeController) QuarantineFile(ctx context.Context, hostname, path string) error {
	deviceID, err := cs.resolveDeviceID(ctx, hostname)
	if err != nil {
		return err
	}
	var sess struct {
		Resources []struct {
			SessionID string `json:"session_id"`
		} `json:"resources"`
	}
	if err := cs.do(ctx, http.MethodPost, "/real-time-response/entities/sessions/v1",
		map[string]interface{}{"device_id": deviceID}, &sess); err != nil {
		return fmt.Errorf("crowdstrike: open RTR session on %q: %w", hostname, err)
	}
	if len(sess.Resources) == 0 || sess.Resources[0].SessionID == "" {
		return fmt.Errorf("crowdstrike: RTR session not created for %q", hostname)
	}
	// Remove the file via RTR. Full quarantine-to-vault requires a richer policy
	// flow; rm neutralizes the artifact and is the honest baseline action.
	if err := cs.do(ctx, http.MethodPost, "/real-time-response/entities/admin-command/v1",
		map[string]interface{}{
			"session_id":     sess.Resources[0].SessionID,
			"base_command":   "rm",
			"command_string": "rm " + path,
		}, nil); err != nil {
		return fmt.Errorf("crowdstrike: quarantine %q on %q: %w", path, hostname, err)
	}
	return nil
}

func (cs *CrowdStrikeController) HealthCheck(ctx context.Context) error {
	if cs.clientID == "" {
		return fmt.Errorf("crowdstrike: not configured")
	}
	return cs.do(ctx, http.MethodGet, "/sensors/queries/sensors/v1?limit=1", nil, nil)
}

func (cs *CrowdStrikeController) Vendor() string { return "crowdstrike" }

// do performs an authenticated JSON request, retrying once on a 401 (expired
// token). A non-2xx status maps to a *vendorHTTPError carrying the body.
func (cs *CrowdStrikeController) do(ctx context.Context, method, path string, body map[string]interface{}, out interface{}) error {
	send := func() error {
		token, err := cs.bearer(ctx)
		if err != nil {
			return err
		}
		var rdr io.Reader
		if body != nil {
			payload, err := json.Marshal(body)
			if err != nil {
				return fmt.Errorf("marshal: %w", err)
			}
			rdr = bytes.NewReader(payload)
		}
		req, err := http.NewRequestWithContext(ctx, method, cs.baseURL+path, rdr)
		if err != nil {
			return fmt.Errorf("request: %w", err)
		}
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Accept", "application/json")
		if body != nil {
			req.Header.Set("Content-Type", "application/json")
		}

		resp, err := cs.client.Do(req)
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

	err := send()
	if isAuthError(err) {
		// Token rejected — invalidate and retry once.
		cs.mu.Lock()
		cs.token = ""
		cs.mu.Unlock()
		err = send()
	}
	return err
}
