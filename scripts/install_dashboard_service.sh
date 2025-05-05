#!/bin/bash
#
# Crypto Trading Bot Dashboard Installation Script
# This script installs the crypto dashboard as a systemd service
# and sets up Nginx as a reverse proxy.

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo."
  exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Installing from base directory: $BASE_DIR"

# Step 1: Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx jq

# Step 2: Create a virtual environment
echo "Setting up virtual environment..."
if [ ! -d "$BASE_DIR/venv" ]; then
  python3 -m venv "$BASE_DIR/venv"
fi

# Step 3: Install dependencies
echo "Installing Python dependencies..."
"$BASE_DIR/venv/bin/pip" install -r "$BASE_DIR/requirements.txt"

# Step 4: Initialize the database
echo "Initializing database..."
"$BASE_DIR/venv/bin/python" "$BASE_DIR/scripts/init_database.py"

# Step 5: Install systemd service file
echo "Installing systemd service file..."
cat > /etc/systemd/system/crypto-dashboard.service << EOF
[Unit]
Description=Crypto Trading Bot Dashboard
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$BASE_DIR
ExecStart=$BASE_DIR/venv/bin/python $BASE_DIR/dashboard_server.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/crypto-dashboard.log
StandardError=append:/var/log/crypto-dashboard.log
Environment=PORT=5003

[Install]
WantedBy=multi-user.target
EOF

# Step 6: Install Nginx configuration
echo "Installing Nginx configuration..."
DOMAIN_NAME=$(hostname)
if [ -z "$DOMAIN_NAME" ]; then
  DOMAIN_NAME="localhost"
fi

cat > /etc/nginx/sites-available/crypto-dashboard << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://127.0.0.1:5003;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

# Create a symbolic link to enable the site
ln -sf /etc/nginx/sites-available/crypto-dashboard /etc/nginx/sites-enabled/

# Test Nginx configuration
nginx -t

# Step 7: Setting up health check monitoring
echo "Setting up health check monitoring..."

# Create health check cron job to restart service if health check fails
cat > /etc/cron.d/crypto-dashboard-health-check << EOF
*/5 * * * * root curl -s http://localhost:5003/health > /dev/null || systemctl restart crypto-dashboard.service
EOF
chmod 644 /etc/cron.d/crypto-dashboard-health-check

# Install monitoring script for more detailed health checks
cat > /usr/local/bin/check-crypto-dashboard << EOF
#!/bin/bash
response=\$(curl -s http://localhost:5003/health)
status=\$(echo \$response | jq -r '.status')

if [ "\$status" != "ok" ]; then
  echo "[WARNING] Crypto dashboard health check failed: \$status"
  echo \$response | jq .
  
  # Log to syslog
  logger -t crypto-dashboard "Health check failed: \$status"
  
  # Check components to see what's failing
  components=\$(echo \$response | jq -r '.components | keys[]')
  
  for component in \$components; do
    comp_status=\$(echo \$response | jq -r ".components.\$component.status")
    if [ "\$comp_status" != "ok" ]; then
      logger -t crypto-dashboard "Component \$component is \$comp_status"
      echo "[WARNING] Component \$component is \$comp_status"
    fi
  done
fi
EOF
chmod +x /usr/local/bin/check-crypto-dashboard

# Add to crontab for regular checking and reporting
echo "*/15 * * * * root /usr/local/bin/check-crypto-dashboard >> /var/log/crypto-dashboard-health.log 2>&1" > /etc/cron.d/crypto-dashboard-health-report
chmod 644 /etc/cron.d/crypto-dashboard-health-report

# Step 8: Start and enable services
echo "Starting services..."
systemctl daemon-reload
systemctl enable crypto-dashboard.service
systemctl start crypto-dashboard.service
systemctl restart nginx

# Step 9: Display status and next steps
echo "Installation complete!"
echo "The dashboard should now be running at http://$DOMAIN_NAME"
echo 
echo "Service status:"
systemctl status crypto-dashboard.service --no-pager
echo
echo "Next steps:"
echo "1. To set up HTTPS, run: sudo certbot --nginx -d $DOMAIN_NAME"
echo "2. To check the logs: sudo journalctl -u crypto-dashboard.service"
echo "3. To check health status: curl http://localhost:5003/health | jq ."
echo "4. To monitor health checks: tail -f /var/log/crypto-dashboard-health.log"
