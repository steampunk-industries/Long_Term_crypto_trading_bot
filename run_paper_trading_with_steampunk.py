#!/usr/bin/env python3
"""
Run the crypto trading bot in paper trading mode with steampunk.holdings integration.
This script configures the bot to use the multi-exchange aggregator and steampunk.holdings integration.
"""

import os
import sys
import argparse
import time
from datetime import datetime
import signal

# Set paper trading mode
os.environ["PAPER_TRADING"] = "true"
os.environ["USE_MULTI_EXCHANGE"] = "true"
os.environ["TRADING_EXCHANGE"] = "multi"

from loguru import logger
from src.config import config
from src.bot import TradingBot
from src.database.models import init_db
from src.integrations.steampunk_holdings import steampunk_integration


def setup_logging():
    """Set up logging configuration."""
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logger
    os.makedirs('logs', exist_ok=True)
    logger.add(
        "logs/paper_trading_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run Paper Trading Bot with Steampunk Holdings Integration")
    
    parser.add_argument(
        "--symbol", 
        type=str, 
        default=config.TRADING_SYMBOL,
        help=f"Trading symbol (default: {config.TRADING_SYMBOL})"
    )
    
    parser.add_argument(
        "--interval", 
        type=int, 
        default=15,
        help="Interval between runs in minutes (default: 15)"
    )
    
    parser.add_argument(
        "--exchanges",
        type=str,
        default="coinbase,gemini,kucoin,kraken",
        help="Comma-separated list of exchanges to use (default: coinbase,gemini,kucoin,kraken)"
    )
    
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=config.INITIAL_CAPITAL,
        help=f"Initial capital in USDT (default: {config.INITIAL_CAPITAL})"
    )
    
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=config.DASHBOARD_PORT,
        help=f"Dashboard port (default: {config.DASHBOARD_PORT})"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def print_header(args):
    """Print header information."""
    print("\n" + "=" * 80)
    print(" CRYPTO TRADING BOT - PAPER TRADING WITH STEAMPUNK.HOLDINGS ".center(80, "="))
    print("=" * 80)
    print(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Trading Symbol: {args.symbol}")
    print(f"Exchanges: {args.exchanges}")
    print(f"Initial Capital: ${args.initial_capital:,.2f}")
    print(f"Run Interval: {args.interval} minutes")
    
    # Check steampunk.holdings integration
    if steampunk_integration.enabled:
        print("Steampunk Holdings Integration: Enabled")
    else:
        print("Steampunk Holdings Integration: Disabled (missing API credentials)")
    
    print("=" * 80)


def setup_environment(args):
    """Set up the environment for paper trading."""
    # Set environment variables
    os.environ["TRADING_SYMBOL"] = args.symbol
    os.environ["INITIAL_CAPITAL"] = str(args.initial_capital)
    os.environ["DASHBOARD_PORT"] = str(args.dashboard_port)
    
    # Set exchanges for multi-exchange
    os.environ["MULTI_EXCHANGE_SOURCES"] = args.exchanges
    
    # Set verbose logging if requested
    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
        print("Verbose logging enabled")
    
    # Initialize database
    if not init_db():
        print("ERROR: Failed to initialize database. Exiting.")
        return False
    
    return True


def run_bot(args):
    """Run the trading bot."""
    # Initialize bot
    bot = TradingBot()
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        print(f"\nSignal {sig} received, stopping bot...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print dashboard info
    dashboard_url = f"http://{config.DASHBOARD_HOST}:{args.dashboard_port}"
    print(f"\nWeb dashboard available at: {dashboard_url}")
    print(f"Log file: logs/paper_trading_{datetime.now().strftime('%Y-%m-%d')}.log")
    print("\nPress Ctrl+C to stop the bot\n")
    
    # Run bot continuously
    bot.run_continuously(interval_minutes=args.interval)


def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Parse arguments
    args = parse_args()
    
    # Print header
    print_header(args)
    
    # Set up environment
    if not setup_environment(args):
        return 1
    
    # Run bot
    try:
        run_bot(args)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nError running bot: {e}")
        logger.exception("Error running bot")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
