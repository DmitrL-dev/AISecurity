//go:build linux

package antitamper

import (
	"os"
	"strconv"
	"strings"

	"golang.org/x/sys/unix"
)

// platformInit applies Linux-specific anti-tamper controls.
func (s *Shield) platformInit() {
	// PR_SET_DUMPABLE = 0 prevents core dumps and ptrace attachment.
	// This is the strongest anti-debug measure on Linux without eBPF.
	if err := unix.Prctl(unix.PR_SET_DUMPABLE, 0, 0, 0, 0); err != nil {
		s.logger.Warn("anti-tamper: PR_SET_DUMPABLE failed", "error", err)
	} else {
		s.logger.Info("anti-tamper: PR_SET_DUMPABLE=0 (core dumps disabled)")
	}

	// PR_SET_NO_NEW_PRIVS prevents privilege escalation.
	if err := unix.Prctl(unix.PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0); err != nil {
		s.logger.Warn("anti-tamper: PR_SET_NO_NEW_PRIVS failed", "error", err)
	} else {
		s.logger.Info("anti-tamper: PR_SET_NO_NEW_PRIVS=1")
	}
}

// isDebuggerAttached checks for debugger attachment on Linux.
func (s *Shield) isDebuggerAttached() bool {
	data, err := os.ReadFile("/proc/self/status")
	if err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "TracerPid:") {
				pidStr := strings.TrimSpace(strings.TrimPrefix(line, "TracerPid:"))
				pid, _ := strconv.Atoi(pidStr)
				if pid != 0 {
					return true
				}
			}
		}
	}

	return false
}
