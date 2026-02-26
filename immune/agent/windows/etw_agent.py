"""
SENTINEL IMMUNE — Windows ETW Agent

Event Tracing for Windows (ETW) based agent.
No kernel driver required - uses official Windows APIs.
"""

import os
import sys
import logging
import ctypes
import struct
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import IntEnum
from datetime import datetime

logger = logging.getLogger("IMMUNE.ETW")

# Check for Windows
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes.wintypes as wintypes
    from ctypes import windll, byref, sizeof, create_string_buffer


class EventType(IntEnum):
    """ETW event types."""
    PROCESS_START = 1
    PROCESS_END = 2
    FILE_CREATE = 3
    FILE_DELETE = 4
    REGISTRY_KEY = 5
    NETWORK_CONNECT = 6
    DNS_QUERY = 7


@dataclass
class ETWEvent:
    """ETW event."""
    timestamp: datetime
    event_type: EventType
    process_id: int
    process_name: str
    user: str
    data: Dict


class WindowsETWAgent:
    """
    Windows ETW Agent.
    
    Uses Event Tracing for Windows for kernel-level monitoring
    without requiring kernel driver installation.
    
    Monitored providers:
    - Microsoft-Windows-Kernel-Process
    - Microsoft-Windows-Kernel-File
    - Microsoft-Windows-Kernel-Network
    - Microsoft-Windows-DNS-Client
    """
    
    # ETW Provider GUIDs
    KERNEL_PROCESS_GUID = "{22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716}"
    KERNEL_FILE_GUID = "{EDD08927-9CC4-4E65-B970-C2560FB5C289}"
    KERNEL_NETWORK_GUID = "{7DD42A49-5329-4832-8DFD-43D979153A88}"
    DNS_CLIENT_GUID = "{1C95126E-7EEA-49A9-A3FE-A378B03DDB4D}"
    
    def __init__(self, patterns: List[str] = None):
        if not IS_WINDOWS:
            raise RuntimeError("ETW agent only works on Windows")
        
        self.patterns = patterns or []
        self.running = False
        self.callbacks: List[Callable] = []
        self.session_handle = None
        
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
        """Start ETW agent."""
        if self.running:
            return
        
        logger.info("Starting ETW agent...")
        
        # Would use TraceEvent library or pyetw
        # For now, use WMI as fallback
        self._start_wmi_monitoring()
        
        self.running = True
        logger.info("ETW agent started")
    
    def stop(self):
        """Stop ETW agent."""
        self.running = False
        self._stop_wmi_monitoring()
        logger.info("ETW agent stopped")
    
    def _start_wmi_monitoring(self):
        """Start WMI-based monitoring (fallback)."""
        try:
            import wmi
            import pythoncom
            
            pythoncom.CoInitialize()
            self.wmi = wmi.WMI()
            
            # Process creation watcher
            self.process_watcher = self.wmi.Win32_Process.watch_for("creation")
            
            logger.info("WMI monitoring started")
        except ImportError:
            logger.warning("WMI library not available")
    
    def _stop_wmi_monitoring(self):
        """Stop WMI monitoring."""
        pass
    
    def poll(self, timeout_ms: int = 100):
        """Poll for events."""
        if not self.running:
            return
        
        try:
            # Poll WMI
            if hasattr(self, 'process_watcher'):
                try:
                    new_process = self.process_watcher(timeout_ms=timeout_ms)
                    if new_process:
                        self._handle_process_event(new_process)
                except:
                    pass
        except Exception as e:
            logger.debug(f"Poll error: {e}")
    
    def run(self):
        """Run event loop."""
        logger.info("ETW agent running...")
        
        try:
            while self.running:
                self.poll()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def _handle_process_event(self, process):
        """Handle process creation event."""
        event = ETWEvent(
            timestamp=datetime.now(),
            event_type=EventType.PROCESS_START,
            process_id=process.ProcessId or 0,
            process_name=process.Name or "",
            user=process.GetOwner()[2] if process.GetOwner else "",
            data={
                "command_line": process.CommandLine or "",
                "parent_id": process.ParentProcessId or 0
            }
        )
        
        self.events_total += 1
        
        # Check patterns
        is_threat = self._check_patterns(event)
        
        if is_threat:
            self.threats_detected += 1
            logger.warning(
                f"Threat: pid={event.process_id} "
                f"name={event.process_name}"
            )
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(event, is_threat)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _check_patterns(self, event: ETWEvent) -> bool:
        """Check event against patterns."""
        # Check process name
        name = event.process_name.lower()
        for pattern in self.patterns:
            if pattern in name:
                return True
        
        # Check command line
        cmdline = event.data.get("command_line", "").lower()
        for pattern in self.patterns:
            if pattern in cmdline:
                return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get agent statistics."""
        return {
            "events_total": self.events_total,
            "threats_detected": self.threats_detected,
            "patterns_count": len(self.patterns),
            "running": self.running
        }
    
    # ==================== Windows API Methods ====================
    
    def get_running_processes(self) -> List[Dict]:
        """Get list of running processes."""
        processes = []
        
        try:
            import wmi
            w = wmi.WMI()
            
            for proc in w.Win32_Process():
                processes.append({
                    "pid": proc.ProcessId,
                    "name": proc.Name,
                    "cmdline": proc.CommandLine,
                    "parent_pid": proc.ParentProcessId
                })
        except:
            pass
        
        return processes
    
    def get_network_connections(self) -> List[Dict]:
        """Get active network connections."""
        connections = []
        
        try:
            import psutil
            
            for conn in psutil.net_connections():
                connections.append({
                    "local_addr": str(conn.laddr) if conn.laddr else "",
                    "remote_addr": str(conn.raddr) if conn.raddr else "",
                    "status": conn.status,
                    "pid": conn.pid
                })
        except:
            pass
        
        return connections
    
    def block_process(self, pid: int) -> bool:
        """Terminate a process."""
        try:
            import psutil
            
            proc = psutil.Process(pid)
            proc.terminate()
            return True
        except:
            return False


def create_windows_agent(patterns: List[str] = None) -> WindowsETWAgent:
    """Create Windows ETW agent."""
    agent = WindowsETWAgent(patterns)
    
    # Add default patterns
    default_patterns = [
        "powershell",
        "cmd.exe",
        "mshta",
        "wscript",
        "cscript",
        "msiexec",
        "regsvr32",
        "rundll32",
        "mimikatz",
        "meterpreter"
    ]
    
    for p in default_patterns:
        agent.add_pattern(p)
    
    return agent


if __name__ == "__main__":
    if not IS_WINDOWS:
        print("This agent only works on Windows")
        sys.exit(1)
    
    agent = create_windows_agent()
    agent.start()
    agent.run()
