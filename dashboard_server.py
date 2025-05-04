#!/usr/bin/env python3
"""
Script to run the full dashboard component.
"""
import os
from loguru import logger

from src.dashboard.app import create_app, run_dashboard

if __name__ == "__main__":
    # Set environment variables if needed
    os.environ['FLASK_ENV'] = 'production'
    
    # Run the full dashboard application
    logger.info("Starting full dashboard application")
    run_dashboard()
