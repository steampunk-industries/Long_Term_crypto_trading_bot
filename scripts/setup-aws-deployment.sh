#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Crypto Trading Bot AWS Deployment Setup ===${NC}"
echo -e "${YELLOW}This script will help you set up the AWS environment for deploying the crypto trading bot.${NC}"
echo -e "${YELLOW}Make sure you have the AWS CLI installed and configured with appropriate credentials.${NC}"
echo

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    echo -e "${YELLOW}Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html${NC}"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}AWS CLI is not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}AWS CLI is installed and configured.${NC}"
echo

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Get AWS region
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
    echo -e "${YELLOW}AWS region not found in config. Using default: ${AWS_REGION}${NC}"
else
    echo -e "${BLUE}AWS Region: ${AWS_REGION}${NC}"
fi

echo
echo -e "${BLUE}=== Step 1: Create ECR Repository ===${NC}"
echo -e "${YELLOW}Creating ECR repository for the crypto trading bot...${NC}"

# Create ECR repository
ECR_REPO_NAME="crypto-trading-bot"
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}

ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
echo -e "${GREEN}ECR repository created: ${ECR_REPO_URI}${NC}"

echo
echo -e "${BLUE}=== Step 2: Create S3 Bucket for CloudFormation Template ===${NC}"
echo -e "${YELLOW}Creating S3 bucket for CloudFormation template...${NC}"

# Create S3 bucket for CloudFormation template
S3_BUCKET_NAME="crypto-trading-bot-${AWS_ACCOUNT_ID}-${AWS_REGION}"
aws s3api head-bucket --bucket ${S3_BUCKET_NAME} 2>/dev/null || \
    aws s3 mb s3://${S3_BUCKET_NAME} --region ${AWS_REGION}

echo -e "${GREEN}S3 bucket created: ${S3_BUCKET_NAME}${NC}"

echo
echo -e "${BLUE}=== Step 3: Upload CloudFormation Template ===${NC}"
echo -e "${YELLOW}Uploading CloudFormation template to S3...${NC}"

# Upload CloudFormation template to S3
aws s3 cp aws-cloudformation.yml s3://${S3_BUCKET_NAME}/aws-cloudformation.yml

echo -e "${GREEN}CloudFormation template uploaded to S3.${NC}"

echo
echo -e "${BLUE}=== Step 4: Create .env File for AWS Deployment ===${NC}"
echo -e "${YELLOW}Creating .env file for AWS deployment...${NC}"

# Create .env file for AWS deployment
cat > .env.aws << EOL
# Exchange API Keys (Replace with your own keys)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Database Configuration
DB_HOST=\${DBInstance.Endpoint.Address}
DB_PORT=5432
DB_NAME=crypto_bot
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
MEDIUM_RISK_LEVERAGE=2
HIGH_RISK_LEVERAGE=5

# Exchange Fees
TAKER_FEE=0.0004
MAKER_FEE=0.0002

# Logging
LOG_LEVEL=INFO
LOG_TO_CLOUDWATCH=true

# AWS Configuration
AWS_REGION=${AWS_REGION}

# Web Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password

# TensorFlow Configuration
TF_ENABLE_GPU=true
TF_GPU_MEMORY_LIMIT=4096
EOL

echo -e "${GREEN}.env.aws file created.${NC}"
echo -e "${YELLOW}Please edit .env.aws to add your API keys and other configuration.${NC}"

echo
echo -e "${BLUE}=== Step 5: Create Key Pair ===${NC}"
echo -e "${YELLOW}Do you want to create a new EC2 key pair? (y/n)${NC}"
read -p "Create key pair? " CREATE_KEY_PAIR

