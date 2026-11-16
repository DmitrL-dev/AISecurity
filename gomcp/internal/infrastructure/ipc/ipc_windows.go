//go:build windows

package ipc

import (
	"fmt"
	"net"
	"time"
)

// platformListen creates a named pipe listener on Windows.
// Uses net.Listen("tcp", ...) on localhost as Windows named pipe fallback.
// For production Windows deployments, use github.com/Microsoft/go-winio.
func platformListen(name string) (net.Listener, error) {
	// Fallback: TCP listener on localhost for Windows development.
	// In production, this would use go-winio for proper Windows named pipes.
	addr := fmt.Sprintf("127.0.0.1:%d", pipeTCPPort(name))
	l, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, fmt.Errorf("ipc/windows: listen %s (tcp %s): %w", name, addr, err)
	}
	return l, nil
}

// platformDial connects to a named pipe on Windows.
func platformDial(name string) (net.Conn, error) {
	addr := fmt.Sprintf("127.0.0.1:%d", pipeTCPPort(name))
	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return nil, fmt.Errorf("ipc/windows: dial %s (tcp %s): %w", name, addr, err)
	}
	return conn, nil
}

// pipeTCPPort maps pipe names to TCP ports for Windows dev fallback.
// In production, these would be actual Windows named pipes.
func pipeTCPPort(name string) int {
	ports := map[string]int{
		"soc-ingest-to-correlate":  19751,
		"soc-correlate-to-respond": 19752,
	}
	if p, ok := ports[name]; ok {
		return p
	}
	// Hash-based fallback for unknown names.
	h := 19700
	for _, c := range name {
		h = (h*31 + int(c)) % 1000
	}
	return 19700 + h
}
