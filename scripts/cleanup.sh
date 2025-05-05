#!/bin/bash
# Comprehensive Cleanup Script for Long-Term Crypto Trading Bot
# Based on the analysis results

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting cleanup process...${NC}"

# Create backup directory
BACKUP_DIR="cleanup_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Step 1: Remove duplicate files (with backup)
echo -e "\n${YELLOW}Step 1: Removing duplicate files...${NC}"

# Duplicate set 1: cloudformation yml files
echo "Processing duplicate set 1: cloudformation yml files"
cp "./aws-cloudformation-enhanced.yml.bak2" "$BACKUP_DIR/"
rm "./aws-cloudformation-enhanced.yml.bak2"

# We're not removing the __init__.py files from models and exchange since they might be needed
# These should be reviewed more carefully first

# Step 2: Remove empty files (with backup)
echo -e "\n${YELLOW}Step 2: Removing empty files...${NC}"
cp "./code_analysis_reports/crypto_security_issues.txt" "$BACKUP_DIR/"
rm "./code_analysis_reports/crypto_security_issues.txt"

# Step 3: Organize dashboard scripts
echo -e "\n${YELLOW}Step 3: Organizing dashboard scripts...${NC}"
for script in run_dashboard.sh start_website.sh install_dashboard_service.sh deploy_production_dashboard.sh; do
  if [ -f "$script" ]; then
    echo "Moving $script to scripts/dashboard/"
    cp "$script" "$BACKUP_DIR/"
    cp "$script" "scripts/dashboard/"
    chmod +x "scripts/dashboard/$script"
  fi
done

# Step 4: Organize AWS deployment scripts
echo -e "\n${YELLOW}Step 4: Organizing AWS deployment scripts...${NC}"
for script in deploy-to-aws.sh setup-aws-deployment.sh setup_aws_permissions.sh deploy_enhanced_aws.sh; do
  if [ -f "$script" ]; then
    echo "Moving $script to scripts/aws/"
    cp "$script" "$BACKUP_DIR/"
    cp "$script" "scripts/aws/"
    chmod +x "scripts/aws/$script"
  fi
done

# Step 5: Organize other deployment scripts
echo -e "\n${YELLOW}Step 5: Organizing other deployment scripts...${NC}"
for script in deploy_final.sh deploy_crypto_app.sh deploy-steampunk.sh deploy_x86.sh deploy_simple.sh; do
  if [ -f "$script" ]; then
    echo "Moving $script to deploy/"
    cp "$script" "$BACKUP_DIR/"
    cp "$script" "deploy/"
    chmod +x "deploy/$script"
  fi
done

# Step 6: Create main dashboard runner script
echo -e "\n${YELLOW}Step 6: Creating consolidated dashboard runner script...${NC}"
cat > "scripts/dashboard/dashboard.sh" << 'EOF'
#!/bin/bash
# Consolidated Dashboard Runner Script
# This script replaces multiple dashboard scripts with a single parameterized script

function usage {
  echo "Usage: $0 [command] [options]"
  echo "Commands:"
  echo "  start       - Start the dashboard server"
  echo "  install     - Install dashboard as a service"
  echo "  deploy      - Deploy the dashboard to production"
  echo "  paper       - Start paper trading with dashboard"
  echo "Options:"
  echo "  --port PORT - Specify port (default: 5000)"
  echo "  --prod      - Use production settings"
  echo "  --help      - Show this help message"
  exit 1
}

# Default values
PORT=5000
ENV="development"

# Parse command
if [ $# -eq 0 ]; then
  usage
fi

COMMAND=$1
shift

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT=$2
      shift 2
      ;;
    --prod)
      ENV="production"
      shift
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

case "$COMMAND" in
  start)
    echo "Starting dashboard server on port $PORT ($ENV mode)..."
    if [ "$ENV" == "production" ]; then
      python production_dashboard.py --port $PORT
    else
      python dashboard_server.py --port $PORT
    fi
    ;;
  install)
    echo "Installing dashboard as a service..."
    sudo ./install_dashboard_service.sh
    ;;
  deploy)
    echo "Deploying dashboard to production..."
    ./deploy_production_dashboard.sh
    ;;
  paper)
    echo "Starting paper trading with dashboard..."
    ./run_paper_trading.sh
    ;;
  *)
    echo "Unknown command: $COMMAND"
    usage
    ;;
esac
EOF

chmod +x "scripts/dashboard/dashboard.sh"

# Step 7: Create main AWS deployment script
echo -e "\n${YELLOW}Step 7: Creating consolidated AWS deployment script...${NC}"
cat > "scripts/aws/aws_deploy.sh" << 'EOF'
#!/bin/bash
# Consolidated AWS Deployment Script
# This script replaces multiple AWS deployment scripts with a single parameterized script

function usage {
  echo "Usage: $0 [command] [options]"
  echo "Commands:"
  echo "  deploy      - Deploy to AWS (default is standard deployment)"
  echo "  setup       - Setup AWS permissions and environment"
  echo "  check       - Check deployment status"
  echo "Options:"
  echo "  --enhanced  - Use enhanced deployment template"
  echo "  --simple    - Use simplified deployment template"
  echo "  --x86       - Deploy to x86 architecture"
  echo "  --region REGION - Specify AWS region (default: us-east-1)"
  echo "  --help      - Show this help message"
  exit 1
}

# Default values
DEPLOY_TYPE="standard"
REGION="us-east-1"

# Parse command
if [ $# -eq 0 ]; then
  usage
fi

COMMAND=$1
shift

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --enhanced)
      DEPLOY_TYPE="enhanced"
      shift
      ;;
    --simple)
      DEPLOY_TYPE="simple"
      shift
      ;;
    --x86)
      DEPLOY_TYPE="x86"
      shift
      ;;
    --region)
      REGION=$2
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

case "$COMMAND" in
  deploy)
    echo "Deploying to AWS ($DEPLOY_TYPE deployment in $REGION)..."
    if [ "$DEPLOY_TYPE" == "enhanced" ]; then
      ./deploy_enhanced_aws.sh --region $REGION
    elif [ "$DEPLOY_TYPE" == "simple" ]; then
      ./deploy_simple.sh --region $REGION
    elif [ "$DEPLOY_TYPE" == "x86" ]; then
      ./deploy_x86.sh --region $REGION
    else
      ./deploy-to-aws.sh --region $REGION
    fi
    ;;
  setup)
    echo "Setting up AWS permissions and environment..."
    ./setup_aws_permissions.sh
    ./setup-aws-deployment.sh
    ;;
  check)
    echo "Checking deployment status..."
    if [ "$DEPLOY_TYPE" == "x86" ]; then
      ./check_x86_deployment.sh
    else
      ./check_deployment.sh
    fi
    ;;
  *)
    echo "Unknown command: $COMMAND"
    usage
    ;;
esac
EOF

chmod +x "scripts/aws/aws_deploy.sh"

echo -e "${GREEN}Cleanup process completed!${NC}"
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Verify that the organized scripts work correctly"
echo "2. Once verified, you can delete the original scripts"
echo "3. Update any documentation or references to the moved scripts"
echo "4. Consider further consolidation of similar files"
