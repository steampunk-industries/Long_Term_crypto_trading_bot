#!/bin/bash
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
STACK_NAME=${STACK_NAME:-"crypto-trading-bot"}
ENV_NAME=${ENV_NAME:-"prod"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"crypto-trading-bot"}
EC2_KEY_NAME=${EC2_KEY_NAME:-""}
VPC_ID=${VPC_ID:-""}
SUBNET_ID=${SUBNET_ID:-""}
DB_PASSWORD=${DB_PASSWORD:-""}
DOMAIN_NAME=${DOMAIN_NAME:-"steampunk.holdings"}
EMAIL=${EMAIL:-"admin@steampunk.holdings"}
ENABLE_SSL=${ENABLE_SSL:-"true"}
API_KEY=${API_KEY:-$(openssl rand -hex 16)}
INITIAL_BTC_PRICE=${INITIAL_BTC_PRICE:-84000}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check required parameters
if [ -z "$EC2_KEY_NAME" ]; then
    echo -e "${RED}EC2_KEY_NAME is required. Please set it before running this script.${NC}"
    echo "Example: EC2_KEY_NAME=my-key-pair ./deploy-steampunk.sh"
    exit 1
fi

if [ -z "$VPC_ID" ]; then
    echo -e "${RED}VPC_ID is required. Please set it before running this script.${NC}"
    echo "Example: VPC_ID=vpc-12345678 ./deploy-steampunk.sh"
    exit 1
fi

if [ -z "$SUBNET_ID" ]; then
    echo -e "${RED}SUBNET_ID is required. Please set it before running this script.${NC}"
    echo "Example: SUBNET_ID=subnet-12345678 ./deploy-steampunk.sh"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}DB_PASSWORD is required. Please set it before running this script.${NC}"
    echo "Example: DB_PASSWORD=your-secure-password ./deploy-steampunk.sh"
    exit 1
fi

echo -e "${GREEN}Starting deployment to AWS with steampunk.holdings configuration...${NC}"

# Create .env file for production
echo -e "${YELLOW}Creating production .env file...${NC}"
cat > .env << EOL
# Environment configuration for production with alternative data sources

# Trading configuration
PAPER_TRADING=true
TRADING_EXCHANGE=multi
TRADING_SYMBOL=BTC/USDT
INITIAL_CAPITAL=10000
INITIAL_BTC_PRICE=${INITIAL_BTC_PRICE}
REAL_WORLD_PRICES=true
USE_MULTI_EXCHANGE=true

# Risk parameters
LOW_RISK_STOP_LOSS=0.02
MEDIUM_RISK_STOP_LOSS=0.03  
HIGH_RISK_STOP_LOSS=0.05

# Leverage
LOW_RISK_LEVERAGE=1.0
MEDIUM_RISK_LEVERAGE=2.0
HIGH_RISK_LEVERAGE=5.0

# API Keys (placeholders for paper trading)
COINBASE_API_KEY=DJB8sxkL7pM5Nw9qTcH2VgXyR6FjKaYzZb4EUnP7L8hQkWmtS3xvCp6rBGdA
COINBASE_API_SECRET=8vLpDzKrNj2BtCX4WY7HgM9TqmEaFfP5dZyJcAVxGs6RkQSbEn3Px88DuD6Kcahm
KUCOIN_API_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890abc
KUCOIN_API_SECRET=abcdefg1234567hijklmno8901234pqrstuvwxyz56789012345abcdef
KRAKEN_API_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHI
KRAKEN_API_SECRET=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ
GEMINI_API_KEY=account-abcdefghijklmnopqrstuvwx
GEMINI_API_SECRET=abcdefghijklmnopqrstuvwxyz1234567890ABCDEFG

# API Key for dashboard configuration
API_KEY=${API_KEY}

# Alternative data source configuration
USE_ALTERNATIVE_DATA=true
EXCHANGE_DATA_PROVIDER=coinbase,kucoin,kraken,gemini
SENTIMENT_ALTERNATIVE=technical,volume,fear_greed

# Database configuration
DB_HOST=\${DB_HOST}
DB_PORT=5432
DB_NAME=crypto_bot
DB_USER=postgres
DB_PASSWORD=\${DB_PASSWORD}

# Dashboard configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5003
DOMAIN_NAME=${DOMAIN_NAME}
ENABLE_SSL=${ENABLE_SSL}
SECRET_KEY=$(openssl rand -hex 24)

# AWS settings
AWS_REGION=${AWS_REGION}

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=logs/crypto_bot.log

# Portfolio configuration
PROFIT_THRESHOLD=50000
PROFIT_WITHDRAWAL_PERCENTAGE=0.5
MAX_PORTFOLIO_DRAWDOWN=0.15
MAX_CORRELATION=0.7
MAX_ALLOCATION_PER_ASSET=0.25
RISK_FREE_RATE=0.02
EOL

echo -e "${GREEN}.env file created for production${NC}"

# Step 1: Create ECR repository if it doesn't exist
echo -e "${YELLOW}Step 1: Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}

# Get ECR repository URI
ECR_REPO_URI=$(aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} --query 'repositories[0].repositoryUri' --output text)
echo -e "${GREEN}ECR repository URI: ${ECR_REPO_URI}${NC}"

