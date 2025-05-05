# AWS Deployment Guide for Crypto Trading Bot

This guide details how to deploy the crypto trading bot with a dashboard hosted at steampunk.holdings, using real-world BTC prices and alternative data sources.

## Required AWS Permissions

Before deployment, ensure your AWS account has the following permissions:

- **AmazonS3FullAccess**: For storing website assets, configuration files, and deployment artifacts
- **AmazonEC2FullAccess**: Essential for managing EC2 instances where your trading bot and website will run
- **AWSKeyManagementServicePowerUser**: For encrypting sensitive trading data and credentials
- **AWSCloudFormationFullAccess**: For deploying infrastructure as code
- **AmazonDynamoDBFullAccess**: If your bot stores trading data or state
- **AWSLambda_FullAccess**: If your architecture uses serverless components
- **CloudWatchFullAccess**: For monitoring both your trading bot and website
- **AmazonRoute53FullAccess**: If you're using custom domains for your website
- **AmazonRDSFullAccess**: If your application uses a database
- **ElasticLoadBalancingFullAccess**: If you're load balancing your website traffic
- **AmazonVPCFullAccess**: For network configuration
- **IAMFullAccess**: Since your script will be creating and managing roles
- **AWSCertificateManagerFullAccess**: If you're using HTTPS for your website

**Note:** AWS limits each user to 10 managed policies. Our script manages this limit through policy sets.

You can set up these permissions using our helper script:

```bash
# To list the available policy sets and policies without making changes
./setup_aws_permissions.sh --list-only

# To check if current user has all required policies
./setup_aws_permissions.sh --check

# To attach policies to current user (uses "standard" policy set - 7 policies)
./setup_aws_permissions.sh

# To create a new user with required policies
./setup_aws_permissions.sh --create-user crypto-bot-deployer

# Available policy sets:
# - minimal: Core infrastructure only (5 policies)
# - database: Core + Database (6 policies)
# - web: Core + Web hosting (7 policies)
# - monitoring: Core + Monitoring (6 policies)
# - serverless: Core + Lambda (6 policies)
# - standard: Core + Database + Monitoring (7 policies) [Default]
# - complete: Core + Database + Web + Monitoring (9 policies)
```

## System Overview

The deployed system consists of:

1. **EC2 Instance** - Runs the trading bot and hosts the dashboard
2. **RDS PostgreSQL Database** - Stores trading data, bot states, and analytics
3. **Docker Containers**:
   - Trading bot container
   - Dashboard container (with real-world prices)
   - Nginx container (for hosting at steampunk.holdings)
   - Prometheus and Grafana for monitoring

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Docker and Docker Compose installed
- Domain name (steampunk.holdings) with DNS control
- SSH key pair for EC2 instance

## Deployment Steps

### 1. Prepare Your Environment

Ensure you have:
- AWS CLI installed: `pip install awscli`
- AWS credentials configured: `aws configure`
- The repository cloned: `git clone <repository-url>`

### 2. Configuration Parameters

The deployment script requires several parameters:

- `EC2_KEY_NAME`: Name of your EC2 key pair
- `VPC_ID`: ID of the VPC to deploy into
- `SUBNET_ID`: ID of the subnet to deploy into
- `DB_PASSWORD`: Password for the PostgreSQL database
- `DOMAIN_NAME`: Domain name (defaults to steampunk.holdings)
- `EMAIL`: Email for SSL certificate notifications
- `INITIAL_BTC_PRICE`: Initial BTC price (defaults to 84000)

### 3. Run the Deployment Script

```bash
# Set required parameters
export EC2_KEY_NAME=your-key-pair
export VPC_ID=vpc-xxxxxxxxx
export SUBNET_ID=subnet-xxxxxxxxx
export DB_PASSWORD=secure-password

# Optional parameters
export DOMAIN_NAME=steampunk.holdings
export EMAIL=admin@steampunk.holdings
export INITIAL_BTC_PRICE=84000
export ENABLE_SSL=true

# Run the deployment script
./deploy-steampunk.sh
```

The script will:
1. Create a production .env file
2. Build and push Docker images to ECR
3. Deploy the CloudFormation stack with EC2, RDS, etc.
4. Configure the EC2 instance with the deployed images
5. Set up SSL certificates with Let's Encrypt

### 4. Post-Deployment Steps

1. **Configure DNS Settings**: 
   - Go to your domain registrar
   - Point your domain (steampunk.holdings) to the EC2 public DNS
   - Wait for DNS propagation (up to 24 hours)

2. **Access the Dashboard**:
   - Once DNS is propagated, access at `https://steampunk.holdings`
   - API key is displayed during deployment for secure access

## Architecture Details

### Trading Bot Container

- Runs the trading system with real-world BTC prices
- Connects to four major exchange APIs:
  - Coinbase
  - Kucoin
  - Kraken
  - Gemini
