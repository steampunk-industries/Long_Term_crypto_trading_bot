"""
Pytest configuration and fixtures.
This file contains shared fixtures and configurations for all tests.
"""

import datetime
import os
import json
from typing import Dict, Any, List, Generator
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.exchange.wrapper import ExchangeWrapper
from src.utils.database import Base
from src.utils.logging import logger
from src.strategies.base import BaseStrategy


# -----------------------------------------------------------------------------
# Mock Exchange Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_exchange():
    """Fixture that provides a mock exchange wrapper."""
    exchange_mock = MagicMock(spec=ExchangeWrapper)
    
    # Mock fetch_market_price
    exchange_mock.fetch_market_price.return_value = 50000.0
    
    # Mock fetch_balance
    exchange_mock.fetch_balance.return_value = {
        "free": {"USDT": 10000.0, "BTC": 0.1},
        "used": {"USDT": 0.0, "BTC": 0.0},
        "total": {"USDT": 10000.0, "BTC": 0.1},
    }
    
    # Mock fetch_ohlcv
    def mock_fetch_ohlcv(symbol, timeframe="1h", limit=100):
        # Generate mock OHLCV data
        now = int(datetime.datetime.now().timestamp() * 1000)
        interval = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
        seconds = interval.get(timeframe, 3600)
        
        price = 50000.0
        data = []
        
        for i in range(limit):
            timestamp = now - (limit - i - 1) * seconds * 1000
            open_price = price * (1 + 0.001 * (0.5 - np.random.random()))
            high_price = open_price * (1 + 0.002 * np.random.random())
            low_price = open_price * (1 - 0.002 * np.random.random())
            close_price = open_price * (1 + 0.001 * (0.5 - np.random.random()))
            volume = 100 * np.random.random()
            
            data.append([timestamp, open_price, high_price, low_price, close_price, volume])
            price = close_price
        
        return data
    
    exchange_mock.fetch_ohlcv.side_effect = mock_fetch_ohlcv
    
    # Mock place_market_order
    exchange_mock.place_market_order.return_value = {
        "id": "mock_order_id",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "price": 50000.0,
        "amount": 0.1,
        "filled": 0.1,
        "status": "closed",
        "timestamp": int(datetime.datetime.now().timestamp() * 1000),
    }
    
    # Mock place_limit_order
    exchange_mock.place_limit_order.return_value = {
        "id": "mock_order_id",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "limit",
        "price": 49000.0,
        "amount": 0.1,
        "filled": 0.0,
        "status": "open",
        "timestamp": int(datetime.datetime.now().timestamp() * 1000),
    }
    
    # Mock fetch_my_trades
    exchange_mock.fetch_my_trades.return_value = []
    
    # Return the mock
    return exchange_mock


@pytest.fixture
def exchange_wrapper_patch(mock_exchange):
    """Patch ExchangeWrapper to return the mock exchange."""
    with patch("src.exchange.wrapper.ExchangeWrapper", return_value=mock_exchange) as patcher:
        yield patcher


# -----------------------------------------------------------------------------
# Mock Database Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def test_db():
    """Set up an in-memory SQLite database for testing."""
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create a session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create a session
    db = TestingSessionLocal()
    
    # Return the session and engine
    yield db
    
    # Close the session
    db.close()


@pytest.fixture
def db_session_patch(test_db):
    """Patch get_db to use the test database."""
    def mock_get_db():
        try:
            yield test_db
            test_db.commit()
        except Exception:
            test_db.rollback()
            raise
    
    with patch("src.utils.database.get_db", mock_get_db):
        yield


# -----------------------------------------------------------------------------
# Test Data Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_ohlcv_data():
    """Fixture that provides sample OHLCV data."""
    # Create a DataFrame with OHLCV data
    data = {
        "timestamp": pd.date_range(start="2023-01-01", periods=100, freq="H"),
        "open": np.random.normal(50000, 1000, 100),
        "high": np.random.normal(51000, 1000, 100),
        "low": np.random.normal(49000, 1000, 100),
        "close": np.random.normal(50000, 1000, 100),
        "volume": np.random.normal(100, 20, 100),
    }
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    
    # Add some technical indicators
    df["rsi"] = np.random.normal(50, 10, 100)
    df["ema_short"] = np.random.normal(50000, 1000, 100)
    df["ema_long"] = np.random.normal(50000, 1000, 100)
    df["macd"] = np.random.normal(0, 100, 100)
    df["macd_signal"] = np.random.normal(0, 100, 100)
    df["macd_hist"] = np.random.normal(0, 100, 100)
    df["bb_upper"] = df["close"] + np.random.normal(1000, 100, 100)
    df["bb_middle"] = df["close"]
    df["bb_lower"] = df["close"] - np.random.normal(1000, 100, 100)
    df["atr"] = np.random.normal(500, 100, 100)
    df["obv"] = np.cumsum(np.random.normal(0, 1000, 100))
    df["adx"] = np.random.normal(30, 5, 100)
    df["cci"] = np.random.normal(0, 100, 100)
    df["price_change"] = df["close"].pct_change().fillna(0)
    df["volume_change"] = df["volume"].pct_change().fillna(0)
    df["price_volatility"] = df["close"].pct_change().rolling(window=14).std().fillna(0)
    
    return df


@pytest.fixture
def sample_model_data(sample_ohlcv_data):
    """Fixture that provides sample data for training models."""
    # Create 3 classes with equal distribution
    y = np.zeros((len(sample_ohlcv_data), 3))
    
    # Randomly assign one-hot encoded classes
    for i in range(len(sample_ohlcv_data)):
        class_idx = np.random.randint(0, 3)
        y[i, class_idx] = 1
    
    return sample_ohlcv_data, y


# -----------------------------------------------------------------------------
# Strategy Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_strategy(mock_exchange):
    """Fixture that provides a mock strategy."""
    # Create a mock strategy
    strategy_mock = MagicMock(spec=BaseStrategy)
    
    # Set attributes
    strategy_mock.exchange = mock_exchange
    strategy_mock.symbol = "BTC/USDT"
    strategy_mock.bot_type = "test"
    strategy_mock.state = {}
    
    # Mock methods
    strategy_mock.calculate_position_size.return_value = 0.1
    
    return strategy_mock


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, check_index: bool = True) -> bool:
    """
    Compare two DataFrames for equality.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame
        check_index: Whether to check index equality
        
    Returns:
        True if equal, False otherwise
    """
    # Check columns
    if set(df1.columns) != set(df2.columns):
        return False
    
    # Check index if required
    if check_index and not df1.index.equals(df2.index):
        return False
    
    # Check data
    for col in df1.columns:
        if not np.array_equal(df1[col].values, df2[col].values):
            return False
    
    return True
