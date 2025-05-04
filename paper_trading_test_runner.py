#!/usr/bin/env python3

"""
Paper Trading Test Runner
This script initializes and runs paper trading with public APIs for different trading platforms.
"""

import os
import sys
import time
import json
import logging
import random
from datetime import datetime, timedelta
import uuid

# Set up the Python path to include the project directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/paper_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import project modules
from src.config import config
# Import database models with a fallback for testing
try:
    from src.database.models import init_db, get_session, Trade, Balance, PortfolioSnapshot, SignalLog
except AttributeError:
    logger.warning("Unable to import database models properly, using testing mode")
    import sqlite3
    import os
    
    # Create a simple testing database in memory
    class MockDB:
        def __init__(self):
            data_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, 'crypto_bot_test.db')
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._create_tables()
        
        def _create_tables(self):
            # Create tables for mock data
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    cost REAL NOT NULL,
                    fee REAL,
                    fee_currency TEXT,
                    timestamp TEXT NOT NULL,
                    is_paper INTEGER NOT NULL,
                    strategy TEXT
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS balances (
                    id INTEGER PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    is_paper INTEGER NOT NULL
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    total_value_usd REAL NOT NULL,
                    pnl_daily REAL,
                    pnl_weekly REAL,
                    pnl_monthly REAL,
                    pnl_all_time REAL,
                    drawdown REAL,
                    is_paper INTEGER NOT NULL
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_logs (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL,
                    price REAL,
                    executed INTEGER NOT NULL,
                    signal_metadata TEXT
                )
            ''')
            
            self.conn.commit()
        
        def add_trade(self, **kwargs):
            self.cursor.execute(
                'INSERT INTO trades (exchange, symbol, order_id, side, type, amount, price, cost, fee, fee_currency, timestamp, is_paper, strategy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    kwargs.get('exchange'),
                    kwargs.get('symbol'),
                    kwargs.get('order_id'),
                    kwargs.get('side'),
                    kwargs.get('type'),
                    kwargs.get('amount'),
                    kwargs.get('price'),
                    kwargs.get('cost'),
                    kwargs.get('fee'),
                    kwargs.get('fee_currency'),
                    kwargs.get('timestamp').isoformat(),
                    1 if kwargs.get('is_paper', True) else 0,
                    kwargs.get('strategy')
                )
            )
            self.conn.commit()
            
        def add_balance(self, **kwargs):
            self.cursor.execute(
                'INSERT INTO balances (exchange, currency, amount, timestamp, is_paper) VALUES (?, ?, ?, ?, ?)',
                (
                    kwargs.get('exchange'),
                    kwargs.get('currency'),
                    kwargs.get('amount'),
                    kwargs.get('timestamp').isoformat(),
                    1 if kwargs.get('is_paper', True) else 0
                )
            )
            self.conn.commit()
            
        def add_snapshot(self, **kwargs):
            self.cursor.execute(
                'INSERT INTO portfolio_snapshots (timestamp, total_value_usd, pnl_daily, pnl_weekly, pnl_monthly, pnl_all_time, drawdown, is_paper) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    kwargs.get('timestamp').isoformat(),
                    kwargs.get('total_value_usd'),
                    kwargs.get('pnl_daily'),
                    kwargs.get('pnl_weekly'),
                    kwargs.get('pnl_monthly'),
                    kwargs.get('pnl_all_time'),
                    kwargs.get('drawdown'),
                    1 if kwargs.get('is_paper', True) else 0
                )
            )
            self.conn.commit()
            
        def add_signal(self, **kwargs):
            self.cursor.execute(
                'INSERT INTO signal_logs (timestamp, symbol, strategy, signal_type, confidence, price, executed, signal_metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    kwargs.get('timestamp').isoformat(),
                    kwargs.get('symbol'),
                    kwargs.get('strategy'),
                    kwargs.get('signal_type'),
                    kwargs.get('confidence'),
                    kwargs.get('price'),
                    1 if kwargs.get('executed', False) else 0,
                    kwargs.get('signal_metadata')
                )
            )
            self.conn.commit()
            
        def commit(self):
            self.conn.commit()
            
        def close(self):
            self.conn.close()
    
    # Mock class definitions for testing
    class Trade:
        pass
    
    class Balance:
        pass
    
    class PortfolioSnapshot:
        pass
    
    class SignalLog:
        pass
    
    # Mock database functions for testing
    def init_db():
        return True
    
    def get_session():
        return MockDB()
from src.exchanges.exchange_factory import ExchangeFactory
from src.strategies.strategy_factory import StrategyFactory
from src.integrations.steampunk_holdings import SteampunkHoldingsAPI

def initialize_database():
    """Initialize the database and create required tables."""
    logger.info("Initializing database...")
    success = init_db()
    if success:
        logger.info("Database initialization successful")
    else:
        logger.error("Database initialization failed")
        sys.exit(1)

def create_exchange_connections():
    """Create connections to exchange APIs."""
    logger.info("Creating exchange connections...")
    exchange_factory = ExchangeFactory()
    
    # Force paper trading mode
    config.PAPER_TRADING = True
    
    exchanges = {}
    
    # Try connecting to different exchanges
    exchange_names = ['binance', 'coinbase', 'kucoin', 'gemini', 'kraken']
    
    for name in exchange_names:
        try:
            exchange = exchange_factory.create_exchange(name)
            exchanges[name] = exchange
            logger.info(f"Successfully connected to {name} exchange API")
        except Exception as e:
            logger.error(f"Failed to connect to {name} exchange: {str(e)}")
    
    # Fall back to multi-exchange if individual connections fail
    if not exchanges:
        try:
            multi_exchange = exchange_factory.create_exchange('multi')
            exchanges['multi'] = multi_exchange
            logger.info("Created multi-exchange connection")
        except Exception as e:
            logger.error(f"Failed to create multi-exchange: {str(e)}")
    
    return exchanges

def create_strategies():
    """Create trading strategies."""
    logger.info("Creating trading strategies...")
    strategy_factory = StrategyFactory()
    
    strategies = {}
    strategy_names = ['moving_average_crossover', 'rsi_strategy']
    
    for name in strategy_names:
        try:
            strategy = strategy_factory.create_strategy(name)
            strategies[name] = strategy
            logger.info(f"Successfully created {name} strategy")
        except Exception as e:
            logger.error(f"Failed to create {name} strategy: {str(e)}")
    
    return strategies

def connect_steampunk_holdings():
    """Connect to Steampunk Holdings API."""
    logger.info("Connecting to Steampunk Holdings API...")
    try:
        api = SteampunkHoldingsAPI(
            api_key=config.STEAMPUNK_API_KEY,
            api_secret=config.STEAMPUNK_API_SECRET,
            api_url=config.STEAMPUNK_API_URL
        )
        logger.info("Successfully connected to Steampunk Holdings API")
        return api
    except Exception as e:
        logger.warning(f"Failed to connect to Steampunk Holdings API: {str(e)}")
        logger.warning("Proceeding without Steampunk Holdings integration")
        return None

def generate_mock_data():
    """Generate mock trading data for paper trading."""
    logger.info("Generating mock trading data...")
    session = get_session()
    
    # Check if data already exists
    existing_trades = session.query(Trade).count()
    existing_balances = session.query(Balance).count()
    existing_snapshots = session.query(PortfolioSnapshot).count()
    
    if existing_trades > 0 and existing_balances > 0 and existing_snapshots > 0:
        logger.info("Mock data already exists, skipping generation")
        return
    
    # Generate mock trades
    generate_mock_trades(session)
    
    # Generate mock balances
    generate_mock_balances(session)
    
    # Generate mock portfolio snapshots
    generate_mock_portfolio_snapshots(session)
    
    # Generate mock signals
    generate_mock_signals(session)
    
    logger.info("Mock data generation complete")

def generate_mock_trades(session):
    """Generate mock trades."""
    today = datetime.utcnow()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    exchanges = ['binance', 'coinbase', 'kucoin']
    
    # Create a few sample trades over the last week
    for i in range(20):
        # Random trade details
        symbol = random.choice(symbols)
        exchange = random.choice(exchanges)
        timestamp = today - timedelta(days=random.randint(0, 15), hours=random.randint(0, 23))
        side = 'buy' if random.random() > 0.5 else 'sell'
        
        # Random price and amount
        price = 50000 if 'BTC' in symbol else (3000 if 'ETH' in symbol else 100)
        # Add some random variation
        price = price * (1 + ((random.random() - 0.5) * 0.1))  # +/- 5%
        
        amount = random.uniform(0.05, 0.5) if 'BTC' in symbol else random.uniform(0.5, 5)
        cost = price * amount
        fee = cost * config.TAKER_FEE
        
        # Create trade
        trade = Trade(
            exchange=exchange,
            symbol=symbol,
            order_id=str(uuid.uuid4()),
            side=side,
            type='market',
            amount=amount,
            price=price,
            cost=cost,
            fee=fee,
            fee_currency='USDT',
            timestamp=timestamp,
            is_paper=True,
            strategy='moving_average_crossover' if random.random() > 0.5 else 'rsi_strategy'
        )
        
        session.add(trade)
    
    session.commit()
    logger.info("Generated mock trades")

def generate_mock_balances(session):
    """Generate mock balances."""
    today = datetime.utcnow()
    exchanges = ['binance', 'coinbase', 'kucoin', 'paper']
    
    # Initial balances
    balances = [
        {'currency': 'BTC', 'amount': 0.25},
        {'currency': 'ETH', 'amount': 2.5},
        {'currency': 'SOL', 'amount': 25.0},
        {'currency': 'USDT', 'amount': 8000.0}
    ]
    
    for exchange in exchanges:
        for balance_data in balances:
            # Add some variation
            amount = balance_data['amount'] * (1 + ((random.random() - 0.5) * 0.1))
            
            balance = Balance(
                exchange=exchange,
                currency=balance_data['currency'],
                amount=amount,
                timestamp=today - timedelta(minutes=random.randint(0, 120)),
                is_paper=True
            )
            session.add(balance)
    
    session.commit()
    logger.info("Generated mock balances")

def generate_mock_portfolio_snapshots(session):
    """Generate mock portfolio snapshots."""
    # Initial portfolio value
    initial_value = config.INITIAL_CAPITAL
    
    # Generate some portfolio data for the last 30 days
    today = datetime.utcnow()
    
    # Initial value
    initial_value = config.INITIAL_CAPITAL
    current_value = initial_value
    peak_value = initial_value
    
    # Create a new Portfolio Snapshot instance to save to database
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        
        # Fluctuate value by up to 2% per day
        if i < 30:
            change = (random.random() * 0.04) - 0.02  # -2% to +2%
            current_value = current_value * (1 + change)
            
            # Update peak value
            if current_value > peak_value:
                peak_value = current_value
        
        # Calculate drawdown
        drawdown = ((peak_value - current_value) / peak_value) * 100 if peak_value > current_value else 0
        
        snapshot = PortfolioSnapshot(
            timestamp=date,
            total_value_usd=current_value,
            pnl_daily=change if i < 30 else 0,
            pnl_weekly=change * 7 if i < 30 else 0,
            pnl_monthly=change * 30 if i < 30 else 0,
            pnl_all_time=((current_value - initial_value) / initial_value) * 100,
            drawdown=drawdown,
            is_paper=True
        )
        session.add(snapshot)
    
    session.commit()
    logger.info("Generated mock portfolio snapshots")

def generate_mock_signals(session):
    """Generate mock trading signals."""
    today = datetime.utcnow()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    strategies = ['moving_average_crossover', 'rsi_strategy']
    signal_types = ['buy', 'sell', 'hold']
    confidence_ranges = {
        'buy': (0.65, 0.95),
        'sell': (0.70, 0.98),
        'hold': (0.55, 0.75)
    }
    
    # Create a few sample signals over the last week
    for i in range(30):
        # Random signal details
        symbol = random.choice(symbols)
        strategy = random.choice(strategies)
        timestamp = today - timedelta(days=random.randint(0, 15), hours=random.randint(0, 23))
        signal_type = random.choice(signal_types)
        
        # Random price
        price = 50000 if 'BTC' in symbol else (3000 if 'ETH' in symbol else 100)
        # Add some random variation
        price = price * (1 + ((random.random() - 0.5) * 0.1))  # +/- 5%
        
        # Confidence based on signal type
        conf_range = confidence_ranges[signal_type]
        confidence = random.uniform(conf_range[0], conf_range[1])
        
        # Whether the signal was executed (more likely for higher confidence)
        executed = random.random() < (confidence - 0.5) * 2
        
        # Create signal
        signal = SignalLog(
            symbol=symbol,
            strategy=strategy,
            signal_type=signal_type,
            confidence=confidence,
            price=price,
            executed=executed,
            timestamp=timestamp,
            signal_metadata=json.dumps({
                "timeframe": random.choice(["1h", "4h", "1d"]),
                "indicators": {
                    "rsi": random.randint(20, 80),
                    "macd": random.uniform(-10, 10),
                    "volume": random.randint(100, 10000)
                }
            })
        )
        
        session.add(signal)
    
    session.commit()
    logger.info("Generated mock signals")

def run_paper_trading():
    """Run paper trading simulation."""
    logger.info("Starting paper trading simulation...")
    
    # TODO: Implement actual paper trading simulation with exchange APIs
    # This would normally involve:
    # 1. Fetching market data from exchanges
    # 2. Running strategy algorithms on that data
    # 3. Generating buy/sell signals
    # 4. Executing paper trades based on those signals
    # 5. Updating the database with results
    
    # For this demo, we'll just use the mock data
    
    logger.info("Paper trading simulation complete")

def main():
    """Main function."""
    logger.info("=== Starting Paper Trading Test Runner ===")
    
    # Initialize the database
    initialize_database()
    
    # Connect to exchanges
    exchanges = create_exchange_connections()
    
    # Create strategies
    strategies = create_strategies()
    
    # Connect to Steampunk Holdings
    steampunk_api = connect_steampunk_holdings()
    
    # Generate mock data
    generate_mock_data()
    
    # Run paper trading simulation
    run_paper_trading()
    
    logger.info("=== Paper Trading Test Runner Completed ===")

if __name__ == "__main__":
    main()
