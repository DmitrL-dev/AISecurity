package httpserver

import (
	"os"

	"github.com/syntrex/gomcp/internal/domain/engines"
)

// Review 14.06 (P0 — fail CLOSED): the public scan path must NEVER serve a
// verdict from the StubSentinelCore, which reports EVERY prompt clean
// (ThreatFound:false). That stub is reached two ways:
//   1. cmd/soc on native-engine build failure calls SetSentinelCore(stub);
//   2. cmd/gomcp never calls SetSentinelCore, so getEngine() returns a fresh stub.
// In both cases a gateway built CGO_ENABLED=0 (the default for ./gomcp/Dockerfile,
// Dockerfile.soc, the Makefile and the CD pipeline) silently allows everything.
// These helpers let handlePublicScan fail closed instead.

// scanEngineReady reports whether a REAL (non-stub) sentinel-core engine is wired.
// A nil engine or the StubSentinelCore is NOT ready.
func (s *Server) scanEngineReady() bool {
	if s.sentinelCore == nil {
		return false
	}
	_, isStub := s.sentinelCore.(*engines.StubSentinelCore)
	return !isStub
}

// stubScanAllowed reports whether an operator has explicitly opted into running
// the gateway with the allow-all stub engine (DEV ONLY).
func stubScanAllowed() bool {
	return os.Getenv("SENTINEL_ALLOW_STUB") == "1"
}
