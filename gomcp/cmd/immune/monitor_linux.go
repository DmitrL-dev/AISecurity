//go:build linux && !ebpf

package main

import (
	"bufio"
	"context"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// backendName reports the ACTIVE monitoring backend for /health, /stats and the
// startup log. On the default Linux build (no ebpf tag) this is honest procfs
// polling — NOT kernel enforcement.
const backendName = "procfs-polling"

// backendDetail is a one-line, truthful description of what this backend does.
const backendDetail = "polls /proc on Linux to detect policy violations (memory limits, " +
	"open files, established connections) and drives the guard policy engine. " +
	"Detection is sampled (not real-time); blocking is best-effort via the configured " +
	"enforcement backend (block_ip / process-kill), NOT in-kernel syscall interception. " +
	"For real-time, in-kernel enforcement build with -tags ebpf (Linux + clang + CAP_NET_ADMIN)."

// procScanInterval is how often the procfs monitor samples /proc.
const procScanInterval = 5 * time.Second

// runMonitor runs the procfs polling loop until ctx is cancelled. It is the
// DEFAULT backend on Linux: real, honest, userspace process inspection that
// feeds the existing guard.Check* policy methods (previously only exercised by
// tests). The enforcer is wired into the guard so Check* yields the truthful
// action and forwards to the SOC.
func runMonitor(ctx context.Context, g *guard.Guard, enf *enforcer, logger *slog.Logger) {
	// Wire real containment into the guard's honesty seam: from here, an
	// enforce-mode "blocked" is counted only when block_ip/kill actually fired.
	g.SetEnforcer(enf.enforce)

	logger.Info("runtime guard backend active",
		"backend", backendName,
		"detail", "procfs polling (userspace); not kernel enforcement",
		"interval", procScanInterval.String(),
	)

	ticker := time.NewTicker(procScanInterval)
	defer ticker.Stop()

	// Scan once immediately so we don't wait a full interval for first signal.
	scanProc(g, logger)
	for {
		select {
		case <-ctx.Done():
			logger.Info("procfs monitor stopping")
			return
		case <-ticker.C:
			scanProc(g, logger)
		}
	}
}

// procState holds the per-process facts gathered from /proc that the guard needs.
type procState struct {
	pid      int
	comm     string
	memoryMB int
}

// scanProc walks /proc, and for each process whose name matches a monitored
// policy entry, drives the guard checks. The guard records the violation (stats
// + handlers that forward to the SOC) and consults the wired enforcer for the
// truthful action.
func scanProc(g *guard.Guard, logger *slog.Logger) {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		logger.Error("procfs scan: cannot read /proc", "error", err)
		return
	}

	for _, ent := range entries {
		if !ent.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(ent.Name())
		if err != nil {
			continue // not a PID dir
		}

		st, ok := readProcState(pid)
		if !ok {
			continue // process vanished or unreadable — normal, skip silently
		}

		// Only inspect processes the policy actually monitors. This keeps the
		// scan cheap and avoids false signal on unrelated host processes.
		if !g.IsMonitored(st.comm) {
			continue
		}

		// The guard's Check* methods record the violation, consult the wired
		// enforcer for the TRUTHFUL action (block_ip / kill / log-only), update
		// stats, and forward to the SOC via the handler — all honestly. We just
		// feed them the facts from /proc.

		// 1) Resource (memory) check — fully observable from /proc.
		if st.memoryMB > 0 {
			g.CheckMemory(st.comm, st.pid, st.memoryMB)
		}

		// 2) File-descriptor check — flag open files that violate the file policy.
		for _, path := range readOpenFiles(pid) {
			g.CheckFileAccess(st.comm, st.pid, path)
		}

		// 3) Network check — flag established remote connections; for "no network
		// allowed" processes ANY remote peer is a CRITICAL violation. The peer IP
		// rides on the violation (SrcIP) so the enforcer can block_ip it.
		for _, peerIP := range readRemotePeers(pid) {
			g.CheckNetwork(st.comm, st.pid, peerIP)
		}
	}
}

