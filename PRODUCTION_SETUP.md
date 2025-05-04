# Production Dashboard Setup for steampunk.holdings

This guide explains the production-ready setup for the steampunk.holdings dashboard application.

## Overview

The dashboard is deployed using a production-ready architecture:

1. **Gunicorn** as the WSGI production server
2. **Nginx** as a reverse proxy and static file server
3. **Systemd** for service management and automatic restarts
4. **SQLite/PostgreSQL** for data persistence

## How to Deploy

### Automated Deployment

The simplest way to deploy is to use the deployment script:

```bash
./deploy_production_dashboard.sh
```

This script will:
- Check dependencies
- Initialize the database
- Set up systemd service
- Configure Nginx
- Start all services
- Verify that everything is working

### Manual Deployment

If you prefer to deploy manually, follow these steps:

1. Set environment variables in `.env`
2. Install Gunicorn: `pip install gunicorn`
3. Copy the service file: `sudo cp crypto-dashboard.service /etc/systemd/system/`
4. Set up Nginx: `sudo cp nginx/dashboard.conf /etc/nginx/sites-available/steampunk.conf`
5. Enable the site: `sudo ln -sf /etc/nginx/sites-available/steampunk.conf /etc/nginx/sites-enabled/`
6. Reload systemd: `sudo systemctl daemon-reload`
7. Enable and start services:
   ```
   sudo systemctl enable crypto-dashboard.service
   sudo systemctl start crypto-dashboard.service
   sudo systemctl restart nginx
   ```

## Monitoring and Management

### Service Status

Check if the dashboard is running:

```bash
sudo systemctl status crypto-dashboard.service
```

### Logs

View application logs:

```bash
# Main application logs
cat logs/dashboard.log

# System service logs
sudo journalctl -u crypto-dashboard.service

# Nginx logs
sudo cat /var/log/nginx/access.log
sudo cat /var/log/nginx/error.log
```

### Health Check

The application exposes a health check endpoint:

```bash
curl http://localhost:5003/health
```

Expected response:
```json
{"status":"ok","timestamp":1714319893.5839462}
```

### Resource Usage

Check CPU and memory usage:

```bash
ps aux | grep gunicorn
```

## Troubleshooting

### Dashboard Not Accessible

1. Check if the service is running:
   ```
   sudo systemctl status crypto-dashboard.service
   ```

2. Check if Nginx is running:
   ```
   sudo systemctl status nginx
   ```

3. Check if port 5003 is listening:
   ```
   sudo netstat -tulpn | grep 5003
   ```

4. Check application logs for errors:
   ```
   tail -n 50 logs/dashboard.log
   ```

5. Check Nginx logs:
   ```
   sudo tail -n 50 /var/log/nginx/error.log
   ```

### Database Issues

If experiencing database issues:

1. Check database connection settings in `.env`
2. Verify database schema:
   ```
   python3 -c "from src.database.models import Base, engine; Base.metadata.create_all(engine)"
   ```

### Restarting Services

To restart after configuration changes:

```bash
sudo systemctl restart crypto-dashboard.service
sudo systemctl restart nginx
```

## Scaling Considerations

For higher traffic loads, consider:

1. Increasing Gunicorn workers:
   ```
   # In crypto-dashboard.service
   ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:5003 --workers 8 ...
   ```

2. Moving to PostgreSQL for database
3. Setting up load balancing across multiple instances
4. Implementing caching with Redis or Memcached

## Security Notes

1. The SECRET_KEY should be changed to a random value specific to your environment
2. Consider enabling HTTPS for production with Let's Encrypt
3. Keep system packages updated regularly
4. When adding external domains to access the API, be sure to add appropriate CORS headers

## Maintenance

Schedule regular maintenance:

1. Database backups
2. Log rotation (handled by systemd)
3. System updates
4. Configuration review
