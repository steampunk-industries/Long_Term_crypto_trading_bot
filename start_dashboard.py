#!/usr/bin/env python3
"""
Script to start the dashboard for the crypto trading bot.
"""

import time
from src.utils.dashboard import dashboard

if __name__ == "__main__":
    # Configure dashboard to use a different port
    dashboard.port = 5001
    
    # Start the dashboard
    print("Starting dashboard...")
    dashboard.start()
    
    # Keep the script running
    try:
        print(f"Dashboard is running at http://localhost:{dashboard.port}")
        print("Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        dashboard.stop()
