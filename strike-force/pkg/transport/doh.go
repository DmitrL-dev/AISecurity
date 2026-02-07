package transport

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// ============================================================================
// DNS-over-HTTPS RESOLVER — Anti-DNS Leak
// ============================================================================
// In corporate environments, direct DNS queries are logged and monitored.
// DoH tunnels DNS lookups through HTTPS, blending with normal web traffic.
// Fixes GAP-5: DNS Leak.
//
// Providers:
//   Cloudflare: https://cloudflare-dns.com/dns-query
//   Google:     https://dns.google/resolve
// ============================================================================

// DoHResolver resolves domain names via DNS-over-HTTPS.
type DoHResolver struct {
	provider   string
	httpClient *http.Client
}

// NewDoHResolver creates a DoH resolver. Empty provider defaults to Cloudflare.
func NewDoHResolver(provider string) *DoHResolver {
	if provider == "" {
		provider = "https://cloudflare-dns.com/dns-query"
	}
	return &DoHResolver{
		provider: provider,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// dohResponse is the JSON response from DoH providers.
type dohResponse struct {
	Status int `json:"Status"`
	Answer []struct {
		Name string `json:"name"`
		Type int    `json:"type"`
		Data string `json:"data"`
	} `json:"Answer"`
}

// Resolve performs a DNS lookup over HTTPS, returning IP addresses.
func (r *DoHResolver) Resolve(ctx context.Context, domain string) ([]string, error) {
	// Build URL (JSON wire format)
	url := fmt.Sprintf("%s?name=%s&type=A", r.provider, domain)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("doh request: %w", err)
	}

	// Accept JSON format (both Cloudflare and Google support this)
	req.Header.Set("Accept", "application/dns-json")
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

	resp, err := r.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("doh query: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("doh read: %w", err)
	}

	var doh dohResponse
	if err := json.Unmarshal(body, &doh); err != nil {
		return nil, fmt.Errorf("doh parse: %w", err)
	}

	if doh.Status != 0 {
		return nil, fmt.Errorf("doh error: RCODE=%d", doh.Status)
	}

	var ips []string
	for _, a := range doh.Answer {
		// Type 1 = A record (IPv4)
		if a.Type == 1 {
			ip := strings.TrimSuffix(a.Data, ".")
			ips = append(ips, ip)
		}
	}

	if len(ips) == 0 {
		return nil, fmt.Errorf("no A records for %s", domain)
	}

	return ips, nil
}
