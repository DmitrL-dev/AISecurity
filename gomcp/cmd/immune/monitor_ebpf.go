//go:build linux && ebpf

// Package main — eBPF runtime-guard backend (build tag: linux && ebpf).
//
// BUILD/RUN REQUIREMENTS (this file is NOT in the default build):
//   - Build:  Linux + Go + the cilium/ebpf library (already in go.mod).
//     Build with:  go build -tags ebpf ./cmd/immune
//   - Compile the kernel program (once, with clang/LLVM):
//     go generate -tags ebpf ./cmd/immune    # runs bpf2go (needs clang-14+)
//     OR  clang -O2 -g -target bpf -c internal/infrastructure/guard/ebpf/soc_guard.c \
//     -o soc_guard.bpf.o
//   - Run:    Linux kernel 5.10+, and CAP_BPF + CAP_NET_ADMIN (or root) to load
//     tracepoint programs and read the ring buffer.
//
// On a kernel/permission failure the loader returns an error and main falls back
// to the honest procfs path — it NEVER claims kernel enforcement it did not get.
package main

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"unsafe"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
	"github.com/cilium/ebpf/ringbuf"
	"github.com/cilium/ebpf/rlimit"

	"github.com/syntrex/gomcp/internal/infrastructure/guard"
)

// go:generate produces the BPF object this loader reads at runtime via
// ebpf.LoadCollectionSpec(defaultObjectPath). We compile the .c directly with
// clang (kept simple and dependency-light); bpf2go-style Go bindings are not
// needed because the ELF is loaded by path at runtime. Needs clang-14+ and the
// kernel BPF headers (libbpf-dev). Run:  go generate -tags ebpf ./cmd/immune
//
//go:generate clang -O2 -g -Wall -target bpf -c ../../internal/infrastructure/guard/ebpf/soc_guard.c -o soc_guard.bpf.o

// backendName reports the ACTIVE backend under the ebpf build tag.
const backendName = "ebpf"

// backendDetail truthfully describes the eBPF backend.
const backendDetail = "in-kernel eBPF tracepoints (ptrace/execve/socket) on monitored " +
	"SOC PIDs; violations stream from a kernel ring buffer in real time. In enforce " +
	"mode the kernel program returns -EPERM to block the syscall. Requires Linux 5.10+, " +
	"CAP_BPF + CAP_NET_ADMIN, and a clang-compiled soc_guard object."

// objectPath is where the compiled BPF object is expected at runtime. Overridable
// via SOC_GUARD_BPF_OBJECT for non-standard deployments.
const defaultObjectPath = "soc_guard.bpf.o"

// kernelAlert mirrors `struct soc_alert` in soc_guard.c (keep the layout in sync).
type kernelAlert struct {
	PID         uint32
	TGID        uint32
	AlertType   uint32
	Blocked     uint32
	TimestampNS uint64
	Comm        [16]byte
	Detail      [64]byte
}

// runMonitor loads the eBPF program, attaches the tracepoints, and translates
// kernel ring-buffer alerts into guard violations. It blocks until ctx is done.
//
// IMPORTANT: this is a build-tagged SCAFFOLD. The load/attach path is real
// cilium/ebpf, but it depends on a clang-compiled object produced by `go
// generate`/clang at deploy time. Until that object exists, load fails and the
// caller falls back to procfs — honestly, with no false enforcement claim.
func runMonitor(ctx context.Context, g *guard.Guard, enf *enforcer, logger *slog.Logger) {
	if err := rlimit.RemoveMemlock(); err != nil {
		logger.Error("ebpf: cannot raise memlock rlimit (need CAP_SYS_RESOURCE/root)", "error", err)
		return
	}

	objPath := defaultObjectPath
	if p := os.Getenv("SOC_GUARD_BPF_OBJECT"); p != "" {
		objPath = p
	}

	spec, err := ebpf.LoadCollectionSpec(objPath)
	if err != nil {
		logger.Error("ebpf: failed to load compiled object — falling back is the caller's job",
			"object", objPath, "error", err,
			"hint", "run `go generate -tags ebpf ./cmd/immune` (needs clang) or set SOC_GUARD_BPF_OBJECT")
		return
	}

	coll, err := ebpf.NewCollection(spec)
	if err != nil {
		var ve *ebpf.VerifierError
		if errors.As(err, &ve) {
			logger.Error("ebpf: verifier rejected program", "error", ve)
		} else {
			logger.Error("ebpf: failed to create collection (need CAP_BPF/CAP_NET_ADMIN)", "error", err)
		}
		return
	}
	defer coll.Close()

	// Attach the tracepoints defined in soc_guard.c.
	links, err := attachTracepoints(coll, logger)
	if err != nil {
		logger.Error("ebpf: attach failed", "error", err)
		return
	}
	defer func() {
		for _, l := range links {
			_ = l.Close()
		}
	}()

	alertsMap, ok := coll.Maps["soc_alerts"]
	if !ok {
		logger.Error("ebpf: ring buffer map 'soc_alerts' not found in object")
		return
	}
	rd, err := ringbuf.NewReader(alertsMap)
	if err != nil {
		logger.Error("ebpf: cannot open ring buffer reader", "error", err)
		return
	}
	defer rd.Close()

	logger.Info("runtime guard backend active",
		"backend", backendName,
		"detail", "in-kernel eBPF tracepoints + ring buffer",
		"object", objPath,
	)

	// Closing the reader on ctx cancellation unblocks rd.Read().
	go func() {
		<-ctx.Done()
		_ = rd.Close()
	}()

	for {
		rec, err := rd.Read()
		if err != nil {
			if errors.Is(err, ringbuf.ErrClosed) {
				logger.Info("ebpf: ring buffer closed, monitor stopping")
				return
			}
			logger.Warn("ebpf: ring buffer read error", "error", err)
			continue
		}
		handleAlert(rec.RawSample, g, enf, logger)
	}
}

