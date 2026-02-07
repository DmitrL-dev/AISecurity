package transport

import (
	"context"
	"crypto/tls"
	"fmt"
	"math/rand"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	utls "github.com/refraction-networking/utls"
)

// ============================================================================
// GHOST DIALER — uTLS WebSocket + Cookie Jar + Jitter
// ============================================================================
// Fixes GAP-1 (WS not through uTLS), GAP-3 (no cookies),
// GAP-6 (deterministic delays), GAP-7 (no warm-up).
// ============================================================================

// GhostDialer creates WebSocket connections with Chrome TLS fingerprint.
type GhostDialer struct {
	jar       http.CookieJar
	userAgent string
	origin    string
}

// NewGhostDialer creates a dialer with cookie jar and Chrome mimicry.
func NewGhostDialer(origin string) *GhostDialer {
	jar, _ := cookiejar.New(nil)
	client := NewStealthClient(30 * time.Second)

	return &GhostDialer{
		jar:       jar,
		userAgent: client.RandomUA(),
		origin:    origin,
	}
}

// WarmUp performs a pre-flight GET request to collect session cookies
// and look like a real browser before opening WebSocket.
func (gd *GhostDialer) WarmUp(ctx context.Context, targetURL string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", targetURL, nil)
	if err != nil {
		return fmt.Errorf("warmup request: %w", err)
	}

	client := &http.Client{
		Jar:     gd.jar,
		Timeout: 15 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	req.Header.Set("User-Agent", gd.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("warmup GET: %w", err)
	}
	resp.Body.Close()
	return nil
}

// GetCookies returns all cookies collected during warm-up for the given URL.
func (gd *GhostDialer) GetCookies(rawURL string) []*http.Cookie {
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil
	}
	return gd.jar.Cookies(u)
}

// GetCSRFToken extracts the CSRF-TOKEN value from collected cookies.
func (gd *GhostDialer) GetCSRFToken(rawURL string) string {
	for _, c := range gd.GetCookies(rawURL) {
		if strings.EqualFold(c.Name, "CSRF-TOKEN") {
			return c.Value
		}
	}
	return ""
}

// CookieString returns cookies formatted for the Cookie header.
func (gd *GhostDialer) CookieString(rawURL string) string {
	cookies := gd.GetCookies(rawURL)
	parts := make([]string, 0, len(cookies))
	for _, c := range cookies {
		parts = append(parts, c.Name+"="+c.Value)
	}
	return strings.Join(parts, "; ")
}

// DialWebSocket opens a WebSocket connection using uTLS Chrome fingerprint.
// The TLS handshake mimics Chrome's JA3, not Go's default.
func (gd *GhostDialer) DialWebSocket(ctx context.Context, wsURL string) (*websocket.Conn, *http.Response, error) {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
		Jar:              gd.jar,
		NetDialTLSContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
			return dialUTLS(ctx, network, addr)
		},
	}

	headers := http.Header{}
	headers.Set("User-Agent", gd.userAgent)
	headers.Set("Origin", gd.origin)
	headers.Set("Accept-Language", "en-US,en;q=0.9")
	headers.Set("Sec-WebSocket-Extensions", "permessage-deflate; client_max_window_bits")

	return dialer.DialContext(ctx, wsURL, headers)
}

// dialUTLS establishes a TLS connection with Chrome's JA3 fingerprint.
func dialUTLS(ctx context.Context, network, addr string) (net.Conn, error) {
	// TCP dial with context
	d := net.Dialer{}
	tcpConn, err := d.DialContext(ctx, network, addr)
	if err != nil {
		return nil, fmt.Errorf("tcp dial: %w", err)
	}

	// Extract hostname for SNI
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		host = addr
	}

	// uTLS handshake with Chrome fingerprint
	tlsConn := utls.UClient(tcpConn, &utls.Config{
		ServerName:         host,
		InsecureSkipVerify: true,
	}, utls.HelloChrome_Auto)

	if err := tlsConn.HandshakeContext(ctx); err != nil {
		tcpConn.Close()
		return nil, fmt.Errorf("utls handshake: %w", err)
	}

	return tlsConn, nil
}

// ============================================================================
// JITTER — Human-Like Delay Generation
// ============================================================================

// HumanDelay returns a randomized delay using Gaussian distribution.
// center is the median delay, spread controls variance.
// Example: HumanDelay(3500, 1500) → 2000-7000ms range
func HumanDelay(centerMs, spreadMs int) time.Duration {
	// Box-Muller transform for Gaussian
	delay := float64(centerMs) + rand.NormFloat64()*float64(spreadMs)
	if delay < float64(centerMs)/3 {
		delay = float64(centerMs) / 3 // Floor at 1/3 of center
	}
	if delay > float64(centerMs)*3 {
		delay = float64(centerMs) * 3 // Cap at 3x center
	}
	return time.Duration(delay) * time.Millisecond
}

// SleepLikeHuman sleeps with human-like jitter, respecting context.
func SleepLikeHuman(ctx context.Context, centerMs, spreadMs int) error {
	delay := HumanDelay(centerMs, spreadMs)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(delay):
		return nil
	}
}
