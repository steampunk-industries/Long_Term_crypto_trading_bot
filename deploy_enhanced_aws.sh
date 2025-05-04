#!/bin/bash
# Enhanced AWS Deployment Script for Crypto Trading Bot
# This script deploys the enhanced CloudFormation template that sets up a complete
# AWS environment with EC2, RDS, monitoring, and auto-scaling.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables with defaults
AWS_REGION=${AWS_REGION:-"us-east-1"}
STACK_NAME=${STACK_NAME:-"crypto-trading-bot-enhanced"}
ENV_NAME=${ENV_NAME:-"prod"}
EC2_KEY_NAME=${EC2_KEY_NAME:-""}
VPC_ID=${VPC_ID:-""}
SUBNET_ID=${SUBNET_ID:-""}
DB_PASSWORD=${DB_PASSWORD:-""}
DOMAIN_NAME=${DOMAIN_NAME:-"steampunk.holdings"}
EMAIL=${EMAIL:-"admin@steampunk.holdings"}
ENABLE_SSL=${ENABLE_SSL:-"true"}
INSTANCE_TYPE=${INSTANCE_TYPE:-"t3.medium"}
DB_INSTANCE_CLASS=${DB_INSTANCE_CLASS:-"db.t3.small"}
INITIAL_BTC_PRICE=${INITIAL_BTC_PRICE:-84000}
API_KEY=${API_KEY:-$(openssl rand -hex 16)}
FALLBACK_SUBNET_ID=${FALLBACK_SUBNET_ID:-""}

# Function to display script usage
function display_usage {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --region REGION          AWS region (default: us-east-1)"
    echo "  --stack-name NAME        CloudFormation stack name (default: crypto-trading-bot-enhanced)"
    echo "  --env-name ENV           Environment name: dev, staging, prod (default: prod)"
    echo "  --key-name KEY           EC2 key pair name (required)"
    echo "  --vpc-id VPC_ID          VPC ID (required)"
    echo "  --subnet-id SUBNET_ID    Subnet ID (required)"
    echo "  --db-password PASSWORD   Database password (required, min 8 chars)"
    echo "  --domain DOMAIN          Domain name (default: steampunk.holdings)"
    echo "  --email EMAIL            Email for SSL certificate (default: admin@steampunk.holdings)"
    echo "  --enable-ssl BOOL        Enable SSL, true or false (default: true)"
    echo "  --instance-type TYPE     EC2 instance type (default: t3.medium)"
    echo "  --db-instance-class CLS  RDS instance class (default: db.t3.small)"
    echo "  --btc-price PRICE        Initial BTC price (default: 84000)"
    echo "  --api-key KEY            API key (default: randomly generated)"
    echo "  --fallback-subnet-id SUBNET_ID   Secondary subnet ID for RDS DB subnet group (required)"
  echo "  --help                   Display this help message and exit"
    echo
    echo "Example:"
    echo "  $0 --key-name my-key --vpc-id vpc-123456 --subnet-id subnet-123456 --db-password mysecurepassword"
}

# Process command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --env-name)
            ENV_NAME="$2"
            shift 2
            ;;
        --key-name)
            EC2_KEY_NAME="$2"
            shift 2
            ;;
        --vpc-id)
            VPC_ID="$2"
            shift 2
            ;;
        --subnet-id)
            SUBNET_ID="$2"
            shift 2
            ;;
        --db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --enable-ssl)
            ENABLE_SSL="$2"
            shift 2
            ;;
        --instance-type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        --db-instance-class)
            DB_INSTANCE_CLASS="$2"
            shift 2
            ;;
        --btc-price)
            INITIAL_BTC_PRICE="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --help)
            display_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            display_usage
            exit 1
            ;;
    esac
done

