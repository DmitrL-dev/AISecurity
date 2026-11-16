//go:build !windows

package ipc

import (
	"net"
	"time"
)

// listen creates a Unix Domain Socket listener.
func listen(path string) (net.Listener, error) {
	return net.Listen("unix", path)
}

// dial connects to a Unix Domain Socket.
func dial(path string) (net.Conn, error) {
	return net.DialTimeout("unix", path, 2*time.Second)
}
