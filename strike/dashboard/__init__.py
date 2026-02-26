"""
SENTINEL Strike Dashboard

Web-based attack console for penetration testing.

Refactored from monolithic strike_console.py (174KB) into modular packages:
- state/    : State management (logger, cache, manager)
- handlers/ : Attack handlers (session, hydra, config)
- ui/       : UI components (themes, formatters)
- reports/  : Report generation (templates, generator)
"""

# Re-export key components for backwards compatibility
from .state import (
    AttackLogger,
    file_logger,
    ReconCache,
    recon_cache,
    StateManager,
    state,
)

from .handlers import (
    AttackConfig,
    AttackMode,
    SessionHandler,
    HydraConfig,
    HydraHandler,
    hydra_handler,
)

from .ui import (
    Theme,
    THEMES,
    get_theme,
    format_log_entry,
    format_finding,
    format_stats,
)

from .reports import (
    ReportGenerator,
    generate_report,
    report_template,
    finding_template,
)

__all__ = [
    # State
    "AttackLogger",
    "file_logger",
    "ReconCache",
    "recon_cache",
    "StateManager",
    "state",
    # Handlers
    "AttackConfig",
    "AttackMode",
    "SessionHandler",
    "HydraConfig",
    "HydraHandler",
    "hydra_handler",
    # UI
    "Theme",
    "THEMES",
    "get_theme",
    "format_log_entry",
    "format_finding",
    "format_stats",
    # Reports
    "ReportGenerator",
    "generate_report",
    "report_template",
    "finding_template",
]
