# Installing and Configuring the Web Server on EC2

This guide provides detailed instructions for installing and configuring the web server on your EC2 instance to host the cryptocurrency trading bot dashboard.

## SSH Access

First, connect to your EC2 instance (see SSH_CONNECTION_GUIDE.md for troubleshooting connection issues):

```bash
ssh -i /path/to/Trading_App_PairKey1.pem ubuntu@3.220.9.26
```

## Installing Nginx

Nginx is a high-performance web server that will serve your trading bot dashboard:

```bash
# Update package lists
sudo apt update

# Install Nginx
sudo apt install -y nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx

# Start Nginx service
sudo systemctl start nginx

# Verify Nginx is running
sudo systemctl status nginx
```

You should see output indicating that Nginx is active (running).

## Configuring Nginx for the Trading Bot Dashboard

Create a new Nginx configuration file for your trading bot:

```bash
sudo nano /etc/nginx/sites-available/crypto-trading-bot
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name steampunk.holdings www.steampunk.holdings;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Additional configuration for static files
    location /static/ {
        alias /home/ubuntu/Long_Term_crypto_trading_bot/static/;
    }
}
```

Enable the site and remove the default configuration:

```bash
# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/crypto-trading-bot /etc/nginx/sites-enabled/

# Remove default site configuration
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload Nginx to apply changes
sudo systemctl reload nginx
```

## Setting Up SSL with Let's Encrypt

For secure HTTPS access:

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d steampunk.holdings -d www.steampunk.holdings

# Follow the prompts to complete the setup
# Choose to redirect HTTP traffic to HTTPS when asked
```

## Verifying the Web Server

After installation, verify that Nginx is working:

```bash
# Check if Nginx is listening on port 80
sudo netstat -tuln | grep 80

# Check if Nginx is listening on port 443 (after SSL setup)
sudo netstat -tuln | grep 443

# View Nginx error logs if needed
sudo tail -f /var/log/nginx/error.log
```

You should be able to access the default Nginx page by visiting your EC2 instance's IP address in a web browser:
http://3.220.9.26

## Troubleshooting

If you encounter issues:

1. **Check Nginx status**:
   ```bash
   sudo systemctl status nginx
   ```

2. **Check Nginx error logs**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Verify firewall settings**:
   ```bash
   sudo ufw status
   ```

4. **Check if ports are open**:
   ```bash
   sudo netstat -tuln
   ```

5. **Restart Nginx**:
   ```bash
   sudo systemctl restart nginx
   ```

## Next Steps

After successfully installing and configuring Nginx, proceed to deploying the trading bot application as detailed in the FINAL_DEPLOYMENT_STEPS.md file.
