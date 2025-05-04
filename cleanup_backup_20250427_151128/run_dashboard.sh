#!/bin/bash

# Set up environment
cd /home/ubuntu/Long_Term_crypto_trading_bot

# Make sure logs directory exists
mkdir -p logs

# Export any needed environment variables
export PYTHONPATH=/home/ubuntu/Long_Term_crypto_trading_bot

# Run the dashboard server
echo "Starting dashboard server..."
python3 dashboard_server.py
