# Website Setup Guide for steampunk.holdings

This guide explains how to fix the "502 Bad Gateway" error on steampunk.holdings and set up the dashboard correctly.

## Problem Analysis

The 502 Bad Gateway error occurred because:

1. Nginx was configured to proxy requests to port 5003, but the dashboard server was configured to run on port 5002
2. There was no service ensuring that the dashboard stays running even after system reboots

## Solution

The following changes have been made to fix the issue:

1. Updated `dashboard_server.py` to use port 5003 to match the Nginx configuration
2. Fixed shebang line in scripts to ensure proper execution
3. Created a systemd service for reliable dashboard operation
4. Added scripts for easy installation and management

## Installation Instructions

### Option 1: Using the Service Installer (Recommended)

This sets up the dashboard as a system service that will automatically start on boot and restart if it crashes.

1. Run the installer script:
```bash
sudo ./install_dashboard_service.sh
```

2. Check that the service is running:
```bash
sudo systemctl status crypto-dashboard.service
```

3. Ensure Nginx is running and correctly configured:
```bash
sudo systemctl status nginx
```

4. The website should now be accessible at http://steampunk.holdings

### Option 2: Manual Start

If you prefer to run the dashboard manually:

1. Run the start script:
```bash
./start_website.sh
```

2. The script will:
   - Start the dashboard on port 5003
   - Create a PID file (dashboard.pid)
   - Start Nginx if it's not running
   - Reload the Nginx configuration

## Troubleshooting

If you're still experiencing issues:

1. Check the dashboard logs:
```bash
cat logs/dashboard.log
```

2. Check the Nginx error logs:
```bash
sudo cat /var/log/nginx/error.log
```

3. Verify the dashboard is running on port 5003:
```bash
netstat -tulpn | grep 5003
```

4. Test the dashboard directly:
```bash
curl http://localhost:5003
```

5. Restart both services:
```bash
sudo systemctl restart crypto-dashboard.service
sudo systemctl restart nginx
```

## Service Management Commands

- Start the dashboard: `sudo systemctl start crypto-dashboard.service`
- Stop the dashboard: `sudo systemctl stop crypto-dashboard.service`
- Restart the dashboard: `sudo systemctl restart crypto-dashboard.service`
- View dashboard logs: `sudo journalctl -u crypto-dashboard.service`
- Check status: `sudo systemctl status crypto-dashboard.service`

## DNS Configuration

If the website is still not accessible, verify that the DNS records for steampunk.holdings point to your server's IP address.