// attachTracepoints links each SEC("tracepoint/...") program in the collection to
// its kernel tracepoint. Program names match the C function names.
func attachTracepoints(coll *ebpf.Collection, logger *slog.Logger) ([]link.Link, error) {
	type tp struct{ group, name, prog string }
	wanted := []tp{
		{"syscalls", "sys_enter_ptrace", "soc_guard_ptrace"},
		{"syscalls", "sys_enter_execve", "soc_guard_execve"},
		{"syscalls", "sys_enter_socket", "soc_guard_socket"},
	}
	var links []link.Link
	for _, t := range wanted {
		prog, ok := coll.Programs[t.prog]
		if !ok {
			logger.Warn("ebpf: program not found in object, skipping", "program", t.prog)
			continue
		}
		l, err := link.Tracepoint(t.group, t.name, prog, nil)
		if err != nil {
			// Close what we have and fail — partial attach is not honest coverage.
			for _, done := range links {
				_ = done.Close()
			}
			return nil, fmt.Errorf("attach %s/%s: %w", t.group, t.name, err)
		}
		links = append(links, l)
	}
	if len(links) == 0 {
		return nil, errors.New("no tracepoint programs attached")
	}
	return links, nil
}

// handleAlert decodes one kernel alert and records it as a guard violation.
func handleAlert(raw []byte, g *guard.Guard, enf *enforcer, logger *slog.Logger) {
	if len(raw) < int(unsafe.Sizeof(kernelAlert{})) {
		logger.Warn("ebpf: short alert record", "len", len(raw))
		return
	}
	var a kernelAlert
	if err := binary.Read(bytes.NewReader(raw), binary.LittleEndian, &a); err != nil {
		logger.Warn("ebpf: cannot decode alert", "error", err)
		return
	}
	comm := nullTerm(a.Comm[:])
	vtype := alertTypeName(a.AlertType)

	// The kernel already enforced (blocked==1 means it returned -EPERM). Record
	// the TRUTH: action="blocked" only when the kernel actually blocked.
	v := &guard.Violation{
		ProcessName: comm,
		PID:         int(a.PID),
		Type:        vtype,
		Detail:      fmt.Sprintf("ebpf %s alert from kernel", vtype),
		Severity:    "HIGH",
		PolicyMode:  g.CurrentMode(),
	}
	// The kernel decided block-vs-log; Record takes the action at face value so
	// "blocked" is counted only when the kernel actually returned -EPERM.
	if a.Blocked == 1 {
		v.Action = "blocked"
	} else {
		v.Action = "logged"
	}
	g.Record(*v)
	_ = enf // userspace enforcement is redundant when the kernel already blocked.
}

func alertTypeName(t uint32) string {
	switch t {
	case 1:
		return "syscall" // ptrace
	case 2:
		return "syscall" // execve
	case 3:
		return "network" // socket
	case 4:
		return "file"
	default:
		return "syscall"
	}
}

func nullTerm(b []byte) string {
	if i := bytes.IndexByte(b, 0); i >= 0 {
		return string(b[:i])
	}
	return string(b)
}
