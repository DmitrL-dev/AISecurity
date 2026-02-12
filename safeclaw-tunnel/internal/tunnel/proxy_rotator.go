package tunnel

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"net"
	"strings"
	"sync"
	"time"
)

// ProxyEntry represents an upstream SOCKS5 proxy.
type ProxyEntry struct {
	Addr     string // host:port
	Username string
	Password string
	Country  string // optional label
	alive    bool
	lastFail time.Time
}

// ProxyRotator is a Dialer that rotates through upstream
// SOCKS5 proxies with automatic failover on connection errors.
type ProxyRotator struct {
	mu      sync.RWMutex
	proxies []*ProxyEntry
	current int
	logger  *log.Logger
	timeout time.Duration

	// Cooldown before retrying a failed proxy.
	cooldown time.Duration
}

// NewProxyRotator creates a rotator from proxy entries.
func NewProxyRotator(
	proxies []*ProxyEntry,
	logger *log.Logger,
) *ProxyRotator {
	for _, p := range proxies {
		p.alive = true
	}
	return &ProxyRotator{
		proxies:  proxies,
		logger:   logger,
		timeout:  10 * time.Second,
		cooldown: 30 * time.Second,
	}
}

// ParseProxyList parses proxy entries from a string.
// Format: user:pass@host:port[:country] (one per line).
func ParseProxyList(raw string) []*ProxyEntry {
	var result []*ProxyEntry
	scanner := bufio.NewScanner(strings.NewReader(raw))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		entry := parseProxyLine(line)
		if entry != nil {
			result = append(result, entry)
		}
	}
	return result
}

// parseProxyLine parses "user:pass@host:port" format.
func parseProxyLine(line string) *ProxyEntry {
	entry := &ProxyEntry{alive: true}

	// Check for country suffix: ...#GB
	if idx := strings.LastIndex(line, "#"); idx > 0 {
		entry.Country = strings.TrimSpace(line[idx+1:])
		line = line[:idx]
	}

	// Check for user:pass@
	if idx := strings.LastIndex(line, "@"); idx > 0 {
		creds := line[:idx]
		entry.Addr = line[idx+1:]
		parts := strings.SplitN(creds, ":", 2)
		if len(parts) == 2 {
			entry.Username = parts[0]
			entry.Password = parts[1]
		}
	} else {
		entry.Addr = line
	}

	// Validate addr has host:port
	if _, _, err := net.SplitHostPort(entry.Addr); err != nil {
		return nil
	}

	return entry
}

// DialContext connects through the next available proxy,
// rotating on failure.
func (r *ProxyRotator) DialContext(
	ctx context.Context,
	network, addr string,
) (net.Conn, error) {
	r.mu.RLock()
	total := len(r.proxies)
	r.mu.RUnlock()

	if total == 0 {
		return nil, fmt.Errorf("no proxies configured")
	}

	// Try each proxy, starting from current
	for attempt := 0; attempt < total; attempt++ {
		r.mu.Lock()
		idx := r.current % total
		proxy := r.proxies[idx]
		r.current = (r.current + 1) % total
		r.mu.Unlock()

		// Skip proxies in cooldown
		if !proxy.alive &&
			time.Since(proxy.lastFail) < r.cooldown {
			r.logger.Printf(
				"⏭ Skip %s (%s) — cooldown",
				proxy.Addr, proxy.Country,
			)
			continue
		}

		conn, err := r.dialThroughProxy(
			ctx, proxy, network, addr,
		)
		if err != nil {
			r.mu.Lock()
			proxy.alive = false
			proxy.lastFail = time.Now()
			r.mu.Unlock()

			r.logger.Printf(
				"✗ %s (%s) failed: %v — rotating",
				proxy.Addr, proxy.Country, err,
			)
			continue
		}

		// Success — mark alive
		r.mu.Lock()
		proxy.alive = true
		r.mu.Unlock()

		r.logger.Printf(
			"✓ %s → %s via %s (%s)",
			network, addr, proxy.Addr, proxy.Country,
		)
		return conn, nil
	}

	return nil, fmt.Errorf(
		"all %d proxies failed for %s", total, addr,
	)
}

// dialThroughProxy performs a SOCKS5 handshake with an
// upstream proxy and requests connection to the target.
func (r *ProxyRotator) dialThroughProxy(
	ctx context.Context,
	proxy *ProxyEntry,
	network, addr string,
) (net.Conn, error) {
	// Connect to proxy
	dialer := &net.Dialer{Timeout: r.timeout}
	conn, err := dialer.DialContext(ctx, "tcp", proxy.Addr)
	if err != nil {
		return nil, fmt.Errorf("connect proxy: %w", err)
	}

	// SOCKS5 handshake
	if err := r.socks5Handshake(
		conn, proxy, addr,
	); err != nil {
		conn.Close()
		return nil, fmt.Errorf("socks5 handshake: %w", err)
	}

	return conn, nil
}

