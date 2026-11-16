//go:build !linux && !windows

package antitamper

// platformInit reports the unavailable OS hardening explicitly. Cross-platform
// binary and environment integrity checks remain active.
func (s *Shield) platformInit() {
	s.logger.Warn("anti-tamper: debugger and core-dump hardening unavailable on this platform")
}

// isDebuggerAttached has no supported implementation on this platform.
func (s *Shield) isDebuggerAttached() bool {
	return false
}
