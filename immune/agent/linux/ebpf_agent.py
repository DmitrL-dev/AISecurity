"""
SENTINEL IMMUNE — Linux eBPF Agent

eBPF-based agent for Linux kernel monitoring.
No kernel module required - runs in user space!
"""

import os
import sys
import logging
import ctypes
import struct
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger("IMMUNE.eBPF")

# Check for BCC library
try:
    from bcc import BPF, PerfType, PerfHWConfig
    BCC_AVAILABLE = True
except ImportError:
    BCC_AVAILABLE = False
    logger.warning("BCC not available, eBPF agent disabled")


class SyscallType(IntEnum):
    """Syscall types we monitor."""
    READ = 0
    WRITE = 1
    OPEN = 2
    EXECVE = 59
    CONNECT = 42
    SOCKET = 41


@dataclass
class SyscallEvent:
    """Syscall event from eBPF."""
    pid: int
    tid: int
    uid: int
    comm: str
    syscall: int
    retval: int
    timestamp: int
    data: bytes


# eBPF program for syscall tracing
EBPF_PROGRAM = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct event_t {
    u32 pid;
    u32 tid;
    u32 uid;
    char comm[16];
    u32 syscall;
    s64 retval;
    u64 ts;
    char data[256];
};

BPF_PERF_OUTPUT(events);
BPF_HASH(active, u64, struct event_t);

// Common function to submit event
static inline void submit_event(struct pt_regs *ctx, u32 syscall_nr) {
    struct event_t event = {};
    u64 id = bpf_get_current_pid_tgid();
    
    event.pid = id >> 32;
    event.tid = id;
    event.uid = bpf_get_current_uid_gid();
    event.syscall = syscall_nr;
    event.ts = bpf_ktime_get_ns();
    
    bpf_get_current_comm(&event.comm, sizeof(event.comm));
    
    events.perf_submit(ctx, &event, sizeof(event));
}

// Trace execve
TRACEPOINT_PROBE(syscalls, sys_enter_execve) {
    submit_event((struct pt_regs *)args, 59);
    return 0;
}

// Trace read
TRACEPOINT_PROBE(syscalls, sys_enter_read) {
    submit_event((struct pt_regs *)args, 0);
    return 0;
}

// Trace write
TRACEPOINT_PROBE(syscalls, sys_enter_write) {
    submit_event((struct pt_regs *)args, 1);
    return 0;
}

// Trace connect
TRACEPOINT_PROBE(syscalls, sys_enter_connect) {
    submit_event((struct pt_regs *)args, 42);
    return 0;
}

// Trace open
TRACEPOINT_PROBE(syscalls, sys_enter_openat) {
    submit_event((struct pt_regs *)args, 2);
    return 0;
}
"""


class LinuxeBPFAgent:
    """
    Linux eBPF Agent.
    
    Uses eBPF for kernel-level monitoring without
    requiring custom kernel modules.
    
    Advantages over kmod:
    - No kernel compilation
    - Safe (verified by kernel)
    - Easy deployment
    - Works on any modern Linux
    """
    
    def __init__(self, patterns: List[str] = None):
        if not BCC_AVAILABLE:
            raise RuntimeError("BCC library required for eBPF agent")
        
        self.patterns = patterns or []
        self.bpf: Optional[BPF] = None
        self.running = False
        self.callbacks: List[Callable] = []
        
        # Stats
        self.events_total = 0
        self.threats_detected = 0
    
    def add_pattern(self, pattern: str):
        """Add detection pattern."""
        self.patterns.append(pattern.lower())
    
    def add_callback(self, callback: Callable):
        """Add event callback."""
        self.callbacks.append(callback)
    
    def start(self):
        """Start eBPF agent."""
        if self.running:
            return
        
        logger.info("Starting eBPF agent...")
        
        # Compile eBPF program
        self.bpf = BPF(text=EBPF_PROGRAM)
        
        # Setup perf buffer
        self.bpf["events"].open_perf_buffer(self._handle_event)
        
        self.running = True
        logger.info("eBPF agent started")
    
    def stop(self):
        """Stop eBPF agent."""
        self.running = False
        if self.bpf:
            self.bpf.cleanup()
            self.bpf = None
        logger.info("eBPF agent stopped")
    
    def poll(self, timeout_ms: int = 100):
        """Poll for events."""
        if self.bpf:
            self.bpf.perf_buffer_poll(timeout=timeout_ms)
    
    def run(self):
        """Run event loop."""
        logger.info("eBPF agent running...")
        
        try:
            while self.running:
                self.poll()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def _handle_event(self, cpu, data, size):
        """Handle eBPF event."""
        # Parse event
        event = self.bpf["events"].event(data)
        
        syscall_event = SyscallEvent(
            pid=event.pid,
            tid=event.tid,
            uid=event.uid,
            comm=event.comm.decode('utf-8', errors='replace'),
            syscall=event.syscall,
            retval=event.retval,
            timestamp=event.ts,
            data=bytes(event.data)
        )
        
        self.events_total += 1
        
        # Check patterns
        is_threat = self._check_patterns(syscall_event)
        
        if is_threat:
            self.threats_detected += 1
            logger.warning(
                f"Threat: pid={syscall_event.pid} "
                f"comm={syscall_event.comm} "
                f"syscall={syscall_event.syscall}"
            )
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(syscall_event, is_threat)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _check_patterns(self, event: SyscallEvent) -> bool:
        """Check event against patterns."""
        # Check command name
        comm = event.comm.lower()
        for pattern in self.patterns:
            if pattern in comm:
                return True
        
        # Check data
        try:
            data = event.data.decode('utf-8', errors='ignore').lower()
            for pattern in self.patterns:
                if pattern in data:
                    return True
        except:
            pass
        
        return False
    
    def get_stats(self) -> Dict:
        """Get agent statistics."""
        return {
            "events_total": self.events_total,
            "threats_detected": self.threats_detected,
            "patterns_count": len(self.patterns),
            "running": self.running
        }


def create_linux_agent(patterns: List[str] = None) -> LinuxeBPFAgent:
    """Create Linux eBPF agent."""
    agent = LinuxeBPFAgent(patterns)
    
    # Add default patterns
    default_patterns = [
        "ignore all previous",
        "jailbreak",
        "system prompt",
        "bypass",
        "meterpreter",
        "reverse_tcp"
    ]
    
    for p in default_patterns:
        agent.add_pattern(p)
    
    return agent


if __name__ == "__main__":
    # Test run
    if os.geteuid() != 0:
        print("Must run as root for eBPF")
        sys.exit(1)
    
    agent = create_linux_agent()
    agent.start()
    agent.run()
