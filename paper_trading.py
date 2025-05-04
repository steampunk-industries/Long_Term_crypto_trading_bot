#!/usr/bin/env python3
"""
Paper trading script for the crypto trading bot.
Runs the bot in paper trading mode with specified settings.
"""

import argparse
import os
import sys
import time
import datetime
import signal
from typing import List, Dict, Any, Optional

# Ensure paper trading mode is set in environment
os.environ["PAPER_TRADING"] = "true"

# Import bot modules
from src.main import CryptoTradingBot
from src.config import settings
from src.utils.logging import logger
from src.utils.database import init_db, health_check
from src.utils.metrics import start_metrics_server


def setup_environment() -> bool:
    """
    Set up the environment for paper trading.
    
    Returns:
        True if setup was successful, False otherwise.
    """
    try:
        # Check if .env file exists
        if not os.path.exists(".env"):
            print("ERROR: .env file not found. Please copy .env.example to .env and configure it.")
            return False
        
        # Verify database connection
        if not health_check():
            print("ERROR: Database connection failed. Please check your database settings.")
            return False
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"Error setting up environment: {e}")
        return False


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Crypto Trading Bot - Paper Trading Mode")
    
    parser.add_argument(
        "--exchange", 
        type=str, 
        default="binance", 
        help="Exchange name (default: binance)"
    )
    
    parser.add_argument(
        "--symbol", 
        type=str, 
        default=None, 
        help=f"Trading symbol (default: {settings.trading.symbol})"
    )
    
    # Strategy selection arguments
    strategy_group = parser.add_argument_group("Strategy Selection")
    strategy_group.add_argument("--low-risk", action="store_true", help="Run low-risk strategy")
    strategy_group.add_argument("--medium-risk", action="store_true", help="Run medium-risk strategy")
    strategy_group.add_argument("--high-risk", action="store_true", help="Run high-risk strategy")
    strategy_group.add_argument("--all", action="store_true", help="Run all strategies (default)")
    
    # Portfolio settings
    portfolio_group = parser.add_argument_group("Portfolio Settings")
    portfolio_group.add_argument(
        "--initial-capital", 
        type=float, 
        default=None, 
        help=f"Initial capital for paper trading (default: {settings.trading.initial_capital})"
    )
    
    portfolio_group.add_argument(
        "--max-drawdown", 
        type=float, 
        default=None, 
        help=f"Maximum portfolio drawdown (default: {settings.portfolio.max_portfolio_drawdown})"
    )
    
    # Display options
    display_group = parser.add_argument_group("Display Options")
    display_group.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def print_header():
    """Print header information about the bot."""
    print("\n" + "=" * 80)
    print(" CRYPTO TRADING BOT - PAPER TRADING MODE ".center(80, "="))
    print("=" * 80)
    print(f"Date/Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Paper Trading Mode: Enabled")
    print(f"Default Trading Symbol: {settings.trading.symbol}")
    print(f"Initial Capital: ${settings.trading.initial_capital:,.2f}")
    print("=" * 80 + "\n")


def run_paper_trading(args: argparse.Namespace) -> None:
    """
    Run the bot in paper trading mode.
    
    Args:
        args: Command-line arguments.
    """
    # Print header
    print_header()
    
    # Set verbose logging if requested
    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
        print("Verbose logging enabled")
    
    # Set initial capital if provided
    if args.initial_capital:
        os.environ["INITIAL_CAPITAL"] = str(args.initial_capital)
        print(f"Initial capital set to ${args.initial_capital:,.2f}")
    
    # Set max drawdown if provided
    max_drawdown = args.max_drawdown or settings.portfolio.max_portfolio_drawdown
    
    # Determine which strategies to run
    run_low_risk = args.low_risk or args.all
    run_medium_risk = args.medium_risk or args.all
    run_high_risk = args.high_risk or args.all
    
    # If no strategies specified, run all
    if not (run_low_risk or run_medium_risk or run_high_risk):
        run_low_risk = run_medium_risk = run_high_risk = True
    
    # Print enabled strategies
    strategies = []
    if run_low_risk:
        strategies.append("Low-Risk")
    if run_medium_risk:
        strategies.append("Medium-Risk")
    if run_high_risk:
        strategies.append("High-Risk")
    
    print(f"Enabled Strategies: {', '.join(strategies)}")
    print(f"Exchange: {args.exchange}")
    print(f"Symbol: {args.symbol or settings.trading.symbol}")
    print(f"Max Drawdown: {max_drawdown:.1%}")
    print("\nStarting bot...\n")
    
    # Initialize bot
    bot = CryptoTradingBot(global_max_drawdown=max_drawdown)
    
    try:
        # Initialize database
        init_db()
        
        # Initialize bots
        bot.initialize_bots(
            exchange_name=args.exchange,
            symbol=args.symbol,
            run_low_risk=run_low_risk,
            run_medium_risk=run_medium_risk,
            run_high_risk=run_high_risk,
        )
        
        # Set up signal handlers
        def signal_handler(sig, frame):
            print(f"\nSignal {sig} received, stopping bot...")
            bot.stop()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Print dashboard info
        dashboard_url = f"http://{settings.dashboard.host}:{settings.dashboard.port}"
        print(f"Web dashboard available at: {dashboard_url}")
        print(f"Log file: {settings.logging.log_file}")
        print("\nPress Ctrl+C to stop the bot\n")
        
        # Run bot
        bot.run()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nError running bot: {e}")
    finally:
        # Ensure bot is stopped
        bot.stop()


def main():
    """Main entry point."""
    # Check and setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Parse arguments
    args = parse_args()
    
    # Run paper trading
    run_paper_trading(args)


if __name__ == "__main__":
    main()
