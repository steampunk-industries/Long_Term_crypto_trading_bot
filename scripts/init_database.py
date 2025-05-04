#!/usr/bin/env python3
"""
Script to initialize the database with sample data.
"""

import os
import sys
import json
from datetime import datetime, timedelta
import random
from sqlalchemy import inspect, text
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import (
    initialize_database, get_session, User, Trade,
    Balance, PortfolioSnapshot, SignalLog
)
from src.config import config


def migrate_database():
    """Migrate existing database to handle schema changes."""
    session = get_session()
    engine = session.bind
    
    try:
        # Check if the old column exists
        inspector = inspect(engine)
        
        if 'signal_logs' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('signal_logs')]
            
            if 'metadata' in columns and 'signal_metadata' not in columns:
                logger.info("Migrating signal_logs table: metadata → signal_metadata")
                
                # SQLite and PostgreSQL have different syntax
                if config.USE_SQLITE:
                    # For SQLite, create new column, copy data, then create new table without old column
                    with engine.connect() as conn:
                        # Add new column
                        conn.execute(text("ALTER TABLE signal_logs ADD COLUMN signal_metadata TEXT"))
                        # Copy data
                        conn.execute(text("UPDATE signal_logs SET signal_metadata = metadata"))
                        
                        # Create temporary table with correct schema
                        conn.execute(text("""
                        CREATE TABLE signal_logs_new (
                            id INTEGER PRIMARY KEY,
                            timestamp TIMESTAMP,
                            symbol VARCHAR(20),
                            strategy VARCHAR(50),
                            signal_type VARCHAR(20),
                            confidence FLOAT,
                            price FLOAT,
                            signal_metadata TEXT,
                            executed BOOLEAN,
                            trade_id INTEGER
                        )
                        """))
                        
                        # Copy data to new table
                        conn.execute(text("""
                        INSERT INTO signal_logs_new 
                        SELECT id, timestamp, symbol, strategy, signal_type, confidence, price, 
                               signal_metadata, executed, trade_id 
                        FROM signal_logs
                        """))
                        
                        # Drop old table and rename new one
                        conn.execute(text("DROP TABLE signal_logs"))
                        conn.execute(text("ALTER TABLE signal_logs_new RENAME TO signal_logs"))
                        
                        # Add indexes
                        conn.execute(text("CREATE INDEX idx_signal_logs_timestamp ON signal_logs(timestamp)"))
                        conn.execute(text("CREATE INDEX idx_signal_logs_symbol ON signal_logs(symbol)"))
                        conn.execute(text("CREATE INDEX idx_signal_logs_strategy ON signal_logs(strategy)"))
                else:
                    # For PostgreSQL
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE signal_logs RENAME COLUMN metadata TO signal_metadata"))
                
                logger.info("Migration completed successfully")
        else:
            logger.info("No signal_logs table found, nothing to migrate")
            
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
    finally:
        session.close()


