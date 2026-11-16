package soc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"strings"
	"time"
)

// Firewall is the enforcement backend for the block_ip SOAR action.
//
// HONESTY CONTRACT: Block returns enforced=false (NOT an error, NOT a fake
// success) when the backend cannot actually drop packets — e.g. the log-only
// default, or the host-firewall backend on a non-Linux/dev box. Callers MUST
// surface enforced=false as a non-success outcome so the system never claims to
// have blocked an IP it did not block (audit #38: stub reported success without
// blocking). enforced=true is returned ONLY when the action genuinely took
// effect (a kernel rule was installed, or a cloud-FW API returned 2xx).
type Firewall interface {
	// Block installs a drop rule for ip for the given ttl. reason is recorded
	// for audit. enforced reports whether the block actually took effect;
	// detail is a human-readable explanation (backend, rule, or why not
	// enforced); err is non-nil only on an operational failure of a backend
	// that WAS supposed to enforce (e.g. nft present but the command failed).
	Block(ip string, ttl time.Duration, reason string) (enforced bool, detail string, err error)
	// Unblock removes a previously installed drop rule for ip.
	Unblock(ip string) error
	// Type returns the backend identifier ("nft", "iptables", "http", "log-only", ...).
	Type() string
}

// FirewallConfig selects and configures the firewall backend.
type FirewallConfig struct {
	// Backend: "nft" | "iptables" → host kernel firewall (Linux only);
	// "http" → HTTPFirewall (cloud/edge FW webhook); "" | "none" | "log" →
	// LogOnlyFirewall (honest, non-enforcing default).
	Backend string
	// ChainOrSet is the nftables set name (with Table) or the iptables chain to
	// install rules into. Defaults applied per-backend when empty.
	ChainOrSet string
	// Table is the nftables table (family is inet). Defaults to "filter".
	Table string
	// APIURL is the cloud-firewall HTTP endpoint for the "http" backend.
	APIURL string
	// APIToken is the bearer token sent to APIURL for the "http" backend.
	APIToken string
}

// NewFirewall constructs the firewall backend selected by cfg.Backend.
// Unknown / empty backends fall back to the honest LogOnlyFirewall so a
// misconfiguration degrades to "not enforced" rather than a silent claim.
func NewFirewall(cfg FirewallConfig) Firewall {
	switch strings.ToLower(strings.TrimSpace(cfg.Backend)) {
	case "nft", "nftables":
		return newHostFirewall("nft", cfg)
	case "iptables", "ipt":
		return newHostFirewall("iptables", cfg)
	case "http", "https", "cloud", "webhook":
		return NewHTTPFirewall(cfg.APIURL, cfg.APIToken)
	case "", "none", "log", "log-only", "logonly":
		return &LogOnlyFirewall{}
	default:
		slog.Warn("firewall: unknown backend, falling back to log-only (not enforcing)",
			"backend", cfg.Backend)
		return &LogOnlyFirewall{}
	}
}

// validateIP rejects anything that is not a literal IP address so no
// user-controlled string is ever passed to a shell / kernel command.
func validateIP(ip string) error {
	if net.ParseIP(strings.TrimSpace(ip)) == nil {
		return fmt.Errorf("invalid IP address %q", ip)
	}
	return nil
}

// --- LogOnlyFirewall: the honest, non-enforcing default ---

// LogOnlyFirewall is the default backend when no real firewall is configured.
// It NEVER claims to block: Block always returns enforced=false. This is the
// fail-safe-and-honest path — block_ip in this mode is recorded as NOT enforced
// so an operator is never misled into thinking a source was contained.
type LogOnlyFirewall struct{}

func (f *LogOnlyFirewall) Type() string { return "log-only" }

func (f *LogOnlyFirewall) Block(ip string, ttl time.Duration, reason string) (bool, string, error) {
	if err := validateIP(ip); err != nil {
		return false, "", err
	}
	slog.Warn("block_ip NOT enforced: no firewall backend configured (log-only). "+
		"Set SOC_FIREWALL_BACKEND=nft|iptables (Linux host w/ NET_ADMIN) or =http (cloud FW API) to enforce.",
		"ip", ip, "ttl", ttl.String(), "reason", reason)
	return false, "firewall backend not configured (log-only); set SOC_FIREWALL_BACKEND to enforce", nil
}

func (f *LogOnlyFirewall) Unblock(ip string) error {
	if err := validateIP(ip); err != nil {
		return err
	}
	slog.Info("block_ip unblock no-op (log-only backend)", "ip", ip)
	return nil
}

// --- HTTPFirewall: pluggable cloud / edge firewall over HTTP ---

// HTTPFirewall POSTs block/unblock requests to a generic cloud-firewall webhook
// (e.g. an operator-supplied lambda fronting AWS SG/NACL, Cloudflare IP Access
// Rules, or a GCP firewall API). It is SSRF-guarded with ValidateWebhookURL +
// SafeDialContext (the same primitives the webhook executors use) and reports
// enforced=true ONLY on a 2xx response.
type HTTPFirewall struct {
	apiURL string
	token  string
	client *http.Client
}

// NewHTTPFirewall builds the HTTP cloud-firewall backend. If apiURL is empty the
// backend stays honestly disabled (Block returns enforced=false).
func NewHTTPFirewall(apiURL, token string) *HTTPFirewall {
	return &HTTPFirewall{
		apiURL: strings.TrimSpace(apiURL),
		token:  token,
		client: &http.Client{
			Timeout: 15 * time.Second,
			Transport: &http.Transport{
				DialContext: SafeDialContext,
			},
		},
	}
}

func (f *HTTPFirewall) Type() string { return "http" }

func (f *HTTPFirewall) Block(ip string, ttl time.Duration, reason string) (bool, string, error) {
	if err := validateIP(ip); err != nil {
		return false, "", err
	}
	if f.apiURL == "" {
		slog.Warn("block_ip NOT enforced: SOC_FIREWALL_BACKEND=http but SOC_FIREWALL_API_URL is unset", "ip", ip)
		return false, "cloud-firewall API URL not configured (set SOC_FIREWALL_API_URL)", nil
	}
	body := map[string]any{
		"action":      "block",
		"ip":          ip,
		"ttl_seconds": int64(ttl.Seconds()),
		"reason":      reason,
	}
	if err := f.post(body); err != nil {
		return false, "", err
	}
	return true, fmt.Sprintf("blocked via cloud firewall (%s) for %s", f.apiURL, ttl), nil
}

func (f *HTTPFirewall) Unblock(ip string) error {
	if err := validateIP(ip); err != nil {
		return err
	}
	if f.apiURL == "" {
		return fmt.Errorf("cloud-firewall API URL not configured")
	}
	return f.post(map[string]any{"action": "unblock", "ip": ip})
}

func (f *HTTPFirewall) post(body map[string]any) error {
	// SSRF guard: refuse to call internal/link-local targets even if misconfigured.
	if err := ValidateWebhookURL(f.apiURL); err != nil {
		slog.Error("firewall HTTP call blocked (SSRF)", "url", f.apiURL, "error", err)
		return fmt.Errorf("firewall http ssrf blocked: %w", err)
	}
	payload, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("firewall http: marshal: %w", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, f.apiURL, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("firewall http: request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if f.token != "" {
		req.Header.Set("Authorization", "Bearer "+f.token)
	}
	resp, err := f.client.Do(req)
	if err != nil {
		return fmt.Errorf("firewall http: send: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return fmt.Errorf("firewall http: HTTP %d from %s", resp.StatusCode, f.apiURL)
	}
	return nil
}
