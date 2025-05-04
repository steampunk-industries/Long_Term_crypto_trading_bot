#!/bin/bash

# ======================================================
# Setup Virtual Environment and Deploy Dashboard
# ======================================================

set -e  # Exit on first error

echo "===== Setting Up Virtual Environment ====="
echo "$(date)"

# Create logs directory if it doesn't exist
mkdir -p logs

# Set up virtual environment as the current user
if [ ! -d "crypto_venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv crypto_venv
else 
    echo "Using existing virtual environment"
fi

# Activate and install dependencies
echo "Installing dependencies..."
source crypto_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Verify Python environment
python --version
pip --version

# Initialize database
echo "Initializing database..."
python -c "from src.database.models import Base, engine; Base.metadata.create_all(engine)"

# Make production-ready dashboard executable
chmod +x production_dashboard.py

# Run dashboard directly to test
echo "Testing the dashboard directly..."
python production_dashboard.py &
DASHBOARD_PID=$!

# Wait a bit for it to start
sleep 3

# Test if it's running
echo "Testing dashboard availability..."
curl -s http://localhost:5003/health

# Kill the test process
kill $DASHBOARD_PID

# Now call the sudo script to set up services
echo
echo "===== Now we will set up the system services ====="
echo "You will be prompted for sudo password"
echo "Press Enter to continue..."
read

# Now run the system-level setup that requires sudo
sudo bash -c '
# Copy service file
echo "Setting up systemd service..."
cp crypto-dashboard.service /etc/systemd/system/
systemctl daemon-reload

# Configure Nginx
echo "Configuring Nginx..."
if [ -f /etc/nginx/sites-enabled/default ]; then
    mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.bak
    echo "Disabled default Nginx site."
fi

cp nginx/dashboard.conf /etc/nginx/sites-available/steampunk.conf
ln -sf /etc/nginx/sites-available/steampunk.conf /etc/nginx/sites-enabled/
echo "Nginx configuration updated."

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t

# Start or restart services
echo "Starting services..."
systemctl enable crypto-dashboard.service
systemctl restart crypto-dashboard.service
systemctl restart nginx

# Check service status
echo "Checking service status..."
systemctl status crypto-dashboard.service --no-pager
systemctl status nginx --no-pager
'

echo
echo "===== Dashboard Deployment Complete ====="
echo "Dashboard should now be accessible at: http://steampunk.holdings"
echo "Check logs at: logs/dashboard.log"
echo
echo "To monitor the service, use:"
echo "  sudo systemctl status crypto-dashboard.service"
echo "  sudo journalctl -u crypto-dashboard.service"
