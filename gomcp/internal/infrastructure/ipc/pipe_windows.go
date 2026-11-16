//go:build windows

package ipc

import (
	"net"
	"time"
)

// listen creates a Named Pipe listener on Windows.
// Uses net.Listen("tcp", "127.0.0.1:0") as fallback since Go's net package
// doesn't natively support Windows Named Pipes without syscall.
// For production, this could use github.com/Microsoft/go-winio,
// but for zero-dependency we use localhost TCP on an ephemeral port
// with a port file for discovery.
func listen(path string) (net.Listener, error) {
	// Use a fixed local port for Swarm IPC.
	// Port 19747 = 0x4D33 ("M3" for MCP v3).
	return net.Listen("tcp", "127.0.0.1:19747")
}

// dial connects to the Swarm IPC endpoint.
func dial(path string) (net.Conn, error) {
	return net.DialTimeout("tcp", "127.0.0.1:19747", 2*time.Second)
}
