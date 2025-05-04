#!/usr/bin/env python3
"""
Test script to verify fixes and improvements.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exchanges.gemini_exchange import GeminiExchange
from src.exchanges.kraken_exchange import KrakenExchange
from src.strategies.moving_average_crossover import MovingAverageCrossover
from src.integrations.steampunk_holdings import steampunk_integration
from src.utils.service_monitor_adapter import report_service_failure, report_service_recovery
from src.database.models import initialize_database, User, Trade, PortfolioSnapshot, get_session

def test_exchange_api_consistency():
    """Test exchange API consistency fixes."""
    print("\n===== Testing Exchange API Consistency =====")
    
    # Test GeminiExchange place_order method
    print("\nTesting GeminiExchange place_order method...")
    gemini = GeminiExchange(paper_trading=True)
    
    # Verify place_order is an alias for create_order
    symbol = "BTC/USD"
    order_type = "market"
    side = "buy"
    amount = 0.01
    
    try:
        order = gemini.place_order(symbol, order_type, side, amount)
        print(f"✅ GeminiExchange place_order method works: {order['id']}")
    except Exception as e:
        print(f"❌ GeminiExchange place_order method failed: {e}")
    
    # Test KrakenExchange cancel_order method
    print("\nTesting KrakenExchange cancel_order method...")
    kraken = KrakenExchange(paper_trading=True)
    
    try:
        # Create an order first
        order = kraken.create_order(symbol, order_type, side, amount)
        order_id = order['id']
        
        # Now cancel it
        result = kraken.cancel_order(order_id, symbol)
        
        if result:
            print(f"✅ KrakenExchange cancel_order method works: Order {order_id} canceled")
        else:
            print(f"❌ KrakenExchange cancel_order method failed to cancel order {order_id}")
    except Exception as e:
        print(f"❌ KrakenExchange cancel_order test failed: {e}")

def test_strategy_risk_management():
    """Test strategy risk management improvements."""
    print("\n===== Testing Strategy Risk Management =====")
    
    # Create exchange and strategy
    exchange = GeminiExchange(paper_trading=True)
    strategy = MovingAverageCrossover(
        exchange=exchange,
        symbol="BTC/USDT",
        timeframe="1h",
        risk_level="medium",
        fast_ma_period=10,
        slow_ma_period=30
    )
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=50, freq='H')
    data = {
        'open': [45000 + i * 100 for i in range(50)],
        'high': [45500 + i * 100 for i in range(50)],
        'low': [44500 + i * 100 for i in range(50)],
        'close': [45200 + i * 100 for i in range(50)],
        'volume': [100 for _ in range(50)]
    }
    df = pd.DataFrame(data, index=dates)
    
    # Calculate moving averages (simulate a bullish crossover)
    df['fast_ma'] = df['close'].rolling(window=10).mean()
    df['slow_ma'] = df['close'].rolling(window=30).mean()
    
    # Modify the last few values to create a bullish crossover
    df.iloc[-2, df.columns.get_loc('fast_ma')] = df.iloc[-2, df.columns.get_loc('slow_ma')] - 10
    df.iloc[-1, df.columns.get_loc('fast_ma')] = df.iloc[-1, df.columns.get_loc('slow_ma')] + 10
    
    # Generate signals
    signal_type, confidence, metadata = strategy.generate_signals(df)
    
    print(f"\nSignal generated: {signal_type} with confidence {confidence:.2f}")
    print("Risk management metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    # Check if stop-loss and take-profit are included
    if 'stop_loss' in metadata and 'take_profit' in metadata:
        print("✅ Strategy includes stop-loss and take-profit levels")
    else:
        print("❌ Strategy is missing stop-loss or take-profit levels")
    
    # Run the strategy
    try:
        # Mock the get_historical_data method to return our sample data
        original_method = strategy.get_historical_data
        strategy.get_historical_data = lambda: df
        
        result = strategy.run()
        
        # Restore original method
        strategy.get_historical_data = original_method
        
        if result is not None:
            print("✅ Strategy run() method works and returns a result")
        else:
            print("ℹ️ Strategy run() method works but no trade was executed (likely due to confidence threshold)")
    except Exception as e:
        print(f"❌ Strategy run() method failed: {e}")

def test_service_monitoring():
    """Test service monitoring integration."""
    print("\n===== Testing Service Monitoring Integration =====")
    
    # Test service monitoring adapter
    print("\nTesting service monitoring adapter...")
    try:
        # Report a test failure
        report_service_failure("test_service", "This is a test failure")
        print("✅ Service failure reporting works")
        
        # Report recovery
        report_service_recovery("test_service")
        print("✅ Service recovery reporting works")
    except Exception as e:
        print(f"❌ Service monitoring adapter test failed: {e}")
    
    # Test Steampunk Holdings integration
    print("\nTesting Steampunk Holdings integration...")
    try:
        # Create a sample portfolio
        portfolio = {
            'total_value': 50000,
            'cash_value': 20000,
            'invested_value': 30000,
            'holdings': {
                'BTC': 0.5,
                'ETH': 5.0,
                'USDT': 20000
            }
        }
        
        # Try to sync portfolio (this will likely fail due to missing API keys, but we're testing the monitoring)
        steampunk_integration.sync_portfolio(portfolio)
        print("✅ Steampunk Holdings integration executed without errors")
    except Exception as e:
        print(f"❌ Steampunk Holdings integration test failed: {e}")

def test_database():
    """Test database models and initialization."""
    print("\n===== Testing Database =====")
    
    try:
        # Initialize database
        engine = initialize_database()
        print("✅ Database initialized successfully")
        
        # Test session connection
        session = get_session()
        print("✅ Database session established")
        
        # Test querying users
        user_count = session.query(User).count()
        print(f"Found {user_count} users in the database")
        
        # Test querying portfolio snapshots
        snapshot_count = session.query(PortfolioSnapshot).count()
        print(f"Found {snapshot_count} portfolio snapshots in the database")
        
        # Close session
        session.close()
    except Exception as e:
        print(f"❌ Database test failed: {e}")

def main():
    """Run all tests."""
    print("Starting tests for fixes and improvements...")
    
    # Run tests
    test_exchange_api_consistency()
    test_strategy_risk_management()
    test_service_monitoring()
    test_database()
    
    print("\nTests completed!")

if __name__ == "__main__":
    main()
