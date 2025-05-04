#!/bin/bash

# This script installs the crypto dashboard as a systemd service

# Make sure we're in the right directory
cd /home/ubuntu/Long_Term_crypto_trading_bot

# Make sure the logs directory exists
mkdir -p logs

# Copy the service file to the systemd directory
sudo cp crypto-dashboard.service /etc/systemd/system/

# Reload systemd configuration
echo "Reloading systemd configuration..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling crypto-dashboard service to start on boot..."
sudo systemctl enable crypto-dashboard.service

# Start the service
echo "Starting crypto-dashboard service..."
sudo systemctl start crypto-dashboard.service

# Check status
echo "Checking service status..."
sudo systemctl status crypto-dashboard.service

echo ""
echo "Dashboard service installation complete."
echo "The dashboard should now be running on port 5003."
echo ""
echo "To check service status: sudo systemctl status crypto-dashboard.service"
echo "To stop the service:     sudo systemctl stop crypto-dashboard.service"
echo "To restart the service:  sudo systemctl restart crypto-dashboard.service"
echo "To view logs:            journalctl -u crypto-dashboard.service"
echo ""
echo "The website should be accessible at: http://steampunk.holdings"
