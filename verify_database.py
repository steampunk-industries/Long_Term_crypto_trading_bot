#!/usr/bin/env python3
"""
Verify database connectivity for the crypto trading bot.
This script tests the database setup and creates some initial records.
"""

import os
import sys
import sqlite3
from datetime import datetime

def verify_sqlite():
    """Test SQLite database connectivity directly."""
    print("\n===== Testing Direct SQLite Connection =====")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Connect to SQLite database
    db_path = os.path.join(data_dir, 'crypto_bot.db')
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    try:
        # Create new connection
        conn = sqlite3.connect(db_path)
        print(f"Connected to SQLite database: {db_path}")
        
        # Create cursor
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
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
        
        print("Created tables successfully")
        
        # Insert sample data
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@example.com', 'password_hash', datetime.now().isoformat()))
        
        cursor.execute('''
            INSERT INTO portfolio_snapshots 
            (timestamp, total_value_usd, pnl_daily, pnl_weekly, pnl_monthly, pnl_all_time, drawdown, is_paper)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), 10000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1))
        
        # Commit changes
        conn.commit()
        print("Inserted sample data successfully")
        
        # Verify data
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM portfolio_snapshots')
        snapshot_count = cursor.fetchone()[0]
        
        print(f"Database has {user_count} users and {snapshot_count} portfolio snapshots")
        
        # Close connection
        conn.close()
        print("SQLite test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error testing SQLite: {e}")
        return False

if __name__ == "__main__":
    print("Database Verification Utility")
    print(f"Current directory: {os.getcwd()}")
    
    # Verify SQLite connection
    sqlite_ok = verify_sqlite()
    
    if sqlite_ok:
        print("\nDatabase verification completed successfully.")
        print("This confirms that SQLite is working properly.")
        print("\nTo verify the SQLAlchemy integration, you need to:") 
        print("1. Fix the metadata issue in src/database/models.py")
        print("2. Run `python3 -c \"from src.database.models import init_db; init_db()\"`")
    else:
        print("\nDatabase verification failed. Check errors above.")
