package tunnel

import (
	"context"
	"net"
	"time"
)

// DirectDialer connects directly to the target (no relay).
// Uses the stealth uTLS dialer for HTTPS connections
// and plain TCP for non-TLS.
type DirectDialer struct {
	// Timeout for connections.
	Timeout time.Duration
}

// NewDirectDialer creates a direct dialer.
func NewDirectDialer() *DirectDialer {
	return &DirectDialer{
		Timeout: 10 * time.Second,
	}
}

// DialContext connects directly to addr.
func (d *DirectDialer) DialContext(
	ctx context.Context,
	network, addr string,
) (net.Conn, error) {
	dialer := &net.Dialer{Timeout: d.Timeout}
	return dialer.DialContext(ctx, network, addr)
}
