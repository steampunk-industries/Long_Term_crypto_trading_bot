#!/usr/bin/env python3
"""
Script to run both paper trading and dashboard for the crypto trading bot.
"""

import os
import time
import threading
import subprocess
import signal
import sys

from src.utils.dashboard import dashboard
from src.utils.database import init_db

def run_paper_trading():
    """Run paper trading in a separate process."""
    print("Starting paper trading...")
    
    # Use subprocess to run paper trading
    try:
        process = subprocess.Popen(
            ["python", "paper_trading.py", "--high-risk", "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Read and print output in real-time
        for line in process.stdout:
            print(f"Paper Trading: {line.strip()}")
            
    except Exception as e:
        print(f"Error running paper trading: {e}")
    
def run_dashboard():
    """Run the dashboard."""
    # Configure dashboard
    dashboard.port = 5001
    
    # Start the dashboard
    print(f"Starting dashboard on http://localhost:{dashboard.port}")
    dashboard.start()

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully shutdown."""
    print("\nShutting down...")
    dashboard.stop()
    
    # Find and kill paper trading process
    try:
        subprocess.run(["pkill", "-f", "paper_trading.py"], check=False)
    except Exception as e:
        print(f"Error stopping paper trading: {e}")
    
    sys.exit(0)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models/scalping", exist_ok=True)
    
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start dashboard in a separate thread
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    # Start paper trading in the main thread
    paper_trading_thread = threading.Thread(target=run_paper_trading)
    paper_trading_thread.daemon = True
    paper_trading_thread.start()
    
    print("System is running. Press Ctrl+C to stop.")
    print(f"Dashboard available at: http://localhost:{dashboard.port}")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
