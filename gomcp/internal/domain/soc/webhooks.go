package soc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"sync"
	"time"
)

// WebhookEventType defines events that trigger webhooks (§15).
type WebhookEventType string

const (
	WebhookIncidentCreated  WebhookEventType = "incident_created"
	WebhookIncidentResolved WebhookEventType = "incident_resolved"
	WebhookCriticalEvent    WebhookEventType = "critical_event"
	WebhookSensorOffline    WebhookEventType = "sensor_offline"
	WebhookKillChainAlert   WebhookEventType = "kill_chain_alert"
)

// WebhookConfig defines a webhook destination.
type WebhookConfig struct {
	ID      string             `yaml:"id" json:"id"`
	URL     string             `yaml:"url" json:"url"`
	Events  []WebhookEventType `yaml:"events" json:"events"`
	Headers map[string]string  `yaml:"headers" json:"headers"`
	Active  bool               `yaml:"active" json:"active"`
	Retries int                `yaml:"retries" json:"retries"`
}

// WebhookPayload is the JSON body sent to webhook endpoints.
type WebhookPayload struct {
	EventType   WebhookEventType `json:"event_type"`
	Timestamp   time.Time        `json:"timestamp"`
	IncidentID  string           `json:"incident_id,omitempty"`
	Severity    string           `json:"severity"`
	Title       string           `json:"title"`
	Description string           `json:"description"`
	URL         string           `json:"url,omitempty"` // Link to dashboard
}

// WebhookEngine manages webhook delivery with retry logic (§15).
type WebhookEngine struct {
	mu       sync.RWMutex
	webhooks []WebhookConfig
	client   *http.Client

	// Stats
	sent   int
	failed int
	queue  chan webhookJob
}

type webhookJob struct {
	config  WebhookConfig
	payload WebhookPayload
	attempt int
}

// Reject embedded-address translators and non-public special-purpose ranges at
// both URL validation and connection pinning. Unmap IPv4-mapped IPv6 first.
func webhookIPDisallowed(ip net.IP) bool {
	addr, ok := netip.AddrFromSlice(ip)
	if !ok {
		return true
	}
	addr = addr.Unmap()
	if !addr.IsGlobalUnicast() || addr.IsPrivate() || addr.IsLoopback() || addr.IsLinkLocalUnicast() {
		return true
	}
	for _, raw := range []string{"0.0.0.0/8", "100.64.0.0/10", "192.0.0.0/24", "192.0.2.0/24", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "240.0.0.0/4", "64:ff9b::/96", "64:ff9b:1::/48", "100::/64", "2001::/32", "2001:db8::/32", "2002::/16"} {
		if netip.MustParsePrefix(raw).Contains(addr) {
			return true
		}
	}
	return false
}

// SafeDialContext prevents DNS Rebinding SSRF by resolving the IP and pinning it
// during the TCP dial phase, validating that the resolved IP is safe.
var SafeDialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, err
	}

	ips, err := net.LookupIP(host)
	if err != nil {
		ip := net.ParseIP(host)
		if ip == nil {
			return nil, fmt.Errorf("failed to resolve hostname")
		}
		ips = []net.IP{ip}
	}

	for _, ip := range ips {
		if webhookIPDisallowed(ip) {
			return nil, fmt.Errorf("ssrf blocked: illegal target IP address %s", ip.String())
		}
	}

	safeAddr := net.JoinHostPort(ips[0].String(), port)
	dialer := &net.Dialer{
		Timeout:   5 * time.Second,
		KeepAlive: 30 * time.Second,
	}
	return dialer.DialContext(ctx, network, safeAddr)
}

// NewWebhookEngine creates a webhook delivery engine.
func NewWebhookEngine() *WebhookEngine {
	e := &WebhookEngine{
		client: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				DialContext: SafeDialContext,
			},
		},
		queue: make(chan webhookJob, 100),
	}
	// Start async delivery worker
	go e.deliveryWorker()
	return e
}