if [[ "$CREATE_KEY_PAIR" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Enter a name for the key pair:${NC}"
    read -p "Key pair name: " KEY_PAIR_NAME
    
    # Create key pair
    aws ec2 create-key-pair --key-name ${KEY_PAIR_NAME} --query 'KeyMaterial' --output text > ${KEY_PAIR_NAME}.pem
    chmod 400 ${KEY_PAIR_NAME}.pem
    
    echo -e "${GREEN}Key pair created: ${KEY_PAIR_NAME}.pem${NC}"
    echo -e "${YELLOW}Keep this file safe, as it's required to SSH into the EC2 instance.${NC}"
else
    echo -e "${YELLOW}Please enter the name of an existing key pair:${NC}"
    read -p "Key pair name: " KEY_PAIR_NAME
    
    # Check if key pair exists
    aws ec2 describe-key-pairs --key-names ${KEY_PAIR_NAME} > /dev/null 2>&1 || \
        (echo -e "${RED}Key pair ${KEY_PAIR_NAME} does not exist.${NC}" && exit 1)
    
    echo -e "${GREEN}Using existing key pair: ${KEY_PAIR_NAME}${NC}"
fi

echo
echo -e "${BLUE}=== Step 6: Get VPC and Subnet IDs ===${NC}"
echo -e "${YELLOW}Fetching VPC and subnet information...${NC}"

# Get default VPC ID
DEFAULT_VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
if [ "$DEFAULT_VPC_ID" == "None" ]; then
    echo -e "${RED}No default VPC found.${NC}"
    echo -e "${YELLOW}Please enter a VPC ID:${NC}"
    read -p "VPC ID: " VPC_ID
else
    echo -e "${GREEN}Default VPC found: ${DEFAULT_VPC_ID}${NC}"
    VPC_ID=$DEFAULT_VPC_ID
fi

# Get subnet IDs in the VPC
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query "Subnets[*].SubnetId" --output text)
if [ -z "$SUBNET_IDS" ]; then
    echo -e "${RED}No subnets found in VPC ${VPC_ID}.${NC}"
    exit 1
fi

# Print subnet IDs
echo -e "${GREEN}Subnets in VPC ${VPC_ID}:${NC}"
SUBNET_ARRAY=($SUBNET_IDS)
for i in "${!SUBNET_ARRAY[@]}"; do
    echo -e "${BLUE}$((i+1)). ${SUBNET_ARRAY[$i]}${NC}"
done

# Ask user to select a subnet
echo -e "${YELLOW}Select a subnet by entering its number:${NC}"
read -p "Subnet number: " SUBNET_NUMBER

if ! [[ "$SUBNET_NUMBER" =~ ^[0-9]+$ ]] || [ "$SUBNET_NUMBER" -lt 1 ] || [ "$SUBNET_NUMBER" -gt ${#SUBNET_ARRAY[@]} ]; then
    echo -e "${RED}Invalid subnet number.${NC}"
    exit 1
fi

SUBNET_ID=${SUBNET_ARRAY[$((SUBNET_NUMBER-1))]}
echo -e "${GREEN}Selected subnet: ${SUBNET_ID}${NC}"

echo
echo -e "${BLUE}=== Step 7: Create Deployment Script ===${NC}"
echo -e "${YELLOW}Creating deployment script...${NC}"

# Create deployment script
cat > deploy-to-aws-cloudformation.sh << EOL
#!/bin/bash
set -e

# Configuration
AWS_REGION=${AWS_REGION}
STACK_NAME=crypto-trading-bot
S3_BUCKET=${S3_BUCKET_NAME}
KEY_PAIR_NAME=${KEY_PAIR_NAME}
VPC_ID=${VPC_ID}
SUBNET_ID=${SUBNET_ID}
ECR_REPO_URI=${ECR_REPO_URI}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "\${GREEN}Starting deployment to AWS...\${NC}"

# Step 1: Build and push Docker image
echo -e "\${YELLOW}Step 1: Building and pushing Docker image...\${NC}"

# Get ECR login token
aws ecr get-login-password --region \${AWS_REGION} | docker login --username AWS --password-stdin \${ECR_REPO_URI}

# Build Docker image
docker build -t crypto-trading-bot:latest .

# Tag and push image
docker tag crypto-trading-bot:latest \${ECR_REPO_URI}:latest
docker push \${ECR_REPO_URI}:latest

echo -e "\${GREEN}Docker image pushed to ECR: \${ECR_REPO_URI}:latest\${NC}"

# Step 2: Deploy CloudFormation stack
echo -e "\${YELLOW}Step 2: Deploying CloudFormation stack...\${NC}"

# Get database password
echo -e "\${YELLOW}Enter a password for the database:${NC}"
read -s -p "Database password: " DB_PASSWORD
echo

# Deploy CloudFormation stack
aws cloudformation deploy \\
    --template-url https://\${S3_BUCKET}.s3.\${AWS_REGION}.amazonaws.com/aws-cloudformation.yml \\
    --stack-name \${STACK_NAME} \\
    --parameter-overrides \\
        EnvironmentName=prod \\
        KeyName=\${KEY_PAIR_NAME} \\
        VpcId=\${VPC_ID} \\
        SubnetId=\${SUBNET_ID} \\
        DBPassword=\${DB_PASSWORD} \\
        DockerImageRepo=\${ECR_REPO_URI} \\
    --capabilities CAPABILITY_IAM \\
    --region \${AWS_REGION}

# Step 3: Get outputs from CloudFormation stack
echo -e "\${YELLOW}Step 3: Getting deployment information...\${NC}"

EC2_PUBLIC_DNS=\$(aws cloudformation describe-stacks --stack-name \${STACK_NAME} --region \${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==\`EC2PublicDNS\`].OutputValue' --output text)
DASHBOARD_URL=\$(aws cloudformation describe-stacks --stack-name \${STACK_NAME} --region \${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==\`DashboardURL\`].OutputValue' --output text)
GRAFANA_URL=\$(aws cloudformation describe-stacks --stack-name \${STACK_NAME} --region \${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==\`GrafanaURL\`].OutputValue' --output text)
PROMETHEUS_URL=\$(aws cloudformation describe-stacks --stack-name \${STACK_NAME} --region \${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==\`PrometheusURL\`].OutputValue' --output text)
RDS_ENDPOINT=\$(aws cloudformation describe-stacks --stack-name \${STACK_NAME} --region \${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==\`RDSEndpoint\`].OutputValue' --output text)

# Step 4: Print deployment information
echo -e "\${GREEN}Deployment completed successfully!\${NC}"
echo -e "\${YELLOW}Deployment Information:\${NC}"
echo -e "EC2 Public DNS: \${GREEN}\${EC2_PUBLIC_DNS}\${NC}"
echo -e "Dashboard URL: \${GREEN}\${DASHBOARD_URL}\${NC}"
echo -e "Grafana URL: \${GREEN}\${GRAFANA_URL}\${NC}"
echo -e "Prometheus URL: \${GREEN}\${PROMETHEUS_URL}\${NC}"
echo -e "RDS Endpoint: \${GREEN}\${RDS_ENDPOINT}\${NC}"

echo -e "\${YELLOW}Note: It may take a few minutes for the EC2 instance to initialize and start the application.\${NC}"
echo -e "\${YELLOW}You can SSH into the EC2 instance using: ssh -i \${KEY_PAIR_NAME}.pem ubuntu@\${EC2_PUBLIC_DNS}\${NC}"

echo -e "\${GREEN}Deployment completed!\${NC}"
EOL

chmod +x deploy-to-aws-cloudformation.sh

echo -e "${GREEN}Deployment script created: deploy-to-aws-cloudformation.sh${NC}"

echo
echo -e "${BLUE}=== Setup Complete ===${NC}"
echo -e "${GREEN}AWS deployment setup is complete.${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Edit .env.aws to add your API keys and other configuration."
echo -e "2. Run ./deploy-to-aws-cloudformation.sh to deploy the application to AWS."
echo
echo -e "${BLUE}Happy trading!${NC}"
