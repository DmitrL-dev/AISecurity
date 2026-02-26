"""
SENTINEL Strike Dashboard - Attack Logger

Logs attack events to JSONL files for history and analysis.

Usage:
    from strike.dashboard.state import file_logger
    
    file_logger.new_attack("https://target.com")
    file_logger.log({"type": "request", "payload": "..."})
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Log directory path
LOG_DIR = Path(__file__).parent.parent.parent / "logs"


class AttackLogger:
    """
    Log attack events to JSONL files for history and analysis.
    
    Features:
    - Creates timestamped log files per attack session
    - JSONL format for easy streaming and analysis
    - Automatic stats tracking
    
    Example:
        logger = AttackLogger()
        logger.new_attack("https://example.com")
        logger.log({"type": "request", "url": "/api/users"})
        stats = logger.get_stats()
    """

    def __init__(self, log_dir: Optional[Path] = None, enabled: bool = True):
        """
        Initialize the attack logger.
        
        Args:
            log_dir: Directory for log files. Defaults to strike/logs/
            enabled: Whether logging is enabled
        """
        self.enabled = enabled
        self.log_dir = log_dir or LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._create_new_file()

    def _create_new_file(self) -> None:
        """Create a new log file with current timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"attack_{timestamp}.jsonl"

    def new_attack(self, target: str = "") -> str:
        """
        Create new log file for new attack. Call at attack start.
        
        Args:
            target: Target URL being attacked
            
        Returns:
            Name of the created log file
        """
        self._create_new_file()
        # Log attack info as first entry
        self.log({
            "type": "attack_start",
            "target": target,
            "message": f"New attack started: {target}",
        })
        return self.log_file.name

    def log(self, event: Dict) -> None:
        """
        Append event to JSONL log file.
        
        Args:
            event: Dictionary with event data. Will have timestamp added.
        """
        if not self.enabled:
            return
        try:
            event["timestamp"] = datetime.now().isoformat()
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Silent fail for logging

    def get_stats(self) -> Dict:
        """
        Get current attack stats from log file.
        
        Returns:
            Dictionary with counts: requests, blocked, bypasses, findings
        """
        stats = {"requests": 0, "blocked": 0, "bypasses": 0, "findings": 0}
        if not self.log_file.exists():
            return stats
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    if event_type == "request":
                        stats["requests"] += 1
                    elif event_type == "blocked":
                        stats["blocked"] += 1
                    elif event_type == "bypass":
                        stats["bypasses"] += 1
                    elif event_type == "finding":
                        stats["findings"] += 1
        except Exception:
            pass
        return stats

    def get_events(self, event_type: Optional[str] = None) -> list:
        """
        Get all events from current log file.
        
        Args:
            event_type: Optional filter by event type
            
        Returns:
            List of event dictionaries
        """
        events = []
        if not self.log_file.exists():
            return events
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    event = json.loads(line)
                    if event_type is None or event.get("type") == event_type:
                        events.append(event)
        except Exception:
            pass
        return events


# Global instance
file_logger = AttackLogger()
