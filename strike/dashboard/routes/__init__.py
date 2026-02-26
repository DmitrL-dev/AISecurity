#!/usr/bin/env python3
"""
SENTINEL Strike — Routes Package

Blueprint registration for modular Flask routes.
"""

from .attack import attack_bp, init_attack_routes, set_attack_running, is_attack_running
from .report import report_bp

__all__ = [
    'attack_bp',
    'report_bp',
    'init_attack_routes',
    'set_attack_running',
    'is_attack_running',
]


def register_blueprints(app, attack_log=None, file_logger=None, run_attack_thread=None):
    """Register all blueprints with the Flask app."""
    # Initialize attack routes with shared state
    if attack_log and file_logger and run_attack_thread:
        init_attack_routes(attack_log, file_logger, run_attack_thread)

    # Register blueprints
    app.register_blueprint(attack_bp)
    app.register_blueprint(report_bp)

    return app
