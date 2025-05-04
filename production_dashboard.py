#!/usr/bin/env python3

"""
Production Dashboard for Crypto Trading Bot
This script runs the dashboard server in production mode.
"""

import os
import time
import json
import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from src.dashboard.app import create_app
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create the Flask application
app = create_app()

# Add health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "timestamp": time.time()})

# Run the application
if __name__ == '__main__':
    logger.info("Starting production dashboard server")
    # Force the server to listen on all interfaces (0.0.0.0) to allow external connections
    app.run(host='0.0.0.0', port=5003, debug=False)
