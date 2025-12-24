#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Session Manager

Checkpoint/resume functionality for long-running operations.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Session state."""
    id: str
    target: str
    started_at: str
    last_checkpoint: str = ""
    iteration: int = 0
    state: str = "running"
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, target: str) -> "Session":
        return cls(
            id=str(uuid.uuid4())[:8],
            target=target,
            started_at=datetime.now().isoformat(),
            last_checkpoint=datetime.now().isoformat(),
        )


class SessionManager:
    """
    Manages session persistence for checkpoint/resume.

    Features:
    - Auto-checkpoint at intervals
    - Resume from last checkpoint
    - Session history
    """

    def __init__(self, session_dir: str = "./sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[Session] = None

    def start(self, target: str) -> Session:
        """Start new session."""
        self.current_session = Session.create(target)
        self._save_session()

        logger.info(f"📁 Session started: {self.current_session.id}")
        return self.current_session

    def save(self, data: Dict[str, Any]) -> None:
        """Save checkpoint data."""
        if not self.current_session:
            return

        self.current_session.data = data
        self.current_session.iteration = data.get("iteration", 0)
        self.current_session.last_checkpoint = datetime.now().isoformat()

        self._save_session()
        logger.debug(
            f"💾 Checkpoint saved: iteration {self.current_session.iteration}")

    def _save_session(self) -> None:
        """Save session to disk."""
        if not self.current_session:
            return

        filepath = self.session_dir / f"session_{self.current_session.id}.json"

        with open(filepath, 'w') as f:
            json.dump(asdict(self.current_session), f, indent=2)

    def load(self, session_id: str) -> Optional[Session]:
        """Load session by ID."""
        filepath = self.session_dir / f"session_{session_id}.json"

        if not filepath.exists():
            logger.warning(f"Session not found: {session_id}")
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        self.current_session = Session(**data)
        logger.info(
            f"📂 Session loaded: {session_id}, iteration {self.current_session.iteration}")
        return self.current_session

    def list_sessions(self) -> list:
        """List all available sessions."""
        sessions = []

        for filepath in self.session_dir.glob("session_*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                sessions.append({
                    "id": data.get("id"),
                    "target": data.get("target"),
                    "started_at": data.get("started_at"),
                    "iteration": data.get("iteration", 0),
                    "state": data.get("state", "unknown"),
                })
            except:
                pass

        return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)

    def resume(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Resume session and return saved data."""
        session = self.load(session_id)
        if session:
            session.state = "running"
            self._save_session()
            return session.data
        return None

    def complete(self) -> None:
        """Mark session as completed."""
        if self.current_session:
            self.current_session.state = "completed"
            self._save_session()
            logger.info(f"✅ Session completed: {self.current_session.id}")

    def get_latest(self) -> Optional[str]:
        """Get ID of latest session."""
        sessions = self.list_sessions()
        if sessions:
            return sessions[0].get("id")
        return None
