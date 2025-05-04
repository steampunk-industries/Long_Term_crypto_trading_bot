#!/usr/bin/env python3
"""
Production-ready trading dashboard that connects to live cryptocurrency prices
and displays data on steampunk.holdings
"""

import os
import sys
import time
import random
import json
import threading
import logging
import argparse
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from functools import wraps
import ccxt

# Parse command line arguments
parser = argparse.ArgumentParser(description='Crypto Trading Dashboard')
parser.add_argument('--host', default=os.environ.get('DASHBOARD_HOST', '0.0.0.0'), help='Host to bind to')
parser.add_argument('--port', type=int, default=int(os.environ.get('DASHBOARD_PORT', 5003)), help='Port to bind to')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--log-level', default=os.environ.get('LOG_LEVEL', 'INFO'), help='Log level')
parser.add_argument('--initial-price', type=float, default=float(os.environ.get('INITIAL_BTC_PRICE', 84000)), help='Initial BTC price')
args = parser.parse_args()

# Create required directories
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Set up logging
log_level = getattr(logging, args.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("logs/crypto_bot.log", maxBytes=10**7, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("crypto_bot")

# Dashboard flask app
app = Flask(__name__, template_folder="src/utils/templates")
CORS(app)  # Enable CORS for all routes

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENABLE_SSL', 'false').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Dashboard authentication settings
DASHBOARD_USERNAME = os.environ.get('DASHBOARD_USERNAME', 'admin')
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'admin')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Global state
mock_state = {
    "running": True,
    "bots": {
        "high_risk": {
            "running": True,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "in_position": False,
            "current_side": None,
            "entry_price": None,
            "position_size": None,
            "last_update": datetime.now().isoformat(),
            "last_prediction": {
                "final_prediction": 0.2,
                "combined_signal": 0.15,
                "signal_details": {
                    "technical_signal": 0.3,
                    "sentiment_signal": 0.1,
                    "on_chain_signal": 0.05,
                    "market_regime_info": {
                        "current_regime": "bullish",
                        "volatility": 0.2,
                        "trend_strength": 0.6,
                        "regime_change_probability": 0.1
                    }
                }
            }
        },
        "medium_risk": {
            "running": True,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "in_position": False,
            "current_side": None,
            "entry_price": None,
            "position_size": None,
            "last_update": datetime.now().isoformat(),
            "is_bullish": True,
            "rsi": 42.5,
            "signal": 0.4
        },
        "low_risk": {
            "running": True,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "in_position": False,
            "current_side": None,
            "entry_price": None,
            "position_size": None,
            "last_update": datetime.now().isoformat(),
            "grid_levels": 10,
            "open_orders": 4
        }
    },
    "portfolio": {
        "total_capital": 10000.0,
        "peak_capital": 10000.0,
        "current_balance": {
            "USDT": 10000.0,
            "BTC": 0.0
        },
        "daily_returns": {},
        "trades": []
    }
}

# Price simulation with real data capability from multiple exchanges
class PriceProvider:
    def __init__(self, use_real_data=True, initial_price=None):
        """Initialize price provider with multiple exchanges."""
        # Exchange configuration
        self.exchanges = []
        self.exchange_names = ['coinbase', 'kucoin', 'kraken', 'gemini']
        self.exchange_weights = {
            'coinbase': 0.25,
            'kucoin': 0.25,
            'kraken': 0.25,
            'gemini': 0.25
        }  # Equal weight by default
        
        # Connect to exchanges if real data is requested
        if use_real_data:
            for exchange_name in self.exchange_names:
                try:
                    exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
                    exchange.load_markets()
                    self.exchanges.append(exchange)
                    logger.info(f"Connected to {exchange_name}")
                except Exception as e:
                    logger.warning(f"Cannot connect to {exchange_name}: {e}")
        
        self.use_real_data = use_real_data and len(self.exchanges) > 0
        
        # Starting price settings
        if initial_price:
            self.price = initial_price
        elif self.use_real_data:
            try:
                self.price = self._get_current_btc_price()
                logger.info(f"Using real BTC price: ${self.price:.2f}")
            except Exception as e:
                logger.error(f"Failed to get real BTC price: {e}")
                self.price = 84000.0  # Fall back to default price
                logger.info(f"Using fallback BTC price: ${self.price:.2f}")
        else:
            self.price = 84000.0
            logger.info(f"Using simulated BTC price starting at: ${self.price:.2f}")
            
        # Simulation parameters (used when real data is not available)
        self.trend = random.choice(["up", "down", "sideways"])
        self.trend_strength = random.uniform(0.1, 0.9)
        self.volatility = random.uniform(0.005, 0.03)
        self.trend_duration = random.randint(10, 50)
        self.current_trend_step = 0
        
        # Cache for real data (to avoid hitting rate limits)
        self.last_real_price_time = 0
        self.price_cache = {}  # Store price by exchange
        self.cache_duration = 60  # seconds
    
    def _get_current_btc_price(self):
        """Get the current BTC price from multiple exchanges and calculate weighted average."""
        current_time = time.time()
        
        # Use cached prices if available and not expired
        if self.price_cache and current_time - self.last_real_price_time < self.cache_duration:
            # Calculate weighted average from cache
            total_weight = 0
            weighted_price = 0
            for exchange_name, price in self.price_cache.items():
                weight = self.exchange_weights.get(exchange_name, 0)
                weighted_price += price * weight
                total_weight += weight
            
            if total_weight > 0:
                return weighted_price / total_weight
            
            # If no weights, use simple average
            if self.price_cache:
                return sum(self.price_cache.values()) / len(self.price_cache)
        
        # Fetch fresh prices
        prices = {}
        for exchange in self.exchanges:
            try:
                ticker = exchange.fetch_ticker('BTC/USDT')
                price = ticker['last']
                prices[exchange.id] = price
                logger.debug(f"{exchange.id} BTC price: ${price:.2f}")
            except Exception as e:
                logger.error(f"Error fetching price from {exchange.id}: {e}")
        
        if not prices:
            logger.error("Could not get price from any exchange")
            if self.price_cache:
                logger.info(f"Using cached prices")
                return sum(self.price_cache.values()) / len(self.price_cache)
            raise Exception("Could not get BTC price from any exchange")
        
        # Update cache
        self.price_cache = prices
        self.last_real_price_time = current_time
        
        # Calculate weighted average
        total_weight = 0
        weighted_price = 0
        for exchange_name, price in prices.items():
            weight = self.exchange_weights.get(exchange_name, 0)
            weighted_price += price * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_price / total_weight
        
        # If no weights, use simple average
        return sum(prices.values()) / len(prices)
        
    def next_price(self):
        """Get the next price - either real or simulated."""
        if self.use_real_data:
            try:
                self.price = self._get_current_btc_price()
                return self.price
            except Exception as e:
                logger.error(f"Failed to get real price, falling back to simulation: {e}")
                self.use_real_data = False
                return self._simulate_next_price()
        else:
            return self._simulate_next_price()
    
    def _simulate_next_price(self):
        """Generate next price based on trend and volatility for simulation."""
        self.current_trend_step += 1
        
        # Check if we need to change trend
        if self.current_trend_step >= self.trend_duration:
            self.trend = random.choice(["up", "down", "sideways"])
            self.trend_strength = random.uniform(0.1, 0.9)
            self.volatility = random.uniform(0.005, 0.03)
            self.trend_duration = random.randint(10, 50)
            self.current_trend_step = 0
            logger.info(f"Changed trend to {self.trend}")
        
        # Base drift based on trend
        if self.trend == "up":
            drift = self.trend_strength * 0.002  # 0.2% max drift up
        elif self.trend == "down":
            drift = -self.trend_strength * 0.002  # 0.2% max drift down
        else:
            drift = 0
        
        # Random walk with drift
        random_walk = random.normalvariate(0, 1) * self.volatility
        percent_change = drift + random_walk
        
        # Update price
        self.price = self.price * (1 + percent_change)
        return self.price

# Mock trading system
class MockTradingSystem:
    def __init__(self, initial_btc_price=None):
        self.price_provider = PriceProvider(
            use_real_data=os.environ.get('REAL_WORLD_PRICES', 'true').lower() == 'true',
            initial_price=initial_btc_price
        )
        self.stop_event = threading.Event()
        
        # Initial state
        self.current_price = self.price_provider.price
        self.rsi = 50.0
        self.macd = 0.0
        self.signal_line = 0.0
        self.sentiment_score = 0.0
        
        # Stats
        self.cycle_count = 0
        self.trade_count = 0
        
        # Position tracking
        self.high_risk_position = False
        self.medium_risk_position = False
        self.low_risk_position = False
        
        self.entry_prices = {
            "high_risk": None,
            "medium_risk": None,
            "low_risk": None
        }
        
        self.position_sizes = {
            "high_risk": None,
            "medium_risk": None,
            "low_risk": None
        }
        
        # Trading thresholds (configurable)
        self.high_risk_buy_threshold = 0.7
        self.high_risk_sell_threshold = 0.3
        self.medium_risk_rsi_buy = 30
        self.medium_risk_rsi_sell = 70
        self.position_sizes_pct = {
            "high_risk": 0.1,    # 10% of portfolio
            "medium_risk": 0.05, # 5% of portfolio
            "low_risk": 0.02     # 2% of portfolio
        }
    
    def start(self):
        """Start the trading system"""
        self.trading_thread = threading.Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        logger.info("Trading system started")
        
    def stop(self):
        """Stop the trading system"""
        self.stop_event.set()
        if hasattr(self, 'trading_thread'):
            self.trading_thread.join(timeout=2)
        logger.info("Trading system stopped")
        
    def _trading_loop(self):
        """Main trading loop"""
        while not self.stop_event.is_set():
            try:
                self._execute_cycle()
                time.sleep(5)  # Run every 5 seconds
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
                time.sleep(1)
    
    def _execute_cycle(self):
        """Execute one trading cycle"""
        self.cycle_count += 1
        
        # Update price and indicators
        self.current_price = self.price_provider.next_price()
        
        # Update RSI (random walk but constrained between 0 and 100)
        self.rsi += random.uniform(-3, 3)
        self.rsi = max(min(self.rsi, 90), 10)
        
        # Update MACD
        self.macd += random.uniform(-0.2, 0.2)
        self.signal_line += random.uniform(-0.1, 0.1)
        
        # Update sentiment (random walk between -1 and 1)
        self.sentiment_score += random.uniform(-0.1, 0.1)
        self.sentiment_score = max(min(self.sentiment_score, 1), -1)
        
        # Update global state with new data
        self._update_global_state()
        
        # Execute trading logic
        self._execute_trading_logic()
        
        # Log current status
        if self.cycle_count % 10 == 0:
            logger.info(f"Cycle {self.cycle_count}: Price=${self.current_price:.2f}, RSI={self.rsi:.1f}")
    
    def _update_global_state(self):
        """Update the global state with new market data"""
        current_time = datetime.now().isoformat()
        
        # Update bot states
        for bot_type in mock_state["bots"]:
            mock_state["bots"][bot_type]["last_update"] = current_time
        
        # Get exchange-specific data for high-risk strategy
        exchange_data = {}
        if hasattr(self.price_provider, 'price_cache') and self.price_provider.price_cache:
            exchange_data = self.price_provider.price_cache.copy()
        
        # Update high-risk bot with enhanced prediction model
        # Combine RSI, MACD, sentiment, and multi-exchange data
        rsi_signal = self.rsi / 100  # Normalize RSI to 0-1
        macd_signal = max(min((self.macd - self.signal_line) / 2 + 0.5, 1), 0)  # Normalize to 0-1
        sentiment_signal = (self.sentiment_score + 1) / 2  # Convert -1,1 to 0,1
        
        # Add exchange divergence signal if available
        exchange_divergence = 0
        if len(exchange_data) > 1:
            # Calculate price divergence between exchanges as a signal
            prices = list(exchange_data.values())
            avg_price = sum(prices) / len(prices)
            max_divergence = max([abs(p - avg_price) / avg_price for p in prices])
            # Use divergence as a volatility indicator (higher divergence = more volatility)
            exchange_divergence = min(max_divergence * 10, 1.0)  # Cap at 1.0
        
        # Combined prediction with weights
        prediction = (
            rsi_signal * 0.35 +
            macd_signal * 0.25 +
            sentiment_signal * 0.25 +
            exchange_divergence * 0.15
        )
        
        # Update prediction and signals in state
        mock_state["bots"]["high_risk"]["last_prediction"]["final_prediction"] = prediction
        mock_state["bots"]["high_risk"]["last_prediction"]["combined_signal"] = (prediction * 0.6) + (self.sentiment_score * 0.4)
        mock_state["bots"]["high_risk"]["last_prediction"]["signal_details"]["technical_signal"] = (self.rsi - 50) / 50
        mock_state["bots"]["high_risk"]["last_prediction"]["signal_details"]["sentiment_signal"] = self.sentiment_score
        mock_state["bots"]["high_risk"]["last_prediction"]["price"] = self.current_price
        
        # Add exchange-specific data
        if exchange_data:
            mock_state["bots"]["high_risk"]["last_prediction"]["exchange_prices"] = exchange_data
            mock_state["bots"]["high_risk"]["last_prediction"]["exchange_divergence"] = exchange_divergence
        
        # Update medium-risk bot
        mock_state["bots"]["medium_risk"]["rsi"] = self.rsi
        mock_state["bots"]["medium_risk"]["signal"] = (self.macd - self.signal_line)
        mock_state["bots"]["medium_risk"]["is_bullish"] = self.rsi < 40
        
        # Update portfolio
        mock_state["portfolio"]["current_balance"]["BTC"] = sum([
            mock_state["bots"][bot_type]["position_size"] or 0 
            for bot_type in mock_state["bots"]
        ])
        
        usdt_value = 10000.0  # Initial capital
        usdt_value -= sum([
            (mock_state["bots"][bot_type]["position_size"] or 0) * 
            (mock_state["bots"][bot_type]["entry_price"] or 0)
            for bot_type in mock_state["bots"] if mock_state["bots"][bot_type]["in_position"]
        ])
        btc_value = mock_state["portfolio"]["current_balance"]["BTC"] * self.current_price
        
        mock_state["portfolio"]["current_balance"]["USDT"] = usdt_value
        mock_state["portfolio"]["total_capital"] = usdt_value + btc_value
        mock_state["portfolio"]["peak_capital"] = max(
            mock_state["portfolio"]["peak_capital"], 
            mock_state["portfolio"]["total_capital"]
        )
    
    def _execute_trading_logic(self):
        """Execute trading logic for all strategies"""
        # High-risk strategy (prediction-based)
        prediction = mock_state["bots"]["high_risk"]["last_prediction"]["final_prediction"]
        
        if prediction > self.high_risk_buy_threshold and not self.high_risk_position:
            # Buy signal
            position_size = self.position_sizes_pct["high_risk"]  # 10% of portfolio in BTC
            entry_price = self.current_price
            
            self.high_risk_position = True
            self.entry_prices["high_risk"] = entry_price
            self.position_sizes["high_risk"] = position_size
            
            mock_state["bots"]["high_risk"]["in_position"] = True
            mock_state["bots"]["high_risk"]["current_side"] = "long"
            mock_state["bots"]["high_risk"]["entry_price"] = entry_price
            mock_state["bots"]["high_risk"]["position_size"] = position_size
            
            self._record_trade("high_risk", "buy", position_size, entry_price)
            
        elif prediction < self.high_risk_sell_threshold and self.high_risk_position:
            # Sell signal
            exit_price = self.current_price
            position_size = self.position_sizes["high_risk"]
            entry_price = self.entry_prices["high_risk"]
            
            profit = (exit_price - entry_price) / entry_price
            
            self.high_risk_position = False
            self.entry_prices["high_risk"] = None
            self.position_sizes["high_risk"] = None
            
            mock_state["bots"]["high_risk"]["in_position"] = False
            mock_state["bots"]["high_risk"]["current_side"] = None
            mock_state["bots"]["high_risk"]["entry_price"] = None
            mock_state["bots"]["high_risk"]["position_size"] = None
            
            self._record_trade("high_risk", "sell", position_size, exit_price, profit * 100)
        
        # Medium-risk strategy (RSI-based)
        is_bullish = mock_state["bots"]["medium_risk"]["is_bullish"]
        
        if is_bullish and not self.medium_risk_position and self.rsi < self.medium_risk_rsi_buy:
            # Buy signal
            position_size = self.position_sizes_pct["medium_risk"]  # 5% of portfolio in BTC
            entry_price = self.current_price
            
            self.medium_risk_position = True
            self.entry_prices["medium_risk"] = entry_price
            self.position_sizes["medium_risk"] = position_size
            
            mock_state["bots"]["medium_risk"]["in_position"] = True
            mock_state["bots"]["medium_risk"]["current_side"] = "long"
            mock_state["bots"]["medium_risk"]["entry_price"] = entry_price
            mock_state["bots"]["medium_risk"]["position_size"] = position_size
            
            self._record_trade("medium_risk", "buy", position_size, entry_price)
            
        elif not is_bullish and self.medium_risk_position and self.rsi > self.medium_risk_rsi_sell:
            # Sell signal
            exit_price = self.current_price
            position_size = self.position_sizes["medium_risk"]
            entry_price = self.entry_prices["medium_risk"]
            
            profit = (exit_price - entry_price) / entry_price
            
            self.medium_risk_position = False
            self.entry_prices["medium_risk"] = None
            self.position_sizes["medium_risk"] = None
            
            mock_state["bots"]["medium_risk"]["in_position"] = False
            mock_state["bots"]["medium_risk"]["current_side"] = None
            mock_state["bots"]["medium_risk"]["entry_price"] = None
            mock_state["bots"]["medium_risk"]["position_size"] = None
            
            self._record_trade("medium_risk", "sell", position_size, exit_price, profit * 100)
        
        # Low-risk strategy (grid-trading simulation)
        if random.random() < 0.05:  # 5% chance of a grid trade
            # Random buy or sell
            action = random.choice(["buy", "sell"])
            position_size = self.position_sizes_pct["low_risk"]  # 2% of portfolio in BTC
            price = self.current_price
            profit_pct = None
            
            # Record position for visualization
            self.low_risk_position = (action == "buy")
            if action == "buy":
                self.entry_prices["low_risk"] = price
                self.position_sizes["low_risk"] = position_size
                
                mock_state["bots"]["low_risk"]["in_position"] = True
                mock_state["bots"]["low_risk"]["current_side"] = "long"
                mock_state["bots"]["low_risk"]["entry_price"] = price
                mock_state["bots"]["low_risk"]["position_size"] = position_size
            else:
                profit_pct = 0.5  # Assume 0.5% profit for grid trades
                
                self.entry_prices["low_risk"] = None
                self.position_sizes["low_risk"] = None
                
                mock_state["bots"]["low_risk"]["in_position"] = False
                mock_state["bots"]["low_risk"]["current_side"] = None
                mock_state["bots"]["low_risk"]["entry_price"] = None
                mock_state["bots"]["low_risk"]["position_size"] = None
            
            self._record_trade("low_risk", action, position_size, price, profit_pct)
    
    def _record_trade(self, strategy, action, size, price, profit_pct=None):
        """Record a trade in the global state"""
        self.trade_count += 1
        
        trade = {
            "id": self.trade_count,
            "strategy": strategy,
            "action": action,
            "size": size,
            "price": price,
            "value": size * price,
            "timestamp": datetime.now().isoformat()
        }
        
        if profit_pct is not None:
            trade["profit_pct"] = profit_pct
        
        mock_state["portfolio"]["trades"].append(trade)
        
        # Keep only the last 100 trades
        if len(mock_state["portfolio"]["trades"]) > 100:
            mock_state["portfolio"]["trades"] = mock_state["portfolio"]["trades"][-100:]
        
        # Record daily returns (simplified)
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in mock_state["portfolio"]["daily_returns"]:
            mock_state["portfolio"]["daily_returns"][today] = 0
            
        # Add profit to daily returns
        if action == "sell" and profit_pct is not None:
            mock_state["portfolio"]["daily_returns"][today] += profit_pct * size * price / 100
        
        logger.info(f"Trade: {strategy} {action} {size:.8f} BTC at ${price:.2f}")

# Flask routes for the dashboard
@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    error = None
    if request.method == 'POST':
        if request.form['username'] == DASHBOARD_USERNAME and request.form['password'] == DASHBOARD_PASSWORD:
            session['authenticated'] = True
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):  # Ensure next URL is relative to prevent open redirect
                return redirect(next_url)
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials. Please try again.'
    
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    """Handle user logout."""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    """Render the dashboard index page."""
    return render_template("index.html")