- Features robust multi-exchange capabilities:
  - Uses weighted average across all exchanges for accurate pricing
  - Continues functioning even if some exchanges are unavailable
  - Detects price divergence between exchanges for arbitrage opportunities
- Uses alternative data sources instead of expensive APIs
- Performs paper trading with configurable parameters

### Dashboard Container

- Runs a Flask web server with our custom dashboard
- Provides real-time monitoring of trading activities
- Shows portfolio performance, trades, and analytics
- Allows control of trading strategies through the web interface

### Nginx Container

- Acts as a reverse proxy for the dashboard
- Handles SSL termination
- Serves static files
- Manages domain hosting

### Database

- PostgreSQL RDS instance
- Stores trading data, bot states, and historical information
- Enables persistence across system restarts

## Maintenance and Updates

### Updating the Bot

To update the trading bot or dashboard:

1. Make changes to the codebase
2. Run the deployment script again:
   ```bash
   ./deploy-steampunk.sh
   ```

The script will rebuild images, push them to ECR, and update the running containers.

### Monitoring

- Access Prometheus at `https://steampunk.holdings:9090`
- Access Grafana at `https://steampunk.holdings:3000`
- Check CloudWatch logs for operational metrics

### SSH Access

If you need to SSH into the EC2 instance:

```bash
ssh -i your-key-pair.pem ubuntu@ec2-public-dns
```

## Configuration Options

### Exchange Settings

Configure multiple exchange APIs and their weights:

```
# API Keys
COINBASE_API_KEY=your_coinbase_api_key  
COINBASE_API_SECRET=your_coinbase_api_secret
KUCOIN_API_KEY=your_kucoin_api_key
KUCOIN_API_SECRET=your_kucoin_api_secret
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret
GEMINI_API_KEY=your_gemini_api_key
GEMINI_API_SECRET=your_gemini_api_secret

# Exchange configuration
TRADING_EXCHANGE=multi
EXCHANGE_DATA_PROVIDER=coinbase,kucoin,kraken,gemini
USE_MULTI_EXCHANGE=true
```

### Risk Parameters

Customize risk parameters in the `.env` file:

```
# Risk parameters
LOW_RISK_STOP_LOSS=0.02
MEDIUM_RISK_STOP_LOSS=0.03  
HIGH_RISK_STOP_LOSS=0.05

# Leverage
LOW_RISK_LEVERAGE=1.0
MEDIUM_RISK_LEVERAGE=2.0
HIGH_RISK_LEVERAGE=5.0
```

### Portfolio Configuration

Adjust portfolio settings:

```
# Portfolio configuration
PROFIT_THRESHOLD=50000
PROFIT_WITHDRAWAL_PERCENTAGE=0.5
MAX_PORTFOLIO_DRAWDOWN=0.15
MAX_CORRELATION=0.7
MAX_ALLOCATION_PER_ASSET=0.25
RISK_FREE_RATE=0.02
```

## API Controls

Configure trading strategies via the API:

```bash
# Example API call to update trading thresholds
curl -X POST https://steampunk.holdings/api/configure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "thresholds": {
      "high_risk_buy": 0.6,
      "high_risk_sell": 0.4,
      "medium_risk_rsi_buy": 35,
      "medium_risk_rsi_sell": 65
    },
    "position_sizes": {
      "high_risk": 0.15,
      "medium_risk": 0.08,
      "low_risk": 0.03
    }
  }'
```

## Troubleshooting

### SSL Certificate Issues

If SSL certificate setup fails:

1. SSH into the EC2 instance
2. Run: 
   ```bash
   cd /app
   docker-compose -f docker-compose.aws.yml run --rm certbot certonly --webroot -w /var/www/certbot -d steampunk.holdings -d www.steampunk.holdings --email admin@steampunk.holdings --agree-tos --no-eff-email
   docker-compose -f docker-compose.aws.yml restart nginx
   ```

### Docker Container Issues

To check container status:

```bash
ssh -i your-key-pair.pem ubuntu@ec2-public-dns
cd /app
docker-compose -f docker-compose.aws.yml ps
docker-compose -f docker-compose.aws.yml logs
```

To restart containers:

```bash
docker-compose -f docker-compose.aws.yml restart
```

### Database Connection Issues

If database connection fails:

1. Check security group settings
2. Verify database credentials in the .env file
3. Ensure the RDS instance is running

## Security Considerations

- API key is used to protect configuration endpoints
- SSL certificates secure traffic to the dashboard
- EC2 security groups restrict access to necessary ports
- Database access is limited to the EC2 instance

## Support and Resources

For additional support:
- Check CloudWatch logs for detailed diagnostics
- Review the AWS CloudFormation stack for resource details
- Refer to the project's documentation at STEP_BY_STEP_GUIDE.md