# Function to check if a command exists
function command_exists {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if we're in the AWS virtual environment
function check_aws_venv {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo -e "${RED}Error: Not running in a virtual environment.${NC}"
        echo -e "Please activate the AWS virtual environment first:"
        echo -e "    source aws_venv/bin/activate  # Linux/macOS"
        echo -e "    .\\aws_venv\\Scripts\\activate  # Windows"
        echo -e "Or create one if it doesn't exist:"
        echo -e "    python setup_aws_venv.py"
        exit 1
    fi

    # Check if AWS CLI is available in the virtual environment
    if ! command_exists aws; then
        echo -e "${RED}Error: AWS CLI not found in the virtual environment.${NC}"
        echo -e "Please install AWS CLI in the virtual environment:"
        echo -e "    pip install awscli boto3"
        exit 1
    fi
}

# Validate required parameters
function validate_parameters {
    local missing_params=0

    if [[ -z "$EC2_KEY_NAME" ]]; then
        echo -e "${RED}Error: EC2 key pair name is required (--key-name)${NC}"
        missing_params=1
    fi

    if [[ -z "$VPC_ID" ]]; then
        echo -e "${RED}Error: VPC ID is required (--vpc-id)${NC}"
        missing_params=1
    fi

    if [[ -z "$SUBNET_ID" ]]; then
        echo -e "${RED}Error: Subnet ID is required (--subnet-id)${NC}"
        missing_params=1
    fi

    if [[ -z "$DB_PASSWORD" ]]; then
        echo -e "${RED}Error: Database password is required (--db-password)${NC}"
        missing_params=1
    elif [[ ${#DB_PASSWORD} -lt 8 ]]; then
        echo -e "${RED}Error: Database password must be at least 8 characters${NC}"
        missing_params=1
    fi

    if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "staging" && "$ENV_NAME" != "prod" ]]; then
        echo -e "${RED}Error: Environment name must be dev, staging, or prod${NC}"
        missing_params=1
    fi

    if [[ "$ENABLE_SSL" != "true" && "$ENABLE_SSL" != "false" ]]; then
        echo -e "${RED}Error: Enable SSL must be true or false${NC}"
        missing_params=1
    fi

    if [[ $missing_params -eq 1 ]]; then
        display_usage
        exit 1
    fi
}

# Function to validate and format ECR repository info
function get_ecr_repo {
    # Get the account ID
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    
    if [[ -z "$account_id" ]]; then
        echo -e "${RED}Error: Unable to get AWS account ID. Check your AWS credentials.${NC}"
        exit 1
    fi
    
    # Format the ECR repository URI
    echo "${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/crypto-trading-bot"
}

# Function to validate the CloudFormation template
function validate_template {
    echo -e "${BLUE}Validating CloudFormation template...${NC}"
    
    if ! aws cloudformation validate-template \
        --template-body file://aws-cloudformation-enhanced.yml \
        --region $AWS_REGION > /dev/null; then
        echo -e "${RED}Error: CloudFormation template validation failed.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}CloudFormation template is valid.${NC}"
}

# Function to create or update the CloudFormation stack
function deploy_stack {
    local ecr_repo_uri=$(get_ecr_repo)
    
    echo -e "${BLUE}Deploying CloudFormation stack ${STACK_NAME}...${NC}"
    echo -e "${YELLOW}This may take 15-20 minutes to complete.${NC}"
    
    # Create or update the stack
    aws cloudformation deploy \
        --template-file aws-cloudformation-enhanced.yml \
        --stack-name ${STACK_NAME} \
        --parameter-overrides \
            EnvironmentName=${ENV_NAME} \
            KeyName=${EC2_KEY_NAME} \
            VpcId=${VPC_ID} \
            SubnetId=${SUBNET_ID} \
            DockerImageRepo=${ecr_repo_uri} \
            DBPassword=${DB_PASSWORD} \
            InstanceType=${INSTANCE_TYPE} \
            DatabaseInstanceClass=${DB_INSTANCE_CLASS} \
            DomainName=${DOMAIN_NAME} \
            EnableSSL=${ENABLE_SSL} \
            InitialBTCPrice=${INITIAL_BTC_PRICE} \
            ApiKey=${API_KEY} \
        --capabilities CAPABILITY_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Error: CloudFormation stack deployment failed.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}CloudFormation stack ${STACK_NAME} deployed successfully.${NC}"
}

# Function to create ECR repository if it doesn't exist
function prepare_ecr_repo {
    local ecr_repo_name="crypto-trading-bot"
    
    echo -e "${BLUE}Checking if ECR repository exists...${NC}"
    
    # Check if repository exists
    if ! aws ecr describe-repositories --repository-names ${ecr_repo_name} --region ${AWS_REGION} > /dev/null 2>&1; then
        echo -e "${YELLOW}ECR repository ${ecr_repo_name} does not exist. Creating...${NC}"
        
        aws ecr create-repository \
            --repository-name ${ecr_repo_name} \
            --region ${AWS_REGION}
        
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}Error: Failed to create ECR repository.${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}ECR repository created successfully.${NC}"
    else
        echo -e "${GREEN}ECR repository ${ecr_repo_name} already exists.${NC}"
    fi
}