@app.route("/api/status")
@login_required
def status():
    """Return the bot status as JSON."""
    return jsonify({
        "running": mock_state["running"],
        "bots": mock_state["bots"],
        "portfolio": mock_state["portfolio"],
    })

@app.route("/api/performance")
def performance():
    """Return performance data as JSON."""
    # Calculate performance metrics
    total_capital = mock_state["portfolio"]["total_capital"]
    peak_capital = mock_state["portfolio"]["peak_capital"]
    drawdown = 0
    
    if peak_capital > 0:
        drawdown = (peak_capital - total_capital) / peak_capital
    
    # Create performance data
    performance_data = {
        "portfolio": {
            "total_capital": total_capital,
            "peak_capital": peak_capital,
            "drawdown": drawdown,
            "sharpe_ratio": random.uniform(0.5, 2.5),
            "sortino_ratio": random.uniform(0.7, 3.0),
            "daily_returns": mock_state["portfolio"]["daily_returns"],
        },
        "bots": {},
    }
    
    # Get performance for each bot
    for bot_type in mock_state["bots"]:
        bot_performance = {
            "total_trades": len([t for t in mock_state["portfolio"]["trades"] if t["strategy"] == bot_type]),
            "win_rate": random.uniform(0.4, 0.7),
            "profit_factor": random.uniform(1.1, 2.5),
            "sharpe_ratio": random.uniform(0.8, 3.0),
            "max_drawdown": random.uniform(0.05, 0.25),
            "profit_percentage": random.uniform(-0.1, 0.5)
        }
        performance_data["bots"][bot_type] = bot_performance
    
    return jsonify(performance_data)