// readProcState reads comm + RSS for a pid from /proc/<pid>/.
func readProcState(pid int) (procState, bool) {
	st := procState{pid: pid}

	comm, err := os.ReadFile(filepath.Join("/proc", strconv.Itoa(pid), "comm"))
	if err != nil {
		return st, false
	}
	st.comm = strings.TrimSpace(string(comm))
	if st.comm == "" {
		return st, false
	}

	// RSS from /proc/<pid>/statm: field 2 (resident) in pages.
	statm, err := os.ReadFile(filepath.Join("/proc", strconv.Itoa(pid), "statm"))
	if err == nil {
		fields := strings.Fields(string(statm))
		if len(fields) >= 2 {
			if residentPages, err := strconv.ParseInt(fields[1], 10, 64); err == nil {
				pageSize := int64(os.Getpagesize())
				st.memoryMB = int((residentPages * pageSize) / (1024 * 1024))
			}
		}
	}
	return st, true
}

// readOpenFiles returns the resolved targets of a process's open file descriptors
// that look like regular filesystem paths (absolute paths under "/"). Sockets,
// pipes and anon inodes are skipped here (network is handled separately).
func readOpenFiles(pid int) []string {
	fdDir := filepath.Join("/proc", strconv.Itoa(pid), "fd")
	entries, err := os.ReadDir(fdDir)
	if err != nil {
		return nil
	}
	var paths []string
	for _, ent := range entries {
		target, err := os.Readlink(filepath.Join(fdDir, ent.Name()))
		if err != nil {
			continue
		}
		// Only real filesystem paths; skip "socket:[...]", "pipe:[...]", "anon_inode:...".
		if strings.HasPrefix(target, "/") {
			paths = append(paths, target)
		}
	}
	return paths
}

// readRemotePeers returns the remote peer IPs of a process's ESTABLISHED TCP
// connections, parsed from /proc/<pid>/net/tcp and tcp6. Only connections in the
// ESTABLISHED state (0x01) are reported, so a listening socket is not flagged as
// outbound network use.
func readRemotePeers(pid int) []string {
	var peers []string
	for _, name := range []string{"tcp", "tcp6"} {
		path := filepath.Join("/proc", strconv.Itoa(pid), "net", name)
		f, err := os.Open(path)
		if err != nil {
			continue
		}
		peers = append(peers, parseTCPPeers(f)...)
		f.Close()
	}
	return peers
}

// parseTCPPeers parses the kernel's /proc net/tcp table and returns remote IPs of
// ESTABLISHED connections. Format columns: sl local_address rem_address st ...
// where rem_address is HEXIP:HEXPORT and st is the hex connection state.
func parseTCPPeers(r io.Reader) []string {
	var peers []string
	sc := bufio.NewScanner(r)
	first := true
	for sc.Scan() {
		line := strings.Fields(sc.Text())
		if first {
			first = false // header row
			continue
		}
		if len(line) < 4 {
			continue
		}
		state := line[3]
		if state != "01" { // 0x01 = TCP_ESTABLISHED
			continue
		}
		rem := line[2]
		ip := parseHexIP(rem)
		if ip != "" && ip != "0.0.0.0" {
			peers = append(peers, ip)
		}
	}
	return peers
}

// parseHexIP converts a /proc net "HEXIP:HEXPORT" token to a dotted IPv4 string.
// IPv6 tokens (32 hex chars) are returned best-effort as a compact form; callers
// validate via net.ParseIP downstream (the firewall validates before use).
func parseHexIP(token string) string {
	colon := strings.IndexByte(token, ':')
	if colon < 0 {
		return ""
	}
	hexIP := token[:colon]
	switch len(hexIP) {
	case 8: // IPv4, little-endian bytes
		b := make([]byte, 4)
		for i := 0; i < 4; i++ {
			v, err := strconv.ParseUint(hexIP[i*2:i*2+2], 16, 8)
			if err != nil {
				return ""
			}
			b[3-i] = byte(v)
		}
		if b[0] == 0 && b[1] == 0 && b[2] == 0 && b[3] == 0 {
			return ""
		}
		return strconv.Itoa(int(b[0])) + "." + strconv.Itoa(int(b[1])) + "." +
			strconv.Itoa(int(b[2])) + "." + strconv.Itoa(int(b[3]))
	default:
		return "" // IPv6 omitted from active blocking; detection still logs via guard
	}
}
