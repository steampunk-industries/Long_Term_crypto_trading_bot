#!/usr/bin/env python3
"""
Generate mock data for the crypto trading bot dashboard.
This script bypasses the SQLAlchemy ORM and uses SQLite directly to create test data.
"""

import os
import random
import json
import sqlite3
import uuid
from datetime import datetime, timedelta

def ensure_directory(path):
    """Ensure a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def setup_database():
    """Set up the SQLite database."""
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), 'data')
    ensure_directory(data_dir)
    
    # Connect to the database
    db_path = os.path.join(data_dir, 'crypto_bot.db')
    print(f"Setting up database at {db_path}")
    
    # Delete existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    # Users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    ''')
    
    # Trades table
    cursor.execute('''
        CREATE TABLE trades (
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
    
    # Balances table
    cursor.execute('''
        CREATE TABLE balances (
            id INTEGER PRIMARY KEY,
            exchange TEXT NOT NULL,
            currency TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL,
            is_paper INTEGER NOT NULL
        )
    ''')
    
    # Portfolio snapshots table
    cursor.execute('''
        CREATE TABLE portfolio_snapshots (
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
    
    # Signal logs table
    cursor.execute('''
        CREATE TABLE signal_logs (
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
    
    # Create admin user
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
    ''', ('admin', 'admin@example.com', 
          'pbkdf2:sha256:150000$q33ygqtq$ed5e81b328cd9cdd3b569aea2d6eac43cc94fee52799a41de453088cf36c42c1', 
          datetime.utcnow().isoformat()))
    
    conn.commit()
    print("Created database tables")
    
    return conn, cursor

def generate_mock_trades(conn, cursor):
    """Generate mock trades."""
    print("Generating mock trades...")
    
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
        fee = cost * 0.001  # Assume 0.1% fee
        
        # Insert trade
        cursor.execute('''
            INSERT INTO trades (
                exchange, symbol, order_id, side, type, amount, price, cost, fee, fee_currency, 
                timestamp, is_paper, strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            exchange, symbol, str(uuid.uuid4()), side, 'market', amount, price, cost, fee, 'USDT',
            timestamp.isoformat(), 1, 'moving_average_crossover' if random.random() > 0.5 else 'rsi_strategy'
        ))
    
    conn.commit()
    print("Generated mock trades")

def generate_mock_balances(conn, cursor):
    """Generate mock balances."""
    print("Generating mock balances...")
    
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
            
            cursor.execute('''
                INSERT INTO balances (exchange, currency, amount, timestamp, is_paper)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                exchange, balance_data['currency'], amount, 
                (today - timedelta(minutes=random.randint(0, 120))).isoformat(), 1
            ))
    
    conn.commit()
    print("Generated mock balances")

def generate_mock_portfolio_snapshots(conn, cursor):
    """Generate mock portfolio snapshots."""
    print("Generating mock portfolio snapshots...")
    
    # Initial portfolio value
    initial_value = 10000  # Default initial capital
    
    # Generate some portfolio data for the last 30 days
    today = datetime.utcnow()
    
    # Initial value
    current_value = initial_value
    peak_value = initial_value
    
    # Create a new Portfolio Snapshot instance to save to database