@app.route("/api/market_regime")
def market_regime():
    """Return market regime data as JSON."""
    regime_data = {
        "current_regime": random.choice(["bullish", "bearish", "ranging", "volatile"]),
        "volatility": random.uniform(0.01, 0.05),
        "trend_strength": random.uniform(0.2, 0.9),
        "regime_change_probability": random.uniform(0.05, 0.3),
    }
    
    return jsonify(regime_data)

@app.route("/api/control", methods=["POST"])
def control():
    """Control the bot."""
    action = request.form.get("action")
    bot_type = request.form.get("bot_type", "all")
    
    if action == "start":
        mock_state["running"] = True
        if bot_type == "all":
            for bot_type in mock_state["bots"]:
                mock_state["bots"][bot_type]["running"] = True
        else:
            mock_state["bots"][bot_type]["running"] = True
        return jsonify({"success": True, "message": f"Started {bot_type} bot(s)"})
    
    elif action == "stop":
        if bot_type == "all":
            for bot_type in mock_state["bots"]:
                mock_state["bots"][bot_type]["running"] = False
        else:
            mock_state["bots"][bot_type]["running"] = False
        return jsonify({"success": True, "message": f"Stopped {bot_type} bot(s)"})
    
    else:
        return jsonify({"error": f"Unknown action: {action}"})

