# Step-by-Step Guide for Crypto Trading Bot Setup and AWS Deployment

This guide provides detailed instructions for setting up the crypto trading bot with exchange-based quantitative data, running it locally, and deploying it to AWS.

## Table of Contents
1. [Overview of Data Sources](#overview-of-data-sources)
2. [Setting Up Required APIs](#setting-up-required-apis)
3. [Local Environment Setup](#local-environment-setup)
4. [AWS Deployment](#aws-deployment)
5. [Git Repository Setup](#git-repository-setup)

## Overview of Data Sources

The crypto trading bot can be configured to use two different types of data sources:

### Exchange-Based Quantitative Data (Recommended)
The bot uses data directly from cryptocurrency exchanges to simulate:
- On-chain metrics (exchange inflows/outflows, miner behavior)
- Market sentiment (through volume analysis and technical indicators)
- Fear & Greed index (through a free public API)

Benefits:
- No expensive API subscriptions required
- Works without access to social media APIs
- Provides comparable signals to premium services
- Self-contained within the trading system

### Premium External APIs (Optional)
For enterprise users who already have subscriptions:
- Glassnode for on-chain metrics ($20k+/year)
- Twitter/X API for social sentiment
- Reddit API for community sentiment
- News API for media sentiment

## Setting Up Required APIs

### 1. Binance API Setup (Required)
1. Go to [Binance](https://www.binance.com/) and create an account if you don't have one
2. Navigate to API Management (under your profile)
3. Click "Create API"
4. Set a label for your API (e.g., "Crypto Trading Bot")
5. Enable the following permissions:
   - Read Info
   - Enable Trading
   - Enable Spot & Margin Trading
6. Set IP restrictions to your server's IP address (or leave unrestricted for testing)
7. Complete security verification
8. Save your API Key and Secret Key in a secure location

### 2. Fear & Greed Index API (Free)
This API is publicly available and doesn't require authentication:
- URL: https://api.alternative.me/fng/
- The bot automatically accesses this API for sentiment data

### 3. External APIs (Optional)
If you have access to premium services, you can configure them as well:

#### Twitter/X API (Optional)
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a developer account
3. Create a new project and app
4. Navigate to the "Keys and Tokens" tab
5. Generate API Key, API Secret, and Bearer Token

#### Reddit API (Optional)
1. Go to [Reddit Developer Portal](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Fill in the required information and create the app
4. Save the Client ID and Client Secret

#### News API (Optional)
1. Go to [News API](https://newsapi.org/)
2. Sign up for an account
3. Obtain your API key from the dashboard

#### Glassnode API (Optional)
1. Go to [Glassnode](https://glassnode.com/)
2. Create an account (enterprise tier)
3. Navigate to API settings
4. Generate an API key

## Local Environment Setup

### 1. Install Required Software
```bash
# Install Python 3.9+ (if not already installed)
# For macOS:
brew install python@3.9

# For Ubuntu:
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev

# Install Docker and Docker Compose
# For macOS:
brew install docker docker-compose

# For Ubuntu:
sudo apt install docker.io docker-compose

# Install AWS CLI
# For macOS:
brew install awscli

# For Ubuntu:
sudo apt install awscli

# Install Git
# For macOS:
brew install git

# For Ubuntu:
sudo apt install git
```

### 2. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your configuration
nano .env
```

Add the following to your .env file:
```
# Exchange API Keys (Required)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Alternative Data Configuration (Recommended)
USE_ALTERNATIVE_DATA=true
EXCHANGE_DATA_PROVIDER=binance
SENTIMENT_ALTERNATIVE=technical,volume,fear_greed

# Premium API Keys (Optional - leave blank if not using)
GLASSNODE_API_KEY=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
NEWS_API_KEY=

# Database Configuration
USE_SQLITE=true  # Set to true for easier local development
DB_NAME=crypto_bot
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Trading Configuration
TRADING_SYMBOL=BTC/USDT
INITIAL_CAPITAL=10000
PAPER_TRADING=true

# Risk Parameters
LOW_RISK_STOP_LOSS=0.02
MEDIUM_RISK_STOP_LOSS=0.03
HIGH_RISK_STOP_LOSS=0.05

# Leverage
LOW_RISK_LEVERAGE=1.0
MEDIUM_RISK_LEVERAGE=2.0
HIGH_RISK_LEVERAGE=5.0

# TensorFlow Configuration
TF_ENABLE_GPU=false
TF_GPU_MEMORY_LIMIT=4096

# Exchange Fees
TAKER_FEE=0.0004
MAKER_FEE=0.0002

# Dashboard Configuration
DASHBOARD_HOST=localhost
DASHBOARD_PORT=5000
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin
```

### 3. Set Up Python Environment
```bash
# Create a virtual environment
python -m venv myenv

# Activate the virtual environment
# For macOS/Linux:
source myenv/bin/activate
# For Windows:
# myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Test the Paper Trading System
Before running, initialize the database:
```bash
# Initialize the database
python -c "from src.utils.database import init_db; init_db()"

# Create required directories
mkdir -p data logs models/scalping
```

Run the paper trading script:
```bash
# Test paper trading with all strategies
python paper_trading.py --all

# Or test individual strategies
python paper_trading.py --high-risk  # Uses the most advanced quantitative analysis

# For more options
python paper_trading.py --help
```

You can also run the main system directly:
```bash
# Run the main system with all strategies
python src/main.py --all

# Monitor the logs
tail -f logs/crypto_bot.log
```

### 5. Access the Web Dashboard
Once the system is running, access the dashboard at:
```
http://localhost:5000
```
Login with the credentials specified in your .env file (default: admin/admin).

## AWS Deployment

### 1. Configure AWS CLI
```bash
# Configure AWS CLI with your credentials
aws configure
```
Enter your AWS Access Key ID, Secret Access Key, default region (e.g., us-east-1), and output format (json).

### 2. Run the AWS Setup Script
```bash
# Make the script executable
chmod +x setup-aws-deployment.sh

# Run the setup script
./setup-aws-deployment.sh
```

Follow the prompts in the script:
1. The script will create an ECR repository for your Docker image
2. It will create an S3 bucket for CloudFormation templates
3. It will upload the CloudFormation template to S3
4. It will create a .env.aws file for AWS deployment
5. It will prompt you to create or select an EC2 key pair
6. It will help you select a VPC and subnet for deployment
7. It will create a deployment script

### 3. Edit AWS Environment Variables
```bash
# Edit the AWS environment file
nano .env.aws
```

Update the file with your API keys and other settings.

### 4. Deploy to AWS
```bash
# Make the deployment script executable
chmod +x deploy-to-aws-cloudformation.sh

# Run the deployment script
./deploy-to-aws-cloudformation.sh
```

The script will:
1. Build and push your Docker image to ECR
2. Deploy the CloudFormation stack
3. Set up EC2, RDS, and other AWS resources
4. Configure networking and security
5. Provide you with URLs for your deployed application

### 5. Configure Route53 for steampunk.holdings

1. Log in to the AWS Management Console
2. Navigate to Route53
3. Select your hosted zone for steampunk.holdings
4. Create a new record set:
   - Name: Choose a subdomain (e.g., trading.steampunk.holdings)
   - Type: A - IPv4 address
   - Value: The public IP of your EC2 instance (provided by the deployment script)
   - TTL: 300
   - Routing Policy: Simple
5. Click "Create"

### 6. Access Your Deployed Application

After deployment and DNS configuration, you can access your application at:
- Dashboard: https://trading.steampunk.holdings
- Grafana: https://grafana.trading.steampunk.holdings
- Prometheus: https://prometheus.trading.steampunk.holdings

## Git Repository Setup

### 1. Initialize Git Repository
```bash
# Initialize a new Git repository
git init

# Add all files to the repository
git add .

# Create .gitignore file
cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
myenv/
venv/
ENV/

# Environment Variables
.env
.env.*
!.env.example

# Logs
logs/
*.log

# Database
*.db
*.sqlite3

# AWS
.aws/
*.pem

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
EOL

# Commit the changes
git commit -m "Initial commit"
```

### 2. Create GitHub Repository

1. Go to [GitHub](https://github.com/)
2. Click "New repository"
3. Name your repository (e.g., "crypto-trading-bot")
4. Choose visibility (public or private)
5. Do not initialize with README, .gitignore, or license
6. Click "Create repository"

### 3. Push to GitHub
```bash
# Add the remote repository
git remote add origin https://github.com/yourusername/crypto-trading-bot.git

# Push to GitHub
git push -u origin master
```

### 4. Set Up GitHub Actions for CI/CD (Optional)

Create a GitHub Actions workflow file:

```bash
mkdir -p .github/workflows
cat > .github/workflows/deploy.yml << EOL
name: Deploy to AWS

on:
  push:
    branches: [ master ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: \${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: \${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: \${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: crypto-trading-bot
        IMAGE_TAG: latest
      run: |
        docker build -t \$ECR_REGISTRY/\$ECR_REPOSITORY:\$IMAGE_TAG .
        docker push \$ECR_REGISTRY/\$ECR_REPOSITORY:\$IMAGE_TAG
    
    - name: Deploy to AWS CloudFormation
      run: |
        aws cloudformation deploy \\
          --template-file aws-cloudformation.yml \\
          --stack-name crypto-trading-bot \\
          --parameter-overrides \\
              EnvironmentName=prod \\
              KeyName=\${{ secrets.EC2_KEY_NAME }} \\
              VpcId=\${{ secrets.VPC_ID }} \\
              SubnetId=\${{ secrets.SUBNET_ID }} \\
              DBPassword=\${{ secrets.DB_PASSWORD }} \\
              DockerImageRepo=\$ECR_REGISTRY/\$ECR_REPOSITORY \\
          --capabilities CAPABILITY_IAM
EOL

# Add and commit the workflow file
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions workflow"
git push
```

5. Add GitHub Secrets

In your GitHub repository:
1. Go to Settings > Secrets
2. Add the following secrets:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - EC2_KEY_NAME
   - VPC_ID
   - SUBNET_ID
   - DB_PASSWORD

## Understanding the Quantitative Data Approach

This bot implements several innovative approaches to replace expensive API services:

### Exchange-Based On-Chain Data Simulation

The `ExchangeDataProvider` in `src/utils/on_chain_data.py` simulates on-chain metrics using exchange data:

1. **Exchange Inflow/Outflow**: Calculated using volume and price action patterns
   - Rising price + rising volume = outflow from exchanges (bullish)
   - Falling price + rising volume = inflow to exchanges (bearish)

2. **Miner Behavior**: Estimated based on price levels and historical patterns
   - Uses price action as a proxy for miner selling behavior

3. **SOPR (Spent Output Profit Ratio)**: Simulated using price changes across multiple timeframes
   - Approximates whether wallets are selling at profit or loss

### Alternative Sentiment Analysis

Multiple data sources replace expensive social media APIs:

1. **Fear & Greed Index**: Free API providing market sentiment measurement
   - Values from 0-100 (extreme fear to extreme greed)
   - Applied with contrarian interpretation

2. **Volume Sentiment**: Analyzes trading volume patterns
   - Volume spikes with price movement indicate strong sentiment
   - Volume/price correlation reveals market conviction

3. **Technical Indicator Sentiment**: Uses indicators to approximate market sentiment
   - RSI: Overbought/oversold conditions
   - MACD: Trend strength and direction
   - Bollinger Bands: Volatility-based sentiment

### Benefits of This Approach

1. **Cost-Efficient**: No expensive subscriptions required
2. **Self-Contained**: All analysis happens within the system
3. **Backward-Compatible**: Works with the original strategy code
4. **Graceful Degradation**: Falls back to technical analysis if needed

## Conclusion

You have now:
1. Set up a cost-effective crypto trading bot using quantitative data
2. Configured the local environment for testing with alternative data sources
3. Prepared for AWS deployment
4. Created a Git repository for version control

The bot is now running in paper trading mode, using exchange-based quantitative data instead of expensive external APIs, while maintaining comparable trading signals and performance.
