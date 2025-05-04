"""
Simplified web dashboard for the crypto trading bot.
"""

import threading
import time
from typing import Dict, Any, List, Optional

from flask import Flask, render_template, jsonify, request, redirect, url_for, Response

from src.config import config
from loguru import logger


class Dashboard:
    """Web dashboard for the crypto trading bot."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize the dashboard.

        Args:
            host: The host to bind to. If None, uses the default.
            port: The port to bind to. If None, uses the default.
        """
        self.host = host or "0.0.0.0"
        self.port = port or 5000
        self.app = Flask(__name__, template_folder="../dashboard/templates", static_folder="../dashboard/static")
        self.thread = None
        self.running = False

        # Set up authentication if username and password are provided
        self.auth_enabled = False
        if hasattr(config, 'DASHBOARD_USERNAME') and hasattr(config, 'DASHBOARD_PASSWORD'):
            if config.DASHBOARD_USERNAME and config.DASHBOARD_PASSWORD:
                self.auth_enabled = True
                self.username = config.DASHBOARD_USERNAME
                self.password = config.DASHBOARD_PASSWORD

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register Flask routes."""
        @self.app.route("/")
        def index():
            """Render the dashboard index page."""
            return render_template("simple.html")
            
        @self.app.route("/health")
        def health():
            """Health check endpoint for the dashboard."""
            return jsonify({"status": "ok", "timestamp": time.time()})

    def start(self) -> None:
        """Start the dashboard server."""
        if self.running:
            logger.warning("Dashboard already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"Dashboard started on http://{self.host}:{self.port}")

    def _run_server(self) -> None:
        """Run the Flask server."""
        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self) -> None:
        """Stop the dashboard server."""
        if not self.running:
            logger.warning("Dashboard already stopped")
            return

        self.running = False
        logger.info("Dashboard stopped")


# Create a global dashboard instance
dashboard = Dashboard()