@app.route("/api/configure", methods=["POST"])
def configure():
    """Update trading system configuration."""
    config = request.get_json()
    
    # Validate access
    if not request.remote_addr.startswith('127.0.0.1') and not request.remote_addr.startswith('localhost'):
        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.environ.get('API_KEY'):
            return jsonify({"error": "Unauthorized"}), 401
    
    if trading_system:
        # Update trading thresholds
        if "thresholds" in config:
            if "high_risk_buy" in config["thresholds"]:
                trading_system.high_risk_buy_threshold = float(config["thresholds"]["high_risk_buy"])
            if "high_risk_sell" in config["thresholds"]:
                trading_system.high_risk_sell_threshold = float(config["thresholds"]["high_risk_sell"])
            if "medium_risk_rsi_buy" in config["thresholds"]:
                trading_system.medium_risk_rsi_buy = float(config["thresholds"]["medium_risk_rsi_buy"])
            if "medium_risk_rsi_sell" in config["thresholds"]:
                trading_system.medium_risk_rsi_sell = float(config["thresholds"]["medium_risk_rsi_sell"])
        
        # Update position sizes
        if "position_sizes" in config:
            if "high_risk" in config["position_sizes"]:
                trading_system.position_sizes_pct["high_risk"] = float(config["position_sizes"]["high_risk"])
            if "medium_risk" in config["position_sizes"]:
                trading_system.position_sizes_pct["medium_risk"] = float(config["position_sizes"]["medium_risk"])
            if "low_risk" in config["position_sizes"]:
                trading_system.position_sizes_pct["low_risk"] = float(config["position_sizes"]["low_risk"])
    
    return jsonify({"success": True, "message": "Configuration updated"})

