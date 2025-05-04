"""
Database module for the crypto trading bot.
Provides database connection and models for the application.
"""

import datetime
import time
from contextlib import contextmanager
from typing import Generator, Dict, Any, List, Optional, TypeVar, Type, Generic

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, event
from sqlalchemy.exc import SQLAlchemyError, DBAPIError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import QueuePool

from src.config import settings
from src.utils.logging import logger

# Create SQLAlchemy engine
connection_string = settings.database.connection_string

# Use appropriate engine configuration based on the database type
if connection_string.startswith('sqlite'):
    # SQLite doesn't support the same pooling options as PostgreSQL
    engine = create_engine(
        connection_string,
        connect_args={"check_same_thread": False},  # Allow SQLite to be used in multiple threads
        pool_pre_ping=True,  # Test connections for liveness upon checkout
    )
    logger.info(f"Using SQLite database at {connection_string}")
else:
    # PostgreSQL and other databases with full pooling support
    engine = create_engine(
        connection_string,
        pool_size=10,  # Maximum number of connections in the pool
        max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
        pool_timeout=30,  # Seconds to wait before timing out on getting a connection from the pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Test connections for liveness upon checkout
    )
    logger.info(f"Using database connection: {connection_string}")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Add connection pool event listeners
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")

# Custom database exceptions
class DatabaseError(Exception):
    """Base exception for database errors."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Exception for database connection errors."""
    pass

class DatabaseQueryError(DatabaseError):
    """Exception for database query errors."""
    pass

class DatabaseTransactionError(DatabaseError):
    """Exception for database transaction errors."""
    pass

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define Model type variable for type hinting
T = TypeVar('T', bound=Base)

# Function to get a database session directly
def get_db_session() -> Session:
    """
    Get a database session directly.
    
    Returns:
        A database session.
    """
    return SessionLocal()


def retry_db_operation(max_retries=3, retry_delay=1.0):
    """
    Decorator for retrying database operations.
    
    Args:
        max_retries: Maximum number of retries.
        retry_delay: Delay between retries in seconds.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    # Connection-related errors that might be transient
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise DatabaseConnectionError(f"Database connection failed: {e}")
                    
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** (retries - 1))
                    logger.warning(f"Database operation failed, retrying in {sleep_time}s: {e}")
                    time.sleep(sleep_time)
                except SQLAlchemyError as e:
                    # Other SQL errors that are likely not transient
                    logger.error(f"Database query error: {e}")
                    raise DatabaseQueryError(f"Database query failed: {e}")
            return None
        return wrapper
    return decorator


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session with transaction management.

    Yields:
        A database session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error, transaction rolled back: {e}")
        if isinstance(e, OperationalError):
            raise DatabaseConnectionError(f"Database connection failed: {e}")
        raise DatabaseQueryError(f"Database query failed: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during database operation: {e}")
        raise DatabaseTransactionError(f"Database transaction failed: {e}")
    finally:
        db.close()


def health_check() -> bool:
    """
    Check database connection health.
    
    Returns:
        True if the database is healthy, False otherwise.
    """
    try:
        # Execute a simple query to check connection
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


class Order(Base):
    """Order model."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    order_id = Column(String, nullable=False, unique=True)
    side = Column(String, nullable=False)  # buy or sell
    type = Column(String, nullable=False)  # limit or market
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Null for market orders
    status = Column(String, nullable=False)  # open, closed, canceled
    filled = Column(Float, nullable=False, default=0.0)
    cost = Column(Float, nullable=True)
    fee = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    bot_type = Column(String, nullable=False)  # low_risk, medium_risk, high_risk
    raw_data = Column(JSON, nullable=True)  # Raw order data from exchange