// socks5Handshake performs the SOCKS5 client handshake
// with optional username/password authentication.
func (r *ProxyRotator) socks5Handshake(
	conn net.Conn,
	proxy *ProxyEntry,
	targetAddr string,
) error {
	conn.SetDeadline(time.Now().Add(r.timeout))
	defer conn.SetDeadline(time.Time{})

	// 1. Greeting — offer auth methods
	var authMethod byte = 0x00 // no auth
	if proxy.Username != "" {
		authMethod = 0x02 // user/pass
	}

	// Send greeting with both methods
	_, err := conn.Write([]byte{
		0x05, // SOCKS5
		0x02, // 2 methods
		0x00, // no auth
		0x02, // user/pass
	})
	if err != nil {
		return fmt.Errorf("write greeting: %w", err)
	}

	// Read server's chosen method
	resp := make([]byte, 2)
	if _, err := conn.Read(resp); err != nil {
		return fmt.Errorf("read greeting resp: %w", err)
	}
	if resp[0] != 0x05 {
		return fmt.Errorf("bad version: %d", resp[0])
	}

	chosenMethod := resp[1]

	// 2. Authenticate if needed
	if chosenMethod == 0x02 && proxy.Username != "" {
		if err := r.socks5Auth(conn, proxy); err != nil {
			return err
		}
	} else if chosenMethod == 0xFF {
		return fmt.Errorf("no acceptable auth methods")
	}
	_ = authMethod

	// 3. Connect request
	host, portStr, err := net.SplitHostPort(targetAddr)
	if err != nil {
		return fmt.Errorf("parse target: %w", err)
	}

	var portNum int
	fmt.Sscanf(portStr, "%d", &portNum)

	// Build connect request
	req := []byte{
		0x05, // VER
		0x01, // CMD: CONNECT
		0x00, // RSV
		0x03, // ATYP: domain
		byte(len(host)),
	}
	req = append(req, []byte(host)...)
	req = append(req,
		byte(portNum>>8),
		byte(portNum&0xFF),
	)

	if _, err := conn.Write(req); err != nil {
		return fmt.Errorf("write connect: %w", err)
	}

	// 4. Read connect response
	respBuf := make([]byte, 4)
	if _, err := conn.Read(respBuf); err != nil {
		return fmt.Errorf("read connect resp: %w", err)
	}
	if respBuf[1] != 0x00 {
		return fmt.Errorf(
			"connect failed: status %d", respBuf[1],
		)
	}

	// Read remaining response (ATYP-dependent)
	switch respBuf[3] {
	case 0x01: // IPv4
		discard := make([]byte, 4+2) // IP + port
		conn.Read(discard)
	case 0x03: // Domain
		lenBuf := make([]byte, 1)
		conn.Read(lenBuf)
		discard := make([]byte, int(lenBuf[0])+2)
		conn.Read(discard)
	case 0x04: // IPv6
		discard := make([]byte, 16+2) // IP + port
		conn.Read(discard)
	}

	return nil
}

// socks5Auth performs SOCKS5 username/password auth (RFC 1929).
func (r *ProxyRotator) socks5Auth(
	conn net.Conn,
	proxy *ProxyEntry,
) error {
	// VER ULEN USER PLEN PASS
	auth := []byte{0x01, byte(len(proxy.Username))}
	auth = append(auth, []byte(proxy.Username)...)
	auth = append(auth, byte(len(proxy.Password)))
	auth = append(auth, []byte(proxy.Password)...)

	if _, err := conn.Write(auth); err != nil {
		return fmt.Errorf("write auth: %w", err)
	}

	resp := make([]byte, 2)
	if _, err := conn.Read(resp); err != nil {
		return fmt.Errorf("read auth resp: %w", err)
	}
	if resp[1] != 0x00 {
		return fmt.Errorf("auth failed: status %d", resp[1])
	}

	return nil
}

// AliveCount returns the number of alive proxies.
func (r *ProxyRotator) AliveCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	count := 0
	for _, p := range r.proxies {
		if p.alive {
			count++
		}
	}
	return count
}

// Status returns a summary of proxy states.
func (r *ProxyRotator) Status() string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	alive := 0
	for _, p := range r.proxies {
		if p.alive {
			alive++
		}
	}
	return fmt.Sprintf(
		"%d/%d proxies alive", alive, len(r.proxies),
	)
}
