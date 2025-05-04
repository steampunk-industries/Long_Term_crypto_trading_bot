#!/usr/bin/env python3
"""
Test script to verify the fixed database model.
"""

import os
import sys
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import initialize_database, SignalLog, get_session

def test_database_fix():
    """Test that the database models work correctly with the renamed column."""
    print("\n===== Testing Database Fixes =====")
    
    try:
        # Initialize the database
        engine = initialize_database()
        print("✅ Database initialized successfully")
        
        # Create a session
        session = get_session()
        print("✅ Database session established")
        
        # Create a test signal log entry
        metadata = {
            'reason': 'Test signal',
            'fast_ma': 45000.0,
            'slow_ma': 44000.0,
            'close': 46000.0,
            'stop_loss': 45000.0,
            'take_profit': 47000.0
        }
        
        signal_log = SignalLog(
            symbol="BTC/USD",
            strategy="TestStrategy",
            signal_type="buy",
            confidence=0.85,
            price=46000.0,
            signal_metadata=json.dumps(metadata),  # Using renamed column
            executed=False,
            trade_id=None
        )
        
        # Add to the database
        session.add(signal_log)
        session.commit()
        print(f"✅ Created test signal log with ID: {signal_log.id}")
        
        # Retrieve it back
        retrieved_log = session.query(SignalLog).filter_by(id=signal_log.id).first()
        print(f"✅ Retrieved test signal log: {retrieved_log.symbol} {retrieved_log.signal_type}")
        
        # Convert to dictionary to test the to_dict method
        log_dict = retrieved_log.to_dict()
        print("✅ Converted signal log to dictionary")
        
        # Verify metadata is properly loaded
        if 'metadata' in log_dict and 'reason' in log_dict['metadata']:
            print(f"✅ Metadata properly stored and retrieved: {log_dict['metadata']['reason']}")
        else:
            print("❌ Metadata not properly stored or retrieved")
        
        # Clean up
        session.delete(signal_log)
        session.commit()
        session.close()
        print("✅ Test data cleaned up")
        
        print("\n✅ Database fixes verified successfully")
        return True
    except Exception as e:
        print(f"❌ Error testing database fix: {e}")
        return False

if __name__ == "__main__":
    test_database_fix()