# Function to get and display the stack outputs
function display_outputs {
    echo -e "${BLUE}Retrieving stack outputs...${NC}"
    
    # Get stack outputs
    local outputs=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    if [[ -z "$outputs" || "$outputs" == "null" ]]; then
        echo -e "${RED}Error: No outputs found for stack ${STACK_NAME}.${NC}"
        return
    fi
    
    echo -e "${GREEN}Deployment Information:${NC}"
    
    # Parse and display outputs
    echo "$outputs" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"' | while read -r line; do
        key=$(echo $line | cut -d':' -f1)
        value=$(echo $line | cut -d':' -f2- | sed 's/^ //' \
    ParameterKey=FallbackSubnetId,ParameterValue='$FALLBACK_SUBNET_ID')
        
        case $key in
            EC2PublicDNS)
                echo -e "EC2 Public DNS: ${GREEN}${value}${NC}"
                ;;
            EC2PublicIP)
                echo -e "EC2 Public IP: ${GREEN}${value}${NC}"
                ;;
            RDSEndpoint)
                echo -e "RDS Endpoint: ${GREEN}${value}${NC}"
                ;;
            DashboardURL)
                echo -e "Dashboard URL: ${GREEN}${value}${NC}"
                ;;
            *)
                echo -e "${key}: ${GREEN}${value}${NC}"
                ;;
        esac
    done
    
    echo -e "${YELLOW}Note: It may take a few minutes for the EC2 instance to initialize and start the application.${NC}"
    echo -e "${YELLOW}You can SSH into the EC2 instance using: ssh -i ${EC2_KEY_NAME}.pem ubuntu@<EC2PublicDNS>${NC}"
    
    echo -e "${YELLOW}Important Next Steps:${NC}"
    echo -e "1. Go to your domain registrar and point ${DOMAIN_NAME} to the EC2 public DNS"
    echo -e "2. Wait for DNS propagation (may take up to 24 hours)"
    echo -e "3. Access your dashboard at https://${DOMAIN_NAME}"
    echo -e "4. Use the following API key for dashboard authentication: ${API_KEY}"
}

# Main execution
echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}    ENHANCED AWS DEPLOYMENT FOR CRYPTO TRADING BOT    ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Region: ${AWS_REGION}"
echo -e "Stack name: ${STACK_NAME}"
echo -e "Environment: ${ENV_NAME}"
echo -e "Domain: ${DOMAIN_NAME}"
echo -e "${BLUE}======================================================${NC}"

# Check for AWS virtual environment and AWS CLI
check_aws_venv

# Validate parameters
validate_parameters

# Check dependencies
if ! command_exists jq; then
    echo -e "${YELLOW}Warning: jq is not installed. Some output formatting may not work correctly.${NC}"
fi

# Prepare ECR repository
prepare_ecr_repo

# Validate CloudFormation template
validate_template

# Deploy the stack
deploy_stack

# Display outputs
display_outputs

echo -e "${GREEN}Enhanced AWS deployment completed successfully!${NC}"        --fallback-subnet-id) FALLBACK_SUBNET_ID="$2"; shift 2 ;;

# Check if fallback subnet ID is provided
if [[ -z "$FALLBACK_SUBNET_ID" ]]; then
  echo -e "${RED}Error:${NC} Fallback subnet ID is required."
  display_usage
  exit 1
fi


