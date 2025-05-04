"""
Test module for the database utilities.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, call
import datetime
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from src.utils.database import (
    Base, SessionLocal, get_db, 
    retry_db_operation, DatabaseConnectionError, DatabaseQueryError,
    Order, Trade, Balance, BotState, BotPerformance, ProfitWithdrawal,
    save_order, get_orders, save_trade, get_trades, save_balance,
    get_latest_balance, save_bot_state, get_bot_state,
    save_bot_performance, get_bot_performance,
    save_profit_withdrawal, get_profit_withdrawals,
    health_check
)


@pytest.mark.unit
class TestDatabaseRetry:
    """Test database retry mechanism."""

    def test_retry_success_after_failure(self):
        """Test that a function is retried after a transient failure."""
        # Create a mock function that fails once then succeeds
        mock_function = MagicMock(side_effect=[OperationalError("connection lost", {}, None), "success"])
        
        # Decorate the mock function
        decorated_function = retry_db_operation(max_retries=3, retry_delay=0.1)(mock_function)
        
        # Call the decorated function
        result = decorated_function()
        
        # Verify the function was called twice
        assert mock_function.call_count == 2
        # Verify the final result
        assert result == "success"

    def test_retry_max_attempts_reached(self):
        """Test that maximum retry attempts are respected."""
        # Create a mock function that always fails
        mock_function = MagicMock(side_effect=OperationalError("connection lost", {}, None))
        
        # Decorate the mock function
        decorated_function = retry_db_operation(max_retries=3, retry_delay=0.1)(mock_function)
        
        # Call the decorated function and expect an exception
        with pytest.raises(DatabaseConnectionError):
            decorated_function()
        
        # Verify the function was called the maximum number of times
        assert mock_function.call_count == 3

    def test_no_retry_for_non_operational_errors(self):
        """Test that non-OperationalErrors are not retried."""
        # Create a mock function that raises a non-retryable error
        mock_function = MagicMock(side_effect=SQLAlchemyError("query error"))
        
        # Decorate the mock function
        decorated_function = retry_db_operation(max_retries=3, retry_delay=0.1)(mock_function)
        
        # Call the decorated function and expect an exception
        with pytest.raises(DatabaseQueryError):
            decorated_function()
        
        # Verify the function was called only once (no retries)
        assert mock_function.call_count == 1


@pytest.mark.unit
class TestDatabaseSessionManagement:
    """Test database session management."""

    def test_get_db_context_manager_success(self):
        """Test the get_db context manager with successful execution."""
        # Create mock db session
        mock_db = MagicMock()
        
        # Patch SessionLocal to return our mock
        with patch('src.utils.database.SessionLocal', return_value=mock_db):
            # Use the context manager
            with get_db() as db:
                # Do something with the db
                pass
            
            # Verify that commit was called
            mock_db.commit.assert_called_once()
            # Verify that close was called
            mock_db.close.assert_called_once()

    def test_get_db_context_manager_exception(self):
        """Test the get_db context manager with an exception."""
        # Create mock db session
        mock_db = MagicMock()
        
        # Patch SessionLocal to return our mock
        with patch('src.utils.database.SessionLocal', return_value=mock_db):
            # Use the context manager with an exception
            try:
                with get_db() as db:
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Verify that rollback was called
            mock_db.rollback.assert_called_once()
            # Verify that close was called
            mock_db.close.assert_called_once()


@pytest.mark.unit
class TestDatabaseHealthCheck:
    """Test database health check."""

    def test_health_check_success(self):
        """Test health check when database is healthy."""
        # Create mock connection
        mock_connection = MagicMock()
        
        # Patch engine.connect() to return our mock
        with patch('src.utils.database.engine.connect', return_value=mock_connection):
            # Call health check
            result = health_check()
            
            # Verify that execute was called
            mock_connection.execute.assert_called_once_with("SELECT 1")
            # Verify that the result is True
            assert result is True

    def test_health_check_failure(self):
        """Test health check when database is unhealthy."""
        # Patch engine.connect() to raise an exception
        with patch('src.utils.database.engine.connect', side_effect=Exception("connection failed")):
            # Call health check
            result = health_check()
            
            # Verify that the result is False
            assert result is False


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseOperations:
    """Test database operations."""

    def test_save_order(self, db_session_patch, test_db):
        """Test saving an order to the database."""
        # Create order data
        order_data = {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "order_id": "12345",
            "side": "buy",
            "type": "limit",
            "amount": 0.1,
            "price": 50000.0,
            "status": "open",
            "filled": 0,
            "cost": None,
            "fee": None,
            "created_at": datetime.datetime.now(),
            "updated_at": None,
            "bot_type": "low_risk",
            "raw_data": {"test": "data"},
        }
        
        # Save order
        order = save_order(order_data)
        
        # Verify order was saved
        assert order.id is not None
        assert order.exchange == "binance"
        assert order.symbol == "BTC/USDT"
        assert order.order_id == "12345"
        assert order.side == "buy"
        assert order.type == "limit"
        assert order.amount == 0.1
        assert order.price == 50000.0
        assert order.status == "open"
        assert order.bot_type == "low_risk"
        
        # Verify there's one order in the database
        saved_orders = test_db.query(Order).all()
        assert len(saved_orders) == 1
        assert saved_orders[0].order_id == "12345"

    def test_get_orders(self, db_session_patch, test_db):
        """Test retrieving orders from the database."""
        # Create two orders
        orders = [
            Order(
                exchange="binance",
                symbol="BTC/USDT",
                order_id="order1",
                side="buy",
                type="limit",
                amount=0.1,
                price=50000.0,
                status="open",
                filled=0.0,
                created_at=datetime.datetime.now(),
                bot_type="low_risk",
            ),
            Order(
                exchange="binance",
                symbol="ETH/USDT",
                order_id="order2",
                side="sell",
                type="market",
                amount=1.0,
                price=3000.0,
                status="closed",
                filled=1.0,
                created_at=datetime.datetime.now(),
                bot_type="high_risk",
            ),
        ]
        
        # Add orders to the database
        for order in orders:
            test_db.add(order)
        test_db.commit()
        
        # Test getting all orders
        all_orders = get_orders()
        assert len(all_orders) == 2
        
        # Test filtering by exchange
        binance_orders = get_orders(exchange="binance")
        assert len(binance_orders) == 2
        
        # Test filtering by symbol
        btc_orders = get_orders(symbol="BTC/USDT")
        assert len(btc_orders) == 1
        assert btc_orders[0].symbol == "BTC/USDT"
        
        # Test filtering by bot_type
        low_risk_orders = get_orders(bot_type="low_risk")
        assert len(low_risk_orders) == 1
        assert low_risk_orders[0].bot_type == "low_risk"
        
        # Test filtering by status
        open_orders = get_orders(status="open")
        assert len(open_orders) == 1
        assert open_orders[0].status == "open"

    def test_save_bot_state(self, db_session_patch, test_db):
        """Test saving bot state to the database."""
        # Create state data
        state_data = {
            "is_running": True,
            "last_run": datetime.datetime.now(),
            "state": {"last_price": 50000.0, "open_orders": []},
        }
        
        # Save bot state
        bot_state = save_bot_state("low_risk", state_data)
        
        # Verify bot state was saved
        assert bot_state.id is not None
        assert bot_state.bot_type == "low_risk"
        assert bot_state.is_running is True
        assert bot_state.state == {"last_price": 50000.0, "open_orders": []}
        
        # Update bot state
        new_state_data = {
            "is_running": False,
            "last_run": datetime.datetime.now(),
            "state": {"last_price": 51000.0, "open_orders": []},
        }
        
        # Save updated bot state
        updated_bot_state = save_bot_state("low_risk", new_state_data)
        
        # Verify bot state was updated, not duplicated
        assert updated_bot_state.id == bot_state.id
        assert updated_bot_state.is_running is False
        assert updated_bot_state.state["last_price"] == 51000.0
        
        # Verify there's only one bot state in the database
        states = test_db.query(BotState).all()
        assert len(states) == 1


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Test integration between database components."""

    def test_full_order_lifecycle(self, db_session_patch, test_db):
        """Test the full lifecycle of an order from creation to querying."""
        # Create order
        order_data = {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "order_id": "lifecycle_test",
            "side": "buy",
            "type": "limit",
            "amount": 0.1,
            "price": 50000.0,
            "status": "open",
            "filled": 0,
            "cost": None,
            "fee": None,
            "created_at": datetime.datetime.now(),
            "updated_at": None,
            "bot_type": "test",
            "raw_data": {"test": "data"},
        }
        
        # Save order
        order = save_order(order_data)
        
        # Query orders
        orders = get_orders(bot_type="test")
        
        # Verify order exists
        assert len(orders) == 1
        assert orders[0].order_id == "lifecycle_test"
        
        # Create trade associated with the order
        trade_data = {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "trade_id": "trade1",
            "order_id": "lifecycle_test",
            "side": "buy",
            "amount": 0.1,
            "price": 50000.0,
            "cost": 5000.0,
            "fee": 5.0,
            "fee_currency": "USDT",
            "timestamp": datetime.datetime.now(),
            "bot_type": "test",
            "raw_data": {"trade": "data"},
        }
        
        # Save trade
        trade = save_trade(trade_data)
        
        # Query trades
        trades = get_trades(bot_type="test")
        
        # Verify trade exists
        assert len(trades) == 1
        assert trades[0].trade_id == "trade1"
        assert trades[0].order_id == "lifecycle_test"

    def test_pagination_with_limit_and_offset(self, db_session_patch, test_db):
        """Test pagination using limit and offset."""
        # Create 10 orders
        for i in range(10):
            order = Order(
                exchange="binance",
                symbol="BTC/USDT",
                order_id=f"pagination_test_{i}",
                side="buy",
                type="limit",
                amount=0.1,
                price=50000.0,
                status="open",
                filled=0.0,
                created_at=datetime.datetime.now() - datetime.timedelta(minutes=i),
                bot_type="pagination_test",
            )
            test_db.add(order)
        test_db.commit()
        
        # Get first page (3 orders)
        page1 = get_orders(bot_type="pagination_test", limit=3, offset=0)
        
        # Get second page (3 orders)
        page2 = get_orders(bot_type="pagination_test", limit=3, offset=3)
        
        # Get third page (3 orders)
        page3 = get_orders(bot_type="pagination_test", limit=3, offset=6)
        
        # Get fourth page (1 order, since we only have 10 total)
        page4 = get_orders(bot_type="pagination_test", limit=3, offset=9)
        
        # Verify pagination works correctly
        assert len(page1) == 3
        assert len(page2) == 3
        assert len(page3) == 3
        assert len(page4) == 1
        
        # Verify we got different orders on each page
        page1_ids = [order.order_id for order in page1]
        page2_ids = [order.order_id for order in page2]
        page3_ids = [order.order_id for order in page3]
        page4_ids = [order.order_id for order in page4]
        
        # No overlap between pages
        assert not set(page1_ids).intersection(page2_ids)
        assert not set(page1_ids).intersection(page3_ids)
        assert not set(page2_ids).intersection(page3_ids)
        
        # Verify ordering is by created_at descending
        # (We created older orders last, so they should be later in pagination)
        # Extract order IDs as integers for comparison
        page1_nums = [int(id.split("_")[-1]) for id in page1_ids]
        page2_nums = [int(id.split("_")[-1]) for id in page2_ids]
        
        # Lower numbers were created later (more recent first)
        assert min(page1_nums) < min(page2_nums)
