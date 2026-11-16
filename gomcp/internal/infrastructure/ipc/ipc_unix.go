//go:build !windows

package ipc

import (
	"fmt"
	"net"
	"os"
	"path/filepath"
	"time"
)

// socketDir is the base directory for Unix domain sockets.
var socketDir = filepath.Join(os.TempDir(), "sentinel-soc")

// platformListen creates a Unix domain socket listener.
func platformListen(name string) (net.Listener, error) {
	// Ensure socket directory exists.
	if err := os.MkdirAll(socketDir, 0700); err != nil {
		return nil, fmt.Errorf("ipc/unix: mkdir %s: %w", socketDir, err)
	}

	sockPath := filepath.Join(socketDir, name+".sock")

	// Remove stale socket file if it exists.
	_ = os.Remove(sockPath)

	l, err := net.Listen("unix", sockPath)
	if err != nil {
		return nil, fmt.Errorf("ipc/unix: listen %s: %w", sockPath, err)
	}

	// Set restrictive permissions on the socket.
	if err := os.Chmod(sockPath, 0600); err != nil {
		l.Close()
		return nil, fmt.Errorf("ipc/unix: chmod %s: %w", sockPath, err)
	}

	return l, nil
}

// platformDial connects to a Unix domain socket.
func platformDial(name string) (net.Conn, error) {
	sockPath := filepath.Join(socketDir, name+".sock")
	conn, err := net.DialTimeout("unix", sockPath, 5*time.Second)
	if err != nil {
		return nil, fmt.Errorf("ipc/unix: dial %s: %w", sockPath, err)
	}
	return conn, nil
}
