#!/usr/bin/env python3
"""
Local deployment script for the Crypto Trading Bot with dashboard.
This script starts both the paper trading bot and dashboard as separate processes.
"""

import os
import sys
import time
import signal
import subprocess

# Create required directories
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("models/scalping", exist_ok=True)
print("✓ Required directories created")

# Initialize database
print("Initializing database...")
subprocess.run([sys.executable, "-c", "from src.utils.database import init_db; init_db()"], check=True)
print("✓ Database initialized")

# Start dashboard in a separate process
print("Starting dashboard server...")
dashboard_process = subprocess.Popen([sys.executable, "dashboard_server.py"], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.STDOUT)
time.sleep(2)  # Give it time to start
print("✓ Dashboard running at http://localhost:5002")

# Start paper trading in a separate process
print("Starting mock trading system...")
trading_process = subprocess.Popen([sys.executable, "simple_mock_trading.py"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
time.sleep(2)  # Give it time to start
print("✓ Paper trading system started")

print("\n=== DEPLOYMENT SUCCESSFUL ===")
print("Paper trading bot is now running with alternative data sources.")
print("Dashboard:    http://localhost:5002")
print("Log file:     logs/crypto_bot.log")
print("\nPress Ctrl+C to stop all systems.")

# Set up signal handler for Ctrl+C
def signal_handler(sig, frame):
    print("\nShutting down all systems...")
    dashboard_process.terminate()
    trading_process.terminate()
    print("Systems stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Keep the main process running
try:
    while True:
        # Check if processes are still running
        if dashboard_process.poll() is not None:
            print(f"! Dashboard has stopped unexpectedly (exit code: {dashboard_process.poll()})")
            signal_handler(None, None)
            
        if trading_process.poll() is not None:
            print(f"! Paper trading has stopped unexpectedly (exit code: {trading_process.poll()})")
            signal_handler(None, None)
            
        time.sleep(1)
except KeyboardInterrupt:
    signal_handler(None, None)