@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current trading system configuration."""
    if not trading_system:
        return jsonify({"error": "Trading system not initialized"}), 500
        
    config = {
        "thresholds": {
            "high_risk_buy": trading_system.high_risk_buy_threshold,
            "high_risk_sell": trading_system.high_risk_sell_threshold,
            "medium_risk_rsi_buy": trading_system.medium_risk_rsi_buy,
            "medium_risk_rsi_sell": trading_system.medium_risk_rsi_sell,
        },
        "position_sizes": {
            "high_risk": trading_system.position_sizes_pct["high_risk"],
            "medium_risk": trading_system.position_sizes_pct["medium_risk"],
            "low_risk": trading_system.position_sizes_pct["low_risk"],
        }
    }
    return jsonify(config)

@app.route("/api/chart/portfolio")
def portfolio_chart():
    """Return portfolio chart data as JSON."""
    # Create chart data
    chart_data = {
        "capital": [],
        "drawdowns": [],
    }
    
    # Generate 30 days of historical data if needed
    if len(mock_state["portfolio"]["daily_returns"]) < 30:
        start_date = datetime.now() - timedelta(days=30)
        capital = 10000.0
        
        for i in range(31):  # 0 to 30
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            
            # Random daily change (-1% to +2%)
            change = random.uniform(-0.01, 0.02)
            capital *= (1 + change)
            
            # Add to chart data if not already in daily returns
            if date not in mock_state["portfolio"]["daily_returns"]:
                chart_data["capital"].append({
                    "date": date,
                    "value": capital,
                })
                
                # Add drawdown data (random 0-10%)
                chart_data["drawdowns"].append({
                    "date": date,
                    "value": random.uniform(0, 10),
                })
    
    # Add current data
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in [item.get("date") for item in chart_data["capital"]]:
        chart_data["capital"].append({
            "date": today,
            "value": mock_state["portfolio"]["total_capital"]
        })
        
        # Calculate current drawdown
        current_drawdown = 0
        if mock_state["portfolio"]["peak_capital"] > 0:
            current_drawdown = (mock_state["portfolio"]["peak_capital"] - mock_state["portfolio"]["total_capital"]) / mock_state["portfolio"]["peak_capital"] * 100
            
        chart_data["drawdowns"].append({
            "date": today,
            "value": current_drawdown
        })
    
    return jsonify(chart_data)

@app.route("/api/chart/bot/<bot_type>")
def bot_chart(bot_type):
    """Return bot-specific chart data as JSON."""
    if bot_type not in mock_state["bots"]:
        return jsonify({"error": f"Bot {bot_type} not found"})
    
    # Create chart data based on bot type
    chart_data = {}
    
    if bot_type == "high_risk":
        # Generate prediction history
        predictions = []
        start_date = datetime.now() - timedelta(days=30)
        
        for i in range(100):
            timestamp = (start_date + timedelta(hours=i*6)).isoformat()
            predictions.append({
                "timestamp": timestamp,
                "prediction": random.uniform(-1.0, 1.0),
                "price": random.uniform(75000, 85000),
            })
        
        chart_data["predictions"] = predictions
    
    elif bot_type == "medium_risk":
        # Generate analysis history
        analysis = []
        start_date = datetime.now() - timedelta(days=30)
        
        for i in range(100):
            timestamp = (start_date + timedelta(hours=i*6)).isoformat()
            analysis.append({
                "timestamp": timestamp,
                "is_bullish": random.choice([True, False]),
                "rsi": random.uniform(20, 80),
                "signal": random.uniform(-1.0, 1.0),
                "price": random.uniform(75000, 85000),
            })
        
        chart_data["analysis"] = analysis
    
    elif bot_type == "low_risk":
        # Generate grid history
        grids = []
        start_date = datetime.now() - timedelta(days=30)
        
        for i in range(100):
            timestamp = (start_date + timedelta(hours=i*6)).isoformat()
            grids.append({
                "timestamp": timestamp,
                "type": random.choice(["buy", "sell"]),
                "price": random.uniform(75000, 85000),
                "level": random.randint(0, 9),
            })
        
        chart_data["grids"] = grids
    
    return jsonify(chart_data)

@app.route("/api/profit_withdrawals")
def profit_withdrawals():
    """Return profit withdrawal data as JSON."""
    # Generate random profit withdrawal summary
    withdrawal_summary = {
        "total_withdrawn": random.uniform(1000, 5000),
        "last_withdrawal": {
            "amount": random.uniform(100, 500),
            "date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        },
        "withdrawals": [],
    }
    
    # Generate withdrawal history
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(12):
        date = (start_date + timedelta(days=i*30 + random.randint(0, 29))).isoformat()
        withdrawal_summary["withdrawals"].append({
            "date": date,
            "amount": random.uniform(100, 500),
            "reason": random.choice(["Monthly profit", "Threshold reached", "Manual withdrawal"]),
        })
    
    return jsonify(withdrawal_summary)

@app.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route("/metrics")
def metrics():
    """Return metrics for prometheus."""
    metrics_text = f"""
