#!/usr/bin/env python3
"""
Run script for the Multi-Currency Trading Bot.

This script sets up and runs the multi-currency trading bot that analyzes
multiple cryptocurrencies and trades the best opportunities based on the
configured strategy.
"""

import os
import argparse
import sys
from loguru import logger

from src.multi_currency_bot import MultiCurrencyBot


def main():
    """
    Parse command line arguments and run the multi-currency trading bot.
    """
    parser = argparse.ArgumentParser(description="Run multi-currency trading bot")
    
    # General configuration
    parser.add_argument("--exchange", type=str, default=os.getenv("TRADING_EXCHANGE", "kucoin"),
                      help="Exchange to use (default: kucoin)")
    parser.add_argument("--strategy", type=str, default=os.getenv("STRATEGY", "rsi_strategy"),
                      help="Strategy to use (default: rsi_strategy)")
    parser.add_argument("--paper", action="store_true", default=True if os.getenv("PAPER_TRADING", "true").lower() == "true" else False,
                      help="Use paper trading mode")
    parser.add_argument("--dry-run", action="store_true", default=True if os.getenv("DRY_RUN", "true").lower() == "true" else False,
                      help="Analyze but don't execute trades")
    
    # Trading parameters
    parser.add_argument("--max-positions", type=int, default=int(os.getenv("MAX_POSITIONS", "3")),
                      help="Maximum number of concurrent positions")
    parser.add_argument("--quote-currency", type=str, default=os.getenv("QUOTE_CURRENCY", "USDT"),
                      help="Quote currency for trading pairs")
    parser.add_argument("--min-confidence", type=float, default=float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.4")),
                      help="Minimum confidence threshold for executing trades")
    
    # Runtime behavior
    parser.add_argument("--once", action="store_true",
                      help="Run the bot once and exit")
    parser.add_argument("--interval", type=int, default=int(os.getenv("INTERVAL_MINUTES", "60")),
                      help="Interval between runs in minutes")
    
    # Strategy-specific parameters
    parser.add_argument("--timeframe", type=str, default=os.getenv("TIMEFRAME", "1h"),
                      help="Timeframe for analysis")
    parser.add_argument("--risk-level", type=str, default=os.getenv("RISK_LEVEL", "medium"),
                      choices=["low", "medium", "high"],
                      help="Risk level for trading")
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="INFO")  # Add stderr handler with INFO level
    logger.add("logs/multi_currency_bot_{time}.log", rotation="500 MB")  # Add file handler
    
    # Log startup information
    logger.info("Starting Multi-Currency Trading Bot")
    logger.info(f"Configuration: exchange={args.exchange}, strategy={args.strategy}, "
               f"paper={args.paper}, dry_run={args.dry_run}")
    logger.info(f"Trading parameters: max_positions={args.max_positions}, "
               f"quote_currency={args.quote_currency}, min_confidence={args.min_confidence}")
    
    # Create and run the bot
    bot = MultiCurrencyBot(
        exchange_name=args.exchange,
        strategy_name=args.strategy,
        paper_trading=args.paper,
        max_positions=args.max_positions,
        quote_currency=args.quote_currency,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
        # Strategy-specific parameters
        timeframe=args.timeframe,
        risk_level=args.risk_level
    )
    
    # Run the bot
    if args.once:
        bot.run_once()
    else:
        bot.run_continuously(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
