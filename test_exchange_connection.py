#!/usr/bin/env python3
"""
Simple test script to verify exchange connectivity and get market data
"""
import os
import sys
from datetime import datetime

# Set paper trading mode
os.environ["PAPER_TRADING"] = "true"
os.environ["USE_MULTI_EXCHANGE"] = "true"
os.environ["TRADING_EXCHANGE"] = "multi"

# Add project directory to path
sys.path.append(os.getcwd())

from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory

def test_exchanges():
    print("\n" + "=" * 50)
    print(" EXCHANGE CONNECTION TEST ".center(50, "="))
    print("=" * 50 + "\n")
    
    exchanges = ["binance", "coinbase", "gemini", "kucoin", "kraken", "multi"]
    results = {}
    
    for name in exchanges:
        print(f"Testing {name}...")
        exchange = ExchangeFactory.create_exchange_from_config(name)
        
        if not exchange:
            print(f"  ❌ Failed to create {name} exchange")
            continue
            
        # Test connection
        if exchange.connect():
            print(f"  ✅ Connected to {name}")
            
            # Get ticker
            try:
                ticker = exchange.get_ticker("BTC/USDT")
                price = ticker.get('last', 0)
                
                if price > 0:
                    print(f"  ✅ BTC Price: ${price:,.2f}")
                    results[name] = price
                else:
                    print(f"  ❌ Invalid price data")
            except Exception as e:
                print(f"  ❌ Error getting ticker: {e}")
        else:
            print(f"  ❌ Connection failed")
    
    # Print summary
    print("\n" + "=" * 50)
    print(" RESULTS SUMMARY ".center(50, "="))
    print("=" * 50)
    
    if results:
        for name, price in results.items():
            print(f"{name}: ${price:,.2f}")
    else:
        print("No successful connections to exchanges")
    
    return results

if __name__ == "__main__":
    # Run tests
    test_exchanges()
