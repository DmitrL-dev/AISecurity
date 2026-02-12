package stealth

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// DoHResolver resolves domain names via DNS-over-HTTPS.
// Bypasses local DNS filtering/interception by ISP/RKN.
type DoHResolver struct {
	// Server is the DoH endpoint (default: Cloudflare).
	Server string

	// Client is the HTTP client to use.
	Client *http.Client
}

// dohResponse is the JSON response from DoH API.
type dohResponse struct {
	Answer []dohAnswer `json:"Answer"`
}

type dohAnswer struct {
	Type int    `json:"type"`
	Data string `json:"data"`
}

// NewDoHResolver creates a resolver using Cloudflare DoH.
func NewDoHResolver() *DoHResolver {
	return &DoHResolver{
		Server: "https://1.1.1.1/dns-query",
		Client: &http.Client{Timeout: 5 * time.Second},
	}
}

// NewGoogleDoHResolver creates a resolver using Google DoH.
func NewGoogleDoHResolver() *DoHResolver {
	return &DoHResolver{
		Server: "https://8.8.8.8/resolve",
		Client: &http.Client{Timeout: 5 * time.Second},
	}
}

// Resolve returns the first A record for the given domain.
func (r *DoHResolver) Resolve(
	ctx context.Context,
	domain string,
) (string, error) {
	url := fmt.Sprintf(
		"%s?name=%s&type=A",
		r.Server, domain,
	)

	req, err := http.NewRequestWithContext(
		ctx, http.MethodGet, url, nil,
	)
	if err != nil {
		return "", err
	}

	req.Header.Set("Accept", "application/dns-json")

	resp, err := r.Client.Do(req)
	if err != nil {
		return "", fmt.Errorf("doh request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("doh read: %w", err)
	}

	var result dohResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("doh parse: %w", err)
	}

	// Find first A record (type 1)
	for _, ans := range result.Answer {
		if ans.Type == 1 {
			return ans.Data, nil
		}
	}

	return "", fmt.Errorf("no A record for %s", domain)
}
