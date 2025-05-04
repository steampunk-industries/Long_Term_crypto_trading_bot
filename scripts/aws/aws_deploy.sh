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
