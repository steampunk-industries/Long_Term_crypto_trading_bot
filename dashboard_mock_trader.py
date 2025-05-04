#!/usr/bin/env python3
"""
Dashboard-integrated mock trader that properly connects with the dashboard component.
"""

import os
import sys
import time
import random
import signal
import threading
import json
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# Set up logging
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("crypto_bot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# File handler
file_handler = RotatingFileHandler("logs/crypto_bot.log", maxBytes=10**7, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Initialize database
try:
    from src.utils.database import init_db, engine, Session, Base, BotState
    from src.exchange.wrapper import ExchangeWrapper
    from src.utils.portfolio_manager import PortfolioManager
    from src.utils.dashboard import dashboard
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
except Exception as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

class MockBotManager:
    """Mock bot manager for dashboard integration."""
    
    def __init__(self):
        """Initialize the bot manager."""
        self.running = True
        self.bots = {}
        self.threads = {}
        self.portfolio_manager = PortfolioManager()
        
        # Initialize exchange connections
        # Note: The wrapper reads paper_trading from settings
        self.exchange = ExchangeWrapper(exchange_name="binance")
        self.symbol = "BTC/USDT"
        
        # Initialize bots
        self._init_bots()
        
        logger.info("MockBotManager initialized")
    
    def _init_bots(self):
        """Initialize bot instances."""
        # Create a mock high risk strategy bot
        self.bots["high_risk"] = MockHighRiskBot("binance", "BTC/USDT")
        
        # Create a mock medium risk strategy bot
        self.bots["medium_risk"] = MockMediumRiskBot("binance", "BTC/USDT")
        
        # Create a mock low risk strategy bot
        self.bots["low_risk"] = MockLowRiskBot("binance", "BTC/USDT")
        
        logger.info(f"Initialized {len(self.bots)} mock strategy bots")
    
    def start(self):
        """Start all bots."""
        if not self.running:
            self.running = True
            
        for bot_type, bot in self.bots.items():
            self.start_bot(bot_type)
        
        logger.info("All bots started")
    
    def start_bot(self, bot_type):
        """Start a specific bot."""
        if bot_type not in self.bots:
            logger.warning(f"Bot type {bot_type} not found")
            return False
        
        if bot_type in self.threads and self.threads[bot_type].is_alive():
            logger.warning(f"Bot {bot_type} already running")
            return False
        
        # Create and start thread
        thread = threading.Thread(target=self._run_bot, args=(bot_type,), daemon=True)
        self.threads[bot_type] = thread
        thread.start()
        
        logger.info(f"Started {bot_type} bot")
        return True
    
    def _run_bot(self, bot_type):
        """Run a bot in its own thread."""
        bot = self.bots[bot_type]
        
        try:
            while self.running:
                if not bot.run_once():
                    time.sleep(5)  # Short pause if nothing to do
                time.sleep(bot.update_interval)
        except Exception as e:
            logger.error(f"Error in {bot_type} bot: {e}")
    
    def stop(self):
        """Stop all bots."""
        self.running = False
        
        for bot_type in self.bots.keys():
            self.stop_bot(bot_type)
        
        logger.info("All bots stopped")
    
    def stop_bot(self, bot_type):
        """Stop a specific bot."""
        if bot_type not in self.threads:
            logger.warning(f"Bot type {bot_type} not found or not running")
            return False
        
        # Thread will terminate when self.running is False
        self.threads[bot_type] = None
        
        logger.info(f"Stopped {bot_type} bot")
        return True


class MockBotBase:
    """Base class for mock bots."""
    
    def __init__(self, exchange_name, symbol, bot_type):
        """Initialize the bot base."""
        self.exchange_name = exchange_name
        self.symbol = symbol
        self.bot_type = bot_type
        self.update_interval = 15  # Seconds between updates
        self.state = {"last_update_time": datetime.now().isoformat()}
        
        # Load bot state from database
        self._load_state()
        
        logger.info(f"Initialized {bot_type} bot for {symbol} on {exchange_name}")
    
    def _load_state(self):
        """Load bot state from database."""
        try:
            with Session() as session:
                bot_state = session.query(BotState).filter_by(
                    exchange=self.exchange_name,
                    symbol=self.symbol,
                    strategy=self.bot_type
                ).first()
                
                if bot_state:
                    if bot_state.state:
                        self.state = json.loads(bot_state.state)
                        logger.info(f"Loaded state for {self.bot_type} bot")
                    else:
                        self._save_state()
                else:
                    # Create new bot state
                    bot_state = BotState(
                        exchange=self.exchange_name,
                        symbol=self.symbol,
                        strategy=self.bot_type,
                        state=json.dumps(self.state)
                    )
                    session.add(bot_state)
                    session.commit()
                    logger.info(f"Created new state for {self.bot_type} bot")
        except Exception as e:
            logger.error(f"Error loading bot state: {e}")
    
    def _save_state(self):
        """Save bot state to database."""
        try:
            with Session() as session:
                bot_state = session.query(BotState).filter_by(
                    exchange=self.exchange_name,
                    symbol=self.symbol,
                    strategy=self.bot_type
                ).first()
                
                if bot_state:
                    bot_state.state = json.dumps(self.state)
                    bot_state.updated_at = datetime.now()
                else:
                    bot_state = BotState(
                        exchange=self.exchange_name,
                        symbol=self.symbol,
                        strategy=self.bot_type,
                        state=json.dumps(self.state)
                    )
                    session.add(bot_state)
                
                session.commit()
                logger.info(f"Saved state for {self.bot_type} bot")
        except Exception as e:
            logger.error(f"Error saving bot state: {e}")
    
    def run_once(self):
        """Run one iteration of the bot."""
        self.state["last_update_time"] = datetime.now().isoformat()
        self._save_state()
        return True
    
    def get_performance_summary(self):
        """Get bot performance summary."""
        return {
            "total_trades": random.randint(10, 100),
            "win_rate": random.uniform(0.4, 0.7),
            "profit_factor": random.uniform(1.1, 2.5),
            "sharpe_ratio": random.uniform(0.8, 3.0),
            "max_drawdown": random.uniform(0.05, 0.25),
            "profit_percentage": random.uniform(-0.1, 0.5)
        }


class MockHighRiskBot(MockBotBase):
    """Mock high risk strategy bot."""
    
    def __init__(self, exchange_name, symbol):
        """Initialize the high risk bot."""
        super().__init__(exchange_name, symbol, "high_risk")
        
        # Initialize state with strategy-specific values
        if "last_prediction" not in self.state:
            self.state["last_prediction"] = {
                "timestamp": datetime.now().isoformat(),
                "final_prediction": 0.0,
                "combined_signal": 0.0,
                "signal_details": {
                    "technical_signal": 0.0,
                    "sentiment_signal": 0.0,
                    "on_chain_signal": 0.0,
                    "market_regime_info": {
                        "current_regime": "unknown",
                        "volatility": 0.0,
                        "trend_strength": 0.0,
                        "regime_change_probability": 0.0
                    }
                }
            }
        
        if "prediction_tracking" not in self.state:
            self.state["prediction_tracking"] = {
                "predictions": []
            }
        
        if "in_position" not in self.state:
            self.state["in_position"] = False
            self.state["current_side"] = None
            self.state["entry_price"] = None
            self.state["position_size"] = None
        
        self.market_regime_detector = True
        self.use_market_regime = True
        
        self._save_state()
    
    def run_once(self):
        """Run one iteration of the high risk bot."""
        # Update timestamp
        self.state["last_update_time"] = datetime.now().isoformat()
        
        # Simulate price movement
        current_price = round(random.uniform(40000, 50000), 2)
        
        # Generate random prediction
        prediction = random.uniform(-1.0, 1.0)
        combined_signal = random.uniform(-1.0, 1.0)
        
        # Update signals
        technical_signal = random.uniform(-1.0, 1.0)
        sentiment_signal = random.uniform(-1.0, 1.0)
        on_chain_signal = random.uniform(-1.0, 1.0)
        
        # Update market regime
        regimes = ["bullish", "bearish", "ranging", "volatile"]
        current_regime = random.choice(regimes)
        
        # Create prediction record
        self.state["last_prediction"] = {
            "timestamp": datetime.now().isoformat(),
            "final_prediction": prediction,
            "combined_signal": combined_signal,
            "price": current_price,
            "signal_details": {
                "technical_signal": technical_signal,
                "sentiment_signal": sentiment_signal,
                "on_chain_signal": on_chain_signal,
                "market_regime_info": {
                    "current_regime": current_regime,
                    "volatility": random.uniform(0.0, 1.0),
                    "trend_strength": random.uniform(0.0, 1.0),
                    "regime_change_probability": random.uniform(0.0, 0.5)
                }
            }
        }
        
        # Add to prediction tracking
        self.state["prediction_tracking"]["predictions"].append({
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "price": current_price
        })
        
        # Keep only last 100 predictions
        if len(self.state["prediction_tracking"]["predictions"]) > 100:
            self.state["prediction_tracking"]["predictions"] = self.state["prediction_tracking"]["predictions"][-100:]
        
        # Simulate trading based on prediction
        if prediction > 0.6 and not self.state["in_position"]:
            # Buy signal
            self.state["in_position"] = True
            self.state["current_side"] = "long"
            self.state["entry_price"] = current_price
            self.state["position_size"] = round(10000 / current_price, 8)
            logger.info(f"High-risk bot: BUY signal at ${current_price}")
        elif prediction < -0.6 and self.state["in_position"]:
            # Sell signal
            self.state["in_position"] = False
            self.state["current_side"] = None
            profit = (current_price - self.state["entry_price"]) / self.state["entry_price"] * 100
            logger.info(f"High-risk bot: SELL signal at ${current_price} (P/L: {profit:.2f}%)")
            self.state["entry_price"] = None
            self.state["position_size"] = None
        
        # Save state
        self._save_state()
        
        return True


class MockMediumRiskBot(MockBotBase):
    """Mock medium risk strategy bot."""
    
    def __init__(self, exchange_name, symbol):
        """Initialize the medium risk bot."""
        super().__init__(exchange_name, symbol, "medium_risk")
        
        # Initialize state with strategy-specific values
        if "last_analysis" not in self.state:
            self.state["last_analysis"] = {
                "timestamp": datetime.now().isoformat(),
                "is_bullish": False,
                "rsi": 50.0,
                "signal": 0.0
            }
        
        if "analysis_history" not in self.state:
            self.state["analysis_history"] = []
        
        if "in_position" not in self.state:
            self.state["in_position"] = False
            self.state["current_side"] = None
            self.state["entry_price"] = None
            self.state["position_size"] = None
        
        self._save_state()
    
    def run_once(self):
        """Run one iteration of the medium risk bot."""
        # Update timestamp
        self.state["last_update_time"] = datetime.now().isoformat()
        
        # Simulate price and indicator movement
        current_price = round(random.uniform(40000, 50000), 2)
        rsi = round(random.uniform(30, 70), 2)
        signal = round(random.uniform(-1.0, 1.0), 2)
        is_bullish = rsi < 40 if self.state["in_position"] else rsi < 30
        
        # Update analysis
        self.state["last_analysis"] = {
            "timestamp": datetime.now().isoformat(),
            "is_bullish": is_bullish,
            "rsi": rsi,
            "signal": signal,
            "price": current_price
        }
        
        # Add to analysis history
        self.state["analysis_history"].append(self.state["last_analysis"])
        
        # Keep only last 100 analyses
        if len(self.state["analysis_history"]) > 100:
            self.state["analysis_history"] = self.state["analysis_history"][-100:]
        
        # Simulate trading based on analysis
        if is_bullish and not self.state["in_position"]:
            # Buy signal
            self.state["in_position"] = True
            self.state["current_side"] = "long"
            self.state["entry_price"] = current_price
            self.state["position_size"] = round(10000 / current_price, 8)
            logger.info(f"Medium-risk bot: BUY signal at ${current_price}")
        elif not is_bullish and self.state["in_position"] and rsi > 70:
            # Sell signal
            self.state["in_position"] = False
            self.state["current_side"] = None
            profit = (current_price - self.state["entry_price"]) / self.state["entry_price"] * 100
            logger.info(f"Medium-risk bot: SELL signal at ${current_price} (P/L: {profit:.2f}%)")
            self.state["entry_price"] = None
            self.state["position_size"] = None
        
        # Save state
        self._save_state()
        
        return True


class MockLowRiskBot(MockBotBase):
    """Mock low risk strategy bot."""
    
    def __init__(self, exchange_name, symbol):
        """Initialize the low risk bot."""
        super().__init__(exchange_name, symbol, "low_risk")
        
        # Initialize state with strategy-specific values
        if "grid_prices" not in self.state:
            self.state["grid_prices"] = {
                "buy": [45000 - i * 1000 for i in range(5)],
                "sell": [45000 + i * 1000 for i in range(5)]
            }
        
        if "open_orders" not in self.state:
            self.state["open_orders"] = []
        
        if "grid_history" not in self.state:
            self.state["grid_history"] = []
        
        if "in_position" not in self.state:
            self.state["in_position"] = False
            self.state["current_side"] = None
            self.state["entry_price"] = None
            self.state["position_size"] = None
        
        self._save_state()
    
    def run_once(self):
        """Run one iteration of the low risk bot."""
        # Update timestamp
        self.state["last_update_time"] = datetime.now().isoformat()
        
        # Simulate price movement
        current_price = round(random.uniform(40000, 50000), 2)
        
        # Check if any grid levels are triggered
        for buy_price in self.state["grid_prices"]["buy"]:
            if current_price <= buy_price and random.random() < 0.1:
                # Simulate buy order filled
                order_id = f"buy-{int(time.time())}"
                btc_amount = round(1000 / current_price, 8)
                
                # Add to open orders
                self.state["open_orders"].append({
                    "id": order_id,
                    "type": "buy",
                    "price": current_price,
                    "amount": btc_amount,
                    "status": "filled",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add to grid history
                self.state["grid_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "buy",
                    "price": current_price,
                    "level": self.state["grid_prices"]["buy"].index(buy_price)
                })
                
                logger.info(f"Low-risk bot: Grid BUY order filled at ${current_price}")
                break
        
        for sell_price in self.state["grid_prices"]["sell"]:
            if current_price >= sell_price and random.random() < 0.1:
                # Simulate sell order filled
                order_id = f"sell-{int(time.time())}"
                btc_amount = round(1000 / current_price, 8)
                
                # Add to open orders
                self.state["open_orders"].append({
                    "id": order_id,
                    "type": "sell",
                    "price": current_price,
                    "amount": btc_amount,
                    "status": "filled",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add to grid history
                self.state["grid_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "sell",
                    "price": current_price,
                    "level": self.state["grid_prices"]["sell"].index(sell_price)
                })
                
                logger.info(f"Low-risk bot: Grid SELL order filled at ${current_price}")
                break
        
        # Keep only last 20 open orders
        if len(self.state["open_orders"]) > 20:
            self.state["open_orders"] = self.state["open_orders"][-20:]
        
        # Keep only last 100 grid history entries
        if len(self.state["grid_history"]) > 100:
            self.state["grid_history"] = self.state["grid_history"][-100:]
        
        # Save state
        self._save_state()
        
        return True


def run_dashboard_trader():
    """Run the dashboard-integrated mock trader."""
    print("\n" + "="*80)
    print("=" + " "*20 + "CRYPTO TRADING BOT WITH DASHBOARD" + " "*20 + "=")
    print("="*80 + "\n")
    
    try:
        # Initialize bot manager
        bot_manager = MockBotManager()
        
        # Connect bot manager to dashboard
        dashboard.set_bot_manager(bot_manager)
        
        # Start dashboard
        dashboard.port = 5002
        dashboard.start()
        print(f"Dashboard started at http://localhost:5002")
        
        # Start trading bots
        print("Starting trading bots...")
        bot_manager.start()
        print("Trading bots started")
        
        print("\nSystem is now running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        if 'bot_manager' in locals():
            bot_manager.stop()
        if 'dashboard' in locals():
            dashboard.stop()
        print("System stopped")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        print(f"Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    run_dashboard_trader()