class Trade(Base):
    """Trade model."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    trade_id = Column(String, nullable=False, unique=True)
    order_id = Column(String, nullable=True)
    side = Column(String, nullable=False)  # buy or sell
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    fee = Column(Float, nullable=True)
    fee_currency = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    bot_type = Column(String, nullable=False)  # low_risk, medium_risk, high_risk
    raw_data = Column(JSON, nullable=True)  # Raw trade data from exchange


class Balance(Base):
    """Balance model."""

    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    free = Column(Float, nullable=False)
    used = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    bot_type = Column(String, nullable=False)  # low_risk, medium_risk, high_risk


class BotState(Base):
    """Bot state model."""

    __tablename__ = "bot_states"

    id = Column(Integer, primary_key=True, index=True)
    bot_type = Column(String, nullable=False, unique=True)  # low_risk, medium_risk, high_risk
    is_running = Column(Boolean, nullable=False, default=False)
    last_run = Column(DateTime, nullable=True)
    config = Column(JSON, nullable=True)  # Bot configuration
    state = Column(JSON, nullable=True)  # Bot state


class BotPerformance(Base):
    """Bot performance model."""

    __tablename__ = "bot_performance"

    id = Column(Integer, primary_key=True, index=True)
    bot_type = Column(String, nullable=False)  # low_risk, medium_risk, high_risk
    balance = Column(Float, nullable=False)  # Current balance
    daily_profit = Column(Float, nullable=True)  # Daily profit
    daily_roi = Column(Float, nullable=True)  # Daily ROI percentage
    total_trades = Column(Integer, nullable=True)  # Total trades
    win_rate = Column(Float, nullable=True)  # Win rate percentage
    sharpe_ratio = Column(Float, nullable=True)  # Sharpe ratio
    max_drawdown = Column(Float, nullable=True)  # Maximum drawdown
    timestamp = Column(DateTime, nullable=False)  # Timestamp


class ProfitWithdrawal(Base):
    """Profit withdrawal model."""

    __tablename__ = "profit_withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    bot_type = Column(String, nullable=False)  # low_risk, medium_risk, high_risk
    amount = Column(Float, nullable=False)  # Withdrawal amount
    timestamp = Column(DateTime, nullable=False)  # Timestamp


@retry_db_operation()
def init_db() -> None:
    """Initialize the database."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


@retry_db_operation()
def save_order(order_data: Dict[str, Any]) -> Order:
    """
    Save an order to the database.

    Args:
        order_data: The order data.

    Returns:
        The saved order.
    """
    with get_db() as db:
        order = Order(**order_data)
        db.add(order)
        
        # We don't need to db.commit() here because the context manager does it
        db.flush()  # Flush to get the generated ID without committing
        db.refresh(order)
        return order


@retry_db_operation()
def get_orders(
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    bot_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Order]:
    """        limit: Maximum number of records to return.
        offset: Number of records to skip.
        
    Get orders from the database.

    Args:
        exchange: Filter by exchange.
        symbol: Filter by symbol.
        bot_type: Filter by bot type.
        status: Filter by status.

    Returns:
        A list of orders.
    """
    with get_db() as db:
        query = db.query(Order)
        if exchange:
            query = query.filter(Order.exchange == exchange)
        if symbol:
            query = query.filter(Order.symbol == symbol)
        if bot_type:
            query = query.filter(Order.bot_type == bot_type)
        if status:
            query = query.filter(Order.status == status)
            
        # Apply limit and offset for pagination
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        # Order by created_at for consistent results
        query = query.order_by(Order.created_at.desc())
            
        return query.all()


@retry_db_operation()
def save_trade(trade_data: Dict[str, Any]) -> Trade:
    """
    Save a trade to the database.

    Args:
        trade_data: The trade data.

    Returns:
        The saved trade.
    """
    with get_db() as db:
        trade = Trade(**trade_data)
        db.add(trade)
        db.flush()
        db.refresh(trade)
        return trade


@retry_db_operation()
def get_trades(
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
    bot_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Trade]:
    """        limit: Maximum number of records to return.
        offset: Number of records to skip.
        
    Get trades from the database.

    Args:
        exchange: Filter by exchange.
        symbol: Filter by symbol.
        bot_type: Filter by bot type.

    Returns:
        A list of trades.
    """
    with get_db() as db:
        query = db.query(Trade)
        if exchange:
            query = query.filter(Trade.exchange == exchange)
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        if bot_type:
            query = query.filter(Trade.bot_type == bot_type)
            
        # Apply limit and offset for pagination
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        # Order by timestamp for consistent results
        query = query.order_by(Trade.timestamp.desc())
            
        return query.all()


