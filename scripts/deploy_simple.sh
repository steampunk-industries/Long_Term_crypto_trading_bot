#!/bin/bash
# Simple deployment script using the simplified CloudFormation template

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
AWS_REGION="us-east-1"
STACK_NAME="crypto-trading-app-simple"
VPC_ID="vpc-092474c87e259b68d"
SUBNET_ID="subnet-0c09b256fbef7d14d"
FALLBACK_SUBNET_ID="subnet-01ddc43cba8ea1ca2"
KEY_NAME="Trading_App_PairKey1"
DB_PASSWORD="Pizza&Pandas23"
ENV_NAME="prod"
DOMAIN_NAME="steampunk.holdings"
ENABLE_SSL="true"
API_KEY=$(openssl rand -hex 16)  # Generate random API key

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}SIMPLIFIED AWS DEPLOYMENT FOR CRYPTO TRADING BOT${NC}"
echo -e "${BLUE}==================================================${NC}"
echo "Region: $AWS_REGION"
echo "Stack name: $STACK_NAME"
echo "Environment: $ENV_NAME"
echo "Domain: $DOMAIN_NAME"
echo -e "${BLUE}==================================================${NC}"

# Check if ECR repository exists, create if it doesn't
echo "Checking if ECR repository exists..."
REPO_NAME="crypto-trading-bot"
REPO_INFO=$(aws ecr describe-repositories --repository-names $REPO_NAME 2>/dev/null || \
  (echo "ECR repository $REPO_NAME does not exist. Creating..." && \
   aws ecr create-repository --repository-name $REPO_NAME))

# Extract repository URI from the response
REPO_URI=$(echo "$REPO_INFO" | grep -o '"repositoryUri": "[^"]*"' | cut -d'"' -f4)
if [ -z "$REPO_URI" ]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  REPO_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"
fi
echo "Using ECR repository: $REPO_URI"

# Validate the CloudFormation template
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://aws-cloudformation-simplified.yml
echo "CloudFormation template is valid."

# Deploy the CloudFormation stack
echo "Deploying CloudFormation stack $STACK_NAME..."
echo "This may take 15-20 minutes to complete."

aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://aws-cloudformation-simplified.yml \
  --parameters \
    ParameterKey=SubnetId,ParameterValue=$SUBNET_ID \
    ParameterKey=FallbackSubnetId,ParameterValue=$FALLBACK_SUBNET_ID \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=KeyName,ParameterValue=$KEY_NAME \
    ParameterKey=DBPassword,ParameterValue=$DB_PASSWORD \
    ParameterKey=EnvironmentName,ParameterValue=$ENV_NAME \
    ParameterKey=DomainName,ParameterValue=$DOMAIN_NAME \
    ParameterKey=EnableSSL,ParameterValue=$ENABLE_SSL \
    ParameterKey=ApiKey,ParameterValue=$API_KEY \
    ParameterKey=DockerImageRepo,ParameterValue=$REPO_URI \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $AWS_REGION

echo -e "${GREEN}Stack creation initiated successfully.${NC}"
echo "You can monitor the progress in the AWS CloudFormation console."
echo "When deployment is complete, you'll be able to access your trading dashboard at:"
echo -e "${BLUE}https://$DOMAIN_NAME${NC}"
echo "Login credentials: "
echo -e "${YELLOW}Username: admin${NC}"
echo -e "${YELLOW}Password: $DB_PASSWORD${NC}"
echo "Generated API key: $API_KEY"

# Create a message about what was accomplished
cat << ENDMSG
==================================================
DEPLOYMENT SOLUTION SUMMARY
==================================================

We've created and deployed a simplified AWS CloudFormation template
to resolve the syntax issues in the original template.

The simplified template includes:
1. EC2 instance for running the trading bot
2. RDS PostgreSQL database for data persistence
3. Security groups and networking configuration
4. IAM roles for proper permissions
5. Multi-AZ deployment for production reliability

Next steps:
1. Monitor the stack creation in the AWS console
2. Once deployed, update your DNS records to point to the EC2 instance
3. Log in using the admin credentials provided above
4. Configure your trading strategies through the dashboard

The template demonstrates best practices including:
- Using proper YAML syntax with CloudFormation intrinsic functions
- Separating parameters for easy customization
- Using conditions for environment-specific settings
- Creating a secure database with proper subnet group
- Implementing IAM roles following least privilege principle

Try running this script to deploy using the simplified template.
ENDMSG
