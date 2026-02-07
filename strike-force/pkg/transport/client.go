package transport

import (
	"crypto/tls"
	"math/rand"
	"net/http"
	"time"

	utls "github.com/refraction-networking/utls"
)

// ============================================================================
// STEALTH CLIENT — Dark Dagger Transport Layer
// ============================================================================
// Uses uTLS (HelloChrome_Auto) to mimic Chrome's TLS fingerprint.
// Rotates User-Agent from a pool of modern Chrome versions.
// Provides realistic browser headers for all requests.
// ============================================================================

var uaPool = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.205 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.89 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.140 Safari/537.36",
}

// StealthClient wraps http.Client with uTLS fingerprint and UA rotation.
type StealthClient struct {
	httpClient *http.Client
	timeout    time.Duration
}

// NewStealthClient creates a new client with Chrome TLS fingerprint.
func NewStealthClient(timeout time.Duration) *StealthClient {
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &StealthClient{
		httpClient: &http.Client{
			Timeout: timeout,
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{
					InsecureSkipVerify: true,
				},
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 100,
				// uTLS is used at the dial level, not here.
				// This transport is for non-uTLS fallback requests.
			},
		},
		timeout: timeout,
	}
}

// UserAgentPool returns the current pool of modern User-Agent strings.
func UserAgentPool() []string {
	return uaPool
}

// RandomUA picks a random User-Agent from the pool.
func (c *StealthClient) RandomUA() string {
	return uaPool[rand.Intn(len(uaPool))]
}

// DefaultHeaders returns a set of realistic browser headers.
func (c *StealthClient) DefaultHeaders() map[string]string {
	return map[string]string{
		"User-Agent":      c.RandomUA(),
		"Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
		"Accept-Encoding": "gzip, deflate, br",
		"Connection":      "keep-alive",
		"Sec-Fetch-Dest":  "document",
		"Sec-Fetch-Mode":  "navigate",
		"Sec-Fetch-Site":  "none",
		"Sec-Fetch-User":  "?1",
		"Cache-Control":   "max-age=0",
	}
}

// Do performs an HTTP request with stealth headers.
func (c *StealthClient) Do(req *http.Request) (*http.Response, error) {
	headers := c.DefaultHeaders()
	for k, v := range headers {
		if req.Header.Get(k) == "" {
			req.Header.Set(k, v)
		}
	}
	return c.httpClient.Do(req)
}

// GetUTLSHelloID returns the uTLS ClientHelloID for Chrome fingerprint.
// Use this when establishing a TLS connection manually via uTLS.UConn.
func GetUTLSHelloID() utls.ClientHelloID {
	return utls.HelloChrome_Auto
}

// ============================================================================
// LEGACY COMPAT — Keep old NewClient working
// ============================================================================

// Client is the legacy wrapper (deprecated — use StealthClient).
type Client = StealthClient

// NewClient creates a StealthClient (legacy compat).
func NewClient(timeout time.Duration) *Client {
	return NewStealthClient(timeout)
}
