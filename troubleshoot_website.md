# Website Connectivity Troubleshooting

## Current Status

The CloudFormation stack `crypto-trading-x86` has been successfully created with all resources:
- EC2 Instance (i-0a647be0188f8831b) with IP 3.220.9.26
- RDS Database
- Security Groups
- IAM Roles

## Connectivity Issues

The website is currently unreachable for the following reasons:

1. **Web Server Not Running**: 
   - The EC2 instance console output shows the system has booted successfully
   - However, there's no indication that a web server (nginx/apache) is running

2. **Security Group Configuration**:
   - Port 80 (HTTP) is open
   - Port 443 (HTTPS) is open (we added this)
   - SSH access is configured correctly

3. **DNS Configuration**:
   - The domain steampunk.holdings needs to be pointed to the EC2 IP address: 3.220.9.26
   - This should be done in Route53 by updating the A record

## Next Steps

1. **SSH into the instance to install and configure the web server**:
   ```bash
   ssh -i Trading_App_PairKey1.pem ubuntu@3.220.9.26
   ```

2. **Install and configure the web server**:
   ```bash
   sudo apt update
   sudo apt install -y nginx
   sudo systemctl enable nginx
   sudo systemctl start nginx
   ```

3. **Deploy the trading bot application**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-repo/crypto-trading-bot.git
   
   # Configure the application
   cd crypto-trading-bot
   # Configure database connection to RDS endpoint:
   # crypto-trading-x86-dbinstance-oqk9b07az0zt.citay02wsl50.us-east-1.rds.amazonaws.com
   ```

4. **Update DNS in Route53**:
   - Go to Route53 in AWS Console
   - Select the hosted zone for steampunk.holdings
   - Update the A record to point to 3.220.9.26
   - Set TTL to 300 seconds (5 minutes) for faster propagation

## Verification

After completing these steps:

1. **Check web server status**:
   ```bash
   sudo systemctl status nginx
   ```

2. **Test local connectivity**:
   ```bash
   curl http://localhost
   ```

3. **Test remote connectivity**:
   ```bash
   # From your local machine
   curl http://3.220.9.26
   ```

4. **Test domain connectivity** (after DNS propagation):
   ```bash
   curl http://steampunk.holdings
   ```

The website should be accessible once the web server is running and DNS has propagated.
