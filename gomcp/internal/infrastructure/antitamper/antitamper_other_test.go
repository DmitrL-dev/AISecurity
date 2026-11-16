//go:build !linux && !windows

package antitamper

import (
	"log/slog"
	"testing"
)

func TestUnsupportedPlatformHooksRemainSafe(t *testing.T) {
	shield := &Shield{logger: slog.Default()}
	shield.platformInit()
	if shield.isDebuggerAttached() {
		t.Fatal("unsupported platform must not report a debugger without evidence")
	}
}
