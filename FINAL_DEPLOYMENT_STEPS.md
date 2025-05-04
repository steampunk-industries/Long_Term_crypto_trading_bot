# Cryptocurrency Trading Bot - Final Deployment Steps

## Current Status

The infrastructure is deployed, but the website is not yet accessible because:

1. The web server (nginx/apache) needs to be installed and configured on the EC2 instance
2. The trading bot application needs to be deployed to the EC2 instance
3. DNS records need to be updated in Route53 to point to the EC2 IP address

## Next Steps

### 1. SSH into the EC2 instance:

```bash
ssh -i Trading_App_PairKey1.pem ubuntu@3.220.9.26
```

### 2. Install and configure the web server:

```bash
# Update package lists
sudo apt update

# Install Nginx
sudo apt install -y nginx

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Verify Nginx is running
sudo systemctl status nginx
```

### 3. Deploy the trading bot application:

```bash
# Clone the repository from your local machine to the EC2 instance
# Option 1: Using SCP
scp -i Trading_App_PairKey1.pem -r /Users/steampunkinc/Documents/Projects/Long_Term_crypto_trading_bot ubuntu@3.220.9.26:~/

# Option 2: Using Git (if your code is in a repository)
git clone https://github.com/your-repo/crypto-trading-bot.git

# Install dependencies
cd ~/Long_Term_crypto_trading_bot
pip install -r requirements.txt

# Configure database connection
# Edit the .env file to point to the RDS instance
cat > .env << EOL
DB_HOST=crypto-trading-x86-dbinstance-oqk9b07az0zt.citay02wsl50.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=crypto_bot
DB_USER=postgres
DB_PASSWORD=Pizza&Pandas23
API_KEY=f3bf7dca6b4afdf971d88ad133baea13
EOL

# Configure Nginx to serve the application
sudo bash -c 'cat > /etc/nginx/sites-available/crypto-trading-bot << EOL
server {
    listen 80;
    server_name steampunk.holdings www.steampunk.holdings;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL'

# Enable the site
sudo ln -s /etc/nginx/sites-available/crypto-trading-bot /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl reload nginx

# Start the application
cd ~/Long_Term_crypto_trading_bot
nohup python src/main.py &
```

### 4. Update DNS in Route53:

1. Go to the AWS Management Console
2. Navigate to Route53 service
3. Select the hosted zone for steampunk.holdings
4. Create or update the A record:
   - Name: @ (or leave blank for root domain)
   - Type: A
   - Value: 3.220.9.26
   - TTL: 300 seconds
5. Create or update the www A record:
   - Name: www
   - Type: A
   - Value: 3.220.9.26
   - TTL: 300 seconds

## Access Information

- **EC2 Public IP**: 3.220.9.26
- **RDS Endpoint**: crypto-trading-x86-dbinstance-oqk9b07az0zt.citay02wsl50.us-east-1.rds.amazonaws.com
- **Dashboard URL** (after DNS setup): https://steampunk.holdings
- **Login Credentials**:
  - Username: admin
  - Password: Pizza&Pandas23
  - API Key: f3bf7dca6b4afdf971d88ad133baea13

## Verification

After completing these steps:

1. **Test local connectivity on the EC2 instance**:
   ```bash
   curl http://localhost
   ```

2. **Test remote connectivity**:
   ```bash
   # From your local machine
   curl http://3.220.9.26
   ```

3. **Test domain connectivity** (after DNS propagation):
   ```bash
   curl http://steampunk.holdings
   ```

## Troubleshooting

If you encounter any issues:

1. **Check Nginx logs**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

2. **Check application logs**:
   ```bash
   tail -f ~/Long_Term_crypto_trading_bot/logs/crypto_bot.log
   ```

3. **Verify security group settings** in the AWS Console to ensure ports 80 and 443 are open

4. **Check DNS propagation** using online tools like whatsmydns.net
