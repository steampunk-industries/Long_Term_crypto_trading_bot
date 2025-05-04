#!/bin/bash

# ======================================================
# Production Dashboard Deployment for steampunk.holdings
# ======================================================

set -e  # Exit on first error

echo "===== Starting Production Dashboard Deployment ====="
echo "$(date)"
echo

# Create logs directory if it doesn't exist
mkdir -p logs
echo "Created logs directory."

# Set up and install dependencies in the virtual environment
echo "Setting up virtual environment..."
if [ ! -d "crypto_venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv crypto_venv
fi

# Activate virtual environment and install dependencies
crypto_venv/bin/pip install --upgrade pip
crypto_venv/bin/pip install -r requirements.txt
crypto_venv/bin/pip install gunicorn

# Verify Python environment and dependencies
echo "Checking Python environment and dependencies..."
crypto_venv/bin/python --version
crypto_venv/bin/pip --version

# Check database initialization
echo "Initializing database if needed..."
PYTHONPATH=$PWD crypto_venv/bin/python -c "from src.database.models import Base, engine; Base.metadata.create_all(engine)"

# Make production-ready dashboard executable
chmod +x production_dashboard.py
echo "Made production dashboard script executable."

# Ensure service file is properly set up
echo "Setting up systemd service file..."
sudo cp crypto-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload

# Configure Nginx
echo "Configuring Nginx..."
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.bak
    echo "Disabled default Nginx site."
fi

sudo cp nginx/dashboard.conf /etc/nginx/sites-available/steampunk.conf
sudo ln -sf /etc/nginx/sites-available/steampunk.conf /etc/nginx/sites-enabled/
echo "Nginx configuration updated."

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Start or restart services
echo "Starting services..."
sudo systemctl enable crypto-dashboard.service
sudo systemctl restart crypto-dashboard.service
sudo systemctl restart nginx

# Wait for services to start
echo "Waiting for services to start..."
sleep 5

# Check service status
echo "Checking service status..."
sudo systemctl status crypto-dashboard.service --no-pager
sudo systemctl status nginx --no-pager

# Test the API availability
echo "Testing dashboard availability..."
curl -s http://localhost:5003/health | grep -q "ok" && echo "Dashboard API is responding correctly" || echo "Dashboard API is not responding"

echo
echo "===== Production Dashboard Deployment Complete ====="
echo "Dashboard should now be accessible at: http://steampunk.holdings"
echo "Check logs at: logs/dashboard.log"
echo
echo "To monitor the service, use:"
echo "  sudo systemctl status crypto-dashboard.service"
echo "  sudo journalctl -u crypto-dashboard.service"
