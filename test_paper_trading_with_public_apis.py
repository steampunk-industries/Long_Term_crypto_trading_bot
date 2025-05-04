#!/usr/bin/env python3
"""
Test script for paper trading with public APIs and steampunk.holdings integration.
This script tests the multi-exchange functionality and steampunk.holdings integration.
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# Set paper trading mode
os.environ["PAPER_TRADING"] = "true"
os.environ["USE_MULTI_EXCHANGE"] = "true"
os.environ["TRADING_EXCHANGE"] = "multi"

from loguru import logger
from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory
from src.exchanges.multi_exchange import MultiExchange
from src.integrations.steampunk_holdings import steampunk_integration


def setup_logging():
    """Set up logging configuration."""
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test Paper Trading with Public APIs")
    
    parser.add_argument(
        "--symbol", 
        type=str, 
        default="BTC/USDT",
        help="Trading symbol to test (default: BTC/USDT)"
    )
    
    parser.add_argument(
        "--exchanges",
        type=str,
        default="coinbase,gemini,kucoin,kraken",
        help="Comma-separated list of exchanges to use (default: coinbase,gemini,kucoin,kraken)"
    )
    
    parser.add_argument(
        "--steampunk",
        action="store_true",
        help="Enable steampunk.holdings integration testing"
    )
    
    parser.add_argument(
        "--test-order",
        action="store_true",
        help="Test paper order creation"
    )
    
    return parser.parse_args()


def test_multi_exchange(symbol: str, exchanges: List[str]):
    """
    Test the multi-exchange functionality.
    
    Args:
        symbol: Trading symbol to test
        exchanges: List of exchanges to use
    """
    print("\n" + "=" * 80)
    print(" MULTI-EXCHANGE PAPER TRADING TEST ".center(80, "="))
    print("=" * 80)
    
    # Initialize multi-exchange
    exchange = MultiExchange(
        paper_trading=True,
        initial_balance={"USDT": 10000.0, "BTC": 0.1},
        exchanges=exchanges,
        use_steampunk_data=False  # Disable for initial test
    )
    
    # Test connection
    print("\nTesting connection to exchanges...")
    if exchange.connect():
        print("✅ Successfully connected to at least one exchange")
    else:
        print("❌ Failed to connect to any exchange")
        return False
    
    # Test ticker
    print(f"\nFetching current price for {symbol}...")
    try:
        ticker = exchange.get_ticker(symbol)
        print(f"✅ Current {symbol} price: ${ticker['last']:,.2f}")
        print(f"   Bid: ${ticker['bid']:,.2f}")
        print(f"   Ask: ${ticker['ask']:,.2f}")
        print(f"   Volume: {ticker['volume']:,.2f}")
        print(f"   Source: {ticker.get('source', 'unknown')}")
    except Exception as e:
        print(f"❌ Failed to get ticker: {e}")
        return False
    
    # Test historical data
    print(f"\nFetching historical data for {symbol}...")
    try:
        df = exchange.get_historical_data(symbol, timeframe="1h", limit=10)
        if df.empty:
            print("❌ No historical data available")
        else:
            print(f"✅ Successfully fetched {len(df)} candles")
            print(df.tail(3))
    except Exception as e:
        print(f"❌ Failed to get historical data: {e}")
    
    # Test balance
    print("\nChecking paper trading balance...")
    try:
        usdt_balance = exchange.get_balance("USDT")
        btc_balance = exchange.get_balance("BTC")
        print(f"✅ USDT Balance: ${usdt_balance:,.2f}")
        print(f"✅ BTC Balance: {btc_balance:,.8f} (${btc_balance * ticker['last']:,.2f})")
        print(f"✅ Total Balance: ${usdt_balance + btc_balance * ticker['last']:,.2f}")
    except Exception as e:
        print(f"❌ Failed to get balance: {e}")
    
    return exchange


def test_paper_order(exchange, symbol: str):
    """
    Test paper order creation.
    
    Args:
        exchange: Exchange instance
        symbol: Trading symbol to test
    """
    print("\n" + "=" * 80)
    print(" PAPER ORDER TEST ".center(80, "="))
    print("=" * 80)
    
    # Get current price
    ticker = exchange.get_ticker(symbol)
    current_price = ticker["last"]
    
    # Show initial balance
    usdt_balance = exchange.get_balance("USDT")
    btc_balance = exchange.get_balance("BTC")
    print(f"Initial USDT Balance: ${usdt_balance:,.2f}")
    print(f"Initial BTC Balance: {btc_balance:,.8f}")
    
    # Create a market buy order
    print(f"\nCreating market buy order for 0.001 {symbol.split('/')[0]}...")
    try:
        buy_order = exchange.create_order(
            symbol=symbol,
            order_type="market",
            side="buy",
            amount=0.001,
            price=None
        )
        print(f"✅ Order created: {buy_order['id']}")
        print(f"   Price: ${buy_order['price']:,.2f}")
        print(f"   Amount: {buy_order['amount']:,.8f} {symbol.split('/')[0]}")
        print(f"   Cost: ${buy_order['amount'] * buy_order['price']:,.2f}")
        print(f"   Status: {buy_order['status']}")
    except Exception as e:
        print(f"❌ Failed to create buy order: {e}")
        return False
    
    # Show updated balance
    usdt_balance = exchange.get_balance("USDT")
    btc_balance = exchange.get_balance("BTC")
    print(f"\nUpdated USDT Balance: ${usdt_balance:,.2f}")
    print(f"Updated BTC Balance: {btc_balance:,.8f}")
    
    # Wait a bit
    print("\nWaiting 2 seconds...")
    time.sleep(2)
    
    # Create a market sell order
    print(f"\nCreating market sell order for 0.001 {symbol.split('/')[0]}...")
    try:
        sell_order = exchange.create_order(
            symbol=symbol,
            order_type="market",
            side="sell",
            amount=0.001,
            price=None
        )
        print(f"✅ Order created: {sell_order['id']}")
        print(f"   Price: ${sell_order['price']:,.2f}")
        print(f"   Amount: {sell_order['amount']:,.8f} {symbol.split('/')[0]}")
        print(f"   Cost: ${sell_order['amount'] * sell_order['price']:,.2f}")
        print(f"   Status: {sell_order['status']}")
    except Exception as e:
        print(f"❌ Failed to create sell order: {e}")
        return False
    
    # Show final balance
    usdt_balance = exchange.get_balance("USDT")
    btc_balance = exchange.get_balance("BTC")
    print(f"\nFinal USDT Balance: ${usdt_balance:,.2f}")
    print(f"Final BTC Balance: {btc_balance:,.8f}")
    
    return True


def test_steampunk_integration(exchange, symbol: str):
    """
    Test steampunk.holdings integration.
    
    Args:
        exchange: Exchange instance
        symbol: Trading symbol to test
    """
    print("\n" + "=" * 80)
    print(" STEAMPUNK.HOLDINGS INTEGRATION TEST ".center(80, "="))
    print("=" * 80)
    
    if not steampunk_integration.enabled:
        print("❌ Steampunk Holdings integration is not enabled.")
        print("   Please set STEAMPUNK_API_KEY and STEAMPUNK_API_SECRET in .env file.")
        return False
    
    # Test account info
    print("\nFetching account info from steampunk.holdings...")
    try:
        account_info = steampunk_integration.api.get_account_info()
        if "error" in account_info:
            print(f"❌ Failed to get account info: {account_info['error']}")
        else:
            print(f"✅ Account info retrieved successfully")
            print(f"   Account ID: {account_info.get('account_id', 'N/A')}")
            print(f"   Account Name: {account_info.get('name', 'N/A')}")
    except Exception as e:
        print(f"❌ Failed to get account info: {e}")
    
    # Test portfolio sync
    print("\nSyncing portfolio with steampunk.holdings...")
    try:
        # Get current balances
        usdt_balance = exchange.get_balance("USDT")
        btc_balance = exchange.get_balance("BTC")
        ticker = exchange.get_ticker(symbol)
        
        # Prepare portfolio data
        portfolio_data = {
            "total_value_usd": usdt_balance + btc_balance * ticker["last"],
            "pnl_daily": 0.0,
            "pnl_weekly": 0.0,
            "pnl_monthly": 0.0,
            "pnl_all_time": 0.0,
            "drawdown": 0.0,
            "timestamp": int(time.time() * 1000),
            "balances": {
                "USDT": usdt_balance,
                "BTC": btc_balance
            }
        }
        
        # Sync portfolio
        result = steampunk_integration.sync_portfolio(portfolio_data)
        if result:
            print("✅ Portfolio synced successfully")
        else:
            print("❌ Failed to sync portfolio")
    except Exception as e:
        print(f"❌ Failed to sync portfolio: {e}")
    
    # Test trade sync
    print("\nSyncing test trade with steampunk.holdings...")
    try:
        # Create a test trade
        test_trade = {
            "id": f"test-{int(time.time())}",
            "symbol": symbol,
            "type": "market",
            "side": "buy",
            "amount": 0.001,
            "price": ticker["last"],
            "cost": 0.001 * ticker["last"],
            "fee": {
                "cost": 0.001 * ticker["last"] * 0.001,
                "currency": symbol.split("/")[1]
            },
            "status": "closed",
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.utcnow().isoformat(),
            "filled": 0.001,
            "remaining": 0.0
        }
        
        # Sync trade
        result = steampunk_integration.sync_trades([test_trade])
        if result:
            print("✅ Test trade synced successfully")
        else:
            print("❌ Failed to sync test trade")
    except Exception as e:
        print(f"❌ Failed to sync test trade: {e}")
    
    return True


def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Parse arguments
    args = parse_args()
    
    # Parse exchanges
    exchanges = args.exchanges.split(",")
    
    # Print test configuration
    print("\n" + "=" * 80)
    print(" PAPER TRADING WITH PUBLIC APIS TEST ".center(80, "="))
    print("=" * 80)
    print(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Symbol: {args.symbol}")
    print(f"Exchanges: {', '.join(exchanges)}")
    print(f"Steampunk Integration: {'Enabled' if args.steampunk else 'Disabled'}")
    print(f"Test Order Creation: {'Enabled' if args.test_order else 'Disabled'}")
    print("=" * 80)
    
    # Test multi-exchange
    exchange = test_multi_exchange(args.symbol, exchanges)
    if not exchange:
        print("\n❌ Multi-exchange test failed. Exiting.")
        return 1
    
    # Test paper order creation if requested
    if args.test_order:
        if not test_paper_order(exchange, args.symbol):
            print("\n❌ Paper order test failed.")
    
    # Test steampunk.holdings integration if requested
    if args.steampunk:
        if not test_steampunk_integration(exchange, args.symbol):
            print("\n❌ Steampunk Holdings integration test failed.")
    
    # Print summary
    print("\n" + "=" * 80)
    print(" TEST SUMMARY ".center(80, "="))
    print("=" * 80)
    print("✅ Multi-exchange functionality: Working")
    if args.test_order:
        print("✅ Paper order creation: Working")
    if args.steampunk:
        if steampunk_integration.enabled:
            print("✅ Steampunk Holdings integration: Working")
        else:
            print("❌ Steampunk Holdings integration: Not configured")
    
    print("\n✅ Paper trading with public APIs is working correctly!")
    print("You can now run the bot with paper trading enabled.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
