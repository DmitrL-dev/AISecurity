#!/usr/bin/env python3
"""
SENTINEL Strike — File Logger

Extracted from strike_console.py for modularity.
Logs attack events to JSONL files for analysis and reporting.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


# Default log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"


class FileLogger:
    """Logs attack events to JSONL file for analysis."""

    def __init__(self, log_dir: Path = LOG_DIR, enabled: bool = True):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self.log_file: Optional[Path] = None
        self._create_new_file()

    def _create_new_file(self):
        """Create a new log file with current timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f"attack_{timestamp}.jsonl"

    def new_attack(self, target: str = "") -> str:
        """Create new log file for new attack. Call at attack start."""
        self._create_new_file()
        # Log attack info as first entry
        self.log({
            'type': 'attack_start',
            'target': target,
            'message': f'New attack started: {target}'
        })
        return self.log_file.name if self.log_file else ""

    def log(self, event: Dict):
        """Append event to JSONL log file."""
        if not self.enabled or not self.log_file:
            return
        try:
            event['timestamp'] = datetime.now().isoformat()
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def get_stats(self) -> Dict:
        """Get current attack stats from log file."""
        stats = {'requests': 0, 'blocked': 0, 'bypasses': 0, 'findings': 0}
        if not self.log_file or not self.log_file.exists():
            return stats
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    event = json.loads(line)
                    event_type = event.get('type', '')
                    if event_type == 'request':
                        stats['requests'] += 1
                    elif event_type == 'blocked':
                        stats['blocked'] += 1
                    elif event_type == 'bypass':
                        stats['bypasses'] += 1
                    elif event_type == 'finding':
                        stats['findings'] += 1
        except Exception:
            pass
        return stats

    def get_log_file(self) -> Optional[Path]:
        """Get current log file path."""
        return self.log_file
