"""
Test module for the exchange wrapper.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch, PropertyMock, ANY
import datetime
import ccxt

from src.exchange.wrapper import ExchangeWrapper, ExchangeNotAvailableError


@pytest.mark.unit
class TestExchangeWrapper:
    """Tests for the ExchangeWrapper class."""

    @pytest.fixture
    def mock_ccxt_exchange(self):
        """Create a mock ccxt exchange."""
        mock_exchange = MagicMock()
        
        # Mock fetchTicker
        mock_exchange.fetchTicker.return_value = {
            "symbol": "BTC/USDT",
            "last": 50000.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 100.0,
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        }
        
        # Mock fetchBalance
        mock_exchange.fetchBalance.return_value = {
            "free": {"USDT": 10000.0, "BTC": 0.1},
            "used": {"USDT": 0.0, "BTC": 0.0},
            "total": {"USDT": 10000.0, "BTC": 0.1},
        }
        
        # Mock fetchOHLCV
        def mock_fetch_ohlcv(symbol, timeframe="1h", limit=100):
            now = int(datetime.datetime.now().timestamp() * 1000)
            interval = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
            seconds = interval.get(timeframe, 3600)
            
            data = []
            price = 50000.0
            
            for i in range(limit):
                timestamp = now - (limit - i - 1) * seconds * 1000
                open_price = price * (1 + 0.001 * (0.5 - 0.5))
                high_price = open_price * 1.002
                low_price = open_price * 0.998
                close_price = open_price * (1 + 0.001 * (0.5 - 0.5))
                volume = 100
                
                data.append([timestamp, open_price, high_price, low_price, close_price, volume])
                price = close_price
            
            return data
        
        mock_exchange.fetchOHLCV.side_effect = mock_fetch_ohlcv
        
        # Mock createMarketOrder
        mock_exchange.createMarketOrder.return_value = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "price": 50000.0,
            "amount": 0.1,
            "filled": 0.1,
            "status": "closed",
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        }
        
        # Mock createLimitOrder
        mock_exchange.createLimitOrder.return_value = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "price": 50000.0,
            "amount": 0.1,
            "filled": 0.0,
            "status": "open",
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        }
        
        # Mock fetchOrder
        mock_exchange.fetchOrder.return_value = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "price": 50000.0,
            "amount": 0.1,
            "filled": 0.0,
            "status": "open",
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        }
        
        # Mock fetchOpenOrders
        mock_exchange.fetchOpenOrders.return_value = [
            {
                "id": "12345",
                "symbol": "BTC/USDT",
                "side": "buy",
                "type": "limit",
                "price": 50000.0,
                "amount": 0.1,
                "filled": 0.0,
                "status": "open",
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            }
        ]
        
        # Mock fetchClosedOrders
        mock_exchange.fetchClosedOrders.return_value = [
            {
                "id": "54321",
                "symbol": "BTC/USDT",
                "side": "buy",
                "type": "market",
                "price": 50000.0,
                "amount": 0.1,
                "filled": 0.1,
                "status": "closed",
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            }
        ]
        
        # Mock fetchMyTrades
        mock_exchange.fetchMyTrades.return_value = [
            {
                "id": "trade_12345",
                "order": "12345",
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": 50000.0,
                "amount": 0.1,
                "cost": 5000.0,
                "fee": {"cost": 5.0, "currency": "USDT"},
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            }
        ]
        
        # Mock cancelOrder
        mock_exchange.cancelOrder.return_value = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "price": 50000.0,
            "amount": 0.1,
            "filled": 0.0,
            "status": "canceled",
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        }
        
        # Set up rate limit
        type(mock_exchange).rateLimit = PropertyMock(return_value=1000)
        
        return mock_exchange

    @pytest.fixture
    def wrapper(self, mock_ccxt_exchange):
        """Create an exchange wrapper with a mock ccxt exchange."""
        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            wrapper = ExchangeWrapper("binance")
            return wrapper

    def test_init(self):
        """Test the constructor."""
        # Test with valid exchange name
        with patch("ccxt.binance") as mock_binance:
            wrapper = ExchangeWrapper("binance")
            assert wrapper.exchange_name == "binance"
            assert wrapper.retry_count == 3
            assert wrapper.retry_delay == 1.0
            mock_binance.assert_called_once()
        
        # Test with invalid exchange name
        with pytest.raises(ValueError):
            ExchangeWrapper("invalid_exchange")

    def test_fetch_market_price(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_market_price method."""
        # Test with default symbol
        price = wrapper.fetch_market_price("BTC/USDT")
        assert price == 50000.0
        mock_ccxt_exchange.fetchTicker.assert_called_once_with("BTC/USDT")
        
        # Test with price source = 'bid'
        mock_ccxt_exchange.fetchTicker.reset_mock()
        price = wrapper.fetch_market_price("BTC/USDT", price_source="bid")
        assert price == 49900.0
        
        # Test with price source = 'ask'
        mock_ccxt_exchange.fetchTicker.reset_mock()
        price = wrapper.fetch_market_price("BTC/USDT", price_source="ask")
        assert price == 50100.0

    def test_fetch_balance(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_balance method."""
        balance = wrapper.fetch_balance()
        assert balance["free"]["USDT"] == 10000.0
        assert balance["free"]["BTC"] == 0.1
        assert balance["total"]["USDT"] == 10000.0
        mock_ccxt_exchange.fetchBalance.assert_called_once()

    def test_fetch_ohlcv(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_ohlcv method."""
        ohlcv = wrapper.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=10)
        assert len(ohlcv) == 10
        assert len(ohlcv[0]) == 6  # timestamp, open, high, low, close, volume
        mock_ccxt_exchange.fetchOHLCV.assert_called_once_with("BTC/USDT", timeframe="1h", limit=10)

    def test_place_market_order(self, wrapper, mock_ccxt_exchange):
        """Test the place_market_order method."""
        order = wrapper.place_market_order("BTC/USDT", "buy", 0.1)
        assert order["id"] == "12345"
        assert order["symbol"] == "BTC/USDT"
        assert order["side"] == "buy"
        assert order["type"] == "market"
        assert order["amount"] == 0.1
        mock_ccxt_exchange.createMarketOrder.assert_called_once_with("BTC/USDT", "buy", 0.1)

    def test_place_limit_order(self, wrapper, mock_ccxt_exchange):
        """Test the place_limit_order method."""
        order = wrapper.place_limit_order("BTC/USDT", "buy", 0.1, 50000.0)
        assert order["id"] == "12345"
        assert order["symbol"] == "BTC/USDT"
        assert order["side"] == "buy"
        assert order["type"] == "limit"
        assert order["price"] == 50000.0
        assert order["amount"] == 0.1
        mock_ccxt_exchange.createLimitOrder.assert_called_once_with("BTC/USDT", "buy", 0.1, 50000.0)

    def test_cancel_order(self, wrapper, mock_ccxt_exchange):
        """Test the cancel_order method."""
        order = wrapper.cancel_order("12345", "BTC/USDT")
        assert order["id"] == "12345"
        assert order["status"] == "canceled"
        mock_ccxt_exchange.cancelOrder.assert_called_once_with("12345", "BTC/USDT")

    def test_fetch_order(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_order method."""
        order = wrapper.fetch_order("12345", "BTC/USDT")
        assert order["id"] == "12345"
        assert order["symbol"] == "BTC/USDT"
        mock_ccxt_exchange.fetchOrder.assert_called_once_with("12345", "BTC/USDT")

    def test_fetch_open_orders(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_open_orders method."""
        orders = wrapper.fetch_open_orders("BTC/USDT")
        assert len(orders) == 1
        assert orders[0]["id"] == "12345"
        assert orders[0]["status"] == "open"
        mock_ccxt_exchange.fetchOpenOrders.assert_called_once_with("BTC/USDT")

    def test_fetch_closed_orders(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_closed_orders method."""
        orders = wrapper.fetch_closed_orders("BTC/USDT")
        assert len(orders) == 1
        assert orders[0]["id"] == "54321"
        assert orders[0]["status"] == "closed"
        mock_ccxt_exchange.fetchClosedOrders.assert_called_once_with("BTC/USDT")

    def test_fetch_my_trades(self, wrapper, mock_ccxt_exchange):
        """Test the fetch_my_trades method."""
        trades = wrapper.fetch_my_trades("BTC/USDT")
        assert len(trades) == 1
        assert trades[0]["id"] == "trade_12345"
        assert trades[0]["order"] == "12345"
        mock_ccxt_exchange.fetchMyTrades.assert_called_once_with("BTC/USDT")

    def test_cancel_all_orders(self, wrapper, mock_ccxt_exchange):
        """Test the cancel_all_orders method."""
        mock_ccxt_exchange.fetchOpenOrders.return_value = [
            {"id": "1", "symbol": "BTC/USDT"},
            {"id": "2", "symbol": "BTC/USDT"},
        ]
        
        orders = wrapper.cancel_all_orders("BTC/USDT")
        assert len(orders) == 2
        assert mock_ccxt_exchange.cancelOrder.call_count == 2

    def test_retry_mechanism(self, mock_ccxt_exchange):
        """Test the retry mechanism for transient errors."""
        # Create a mock that fails twice with network error, then succeeds
        side_effects = [
            ccxt.NetworkError("Network error"),
            ccxt.NetworkError("Network error"),
            {"symbol": "BTC/USDT", "last": 50000.0}
        ]
        mock_ccxt_exchange.fetchTicker.side_effect = side_effects
        
        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            wrapper = ExchangeWrapper("binance", retry_count=3, retry_delay=0.01)
            price = wrapper.fetch_market_price("BTC/USDT")
            
            # Should succeed on the third attempt
            assert price == 50000.0
            assert mock_ccxt_exchange.fetchTicker.call_count == 3

    def test_retry_exhaustion(self, mock_ccxt_exchange):
        """Test that an exception is raised when retries are exhausted."""
        # Create a mock that always fails with network error
        mock_ccxt_exchange.fetchTicker.side_effect = ccxt.NetworkError("Network error")
        
        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            wrapper = ExchangeWrapper("binance", retry_count=3, retry_delay=0.01)
            
            # Should raise ExchangeNotAvailableError after 3 attempts
            with pytest.raises(ExchangeNotAvailableError):
                wrapper.fetch_market_price("BTC/USDT")
            
            assert mock_ccxt_exchange.fetchTicker.call_count == 3
