"""
Web dashboard for the crypto trading bot.
Provides a UI for monitoring and controlling the bot.
"""

import threading
import time
from typing import Dict, Any, List, Optional
from functools import wraps

from flask import Flask, render_template, jsonify, request, redirect, url_for, Response
import pandas as pd
import plotly
import plotly.graph_objs as go
import json

from src.config import settings
from src.utils.logging import logger
from src.utils.profit_withdrawal import profit_withdrawal_manager


class Dashboard:
    """Web dashboard for the crypto trading bot."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize the dashboard.

        Args:
            host: The host to bind to. If None, uses the value from settings.
            port: The port to bind to. If None, uses the value from settings.
        """
        self.host = host or settings.dashboard.host
        self.port = port or settings.dashboard.port
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.bot_manager = None
        self.thread = None
        self.running = False
        
        # Set up authentication if username and password are provided
        if settings.dashboard.username and settings.dashboard.password:
            self.auth_enabled = True
            self.username = settings.dashboard.username
            self.password = settings.dashboard.password
        else:
            self.auth_enabled = False
        
        # Register routes
        self._register_routes()
    
    def _check_auth(self, username: str, password: str) -> bool:
        """
        Check if the provided credentials are valid.
        
        Args:
            username: The username.
            password: The password.
            
        Returns:
            True if the credentials are valid, False otherwise.
        """
        return username == self.username and password == self.password
    
    def _requires_auth(self, f):
        """
        Decorator for routes that require authentication.
        
        Args:
            f: The function to decorate.
            
        Returns:
            The decorated function.
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            if not self.auth_enabled:
                return f(*args, **kwargs)
                
            auth = request.authorization
            if not auth or not self._check_auth(auth.username, auth.password):
                return Response(
                    'Authentication required',
                    401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'}
                )
            return f(*args, **kwargs)
        return decorated
    
    def _register_routes(self) -> None:
        """Register Flask routes."""
        @self.app.route("/")
        def index():
            """Render the dashboard index page."""
            return render_template("index.html")
        
        @self.app.route("/api/status")
        def status():
            """Return the bot status as JSON."""
            if not self.bot_manager:
                return jsonify({"error": "Bot manager not initialized"})
            
            status_data = {
                "running": self.bot_manager.running,
                "bots": {},
                "portfolio": self._get_portfolio_data(),
            }
            
            # Get status for each bot
            for bot_type, bot in self.bot_manager.bots.items():
                bot_status = {
                    "running": bot_type in self.bot_manager.threads and self.bot_manager.threads[bot_type].is_alive(),
                    "symbol": bot.symbol,
                    "exchange": bot.exchange_name,
                    "last_update": bot.state.get("last_update_time"),
                    "in_position": bot.state.get("in_position", False),
                    "current_side": bot.state.get("current_side"),
                    "entry_price": bot.state.get("entry_price"),
                    "position_size": bot.state.get("position_size"),
                }
                
                # Add strategy-specific data
                if bot_type == "low_risk":
                    bot_status["grid_levels"] = len(bot.state.get("grid_prices", {}).get("buy", [])) + len(bot.state.get("grid_prices", {}).get("sell", []))
                    bot_status["open_orders"] = len(bot.state.get("open_orders", []))
                elif bot_type == "medium_risk":
                    last_analysis = bot.state.get("last_analysis", {})
                    bot_status["is_bullish"] = last_analysis.get("is_bullish")
                    bot_status["rsi"] = last_analysis.get("rsi")
                    bot_status["signal"] = last_analysis.get("signal")
                elif bot_type == "high_risk":
                    last_prediction = bot.state.get("last_prediction", {})
                    bot_status["prediction"] = last_prediction.get("final_prediction")
                    bot_status["combined_signal"] = last_prediction.get("combined_signal")
                
                status_data["bots"][bot_type] = bot_status
            
            return jsonify(status_data)
        
        @self.app.route("/api/performance")
        def performance():
            """Return performance data as JSON."""
            if not self.bot_manager:
                return jsonify({"error": "Bot manager not initialized"})
            
            performance_data = {
                "portfolio": self._get_portfolio_performance(),
                "bots": {},
            }
            
            # Get performance for each bot
            for bot_type, bot in self.bot_manager.bots.items():
                bot_performance = bot.get_performance_summary()
                performance_data["bots"][bot_type] = bot_performance
            
            return jsonify(performance_data)
        
        @self.app.route("/api/market_regime")
        def market_regime():
            """Return market regime data as JSON."""
            if not self.bot_manager:
                return jsonify({"error": "Bot manager not initialized"})
            
            regime_data = {}
            
            # Get market regime data from high-risk bot (if available)
            if "high_risk" in self.bot_manager.bots:
                bot = self.bot_manager.bots["high_risk"]
                if hasattr(bot, "market_regime_detector") and bot.use_market_regime:
                    last_analysis = bot.state.get("last_prediction", {})
                    if "signal_details" in last_analysis and "market_regime_info" in last_analysis["signal_details"]:
                        regime_data = last_analysis["signal_details"]["market_regime_info"]
            
            return jsonify(regime_data)
        
        @self.app.route("/api/control", methods=["POST"])
        def control():
            """Control the bot."""
            if not self.bot_manager:
                return jsonify({"error": "Bot manager not initialized"})
            
            action = request.form.get("action")
            bot_type = request.form.get("bot_type", "all")
            
            if action == "start":
                if bot_type == "all":
                    self.bot_manager.start()
                else:
                    self.bot_manager.start_bot(bot_type)
                return jsonify({"success": True, "message": f"Started {bot_type} bot(s)"})
            
            elif action == "stop":
                if bot_type == "all":
                    self.bot_manager.stop()
                else:
                    self.bot_manager.stop_bot(bot_type)
                return jsonify({"success": True, "message": f"Stopped {bot_type} bot(s)"})
            
            else:
                return jsonify({"error": f"Unknown action: {action}"})
        
        @self.app.route("/api/chart/portfolio")
        def portfolio_chart():
            """Return portfolio chart data as JSON."""
            if not self.bot_manager or not hasattr(self.bot_manager, "portfolio_manager"):
                return jsonify({"error": "Portfolio manager not initialized"})
            
            # Get portfolio state
            portfolio_state = self.bot_manager.portfolio_manager.portfolio_state
            
            # Create chart data
            chart_data = {
                "capital": [],
                "drawdowns": [],
            }
            
            # Add daily capital data
            if "daily_capital" in portfolio_state:
                for date, capital in portfolio_state["daily_capital"].items():
                    chart_data["capital"].append({
                        "date": date,
                        "value": capital,
                    })
            
            # Add drawdown data
            if "performance" in portfolio_state and "drawdowns" in portfolio_state["performance"]:
                for date, drawdown in portfolio_state["performance"]["drawdowns"].items():
                    chart_data["drawdowns"].append({
                        "date": date,
                        "value": drawdown * 100,  # Convert to percentage
                    })
            
            return jsonify(chart_data)
        
        @self.app.route("/api/chart/bot/<bot_type>")
        def bot_chart(bot_type):
            """Return bot-specific chart data as JSON."""
            if not self.bot_manager or bot_type not in self.bot_manager.bots:
                return jsonify({"error": f"Bot {bot_type} not found"})
            
            bot = self.bot_manager.bots[bot_type]
            
            # Create chart data based on bot type
            chart_data = {}
            
            if bot_type == "high_risk":
                # Get prediction history
                if "prediction_tracking" in bot.state and "predictions" in bot.state["prediction_tracking"]:
                    predictions = bot.state["prediction_tracking"]["predictions"]
                    chart_data["predictions"] = predictions
            
            elif bot_type == "medium_risk":
                # Get analysis history
                if "analysis_history" in bot.state:
                    chart_data["analysis"] = bot.state["analysis_history"]
            
            elif bot_type == "low_risk":
                # Get grid history
                if "grid_history" in bot.state:
                    chart_data["grids"] = bot.state["grid_history"]
            
            return jsonify(chart_data)
        
        @self.app.route("/api/profit_withdrawals")
        def profit_withdrawals():
            """Return profit withdrawal data as JSON."""
            # Get profit withdrawal summary
            withdrawal_summary = profit_withdrawal_manager.get_withdrawal_summary()
            
            return jsonify(withdrawal_summary)
    
    def _get_portfolio_data(self) -> Dict[str, Any]:
        """
        Get portfolio data.
        
        Returns:
            Dictionary with portfolio data.
        """
        if not hasattr(self.bot_manager, "portfolio_manager"):
            return {}
        
        # Get portfolio summary
        portfolio_summary = self.bot_manager.portfolio_manager.get_portfolio_summary()
        
        return portfolio_summary
    
    def _get_portfolio_performance(self) -> Dict[str, Any]:
        """
        Get portfolio performance data.
        
        Returns:
            Dictionary with portfolio performance data.
        """
        if not hasattr(self.bot_manager, "portfolio_manager"):
            return {}
        
        # Get portfolio state
        portfolio_state = self.bot_manager.portfolio_manager.portfolio_state
        
        # Extract performance metrics
        performance = {
            "total_capital": portfolio_state.get("total_capital", 0),
            "peak_capital": portfolio_state.get("peak_capital", 0),
            "drawdown": 0,
            "sharpe_ratio": portfolio_state.get("performance", {}).get("sharpe_ratio"),
            "sortino_ratio": portfolio_state.get("performance", {}).get("sortino_ratio"),
            "daily_returns": portfolio_state.get("performance", {}).get("daily_returns", {}),
        }
        
        # Calculate drawdown
        if performance["peak_capital"] > 0:
            performance["drawdown"] = (performance["peak_capital"] - performance["total_capital"]) / performance["peak_capital"]
        
        return performance
    
    def set_bot_manager(self, bot_manager) -> None:
        """
        Set the bot manager.
        
        Args:
            bot_manager: The bot manager instance.
        """
        self.bot_manager = bot_manager
    
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
        # Flask doesn't provide a clean way to stop the server from another thread
        # In a production environment, you would use a proper WSGI server like Gunicorn
        logger.info("Dashboard stopped")


# Create a global dashboard instance
dashboard = Dashboard()
