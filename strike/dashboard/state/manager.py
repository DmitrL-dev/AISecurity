"""
SENTINEL Strike Dashboard - State Manager

Centralized state management for attack console.
Replaces global variables with a proper state container.

Usage:
    from strike.dashboard.state import state
    
    state.start_attack()
    state.add_result({...})
    state.stop_attack()
"""

import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StateManager:
    """
    Centralized state management for Strike Dashboard.
    
    Thread-safe container for attack state instead of global variables.
    
    Attributes:
        attack_log: Queue for streaming attack events
        attack_running: Whether an attack is currently running
        attack_results: List of attack results
    """
    
    attack_log: queue.Queue = field(default_factory=queue.Queue)
    attack_running: bool = False
    attack_results: List[Dict] = field(default_factory=list)
    current_target: str = ""
    
    # Thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def start_attack(self, target: str = "") -> None:
        """
        Mark attack as started.
        
        Args:
            target: Target URL
        """
        with self._lock:
            self.attack_running = True
            self.current_target = target
            self.attack_results = []
            # Clear queue
            while not self.attack_log.empty():
                try:
                    self.attack_log.get_nowait()
                except queue.Empty:
                    break
    
    def stop_attack(self) -> None:
        """Mark attack as stopped."""
        with self._lock:
            self.attack_running = False
    
    def is_running(self) -> bool:
        """Check if attack is running."""
        return self.attack_running
    
    def add_result(self, result: Dict) -> None:
        """
        Add result to attack results.
        
        Args:
            result: Result dictionary
        """
        with self._lock:
            self.attack_results.append(result)
    
    def get_results(self) -> List[Dict]:
        """Get all attack results."""
        return self.attack_results.copy()
    
    def log_event(self, event: str) -> None:
        """
        Add event to attack log queue (for SSE streaming).
        
        Args:
            event: Event string
        """
        self.attack_log.put(event)
    
    def get_event(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get next event from log queue.
        
        Args:
            timeout: Seconds to wait for event
            
        Returns:
            Event string or None if timeout
        """
        try:
            return self.attack_log.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get state summary.
        
        Returns:
            Dictionary with current state info
        """
        return {
            "running": self.attack_running,
            "target": self.current_target,
            "result_count": len(self.attack_results),
            "queue_size": self.attack_log.qsize(),
        }


# Global instance
state = StateManager()

# Backwards compatibility exports
attack_log = state.attack_log
attack_running = property(lambda: state.attack_running)
attack_results = state.attack_results
