"""
🏆 SENTINEL Fortress Leaderboard
Storage via HuggingFace Dataset or local JSON fallback
"""

import os
import json
from datetime import datetime
from typing import Optional

# Local storage path
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "leaderboard.json")


def load_leaderboard():
    """Load leaderboard from file."""
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_leaderboard(data):
    """Save leaderboard to file."""
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_entry(
    username: str,
    level_reached: int,
    total_attempts: int,
    techniques: list = None,
    lang: str = "en"
):
    """Add or update leaderboard entry."""
    leaderboard = load_leaderboard()
    
    # Find existing entry
    existing = next(
        (e for e in leaderboard if e["username"] == username), None
    )
    
    entry = {
        "username": username,
        "level_reached": level_reached,
        "total_attempts": total_attempts,
        "techniques": techniques or [],
        "timestamp": datetime.utcnow().isoformat(),
        "lang": lang,
    }
    
    if existing:
        # Update only if better result
        if level_reached > existing["level_reached"]:
            idx = leaderboard.index(existing)
            leaderboard[idx] = entry
    else:
        leaderboard.append(entry)
    
    # Sort by level (desc), then by attempts (asc)
    leaderboard.sort(
        key=lambda x: (-x["level_reached"], x["total_attempts"])
    )
    
    # Keep top 100
    leaderboard = leaderboard[:100]
    
    save_leaderboard(leaderboard)
    return entry


def get_top_players(limit: int = 10):
    """Get top N players from leaderboard."""
    leaderboard = load_leaderboard()
    return leaderboard[:limit]


def format_leaderboard_md(limit: int = 10, lang: str = "en"):
    """Format leaderboard as Markdown table."""
    titles = {
        "en": ("Rank", "Player", "Level", "Attempts"),
        "ru": ("Место", "Игрок", "Уровень", "Попыток"),
    }
    headers = titles.get(lang, titles["en"])
    
    top = get_top_players(limit)
    
    if not top:
        return "*No players yet. Be the first!*"
    
    lines = [
        f"| {headers[0]} | {headers[1]} | {headers[2]} | {headers[3]} |",
        "|---:|:---|:---:|---:|",
    ]
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, p in enumerate(top):
        rank = medals[i] if i < 3 else f"{i + 1}"
        lines.append(
            f"| {rank} | {p['username']} | {p['level_reached']}/10 "
            f"| {p['total_attempts']} |"
        )
    
    return "\n".join(lines)


def generate_anonymous_name():
    """Generate a fun anonymous username."""
    import random
    
    adjectives = [
        "Swift", "Clever", "Silent", "Bold", "Wise",
        "Mystic", "Shadow", "Cyber", "Ghost", "Stealth"
    ]
    nouns = [
        "Hacker", "Fox", "Ninja", "Wolf", "Phoenix",
        "Eagle", "Dragon", "Tiger", "Panther", "Hawk"
    ]
    
    return f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(1, 99)}"
