package stealth

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"time"

	utls "github.com/refraction-networking/utls"
)

// ChromeDialer creates TLS connections with Chrome's JA3 fingerprint.
// DPI systems see this as a normal Chrome browser connection.
type ChromeDialer struct {
	// ServerName is the SNI to present (can differ from actual target
	// for domain fronting).
	ServerName string

	// Resolver is the DNS resolver to use. If nil, uses system default.
	Resolver *DoHResolver

	// Timeout for dial operations.
	Timeout time.Duration
}

// NewChromeDialer creates a dialer mimicking Chrome 120+.
func NewChromeDialer(sni string) *ChromeDialer {
	return &ChromeDialer{
		ServerName: sni,
		Timeout:    10 * time.Second,
	}
}

// DialTLS connects to addr using uTLS with Chrome fingerprint.
// The connection looks identical to Chrome 120 to any DPI system.
func (d *ChromeDialer) DialTLS(
	ctx context.Context,
	network, addr string,
) (net.Conn, error) {
	// Resolve via DoH if resolver is set
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, fmt.Errorf("invalid addr %s: %w", addr, err)
	}

	var dialAddr string
	if d.Resolver != nil {
		ip, err := d.Resolver.Resolve(ctx, host)
		if err != nil {
			return nil, fmt.Errorf("doh resolve %s: %w", host, err)
		}
		dialAddr = net.JoinHostPort(ip, port)
	} else {
		dialAddr = addr
	}

	// Plain TCP connection
	dialer := &net.Dialer{Timeout: d.Timeout}
	rawConn, err := dialer.DialContext(ctx, network, dialAddr)
	if err != nil {
		return nil, fmt.Errorf("tcp dial %s: %w", dialAddr, err)
	}

	// Determine SNI
	sni := d.ServerName
	if sni == "" {
		sni = host
	}

	// uTLS handshake with Chrome fingerprint
	tlsConn := utls.UClient(rawConn, &utls.Config{
		ServerName:         sni,
		InsecureSkipVerify: false,
		MinVersion:         tls.VersionTLS12,
	}, utls.HelloChrome_Auto)

	if err := tlsConn.HandshakeContext(ctx); err != nil {
		rawConn.Close()
		return nil, fmt.Errorf("utls handshake: %w", err)
	}

	return tlsConn, nil
}

// DialWS creates a stealth WebSocket connection over uTLS.
// Used to establish the tunnel to relay server.
func (d *ChromeDialer) DialWS(
	ctx context.Context,
	relayURL string,
) (net.Conn, error) {
	// For WSS, we first establish uTLS then upgrade to WebSocket
	// This is handled by the tunnel/wss.go layer
	return nil, fmt.Errorf("use tunnel.WSSClient instead")
}
