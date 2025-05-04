#!/usr/bin/env python3
"""
Simple trading dashboard that bypasses database schema issues.
Uses a direct integration between mock trading and dashboard.
"""

import os
import sys
import time
import random
import json
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for

# Create required directories
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/crypto_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("crypto_bot")

# Dashboard flask app
app = Flask(__name__, template_folder="src/utils/templates")

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

# Price simulation
class PriceSimulator:
    def __init__(self):
        self.price = 45000.0
        self.trend = random.choice(["up", "down", "sideways"])
        self.trend_strength = random.uniform(0.1, 0.9)
        self.volatility = random.uniform(0.005, 0.03)
        self.trend_duration = random.randint(10, 50)
        self.current_trend_step = 0
        
    def next_price(self):
        """Generate next price based on trend and volatility"""
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
    def __init__(self):
        self.price_simulator = PriceSimulator()
        self.stop_event = threading.Event()
        
        # Initial state
        self.current_price = self.price_simulator.price
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
                logger.error(f"Error in trading cycle: {e}")
                time.sleep(1)
    
    def _execute_cycle(self):
        """Execute one trading cycle"""
        self.cycle_count += 1
        
        # Update price and indicators
        self.current_price = self.price_simulator.next_price()
        
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
        
        # Update high-risk bot
        prediction = self.rsi / 100  # Simple prediction based on RSI
        mock_state["bots"]["high_risk"]["last_prediction"]["final_prediction"] = prediction
        mock_state["bots"]["high_risk"]["last_prediction"]["combined_signal"] = (prediction * 0.5) + (self.sentiment_score * 0.5)
        mock_state["bots"]["high_risk"]["last_prediction"]["signal_details"]["technical_signal"] = (self.rsi - 50) / 50
        mock_state["bots"]["high_risk"]["last_prediction"]["signal_details"]["sentiment_signal"] = self.sentiment_score
        
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
        
        if prediction > 0.7 and not self.high_risk_position:
            # Buy signal
            position_size = 0.1  # 10% of portfolio in BTC
            entry_price = self.current_price
            
            self.high_risk_position = True
            self.entry_prices["high_risk"] = entry_price
            self.position_sizes["high_risk"] = position_size
            
            mock_state["bots"]["high_risk"]["in_position"] = True
            mock_state["bots"]["high_risk"]["current_side"] = "long"
            mock_state["bots"]["high_risk"]["entry_price"] = entry_price
            mock_state["bots"]["high_risk"]["position_size"] = position_size
            
            self._record_trade("high_risk", "buy", position_size, entry_price)
            
        elif prediction < 0.3 and self.high_risk_position:
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
        
        if is_bullish and not self.medium_risk_position:
            # Buy signal
            position_size = 0.05  # 5% of portfolio in BTC
            entry_price = self.current_price
            
            self.medium_risk_position = True
            self.entry_prices["medium_risk"] = entry_price
            self.position_sizes["medium_risk"] = position_size
            
            mock_state["bots"]["medium_risk"]["in_position"] = True
            mock_state["bots"]["medium_risk"]["current_side"] = "long"
            mock_state["bots"]["medium_risk"]["entry_price"] = entry_price
            mock_state["bots"]["medium_risk"]["position_size"] = position_size
            
            self._record_trade("medium_risk", "buy", position_size, entry_price)
            
        elif not is_bullish and self.medium_risk_position and self.rsi > 60:
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
            position_size = 0.02  # 2% of portfolio in BTC
            price = self.current_price
            
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
                profit = 0.5  # Assume 0.5% profit for grid trades
                
                self.entry_prices["low_risk"] = None
                self.position_sizes["low_risk"] = None
                
                mock_state["bots"]["low_risk"]["in_position"] = False
                mock_state["bots"]["low_risk"]["current_side"] = None
                mock_state["bots"]["low_risk"]["entry_price"] = None
                mock_state["bots"]["low_risk"]["position_size"] = None
                
                profit_pct = profit if action == "sell" else None
            
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
@app.route("/")
def index():
    """Render the dashboard index page."""
    return render_template("index.html")

@app.route("/api/status")
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

@app.route("/api/chart/portfolio")
def portfolio_chart():
    """Return portfolio chart data as JSON."""
    # Create chart data
    chart_data = {
        "capital": [],
        "drawdowns": [],
    }
    
    # Generate 30 days of historical data
    start_date = datetime.now() - timedelta(days=30)
    capital = 10000.0
    
    for i in range(31):  # 0 to 30
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Random daily change (-1% to +2%)
        change = random.uniform(-0.01, 0.02)
        capital *= (1 + change)
        
        # Add to chart data
        chart_data["capital"].append({
            "date": date,
            "value": capital,
        })
        
        # Add drawdown data (random 0-10%)
        chart_data["drawdowns"].append({
            "date": date,
            "value": random.uniform(0, 10),
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
                "price": random.uniform(40000, 50000),
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
                "price": random.uniform(40000, 50000),
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
                "price": random.uniform(40000, 50000),
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

def run_dashboard(host="0.0.0.0", port=5003):
    """Run the Flask dashboard."""
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Create trading system
    trading_system = MockTradingSystem()
    
    try:
        # Start trading system
        trading_system.start()
        
        # Start dashboard
        logger.info(f"Starting dashboard on http://localhost:5003")
        dashboard_thread = threading.Thread(target=run_dashboard)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        print("\n" + "="*80)
        print("=" + " "*20 + "CRYPTO TRADING BOT SIMULATION" + " "*20 + "=")
        print("="*80 + "\n")
        print("Trading system started with realistic mock data")
        print("Dashboard is running at http://localhost:5003")
        print("Press Ctrl+C to stop all systems")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        trading_system.stop()
        print("Systems stopped")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        print(f"Error: {e}")
