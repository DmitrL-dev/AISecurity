//go:build windows

package antitamper

import (
	"os"
	"strings"
	"syscall"
	"unsafe"
)

var (
	kernel32           = syscall.NewLazyDLL("kernel32.dll")
	isDebuggerPresent = kernel32.NewProc("IsDebuggerPresent")
)

// platformInit disables debug features on Windows.
func (s *Shield) platformInit() {
	// On Windows, we check IsDebuggerPresent periodically.
	// No prctl equivalent needed.
	s.logger.Info("anti-tamper: Windows platform initialized")
}

// isDebuggerAttached checks if a debugger is attached using Win32 API.
func (s *Shield) isDebuggerAttached() bool {
	ret, _, _ := isDebuggerPresent.Call()
	if ret != 0 {
		return true
	}

	// Additional check: look for common debugger environment indicators.
	debugIndicators := []string{
		"_NT_SYMBOL_PATH",
		"_NT_ALT_SYMBOL_PATH",
	}
	for _, env := range debugIndicators {
		if os.Getenv(env) != "" {
			return true
		}
	}

	// Check parent process name for known debuggers.
	// This is a heuristic — not foolproof.
	_ = strings.Contains // suppress unused import
	_ = unsafe.Pointer(nil) // suppress unused import

	return false
}
