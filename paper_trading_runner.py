#!/usr/bin/env python3
"""
Simplified paper trading runner focused on running the high risk strategy
with fewer complexities than the main paper_trading.py
"""

import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import os

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

def run_trading():
    try:
        # Import necessary components
        from src.utils.database import init_db
        from src.exchange.wrapper import ExchangeWrapper
        from src.strategies.high_risk import HighRiskStrategy
        
        # Initialize database
        init_db()
        
        # Print banner
        print("\n" + "="*80)
        print("=" + " "*30 + "CRYPTO TRADING BOT" + " "*30 + "=")
        print("="*80 + "\n")
        print("Starting paper trading with High-Risk strategy...")
        print("Bot will check for signals every 60 seconds.\n")
        
        # Initialize exchange
        exchange = ExchangeWrapper('binance', 'BTC/USDT', paper_trading=True)
        print(f"Connected to mock exchange (Binance) in paper trading mode")
        print(f"Trading pair: BTC/USDT")
        print(f"Initial balance: {exchange.get_balance()}")
        
        # Initialize strategy
        strategy = HighRiskStrategy('binance', 'BTC/USDT')
        print("\nTrading strategy initialized.")
        print("Running with alternative data sources.")
        print("Log file: logs/crypto_bot.log\n")
        print("Press Ctrl+C to stop the trading bot.\n")
        
        # Trading loop
        while True:
            try:
                # Run the strategy once
                analysis_result = strategy.run_once()
                
                if analysis_result:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Analysis complete - waiting 60 seconds")
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Waiting for next analysis cycle")
                
                # Wait for next cycle
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                print(f"Error in trading cycle: {e}")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\nTrading bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    run_trading()