def create_sample_data():
    """Create sample data for the dashboard if none exists."""
    session = get_session()

    # Check if we already have portfolio snapshots
    snapshot_count = session.query(PortfolioSnapshot).count()
    if snapshot_count > 0:
        print(f"Database already has {snapshot_count} portfolio snapshots. Skipping sample data creation.")
        session.close()
        return

    print("Creating sample data for the dashboard...")

    # Create sample portfolio snapshots for the last 30 days
    start_date = datetime.utcnow() - timedelta(days=30)
    current_value = config.INITIAL_CAPITAL

    # Create a realistic portfolio growth curve
    for day in range(31):  # 0 to 30 days
        date = start_date + timedelta(days=day)

        # Add some randomness to the portfolio value (realistic market fluctuations)
        daily_change_pct = random.uniform(-0.02, 0.025)  # -2% to 2.5% daily change
        daily_change = current_value * daily_change_pct
        current_value += daily_change

        # Calculate previous day value for PnL calculations
        prev_day_value = current_value - daily_change

        # Determine cash and invested values
        # As time progresses, more capital gets invested
        investment_ratio = min(0.8, day * 0.025)  # Gradually increase to 80% invested
        invested_value = current_value * investment_ratio
        cash_value = current_value - invested_value

        # Create holdings JSON
        holdings = {
            "USDT": cash_value,
            "BTC": (invested_value * 0.4) / 50000,  # Assuming BTC price of $50,000
            "ETH": (invested_value * 0.3) / 3000,   # Assuming ETH price of $3,000
            "SOL": (invested_value * 0.2) / 100,    # Assuming SOL price of $100
            "ADA": (invested_value * 0.1) / 0.5     # Assuming ADA price of $0.50
        }

        # Create the portfolio snapshot
        snapshot = PortfolioSnapshot(
            timestamp=date,
            total_value=current_value,
            cash_value=cash_value,
            invested_value=invested_value,
            pnl_24h=daily_change,
            pnl_24h_percent=daily_change_pct * 100,  # Convert to percentage
            pnl_total=current_value - config.INITIAL_CAPITAL,
            pnl_total_percent=((current_value / config.INITIAL_CAPITAL) - 1) * 100,
            holdings=json.dumps(holdings)
        )
        session.add(snapshot)

    # Create sample trades (more frequent in recent days)
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
    strategies = ["MovingAverageCrossover", "RSIStrategy"]

    for day in range(15):  # Last 15 days
        date = datetime.utcnow() - timedelta(days=14-day)

        # More trades in recent days
        num_trades = random.randint(1, 3) if day < 10 else random.randint(2, 5)

        for _ in range(num_trades):
            # Randomize trade details
            symbol = random.choice(symbols)
            side = random.choice(["buy", "sell"])
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1]

            # Determine price based on symbol
            price = 0
            if base_currency == "BTC":
                price = random.uniform(45000, 55000)
            elif base_currency == "ETH":
                price = random.uniform(2800, 3200)
            elif base_currency == "SOL":
                price = random.uniform(90, 110)
            elif base_currency == "ADA":
                price = random.uniform(0.45, 0.55)

            amount = random.uniform(0.01, 0.5) if base_currency in ["BTC", "ETH"] else random.uniform(1, 10)
            value = amount * price
            fee = value * config.TAKER_FEE
            strategy = random.choice(strategies)

            # Randomize timestamp within the day
            hours = random.randint(0, 23)
            minutes = random.randint(0, 59)
            seconds = random.randint(0, 59)
            timestamp = date.replace(hour=hours, minute=minutes, second=seconds)

            trade = Trade(
                timestamp=timestamp,
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                value=value,
                fee=fee,
                exchange=config.TRADING_EXCHANGE,
                strategy=strategy,
                executed=True
            )
            session.add(trade)

            # Also create a signal log for this trade
            confidence = random.uniform(0.65, 0.95)
            signal = SignalLog(
                timestamp=timestamp - timedelta(minutes=random.randint(1, 5)),
                symbol=symbol,
                strategy=strategy,
                signal_type=side,
                confidence=confidence,
                price=price * (1 - 0.001) if side == "buy" else price * (1 + 0.001),  # Slight difference from executed price
                signal_metadata=json.dumps({  # Changed from metadata to signal_metadata
                    "reason": f"{'Bullish' if side == 'buy' else 'Bearish'} signal",
                    "indicators": {
                        "ma_fast": price * (0.98 if side == "buy" else 1.02),
                        "ma_slow": price * (0.97 if side == "buy" else 1.03),
                        "rsi": 30 if side == "buy" else 70
                    }
                }),
                executed=True
            )
            session.add(signal)

    # Create some unexecuted signals too
    for _ in range(5):
        symbol = random.choice(symbols)
        side = random.choice(["buy", "sell"])
        strategy = random.choice(strategies)

        price = 0
        base_currency = symbol.split('/')[0]
        if base_currency == "BTC":
            price = random.uniform(45000, 55000)
        elif base_currency == "ETH":
            price = random.uniform(2800, 3200)
        elif base_currency == "SOL":
            price = random.uniform(90, 110)
        elif base_currency == "ADA":
            price = random.uniform(0.45, 0.55)

        confidence = random.uniform(0.5, 0.64)  # Not high enough confidence
        timestamp = datetime.utcnow() - timedelta(days=random.randint(0, 7))

        signal = SignalLog(
            timestamp=timestamp,
            symbol=symbol,
            strategy=strategy,
            signal_type=side,
            confidence=confidence,
            price=price,
            executed=False,
            signal_metadata=json.dumps({  # Changed from metadata to signal_metadata
                "reason": f"{'Bullish' if side == 'buy' else 'Bearish'} signal but confidence too low",
                "indicators": {
                    "ma_fast": price * (0.99 if side == "buy" else 1.01),
                    "ma_slow": price * (0.98 if side == "buy" else 1.02),
                    "rsi": 40 if side == "buy" else 60
                }
            })
        )
        session.add(signal)

    # Create some example balances
    currencies = ["USDT", "BTC", "ETH", "SOL", "ADA"]
    amounts = {
        "USDT": cash_value,
        "BTC": holdings["BTC"],
        "ETH": holdings["ETH"],
        "SOL": holdings["SOL"],
        "ADA": holdings["ADA"]
    }

    for currency in currencies:
        balance = Balance(
            currency=currency,
            amount=amounts[currency],
            exchange=config.TRADING_EXCHANGE
        )
        session.add(balance)

    # Commit all changes
    session.commit()
    session.close()

    print("Sample data created successfully!")


if __name__ == "__main__":
    print("Initializing database...")
    engine = initialize_database()
    
    print("Running database migrations...")
    migrate_database()
    
    print("Creating sample data...")
    create_sample_data()
    
    print("Database initialization complete!")
