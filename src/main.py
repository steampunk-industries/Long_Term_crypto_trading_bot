#!/usr/bin/env python3
import os
import sys
import argparse
import time
from loguru import logger

from src.config import config
from src.bot import TradingBot
from src.dashboard.app import run_dashboard

def setup_logging():
    """
    Set up logging configuration.
    """
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
        "logs/crypto_bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info(f"Logging initialized with level {config.LOG_LEVEL}")

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Bot command
    bot_parser = subparsers.add_parser('bot', help='Run the trading bot')
    bot_parser.add_argument('--interval', type=int, default=60, help='Interval between runs in minutes')
    bot_parser.add_argument('--once', action='store_true', help='Run the bot once and exit')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Run the web dashboard')
    
    # Both command
    both_parser = subparsers.add_parser('both', help='Run both the bot and dashboard')
    both_parser.add_argument('--interval', type=int, default=60, help='Interval between bot runs in minutes')
    
    return parser.parse_args()

def main():
    """
    Main entry point for the application.
    """
    # Set up logging
    setup_logging()
    
    # Parse command-line arguments
    args = parse_args()
    
    # Validate configuration
    config.validate()
    
    # Run the appropriate command
    if args.command == 'bot':
        # Run the trading bot
        bot = TradingBot()
        
        if args.once:
            logger.info("Running bot once")
            bot.run_once()
        else:
            logger.info(f"Running bot continuously with {args.interval} minute intervals")
            bot.run_continuously(interval_minutes=args.interval)
    
    elif args.command == 'dashboard':
        # Run the dashboard
        run_dashboard()
    
    elif args.command == 'both':
        # Run both the bot and dashboard
        # For this, we'll run the bot in a separate thread
        import threading
        
        bot = TradingBot()
        
        def run_bot():
            logger.info(f"Running bot continuously with {args.interval} minute intervals")
            bot.run_continuously(interval_minutes=args.interval)
        
        # Start the bot in a separate thread
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True  # This makes the thread exit when the main program exits
        bot_thread.start()
        
        # Run the dashboard in the main thread
        run_dashboard()
    
    else:
        # No command specified, show help
        logger.error("No command specified")
        print("Please specify a command. Use --help for more information.")
        sys.exit(1)

if __name__ == '__main__':
    main()
