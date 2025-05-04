#!/usr/bin/env python3

"""
WSGI entry point for the Crypto Trading Bot Dashboard
This file serves as the application entry point for Gunicorn
"""

import logging
from src.dashboard.app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Flask application using the factory pattern
try:
    app = create_app()
    logger.info("Dashboard application created successfully")
except Exception as e:
    logger.error(f"Failed to create application: {e}")
    raise

if __name__ == "__main__":
    # This allows the file to be run directly during development
    app.run(host='0.0.0.0', port=5003, debug=True)
