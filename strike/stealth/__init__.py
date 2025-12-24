"""
SENTINEL Strike — Stealth Engine

Advanced stealth capabilities for complete invisibility:
- TLS fingerprint evasion (JA3/JA4)
- Browser impersonation
- Human-like timing
- Header ordering
- IP reputation management
- VPN rotation
- Proxy chains
"""

# Legacy modules
try:
    from .identity import IdentityManager
except ImportError:
    IdentityManager = None

try:
    from .timing import TimingEngine
except ImportError:
    TimingEngine = None

try:
    from .proxy import ProxyChain
except ImportError:
    ProxyChain = None

# Advanced stealth
from .advanced_stealth import (
    BrowserProfile,
    HumanTiming,
    RequestOrderer,
    TLSEvasion,
    BrowserStealth,
    IPReputation,
    StealthConfig,
    AdvancedStealthSession,
    USER_AGENTS,
    CLIENT_HINTS,
    BROWSER_HEADER_ORDER,
)

__all__ = [
    # Legacy
    "IdentityManager",
    "TimingEngine",
    "ProxyChain",
    # Advanced
    "BrowserProfile",
    "HumanTiming",
    "RequestOrderer",
    "TLSEvasion",
    "BrowserStealth",
    "IPReputation",
    "StealthConfig",
    "AdvancedStealthSession",
    "USER_AGENTS",
    "CLIENT_HINTS",
    "BROWSER_HEADER_ORDER",
]
