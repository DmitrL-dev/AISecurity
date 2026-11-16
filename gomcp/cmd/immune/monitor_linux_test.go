//go:build linux && !ebpf

package main

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/guard"
	"github.com/syntrex/gomcp/internal/infrastructure/logging"
)

// TestParseHexIP covers the /proc net hex-IP decoding (little-endian IPv4).
func TestParseHexIP(t *testing.T) {
	cases := []struct {
		token string
		want  string
	}{
		// 0100007F:0035 -> 127.0.0.1 (little-endian bytes 01 00 00 7F reversed)
		{"0100007F:0035", "127.0.0.1"},
		// 08080808:01BB -> 8.8.8.8
		{"08080808:01BB", "8.8.8.8"},
		// 0101A8C0:0050 -> 192.168.1.1
		{"0101A8C0:0050", "192.168.1.1"},
		{"00000000:0000", ""}, // 0.0.0.0 is filtered out
		{"garbage", ""},       // no colon
	}
	for _, c := range cases {
		got := parseHexIP(c.token)
		if got != c.want {
			t.Errorf("parseHexIP(%q) = %q, want %q", c.token, got, c.want)
		}
	}
}

// TestParseTCPPeers verifies that only ESTABLISHED (state 01) connections yield a
// remote peer IP, and that the header row + non-established rows are skipped.
func TestParseTCPPeers(t *testing.T) {
	// Real-format /proc/<pid>/net/tcp sample: header, one ESTABLISHED to 8.8.8.8,
	// one LISTEN (0A) on 0.0.0.0, one ESTABLISHED to 1.1.1.1.
	sample := strings.Join([]string{
		"  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode",
		"   0: 0100007F:9760 08080808:01BB 01 00000000:00000000 00:00000000 00000000  1000        0 12345 1 0000 0",
		"   1: 00000000:2604 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 12346 1 0000 0",
		"   2: 0100007F:9760 01010101:01BB 01 00000000:00000000 00:00000000 00000000  1000        0 12347 1 0000 0",
		"",
	}, "\n")

	peers := parseTCPPeers(strings.NewReader(sample))
	if len(peers) != 2 {
		t.Fatalf("expected 2 established peers, got %d: %v", len(peers), peers)
	}
	if peers[0] != "8.8.8.8" || peers[1] != "1.1.1.1" {
		t.Errorf("peers = %v, want [8.8.8.8 1.1.1.1]", peers)
	}
}

// TestReadProcState_Self reads the test process's own /proc entry and checks the
// fields parse (comm non-empty, memory >= 0). This exercises the real procfs read
// path on the build platform.
func TestReadProcState_Self(t *testing.T) {
	pid := 1 // init always exists on Linux; readable comm
	st, ok := readProcState(pid)
	if !ok {
		t.Skip("cannot read /proc/1 in this sandbox; procfs read path covered by parse tests")
	}
	if st.comm == "" {
		t.Error("expected non-empty comm for pid 1")
	}
	if st.memoryMB < 0 {
		t.Errorf("memoryMB = %d, want >= 0", st.memoryMB)
	}
}

// TestScanProc_NoPanicAndRespectsMonitored runs a real scan against /proc with a
// policy that monitors a process name unlikely to be present, so it must complete
// without recording violations or panicking.
func TestScanProc_NoPanicAndRespectsMonitored(t *testing.T) {
	g := guard.New(&guard.Policy{
		Mode: guard.ModeAudit,
		Processes: map[string]guard.ProcessPolicy{
			"definitely-not-a-real-proc-xyz": {MaxMemoryMB: 1},
		},
	})
	scanProc(g, logging.New("text", "error"))
	if v := g.Stats().Violations; v != 0 {
		t.Errorf("expected 0 violations for unmonitored host, got %d", v)
	}
}

// TestRunMonitor_WiresEnforcerAndStops confirms runMonitor wires the enforcer and
// returns promptly on context cancel.
func TestRunMonitor_WiresEnforcerAndStops(t *testing.T) {
	g := guard.New(&guard.Policy{
		Mode:      guard.ModeAudit,
		Processes: map[string]guard.ProcessPolicy{"x": {}},
	})
	enf := newEnforcer(newLogOnlyFW(), false, logging.New("text", "error"))

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		runMonitor(ctx, g, enf, logging.New("text", "error"))
		close(done)
	}()
	cancel()
	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("runMonitor did not stop within 3s of ctx cancel")
	}
}
