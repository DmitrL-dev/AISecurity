package transport

import (
	"context"
	"crypto/rand"
	"io"
	"math/big"
	"net"
	"net/http"
	"strings"
	"time"

	"fmt"

	utls "github.com/refraction-networking/utls"
	"github.com/sentinel-community/strike-force/internal/domain/entity"
	"github.com/sentinel-community/strike-force/internal/domain/port"
	"golang.org/x/net/http2"
)

// Wrapper implements port.Transport with high-performance/evasion features
type Wrapper struct {
	client *http.Client
	uas    []string
}

func NewWrapper(timeout time.Duration) port.Transport {
	// uTLS Dialer
	dialTLS := func(ctx context.Context, network, addr string) (net.Conn, error) {
		conn, err := net.DialTimeout(network, addr, timeout)
		if err != nil {
			return nil, err
		}

		// Pick a random fingerprint
		// Mimic: Chrome, Firefox, or Safari
		fingerprints := []utls.ClientHelloID{
			utls.HelloChrome_Auto,
			utls.HelloFirefox_Auto,
			utls.HelloIOS_Auto,
		}

		// Random selection
		idx, _ := rand.Int(rand.Reader, big.NewInt(int64(len(fingerprints))))
		fp := fingerprints[idx.Int64()]

		uConn := utls.UClient(conn, &utls.Config{
			InsecureSkipVerify: true, // Scanner needs to ignore cert errors
			ServerName:         strings.Split(addr, ":")[0],
			NextProtos:         []string{"h2", "http/1.1"}, // Try to appease strict WAFs expecting H2
		}, fp)

		if err := uConn.Handshake(); err != nil {
			conn.Close()
			return nil, fmt.Errorf("uTLS handshake failed: %w", err)
		}

		return uConn, nil
	}

	t := &http.Transport{
		DialTLSContext:      dialTLS, // Override TLS dialing with uTLS
		MaxIdleConns:        1000,
		MaxIdleConnsPerHost: 100,
		IdleConnTimeout:     90 * time.Second,
		DisableKeepAlives:   false,
		ForceAttemptHTTP2:   true, // Explicitly attempt H2
	}

	// Enable HTTP/2 Support explicitly for the custom transport
	if err := http2.ConfigureTransport(t); err != nil {
		fmt.Printf("Warning: Failed to configure HTTP/2: %v\n", err)
	}

	return &Wrapper{
		client: &http.Client{
			Transport: t,
			Timeout:   timeout,
			// Do not follow redirects automatically in scanner?
			// Or maybe yes? Let's use default (follows 10)
		},
		uas: []string{
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
		},
	}
}

func (w *Wrapper) Send(ctx context.Context, target entity.Target, payload entity.Payload) (*entity.Result, error) {
	start := time.Now()

	// Construct Request
	// TODO: Handle method properly, default to target.Method
	method := target.Method
	if method == "" {
		method = "GET"
	}

	// Inject payload into URL or Body based on context
	// Simplified: Inject to Query Param "q" if GET, Body if POST
	targetURL := target.URL
	var body io.Reader

	if method == "GET" {
		if strings.Contains(targetURL, "?") {
			targetURL += "&q=" + urlEncode(payload.Value)
		} else {
			targetURL += "?q=" + urlEncode(payload.Value)
		}
	} else {
		// POST
		body = strings.NewReader("data=" + urlEncode(payload.Value))
	}

	req, err := http.NewRequestWithContext(ctx, method, targetURL, body)
	if err != nil {
		return nil, err
	}

	// Headers
	req.Header.Set("User-Agent", w.getRandomUA())
	for k, v := range target.Headers {
		req.Header.Set(k, v)
	}

	// Execute
	resp, err := w.client.Do(req)
	latency := time.Since(start)

	res := &entity.Result{
		TargetID:    target.ID,
		PayloadID:   payload.ID,
		Timestamp:   time.Now(),
		Latency:     latency,
		Environment: "Origin", // Default
	}

	if err != nil {
		res.Error = err
		return res, nil // Return result with error, not error itself (pipeline continues)
	}
	defer resp.Body.Close()

	res.StatusCode = resp.StatusCode

	// Read simplified body
	b, _ := io.ReadAll(resp.Body)
	res.Response = string(b)

	// Check blocking
	if resp.StatusCode == 403 || resp.StatusCode == 406 {
		res.Blocked = true
		res.Environment = "WAF"
	} else if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		res.Success = true // Naive check
	}

	return res, nil
}

func (w *Wrapper) getRandomUA() string {
	idx, _ := rand.Int(rand.Reader, big.NewInt(int64(len(w.uas))))
	return w.uas[idx.Int64()]
}

func urlEncode(s string) string {
	// Simple url encode wrapper or reuse evasion logic?
	// For transport correctness, we should assume payload is already mutated/encoded by Evasion adapter if intent was evasion.
	// But network transport implies necessary wire encoding.
	// We'll leave it raw if the user wants raw, but for safety `net/http` might escape?
	// Actually `NewRequest` doesn't escape params in URL string manually constructed.
	// We'll simplisticly escape here.
	return s // Placeholder: assume payload arrived ready-to-send from "Payload" entity
}