# Step 2: Build and push Docker images
echo -e "${YELLOW}Step 2: Building and pushing Docker images...${NC}"
# Get ECR login token
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URI}

# Build and push main image
echo -e "${YELLOW}Building and pushing main image...${NC}"
docker build -t ${ECR_REPO_NAME}:latest .
docker tag ${ECR_REPO_NAME}:latest ${ECR_REPO_URI}:latest
docker push ${ECR_REPO_URI}:latest

# Build and push dashboard image
echo -e "${YELLOW}Building and pushing dashboard image...${NC}"
docker build -t ${ECR_REPO_NAME}-dashboard:latest -f Dockerfile.dashboard .
docker tag ${ECR_REPO_NAME}-dashboard:latest ${ECR_REPO_URI}:dashboard
docker push ${ECR_REPO_URI}:dashboard

echo -e "${GREEN}Docker images pushed to ECR${NC}"

# Step 3: Deploy CloudFormation stack
echo -e "${YELLOW}Step 3: Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file aws-cloudformation.yml \
    --stack-name ${STACK_NAME} \
    --parameter-overrides \
        EnvironmentName=${ENV_NAME} \
        KeyName=${EC2_KEY_NAME} \
        VpcId=${VPC_ID} \
        SubnetId=${SUBNET_ID} \
        DBPassword=${DB_PASSWORD} \
        DockerImageRepo=${ECR_REPO_URI} \
        DomainName=${DOMAIN_NAME} \
        EnableSSL=${ENABLE_SSL} \
        InitialBTCPrice=${INITIAL_BTC_PRICE} \
        ApiKey=${API_KEY} \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}

# Step 4: Get outputs from CloudFormation stack
echo -e "${YELLOW}Step 4: Getting deployment information...${NC}"
EC2_PUBLIC_DNS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`EC2PublicDNS`].OutputValue' --output text)
DASHBOARD_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' --output text)
RDS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' --output text)

# Step 5: Upload production configuration to EC2 instance
echo -e "${YELLOW}Step 5: Uploading production configuration to EC2 instance...${NC}"
# Wait for EC2 instance to be ready
echo -e "${YELLOW}Waiting for EC2 instance to be initialized...${NC}"
sleep 60

# Transfer files to EC2 instance using SSM
echo -e "${YELLOW}Transferring configuration files to EC2 instance...${NC}"
aws ec2 describe-instances --filters "Name=tag:Name,Values=${ENV_NAME}-crypto-bot-ec2" --query "Reservations[].Instances[].InstanceId" --output text | xargs -I {} aws ssm send-command \
    --instance-ids {} \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[
        'mkdir -p /app',
        'cd /app',
        'aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URI}',
        'echo \"DB_HOST=${RDS_ENDPOINT}\" >> .env',
        'echo \"DB_PASSWORD=${DB_PASSWORD}\" >> .env',
        'echo \"DOMAIN_NAME=${DOMAIN_NAME}\" >> .env',
        'echo \"ENABLE_SSL=${ENABLE_SSL}\" >> .env',
        'echo \"API_KEY=${API_KEY}\" >> .env',
        'echo \"INITIAL_BTC_PRICE=${INITIAL_BTC_PRICE}\" >> .env',
        'docker-compose -f docker-compose.aws.yml pull',
        'docker-compose -f docker-compose.aws.yml up -d'
    ]" \
    --region ${AWS_REGION}

# Step 6: Set up SSL certificate with Let's Encrypt (if enabled)
if [ "${ENABLE_SSL}" = "true" ]; then
    echo -e "${YELLOW}Step 6: Setting up SSL certificate with Let's Encrypt...${NC}"
    aws ec2 describe-instances --filters "Name=tag:Name,Values=${ENV_NAME}-crypto-bot-ec2" --query "Reservations[].Instances[].InstanceId" --output text | xargs -I {} aws ssm send-command \
        --instance-ids {} \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[
            'cd /app',
            'docker-compose -f docker-compose.aws.yml run --rm certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN_NAME} -d www.${DOMAIN_NAME} --email ${EMAIL} --agree-tos --no-eff-email',
            'docker-compose -f docker-compose.aws.yml restart nginx'
        ]" \
        --region ${AWS_REGION}
fi

# Step 7: Print deployment information
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Deployment Information:${NC}"
echo -e "EC2 Public DNS: ${GREEN}${EC2_PUBLIC_DNS}${NC}"
echo -e "Dashboard URL: ${GREEN}https://${DOMAIN_NAME}${NC}"
echo -e "Dashboard API Key: ${GREEN}${API_KEY}${NC}"
echo -e "RDS Endpoint: ${GREEN}${RDS_ENDPOINT}${NC}"

echo -e "${YELLOW}Note: It may take a few minutes for the EC2 instance to initialize and start the application.${NC}"
echo -e "${YELLOW}You can SSH into the EC2 instance using: ssh -i ${EC2_KEY_NAME}.pem ubuntu@${EC2_PUBLIC_DNS}${NC}"

echo -e "${YELLOW}Important Next Steps:${NC}"
echo -e "1. Go to your domain registrar and point ${DOMAIN_NAME} to ${EC2_PUBLIC_DNS}"
echo -e "2. Wait for DNS propagation (may take up to 24 hours)"
echo -e "3. Access your dashboard at https://${DOMAIN_NAME}"

echo -e "${GREEN}Deployment completed!${NC}"