# HELP crypto_bot_price Current BTC price
# TYPE crypto_bot_price gauge
crypto_bot_price {trading_system.current_price if trading_system else 0}

# HELP crypto_bot_rsi Current RSI value
# TYPE crypto_bot_rsi gauge
crypto_bot_rsi {trading_system.rsi if trading_system else 0}

# HELP crypto_bot_total_capital Total portfolio value
# TYPE crypto_bot_total_capital gauge
crypto_bot_total_capital {mock_state["portfolio"]["total_capital"]}

# HELP crypto_bot_trade_count Total number of trades
# TYPE crypto_bot_trade_count counter
crypto_bot_trade_count {len(mock_state["portfolio"]["trades"])}
"""
    return metrics_text, 200, {'Content-Type': 'text/plain'}

# Initialize and start trading system
trading_system = None

def run_dashboard(host=args.host, port=args.port, debug=args.debug):
    """Run the Flask dashboard."""
    global trading_system
    
    # Initialize trading system
    trading_system = MockTradingSystem(initial_btc_price=args.initial_price)
    trading_system.start()
    
    try:
        # Announce startup
        print("\n" + "="*80)
        print("=" + " "*20 + "CRYPTO TRADING BOT WITH DASHBOARD" + " "*20 + "=")
        print("="*80 + "\n")
        print(f"Trading system started with {'real' if trading_system.price_provider.use_real_data else 'simulated'} BTC price: ${trading_system.current_price:.2f}")
        print(f"Dashboard is running at http://{host}:{port}")
        print("Press Ctrl+C to stop all systems")
        
        # Start Flask app
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if trading_system:
            trading_system.stop()
        print("Systems stopped")
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
        print(f"Error: {e}")

if __name__ == "__main__":
    run_dashboard()
