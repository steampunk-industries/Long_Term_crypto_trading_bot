#!/usr/bin/env python3
"""
Simple mock trading script that simulates trading activity without relying on 
complex SQLAlchemy sessions. This is useful for demonstrating the dashboard without
running into database session issues.
"""

import os
import sys
import time
import random
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Configure logging
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

# Constants
INITIAL_CAPITAL = 10000.0
TRADING_PAIR = "BTC/USDT"
MOCK_EXCHANGE_STATE_FILE = "data/mock_exchange_state_binance.json"

class SimpleMockTrader:
    """
    A simplified mock trader that simulates trading activity for demonstration purposes.
    """
    
    def __init__(self):
        """Initialize the mock trader."""
        self.balance = {"USDT": INITIAL_CAPITAL, "BTC": 0.0}
        self.in_position = False
        self.position_size = 0.0
        self.entry_price = 0.0
        self.current_price = 45000.0  # Starting BTC price
        self.price_history = []
        self.trade_history = []
        self.cycle_count = 0
        
        # Technical indicators
        self.rsi = 50.0
        self.macd = 0.0
        self.signal = 0.0
        self.volume = 100.0
        
        # Alternative data
        self.sentiment_score = 0.0
        self.on_chain_metrics = {
            "exchange_inflow": 0.0,
            "exchange_outflow": 0.0,
            "miner_outflow": 0.0
        }
        
        # Load state if exists
        self._load_state()
        
        logger.info(f"Mock trader initialized with balance: {self.balance}")
    
    def _load_state(self):
        """Load state from file if it exists."""
        if os.path.exists(MOCK_EXCHANGE_STATE_FILE):
            try:
                with open(MOCK_EXCHANGE_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.balance = state.get('balance', self.balance)
                    self.in_position = state.get('in_position', self.in_position)
                    self.position_size = state.get('position_size', self.position_size)
                    self.entry_price = state.get('entry_price', self.entry_price)
                    self.current_price = state.get('current_price', self.current_price)
                    self.price_history = state.get('price_history', self.price_history)
                    self.trade_history = state.get('trade_history', self.trade_history)
                logger.info(f"Loaded state from {MOCK_EXCHANGE_STATE_FILE}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        os.makedirs(os.path.dirname(MOCK_EXCHANGE_STATE_FILE), exist_ok=True)
        state = {
            'balance': self.balance,
            'in_position': self.in_position,
            'position_size': self.position_size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'price_history': self.price_history[-100:] if len(self.price_history) > 100 else self.price_history,
            'trade_history': self.trade_history[-50:] if len(self.trade_history) > 50 else self.trade_history
        }
        
        try:
            with open(MOCK_EXCHANGE_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved state to {MOCK_EXCHANGE_STATE_FILE}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def _update_market_data(self):
        """Update market data with random variations to simulate market movements."""
        # Update price with random walk (slightly upward biased)
        price_change_pct = random.uniform(-0.005, 0.006)
        self.current_price *= (1 + price_change_pct)
        
        # Record price in history
        self.price_history.append({
            'timestamp': datetime.now().isoformat(),
            'price': self.current_price
        })
        
        # Update technical indicators
        self.rsi += random.uniform(-5, 5)
        self.rsi = max(min(self.rsi, 90), 10)  # Keep RSI between 10 and 90
        
        self.macd += random.uniform(-0.5, 0.5)
        self.signal += random.uniform(-0.3, 0.3)
        
        self.volume *= (1 + random.uniform(-0.2, 0.3))
        
        # Update alternative data
        self.sentiment_score = random.uniform(-1, 1)
        self.on_chain_metrics = {
            "exchange_inflow": random.uniform(0, 100),
            "exchange_outflow": random.uniform(0, 100),
            "miner_outflow": random.uniform(0, 50)
        }
        
        logger.info(f"Current price: ${self.current_price:.2f}, RSI: {self.rsi:.2f}")
    
    def _make_trading_decision(self):
        """Make a trading decision based on market data and indicators."""
        # Simple trading logic: buy when RSI < 30, sell when RSI > 70
        if not self.in_position and self.rsi < 30:
            return 'buy'
        elif self.in_position and self.rsi > 70:
            return 'sell'
        elif self.in_position and (self.current_price < self.entry_price * 0.95):
            return 'sell'  # Stop loss
        elif self.in_position and (self.current_price > self.entry_price * 1.1):
            return 'sell'  # Take profit
        return None
    
    def _execute_trade(self, action):
        """Execute a trade action."""
        if action == 'buy' and not self.in_position:
            # Calculate position size (use 90% of USDT balance)
            amount_to_spend = self.balance['USDT'] * 0.9
            btc_amount = amount_to_spend / self.current_price
            
            # Update balance
            self.balance['USDT'] -= amount_to_spend
            self.balance['BTC'] += btc_amount
            
            # Update position info
            self.in_position = True
            self.position_size = btc_amount
            self.entry_price = self.current_price
            
            # Record trade
            trade = {
                'timestamp': datetime.now().isoformat(),
                'action': 'buy',
                'price': self.current_price,
                'amount': btc_amount,
                'value': amount_to_spend
            }
            self.trade_history.append(trade)
            
            logger.info(f"BUY: {btc_amount:.8f} BTC at ${self.current_price:.2f}")
            
        elif action == 'sell' and self.in_position:
            # Calculate value
            value = self.balance['BTC'] * self.current_price
            
            # Update balance
            self.balance['USDT'] += value
            btc_amount = self.balance['BTC']
            self.balance['BTC'] = 0.0
            
            # Calculate profit/loss
            profit = value - (self.position_size * self.entry_price)
            profit_pct = (self.current_price - self.entry_price) / self.entry_price * 100
            
            # Update position info
            self.in_position = False
            self.position_size = 0.0
            
            # Record trade
            trade = {
                'timestamp': datetime.now().isoformat(),
                'action': 'sell',
                'price': self.current_price,
                'amount': btc_amount,
                'value': value,
                'profit': profit,
                'profit_pct': profit_pct
            }
            self.trade_history.append(trade)
            
            logger.info(f"SELL: {btc_amount:.8f} BTC at ${self.current_price:.2f} (P/L: ${profit:.2f}, {profit_pct:.2f}%)")
    
    def run_cycle(self):
        """Run one trading cycle."""
        self.cycle_count += 1
        
        # Update market data
        self._update_market_data()
        
        # Make trading decision
        action = self._make_trading_decision()
        
        # Execute trade if needed
        if action:
            self._execute_trade(action)
        
        # Calculate portfolio value
        portfolio_value = self.balance['USDT'] + (self.balance['BTC'] * self.current_price)
        
        # Log status
        status_msg = (
            f"Cycle {self.cycle_count} | "
            f"Price: ${self.current_price:.2f} | "
            f"RSI: {self.rsi:.2f} | "
            f"Position: {'YES' if self.in_position else 'NO'} | "
            f"Portfolio: ${portfolio_value:.2f}"
        )
        print(status_msg)
        
        # Every 5 cycles, save state
        if self.cycle_count % 5 == 0:
            self._save_state()
        
        return {
            'cycle': self.cycle_count,
            'price': self.current_price,
            'portfolio_value': portfolio_value,
            'in_position': self.in_position,
            'action': action
        }


def run_mock_trading():
    """Run the mock trading system."""
    print("\n" + "="*80)
    print("=" + " "*25 + "CRYPTO TRADING BOT SIMULATION" + " "*25 + "=")
    print("="*80 + "\n")
    print("Starting mock trading system with alternative data sources...")
    print("Bot will execute a trading cycle every 30 seconds.\n")
    
    trader = SimpleMockTrader()
    
    print(f"Connected to mock exchange (Binance) in paper trading mode")
    print(f"Trading pair: {TRADING_PAIR}")
    print(f"Initial balance: {trader.balance}")
    print(f"Log file: logs/crypto_bot.log\n")
    print("Press Ctrl+C to stop the trading bot.\n")
    
    try:
        while True:
            result = trader.run_cycle()
            time.sleep(30)  # Wait 30 seconds between cycles
    except KeyboardInterrupt:
        print("\nMock trading stopped by user.")
        trader._save_state()  # Save final state
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    run_mock_trading()
