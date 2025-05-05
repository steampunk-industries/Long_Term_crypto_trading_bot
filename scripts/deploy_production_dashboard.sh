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

# Backup critical files before modification
echo "Creating backups of critical files..."
cp crypto-dashboard.service crypto-dashboard.service.bak
[ -f wsgi.py ] && cp wsgi.py wsgi.py.bak

# Activate virtual environment and install dependencies
crypto_venv/bin/pip install --upgrade pip
crypto_venv/bin/pip install -r requirements.txt
crypto_venv/bin/pip install gunicorn

# Check Gunicorn version
echo "Gunicorn version:"
crypto_venv/bin/gunicorn --version

# Make WSGI file executable
chmod +x wsgi.py
echo "Made WSGI entry point executable."

# Set up log rotation for gunicorn logs
echo "Setting up log rotation for gunicorn logs..."
sudo tee /etc/logrotate.d/gunicorn-dashboard << EOF
/home/ubuntu/Long_Term_crypto_trading_bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ubuntu ubuntu
}
EOF

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

# Test the API availability with retries
echo "Testing dashboard availability..."
MAX_RETRIES=5
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:5003/health | grep -q "ok"; then
        echo "Dashboard API is responding correctly"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT+1))
        echo "Attempt $RETRY_COUNT of $MAX_RETRIES: Dashboard not ready, waiting..."
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "WARNING: Dashboard API is not responding after $MAX_RETRIES attempts"
    echo "Check the logs with: sudo journalctl -u crypto-dashboard.service -n 50"
fi

echo
echo "===== Production Dashboard Deployment Complete ====="
echo "Dashboard should now be accessible at: http://steampunk.holdings"
echo "Check logs at: logs/dashboard.log"
echo
echo "To monitor the service, use:"
echo "  sudo systemctl status crypto-dashboard.service"
echo "  sudo journalctl -u crypto-dashboard.service"
