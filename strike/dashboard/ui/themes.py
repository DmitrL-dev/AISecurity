"""
SENTINEL Strike Dashboard - Theme Configuration

Color schemes and styling constants for the dashboard.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Theme:
    """
    Dashboard color theme.
    
    Contains all color definitions for a theme.
    """
    name: str
    
    # Background colors
    bg_primary: str = "#0d1117"
    bg_secondary: str = "#161b22"
    bg_panel: str = "rgba(22, 27, 34, 0.9)"
    
    # Border colors
    border_primary: str = "#30363d"
    border_active: str = "#58a6ff"
    
    # Text colors
    text_primary: str = "#c9d1d9"
    text_secondary: str = "#8b949e"
    text_muted: str = "#6e7681"
    
    # Accent colors
    accent_blue: str = "#58a6ff"
    accent_green: str = "#3fb950"
    accent_yellow: str = "#d29922"
    accent_red: str = "#f85149"
    accent_purple: str = "#a371f7"
    accent_cyan: str = "#00d4ff"
    
    # Attack-specific colors
    color_attack: str = "#ff6b6b"
    color_bypass: str = "#a371f7"
    color_stealth: str = "#00d4ff"
    color_finding: str = "#f85149"
    
    # Gradient definitions
    gradient_header: str = "linear-gradient(90deg, #ff6b6b, #00d4ff)"
    gradient_attack: str = "linear-gradient(90deg, #ff6b6b, #ee5a5a)"
    gradient_success: str = "linear-gradient(90deg, #238636, #2ea043)"
    gradient_llm: str = "linear-gradient(90deg, #8957e5, #a371f7)"
    gradient_hybrid: str = "linear-gradient(90deg, #d29922, #e3b341)"
    
    def to_css_vars(self) -> str:
        """Generate CSS custom properties."""
        return f"""
        :root {{
            --bg-primary: {self.bg_primary};
            --bg-secondary: {self.bg_secondary};
            --bg-panel: {self.bg_panel};
            --border-primary: {self.border_primary};
            --border-active: {self.border_active};
            --text-primary: {self.text_primary};
            --text-secondary: {self.text_secondary};
            --accent-blue: {self.accent_blue};
            --accent-green: {self.accent_green};
            --accent-yellow: {self.accent_yellow};
            --accent-red: {self.accent_red};
            --accent-purple: {self.accent_purple};
            --accent-cyan: {self.accent_cyan};
            --color-attack: {self.color_attack};
            --color-bypass: {self.color_bypass};
            --color-stealth: {self.color_stealth};
        }}
        """


# Predefined themes
THEMES: Dict[str, Theme] = {
    "dark": Theme(
        name="dark",
    ),
    "hacker": Theme(
        name="hacker",
        bg_primary="#000000",
        bg_secondary="#0a0a0a",
        accent_green="#00ff00",
        text_primary="#00ff00",
        text_secondary="#008800",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        bg_primary="#0a0015",
        bg_secondary="#120020",
        accent_cyan="#00ffff",
        accent_purple="#ff00ff",
        gradient_header="linear-gradient(90deg, #ff00ff, #00ffff)",
    ),
}


def get_theme(name: str = "dark") -> Theme:
    """
    Get theme by name.
    
    Args:
        name: Theme name (dark, hacker, cyberpunk)
        
    Returns:
        Theme instance
    """
    return THEMES.get(name, THEMES["dark"])


# Log type to CSS class mapping
LOG_CLASSES = {
    "info": "log-info",
    "success": "log-success",
    "warning": "log-warning",
    "error": "log-error",
    "attack": "log-attack",
    "bypass": "log-bypass",
    "stealth": "log-stealth",
    "finding": "log-error",
    "blocked": "log-warning",
}


# Severity to CSS class mapping
SEVERITY_CLASSES = {
    "critical": "finding critical",
    "high": "finding high",
    "medium": "finding medium",
    "low": "finding low",
    "info": "finding info",
}