// ValidateWebhookURL parses and verifies the target URL against SSRF patterns.
var ValidateWebhookURL = func(targetURL string) error {
	u, err := url.Parse(targetURL)
	if err != nil {
		return fmt.Errorf("invalid URL")
	}

	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Errorf("ssrf blocked: invalid scheme %s", u.Scheme)
	}

	hostname := u.Hostname()
	ips, err := net.LookupIP(hostname)
	if err != nil {
		// If it's literally an IP address like 169.254.169.254, lookup fails but parses as IP.
		ip := net.ParseIP(hostname)
		if ip == nil {
			return fmt.Errorf("failed to resolve hostname")
		}
		ips = []net.IP{ip}
	}

	for _, ip := range ips {
		if webhookIPDisallowed(ip) {
			return fmt.Errorf("ssrf blocked: illegal target IP address %s", ip.String())
		}
	}
	return nil
}

// AddWebhook registers a webhook destination.
func (e *WebhookEngine) AddWebhook(wh WebhookConfig) error {
	if err := ValidateWebhookURL(wh.URL); err != nil {
		return err
	}

	e.mu.Lock()
	defer e.mu.Unlock()
	if wh.Retries == 0 {
		wh.Retries = 3
	}
	if wh.ID == "" {
		wh.ID = fmt.Sprintf("wh-%d", time.Now().UnixNano())
	}
	e.webhooks = append(e.webhooks, wh)
	return nil
}

// RemoveWebhook deactivates a webhook by ID.
func (e *WebhookEngine) RemoveWebhook(id string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	for i := range e.webhooks {
		if e.webhooks[i].ID == id {
			e.webhooks[i].Active = false
		}
	}
}

// Fire sends a webhook payload to all matching subscribers.
func (e *WebhookEngine) Fire(eventType WebhookEventType, payload WebhookPayload) {
	payload.EventType = eventType
	payload.Timestamp = time.Now()

	e.mu.RLock()
	defer e.mu.RUnlock()

	for _, wh := range e.webhooks {
		if !wh.Active {
			continue
		}
		for _, et := range wh.Events {
			if et == eventType {
				select {
				case e.queue <- webhookJob{config: wh, payload: payload, attempt: 0}:
				default:
					slog.Warn("webhook queue full, dropping event", "event_type", eventType, "url", wh.URL)
				}
				break
			}
		}
	}
}

// deliveryWorker processes webhook jobs with retries.
func (e *WebhookEngine) deliveryWorker() {
	for job := range e.queue {
		err := e.deliver(job.config, job.payload)
		if err != nil {
			job.attempt++
			if job.attempt < job.config.Retries {
				// Exponential backoff: 1s, 2s, 4s
				go func(j webhookJob) {
					time.Sleep(time.Duration(1<<j.attempt) * time.Second)
					select {
					case e.queue <- j:
					default:
					}
				}(job)
			} else {
				e.mu.Lock()
				e.failed++
				e.mu.Unlock()
				slog.Error("webhook delivery failed", "attempts", job.attempt, "url", job.config.URL, "error", err)
			}
		} else {
			e.mu.Lock()
			e.sent++
			e.mu.Unlock()
		}
	}
}

// deliver sends the HTTP request.
func (e *WebhookEngine) deliver(wh WebhookConfig, payload WebhookPayload) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", wh.URL, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "SYNTREX-SOAR/1.0")

	for k, v := range wh.Headers {
		req.Header.Set(k, v)
	}

	resp, err := e.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("webhook returned %d", resp.StatusCode)
	}
	return nil
}

// Stats returns webhook delivery statistics.
func (e *WebhookEngine) Stats() map[string]any {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return map[string]any{
		"webhooks_configured": len(e.webhooks),
		"sent":                e.sent,
		"failed":              e.failed,
		"queue_depth":         len(e.queue),
	}
}

// Webhooks returns all configured webhooks.
func (e *WebhookEngine) Webhooks() []WebhookConfig {
	e.mu.RLock()
	defer e.mu.RUnlock()
	result := make([]WebhookConfig, len(e.webhooks))
	copy(result, e.webhooks)
	return result
}
