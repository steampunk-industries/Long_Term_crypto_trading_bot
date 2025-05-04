"""
Test module for the low-risk strategy.
"""

import pytest
from unittest.mock import MagicMock, patch, call

import pandas as pd
import numpy as np

from src.strategies.low_risk import LowRiskStrategy
from src.exchange.wrapper import ExchangeWrapper


@pytest.mark.unit
class TestLowRiskStrategy:
    """Test case for the low-risk strategy."""

    @pytest.fixture
    def strategy(self, mock_exchange):
        """Create a low-risk strategy with the mock exchange."""
        strategy = LowRiskStrategy(
            exchange_name="binance",
            symbol="BTC/USDT",
            grid_levels=3,
            grid_spacing=1.0,
        )
        strategy.exchange = mock_exchange
        strategy.state = {
            "open_orders": [],
            "last_price": 50000.0,
        }
        return strategy

    def test_calculate_position_size(self, strategy):
        """Test the calculate_position_size method."""
        # Calculate position size
        position_size = strategy.calculate_position_size(50000.0)
        
        # Check that the position size is correct
        assert round(position_size, 5) == 0.03333

    def test_calculate_grid_prices(self, strategy):
        """Test the _calculate_grid_prices method."""
        # Calculate grid prices
        grid_prices = strategy._calculate_grid_prices(50000.0)
        
        # Check that the grid prices are correct
        assert len(grid_prices["buy"]) == 3
        assert len(grid_prices["sell"]) == 3
        
        # Check buy prices (should be below current price)
        for i, price in enumerate(grid_prices["buy"]):
            expected_price = 50000.0 * (1 - (i + 1) * (1.0 / 100))
            assert abs(price - expected_price) < 0.01
        
        # Check sell prices (should be above current price)
        for i, price in enumerate(grid_prices["sell"]):
            expected_price = 50000.0 * (1 + (i + 1) * (1.0 / 100))
            assert abs(price - expected_price) < 0.01

    def test_place_grid_orders(self, strategy, mock_exchange):
        """Test the _place_grid_orders method."""
        # Place grid orders
        strategy._place_grid_orders(50000.0)
        
        # Check that place_limit_order was called the correct number of times
        assert mock_exchange.place_limit_order.call_count == 6  # 3 buy orders + 3 sell orders
        
        # Check that the open orders list was updated
        assert len(strategy.state["open_orders"]) == 6

    def test_should_reset_grid(self, strategy):
        """Test the _should_reset_grid method."""
        # Set last price
        strategy.state["last_price"] = 50000.0
        
        # Check that the grid should not be reset for small price changes
        assert not strategy._should_reset_grid(50100.0)
        
        # Check that the grid should be reset for large price changes
        assert strategy._should_reset_grid(51500.0)

    def test_run_strategy(self, strategy, mock_exchange):
        """Test the run_strategy method."""
        # Run the strategy
        strategy.run_strategy()
        
        # Check that fetch_market_price was called
        mock_exchange.fetch_market_price.assert_called_once()
        
        # Check that place_limit_order was called
        assert mock_exchange.place_limit_order.called
        
        # Check that the last price was updated
        assert strategy.state["last_price"] == 50000.0

    def test_manage_existing_orders(self, strategy, mock_exchange):
        """Test the _manage_existing_orders method."""
        # Add some open orders to the state
        strategy.state["open_orders"] = [
            {"id": "1", "side": "buy", "price": 49000.0, "amount": 0.1},
            {"id": "2", "side": "sell", "price": 51000.0, "amount": 0.1},
        ]
        
        # Mock fetch_order to return filled order for the first order
        mock_exchange.fetch_order.side_effect = [
            {"id": "1", "status": "closed", "filled": 0.1},  # First order filled
            {"id": "2", "status": "open", "filled": 0.0},    # Second order still open
        ]
        
        # Call method
        strategy._manage_existing_orders()
        
        # Check that fetch_order was called twice
        assert mock_exchange.fetch_order.call_count == 2
        
        # Check that only the filled order was removed from open_orders
        assert len(strategy.state["open_orders"]) == 1
        assert strategy.state["open_orders"][0]["id"] == "2"

    @pytest.mark.parametrize("num_active_orders", [0, 3, 6])
    def test_place_grid_orders_with_existing_orders(self, strategy, mock_exchange, num_active_orders):
        """Test grid order placement with varying numbers of existing orders."""
        # Add some active orders
        strategy.state["open_orders"] = [
            {"id": str(i), "side": "buy" if i % 2 == 0 else "sell", "price": 50000.0 * (1 - 0.01 * i), "amount": 0.1}
            for i in range(num_active_orders)
        ]
        
        # Reset mock to clear call history
        mock_exchange.place_limit_order.reset_mock()
        
        # Place grid orders
        strategy._place_grid_orders(50000.0)
        
        # If we have 6 or more orders, no new orders should be placed
        if num_active_orders >= 6:
            assert mock_exchange.place_limit_order.call_count == 0
        else:
            # We should place (6 - num_active_orders) new orders
            assert mock_exchange.place_limit_order.call_count == 6 - num_active_orders

    def test_cancel_all_orders(self, strategy, mock_exchange):
        """Test cancelling all orders."""
        # Add some open orders to the state
        strategy.state["open_orders"] = [
            {"id": "1", "side": "buy", "price": 49000.0, "amount": 0.1},
            {"id": "2", "side": "sell", "price": 51000.0, "amount": 0.1},
        ]
        
        # Mock cancel_all_orders
        mock_exchange.cancel_all_orders.return_value = [
            {"id": "1", "status": "canceled"},
            {"id": "2", "status": "canceled"},
        ]
        
        # Call the reset method
        strategy._reset_grid(50000.0)
        
        # Check that cancel_all_orders was called
        mock_exchange.cancel_all_orders.assert_called_once_with("BTC/USDT")
        
        # Check that open_orders was cleared
        assert len(strategy.state["open_orders"]) == 0
        
        # Check that place_limit_order was called to create new grid
        assert mock_exchange.place_limit_order.called

    @pytest.mark.parametrize("initial_price,new_price,should_reset", [
        (50000.0, 50100.0, False),   # Small change, don't reset
        (50000.0, 51500.0, True),    # Large change (3%), should reset
        (50000.0, 48500.0, True),    # Large change (3%), should reset
    ])
    def test_price_change_threshold(self, strategy, initial_price, new_price, should_reset):
        """Test grid reset based on price change thresholds."""
        # Set last price
        strategy.state["last_price"] = initial_price
        
        # Check if grid should reset
        result = strategy._should_reset_grid(new_price)
        
        # Verify result matches expectation
        assert result == should_reset
