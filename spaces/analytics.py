"""
📊 SENTINEL Fortress Analytics
Track attack techniques and session data
"""

import os
import json
from datetime import datetime

ANALYTICS_FILE = os.path.join(os.path.dirname(__file__), "analytics.json")

# Attack technique patterns
TECHNIQUE_PATTERNS = {
    "roleplay": [
        "представь", "imagine", "pretend", "you are", "ты теперь",
        "act as", "role", "игра", "сценарий"
    ],
    "encoding": [
        "base64", "hex", "rot13", "binary", "morse", "unicode",
        "encode", "decode", "зашифруй", "закодируй"
    ],
    "authority": [
        "admin", "root", "sudo", "developer", "CEO", "boss",
        "админ", "разработчик", "начальник", "директор"
    ],
    "context_switch": [
        "forget", "ignore", "новая тема", "забудь",
        "previous", "change", "переключи", "другая тема"
    ],
    "social_engineering": [
        "please", "пожалуйста", "urgent", "срочно", "emergency",
        "help", "помоги", "важно", "important"
    ],
    "indirect": [
        "hint", "подсказка", "first letter", "первая буква",
        "starts with", "begins", "rhymes", "рифмуется"
    ],
    "jailbreak": [
        "DAN", "jailbreak", "bypass", "ignore instructions",
        "system prompt", "developer mode"
    ],
    "translation": [
        "translate", "переведи", "spanish", "french", "german",
        "chinese", "japanese", "на английском", "на испанском"
    ],
}


def detect_techniques(message: str) -> list:
    """Detect attack techniques used in a message."""
    detected = []
    msg_lower = message.lower()
    for technique, patterns in TECHNIQUE_PATTERNS.items():
        if any(p in msg_lower for p in patterns):
            detected.append(technique)
    return detected


def load_analytics():
    """Load analytics data from file."""
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": [], "technique_stats": {}}


def save_analytics(data):
    """Save analytics data to file."""
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def start_session(session_id: str, lang: str = "en"):
    """Start a new analytics session."""
    analytics = load_analytics()
    session = {
        "id": session_id,
        "started": datetime.utcnow().isoformat(),
        "lang": lang,
        "attempts": [],
        "levels_completed": [],
        "techniques_used": [],
    }
    analytics["sessions"].append(session)
    save_analytics(analytics)
    return session_id


def log_attempt(session_id: str, level: int, message: str, success: bool):
    """Log an attempt and detect techniques used."""
    analytics = load_analytics()
    techniques = detect_techniques(message)
    session = next(
        (s for s in analytics["sessions"] if s["id"] == session_id), None
    )
    if session:
        session["attempts"].append({
            "level": level,
            "techniques": techniques,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        })
        session["techniques_used"].extend(techniques)
        session["techniques_used"] = list(set(session["techniques_used"]))
        if success and level not in session["levels_completed"]:
            session["levels_completed"].append(level)
        # Update global technique stats
        for t in techniques:
            analytics["technique_stats"][t] = (
                analytics["technique_stats"].get(t, 0) + 1
            )
        save_analytics(analytics)
    return techniques


def get_technique_stats():
    """Get global technique usage statistics."""
    analytics = load_analytics()
    return analytics.get("technique_stats", {})


def format_stats_md():
    """Format technique stats as Markdown."""
    stats = get_technique_stats()
    if not stats:
        return "*No data yet*"
    sorted_stats = sorted(stats.items(), key=lambda x: -x[1])
    lines = ["| Technique | Count |", "|:---|---:|"]
    for technique, count in sorted_stats[:10]:
        lines.append(f"| {technique} | {count} |")
    return "\n".join(lines)
