"""
SENTINEL Strike — Dashboard Server

Simple HTTP server for the Strike dashboard.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path
from typing import Optional


def get_dashboard_dir() -> Path:
    """Get dashboard directory path."""
    return Path(__file__).parent.parent.parent.parent / "dashboard"


def run_dashboard(
    port: int = 8888,
    open_browser: bool = True,
) -> None:
    """Run the dashboard HTTP server."""
    dashboard_dir = get_dashboard_dir()

    if not (dashboard_dir / "index.html").exists():
        raise FileNotFoundError(f"Dashboard not found at {dashboard_dir}")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def log_message(self, format, *args):
            # Suppress logging
            pass

    with socketserver.TCPServer(("", port), Handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"🎯 SENTINEL Strike Dashboard running at {url}")
        print("Press Ctrl+C to stop")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped")
