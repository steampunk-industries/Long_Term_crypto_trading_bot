#!/bin/bash
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
STACK_NAME=${STACK_NAME:-"crypto-trading-bot"}
ENV_NAME=${ENV_NAME:-"dev"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"crypto-trading-bot"}
EC2_KEY_NAME=${EC2_KEY_NAME:-""}
VPC_ID=${VPC_ID:-""}
SUBNET_ID=${SUBNET_ID:-""}
DB_PASSWORD=${DB_PASSWORD:-""}

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
    echo "Example: EC2_KEY_NAME=my-key-pair ./deploy-to-aws.sh"
    exit 1
fi

if [ -z "$VPC_ID" ]; then
    echo -e "${RED}VPC_ID is required. Please set it before running this script.${NC}"
    echo "Example: VPC_ID=vpc-12345678 ./deploy-to-aws.sh"
    exit 1
fi

if [ -z "$SUBNET_ID" ]; then
    echo -e "${RED}SUBNET_ID is required. Please set it before running this script.${NC}"
    echo "Example: SUBNET_ID=subnet-12345678 ./deploy-to-aws.sh"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}DB_PASSWORD is required. Please set it before running this script.${NC}"
    echo "Example: DB_PASSWORD=your-secure-password ./deploy-to-aws.sh"
    exit 1
fi

echo -e "${GREEN}Starting deployment to AWS...${NC}"

# Step 1: Create ECR repository if it doesn't exist
echo -e "${YELLOW}Step 1: Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}

# Get ECR repository URI
ECR_REPO_URI=$(aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} --query 'repositories[0].repositoryUri' --output text)
echo -e "${GREEN}ECR repository URI: ${ECR_REPO_URI}${NC}"

# Step 2: Build and push Docker image
echo -e "${YELLOW}Step 2: Building and pushing Docker image...${NC}"
# Get ECR login token
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URI}

# Build Docker image
docker build -t ${ECR_REPO_NAME}:latest .

# Tag and push image
docker tag ${ECR_REPO_NAME}:latest ${ECR_REPO_URI}:latest
docker push ${ECR_REPO_URI}:latest

echo -e "${GREEN}Docker image pushed to ECR: ${ECR_REPO_URI}:latest${NC}"

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
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}

# Step 4: Get outputs from CloudFormation stack
echo -e "${YELLOW}Step 4: Getting deployment information...${NC}"
EC2_PUBLIC_DNS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`EC2PublicDNS`].OutputValue' --output text)
DASHBOARD_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' --output text)
GRAFANA_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`GrafanaURL`].OutputValue' --output text)
PROMETHEUS_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`PrometheusURL`].OutputValue' --output text)
RDS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' --output text)

# Step 5: Print deployment information
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Deployment Information:${NC}"
echo -e "EC2 Public DNS: ${GREEN}${EC2_PUBLIC_DNS}${NC}"
echo -e "Dashboard URL: ${GREEN}${DASHBOARD_URL}${NC}"
echo -e "Grafana URL: ${GREEN}${GRAFANA_URL}${NC}"
echo -e "Prometheus URL: ${GREEN}${PROMETHEUS_URL}${NC}"
echo -e "RDS Endpoint: ${GREEN}${RDS_ENDPOINT}${NC}"

echo -e "${YELLOW}Note: It may take a few minutes for the EC2 instance to initialize and start the application.${NC}"
echo -e "${YELLOW}You can SSH into the EC2 instance using: ssh -i ${EC2_KEY_NAME}.pem ubuntu@${EC2_PUBLIC_DNS}${NC}"

echo -e "${GREEN}Deployment completed!${NC}"
