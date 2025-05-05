#!/bin/bash

# Start the dashboard server in the background
echo "Starting dashboard server on port 5003"
cd /home/ubuntu/Long_Term_crypto_trading_bot
python3 dashboard_server.py > logs/dashboard.log 2>&1 &

# Store the PID of the dashboard process
echo $! > dashboard.pid

# Check if Nginx is running, start if not
if ! systemctl is-active --quiet nginx; then
    echo "Starting Nginx"
    sudo systemctl start nginx
else
    echo "Nginx is already running"
fi

# Reload Nginx configuration
echo "Reloading Nginx configuration"
sudo systemctl reload nginx

echo "Website should now be accessible at http://steampunk.holdings"
echo "Check logs/dashboard.log for any issues"
