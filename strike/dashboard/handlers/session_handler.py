"""
SENTINEL Strike Dashboard - Session Handler

Manages attack session lifecycle: start, stop, status.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# Import state - try both absolute and relative for flexibility
try:
    from strike.dashboard.state import state, file_logger
except ImportError:
    from ..state import state, file_logger

from .attack_config import AttackConfig


@dataclass
class AttackSession:
    """
    Represents a single attack session.
    """
    id: str
    config: AttackConfig
    started_at: datetime
    stopped_at: Optional[datetime] = None
    status: str = "running"  # running, stopped, completed, error
    thread: Optional[threading.Thread] = None
    results: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        end = self.stopped_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    @property
    def is_running(self) -> bool:
        """Check if session is running."""
        return self.status == "running"
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "target": self.config.target,
            "mode": self.config.mode.value,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "duration": self.duration_seconds,
            "result_count": len(self.results),
            "error": self.error,
        }


class SessionHandler:
    """
    Manages attack sessions.
    
    Handles starting, stopping, and tracking attack sessions.
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        self._sessions: Dict[str, AttackSession] = {}
        self._current_session: Optional[str] = None
        self._lock = threading.Lock()
        self._attack_func: Optional[Callable] = None
    
    def set_attack_function(self, func: Callable) -> None:
        """
        Set the attack execution function.
        
        Args:
            func: Function that executes attack (takes AttackConfig)
        """
        self._attack_func = func
    
    def start(self, config: AttackConfig) -> AttackSession:
        """
        Start a new attack session.
        
        Args:
            config: Attack configuration
            
        Returns:
            New AttackSession
            
        Raises:
            ValueError: If another session is running
        """
        with self._lock:
            if self._current_session and self._sessions[self._current_session].is_running:
                raise ValueError("Another attack is already running")
            
            # Generate session ID
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create session
            session = AttackSession(
                id=session_id,
                config=config,
                started_at=datetime.now(),
            )
            
            # Store session
            self._sessions[session_id] = session
            self._current_session = session_id
            
            # Update global state
            state.start_attack(config.target)
            
            # Start file logger
            file_logger.new_attack(config.target)
            
            # Start attack in background thread
            def run_attack():
                try:
                    if self._attack_func:
                        self._attack_func(config)
                    session.status = "completed"
                except Exception as e:
                    session.status = "error"
                    session.error = str(e)
                finally:
                    session.stopped_at = datetime.now()
                    state.stop_attack()
            
            thread = threading.Thread(target=run_attack, daemon=True)
            session.thread = thread
            thread.start()
            
            return session
    
    def stop(self) -> Optional[AttackSession]:
        """
        Stop current attack session.
        
        Returns:
            Stopped session or None if no session running
        """
        with self._lock:
            if not self._current_session:
                return None
            
            session = self._sessions[self._current_session]
            if not session.is_running:
                return session
            
            # Mark as stopped
            session.status = "stopped"
            session.stopped_at = datetime.now()
            
            # Update global state
            state.stop_attack()
            
            return session
    
    def get_current(self) -> Optional[AttackSession]:
        """Get current session."""
        if not self._current_session:
            return None
        return self._sessions.get(self._current_session)
    
    def get_session(self, session_id: str) -> Optional[AttackSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def list_sessions(self, limit: int = 10) -> List[AttackSession]:
        """Get recent sessions."""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.started_at,
            reverse=True
        )
        return sessions[:limit]
    
    def add_result(self, result: Dict) -> None:
        """Add result to current session."""
        with self._lock:
            if self._current_session:
                self._sessions[self._current_session].results.append(result)
            state.add_result(result)
    
    def is_running(self) -> bool:
        """Check if any attack is running."""
        return state.is_running()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        current = self.get_current()
        return {
            "running": self.is_running(),
            "session": current.to_dict() if current else None,
            "queue_size": state.attack_log.qsize(),
        }


# Global instance
session_handler = SessionHandler()
