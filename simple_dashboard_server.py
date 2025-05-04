#!/usr/bin/env python3
"""
Simple dashboard server script that uses the simplified dashboard implementation.
"""

import time
from src.utils.dashboard_simplified import dashboard
from loguru import logger

if __name__ == "__main__":
    # Configure dashboard to use port 5003 to match Nginx config
    dashboard.port = 5003
    dashboard.host = "0.0.0.0"
    
    # Start the dashboard
    print(f"Starting dashboard on http://localhost:{dashboard.port}")
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