@retry_db_operation()
def save_balance(balance_data: Dict[str, Any]) -> Balance:
    """
    Save a balance to the database.

    Args:
        balance_data: The balance data.

    Returns:
        The saved balance.
    """
    with get_db() as db:
        balance = Balance(**balance_data)
        db.add(balance)
        db.flush()
        db.refresh(balance)
        return balance


@retry_db_operation()
def get_latest_balance(
    exchange: str, currency: str, bot_type: str
) -> Optional[Balance]:
    """
    Get the latest balance for a currency.

    Args:
        exchange: The exchange.
        currency: The currency.
        bot_type: The bot type.

    Returns:
        The latest balance, or None if not found.
    """
    with get_db() as db:
        return (
            db.query(Balance)
            .filter(
                Balance.exchange == exchange,
                Balance.currency == currency,
                Balance.bot_type == bot_type,
            )
            .order_by(Balance.timestamp.desc())
            .first()
        )


@retry_db_operation()
def save_bot_state(bot_type: str, state_data: Dict[str, Any]) -> BotState:
    """
    Save a bot state to the database.

    Args:
        bot_type: The bot type.
        state_data: The state data.

    Returns:
        The saved bot state.
    """
    with get_db() as db:
        bot_state = (
            db.query(BotState).filter(BotState.bot_type == bot_type).first()
        )
        if bot_state:
            for key, value in state_data.items():
                setattr(bot_state, key, value)
        else:
            bot_state = BotState(bot_type=bot_type, **state_data)
            db.add(bot_state)
        db.flush()
        db.refresh(bot_state)
        return bot_state


@retry_db_operation()
def get_bot_state(bot_type: str) -> Optional[BotState]:
    """
    Get a bot state from the database.

    Args:
        bot_type: The bot type.

    Returns:
        The bot state, or None if not found.
    """
    with get_db() as db:
        return db.query(BotState).filter(BotState.bot_type == bot_type).first()


@retry_db_operation()
def save_bot_performance(performance_data: Dict[str, Any]) -> BotPerformance:
    """
    Save bot performance data to the database.

    Args:
        performance_data: The performance data.

    Returns:
        The saved bot performance.
    """
    with get_db() as db:
        performance = BotPerformance(**performance_data)
        db.add(performance)
        db.flush()
        db.refresh(performance)
        return performance


@retry_db_operation()
def get_bot_performance(
    bot_type: str, 
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
) -> List[BotPerformance]:
    """
    Get bot performance data from the database.

    Args:
        bot_type: The bot type.
        start_date: Start date for filtering.
        end_date: End date for filtering.

    Returns:
        A list of bot performance records.
    """
    with get_db() as db:
        query = db.query(BotPerformance).filter(BotPerformance.bot_type == bot_type)
        
        if start_date:
            query = query.filter(BotPerformance.timestamp >= start_date)
        
        if end_date:
            query = query.filter(BotPerformance.timestamp <= end_date)
        
        return query.order_by(BotPerformance.timestamp.desc()).all()


@retry_db_operation()
def save_profit_withdrawal(withdrawal_data: Dict[str, Any]) -> ProfitWithdrawal:
    """
    Save profit withdrawal data to the database.

    Args:
        withdrawal_data: The withdrawal data.

    Returns:
        The saved profit withdrawal.
    """
    with get_db() as db:
        withdrawal = ProfitWithdrawal(**withdrawal_data)
        db.add(withdrawal)
        db.flush()
        db.refresh(withdrawal)
        return withdrawal


@retry_db_operation()
def get_profit_withdrawals(
    bot_type: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
) -> List[ProfitWithdrawal]:
    """
    Get profit withdrawal data from the database.

    Args:
        bot_type: The bot type for filtering.
        start_date: Start date for filtering.
        end_date: End date for filtering.

    Returns:
        A list of profit withdrawal records.
    """
    with get_db() as db:
        query = db.query(ProfitWithdrawal)
        
        if bot_type:
            query = query.filter(ProfitWithdrawal.bot_type == bot_type)
        
        if start_date:
            query = query.filter(ProfitWithdrawal.timestamp >= start_date)
        
        if end_date:
            query = query.filter(ProfitWithdrawal.timestamp <= end_date)
        
        return query.order_by(ProfitWithdrawal.timestamp.desc()).all()
