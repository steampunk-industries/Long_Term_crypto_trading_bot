#!/bin/bash
# AWS IAM Permissions Setup Script for Crypto Trading Bot
# This script helps set up the necessary AWS IAM permissions for deploying
# and running the crypto trading bot infrastructure.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# AWS policies required for this project
# Note: AWS limits users to 10 managed policies. We provide policy sets to stay within this limit.

# Core policies (essential)
CORE_POLICIES=(
    "AmazonEC2FullAccess"            # Essential for EC2 instances
    "AWSCloudFormationFullAccess"    # For deploying infrastructure as code
    "IAMFullAccess"                  # For creating and managing roles
    "AmazonVPCFullAccess"            # For network configuration
    "AmazonS3FullAccess"             # For assets, config files, and artifacts
)

# Database policies
DATABASE_POLICIES=(
    "AmazonRDSFullAccess"            # For PostgreSQL database
    "AmazonDynamoDBFullAccess"       # For NoSQL data storage
)

# Web hosting policies
WEB_POLICIES=(
    "ElasticLoadBalancingFullAccess" # For load balancing web traffic
    "AWSCertificateManagerFullAccess" # For HTTPS
    "AmazonRoute53FullAccess"        # For DNS and domain management
)

# Monitoring and serverless policies
MONITORING_POLICIES=(
    "CloudWatchFullAccess"           # For monitoring 
    "AWSLambda_FullAccess"           # For serverless components
    "AWSKeyManagementServicePowerUser" # For encrypting data and credentials
)

# Default to core + database as a standard set that fits within the 10-policy limit
REQUIRED_POLICIES=(
    "${CORE_POLICIES[@]}"
    "${DATABASE_POLICIES[@]}"
)

# Policy sets for different use cases as string arrays for use with --policy-set
declare -A POLICY_SETS
POLICY_SETS["minimal"]="AmazonEC2FullAccess AWSCloudFormationFullAccess IAMFullAccess AmazonVPCFullAccess AmazonS3FullAccess"
POLICY_SETS["database"]="${POLICY_SETS["minimal"]} AmazonRDSFullAccess"
POLICY_SETS["web"]="${POLICY_SETS["minimal"]} ElasticLoadBalancingFullAccess AWSCertificateManagerFullAccess"
POLICY_SETS["monitoring"]="${POLICY_SETS["minimal"]} CloudWatchFullAccess"
POLICY_SETS["serverless"]="${POLICY_SETS["minimal"]} AWSLambda_FullAccess"
POLICY_SETS["standard"]="${POLICY_SETS["minimal"]} AmazonRDSFullAccess CloudWatchFullAccess"
POLICY_SETS["complete"]="${POLICY_SETS["minimal"]} AmazonRDSFullAccess ElasticLoadBalancingFullAccess AWSCertificateManagerFullAccess"

# Function to display script usage
function display_usage {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --user USERNAME        IAM username to grant permissions to (default: current user)"
    echo "  --create-user USERNAME Create a new IAM user with the specified name"
    echo "  --list-only            Only list required policies without making changes"
    echo "  --check                Check if the user already has the required policies"
    echo "  --help                 Display this help message and exit"
    echo
    echo "Example:"
    echo "  $0 --user my-deployment-user"
    echo "  $0 --create-user crypto-bot-deployer"
}

# Initialize variables
USERNAME=""
CREATE_USER=false
LIST_ONLY=false
CHECK_ONLY=false

# Process command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --user)
            USERNAME="$2"
            shift 2
            ;;
        --create-user)
            CREATE_USER=true
            USERNAME="$2"
            shift 2
            ;;
        --list-only)
            LIST_ONLY=true
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
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

# Function to check if the AWS CLI is available
function check_aws_cli {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI is not installed. Please install it first.${NC}"
        echo "Instructions: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi

    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}Error: AWS CLI is not configured with valid credentials.${NC}"
        echo "Please run 'aws configure' first to set up your AWS credentials."
        exit 1
    fi
}

# Function to get policy description
function get_policy_description {
    local policy=$1
    case $policy in
        "AmazonS3FullAccess")
            echo "For storing website assets, configuration files, and deployment artifacts"
            ;;
        "AmazonEC2FullAccess")
            echo "Essential for managing EC2 instances where your trading bot and website will run"
            ;;
        "AWSKeyManagementServicePowerUser")
            echo "For encrypting sensitive trading data and credentials"
            ;;
        "AWSCloudFormationFullAccess")
            echo "For deploying infrastructure as code"
            ;;
        "AmazonDynamoDBFullAccess")
            echo "If your bot stores trading data or state"
            ;;
        "AWSLambda_FullAccess")
            echo "If your architecture uses serverless components"
            ;;
        "CloudWatchFullAccess")
            echo "For monitoring both your trading bot and website"
            ;;
        "AmazonRoute53FullAccess")
            echo "If you're using custom domains for your website"
            ;;
        "AmazonRDSFullAccess")
            echo "If your application uses a database"
            ;;
        "ElasticLoadBalancingFullAccess")
            echo "If you're load balancing your website traffic"
            ;;
        "AmazonVPCFullAccess")
            echo "For network configuration"
            ;;
        "IAMFullAccess")
            echo "Since your script will be creating and managing roles"
            ;;
        "AWSCertificateManagerFullAccess")
            echo "If you're using HTTPS for your website"
            ;;
        *)
            echo "No description available"
            ;;
    esac
}

# Function to list required policies
function list_policies {
    echo -e "${BLUE}AWS IAM Policies for Crypto Trading Bot:${NC}"
    echo
    echo -e "${YELLOW}NOTE: AWS limits users to 10 managed policies${NC}"
    echo -e "${YELLOW}We've organized policies into sets to stay within this limit${NC}"
    echo

    echo -e "${BLUE}Available Policy Sets:${NC}"
    echo -e "  ${GREEN}minimal${NC}: Core infrastructure only (5 policies)"
    echo -e "  ${GREEN}database${NC}: Core + Database (6 policies)"
    echo -e "  ${GREEN}web${NC}: Core + Web hosting (7 policies)"
    echo -e "  ${GREEN}monitoring${NC}: Core + Monitoring (6 policies)"
    echo -e "  ${GREEN}serverless${NC}: Core + Lambda (6 policies)"
    echo -e "  ${GREEN}standard${NC}: Core + Database + Monitoring (7 policies) [Default]"
    echo -e "  ${GREEN}complete${NC}: Core + Database + Web + Monitoring (9 policies)"
    echo

    echo -e "${BLUE}Currently using policy set: standard${NC}"
    echo -e "${BLUE}Total policies: ${#REQUIRED_POLICIES[@]}${NC}"
    echo

    echo -e "${BLUE}Core Policies:${NC}"
    for policy in "${CORE_POLICIES[@]}"; do
        description=$(get_policy_description "$policy")
        echo -e "${GREEN}${policy}${NC}"
        echo -e "  ${description}"
        echo
    done
    
    echo -e "${BLUE}Database Policies:${NC}"
    for policy in "${DATABASE_POLICIES[@]}"; do
        description=$(get_policy_description "$policy")
        echo -e "${GREEN}${policy}${NC}"
        echo -e "  ${description}"
        echo
    done
    
    echo -e "${BLUE}Web Hosting Policies:${NC}"
    for policy in "${WEB_POLICIES[@]}"; do
        description=$(get_policy_description "$policy")
        echo -e "${GREEN}${policy}${NC}"
        echo -e "  ${description}"
        echo
    done
    
    echo -e "${BLUE}Monitoring and Serverless Policies:${NC}"
    for policy in "${MONITORING_POLICIES[@]}"; do
        description=$(get_policy_description "$policy")
        echo -e "${GREEN}${policy}${NC}"
        echo -e "  ${description}"
        echo
    done
}

# Function to create a new IAM user
function create_iam_user {
    local username=$1
    
    echo -e "${BLUE}Creating new IAM user: ${username}${NC}"
    
    # Check if the user already exists
    if aws iam get-user --user-name "$username" &> /dev/null; then
        echo -e "${YELLOW}User ${username} already exists.${NC}"
    else
        # Create the user
        aws iam create-user --user-name "$username"
        echo -e "${GREEN}User ${username} created successfully.${NC}"
        
        # Generate access keys for the user
        echo -e "${BLUE}Generating access keys for ${username}...${NC}"
        aws iam create-access-key --user-name "$username" > "access_keys_${username}.json"
        echo -e "${GREEN}Access keys generated and saved to access_keys_${username}.json${NC}"
        echo -e "${YELLOW}IMPORTANT: Keep this file secure and download it, as you won't be able to retrieve the secret key again.${NC}"
    fi
}

# Function to set policy set based on input
function set_policy_set {
    local policy_set=$1
    
    if [[ -z "$policy_set" ]]; then
        # Default to standard if not specified
        policy_set="standard"
    fi
    
    # Check if the policy set exists
    if [[ -z "${POLICY_SETS[$policy_set]}" ]]; then
        echo -e "${RED}Error: Policy set ${policy_set} not found.${NC}"
        echo -e "Available policy sets: minimal, database, web, monitoring, serverless, standard, complete"
        exit 1
    fi
    
    # Convert the space-separated string to an array
    REQUIRED_POLICIES=()
    for policy in ${POLICY_SETS[$policy_set]}; do
        # Only add each policy once (avoid duplicates)
        if [[ ! " ${REQUIRED_POLICIES[*]} " =~ " ${policy} " ]]; then
            REQUIRED_POLICIES+=("$policy")
        fi
    done
    
    local policy_count=${#REQUIRED_POLICIES[@]}
    echo -e "${BLUE}Using policy set: ${policy_set} (${policy_count} policies)${NC}"
    
    if [[ $policy_count -gt 10 ]]; then
        echo -e "${RED}Warning: This policy set contains ${policy_count} policies, but AWS limits users to 10 managed policies.${NC}"
        echo -e "${RED}The script will attempt to attach only the first 10 policies.${NC}"
    fi
}

# Function to attach policies to a user
function attach_policies {
    local username=$1
    local policy_set=${2:-"standard"}
    
    # Set up the policy set
    set_policy_set "$policy_set"
    
    echo -e "${BLUE}Attaching policies to user: ${username}${NC}"
    
    # Check if the user exists
    if ! aws iam get-user --user-name "$username" &> /dev/null; then
        echo -e "${RED}Error: User ${username} does not exist.${NC}"
        exit 1
    fi
    
    # First, get the count of already attached policies
    local attached_count=$(aws iam list-attached-user-policies --user-name "$username" --query "length(AttachedPolicies)" --output text)
    local max_policies=10
    local policies_to_attach=$((max_policies - attached_count))
    
    if [[ $policies_to_attach -le 0 ]]; then
        echo -e "${RED}User ${username} already has ${attached_count} policies attached (AWS limit is ${max_policies}).${NC}"
        echo -e "${RED}No additional policies can be attached. You may need to detach some policies first.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}User already has ${attached_count} policies. Can attach up to ${policies_to_attach} more.${NC}"
    
    local attached=0
    for policy in "${REQUIRED_POLICIES[@]}"; do
        if [[ $attached -ge $policies_to_attach ]]; then
            echo -e "${YELLOW}Reached AWS limit of ${max_policies} policies. Cannot attach more policies.${NC}"
            break
        fi
        
        echo -e "Attaching policy: ${policy}..."
        
        # Get the policy ARN
        policy_arn=$(aws iam list-policies --query "Policies[?PolicyName=='$policy'].Arn" --output text)
        
        if [[ -z "$policy_arn" ]]; then
            echo -e "${RED}Policy ${policy} not found.${NC}"
            continue
        fi
        
        # Check if the policy is already attached
        if aws iam list-attached-user-policies --user-name "$username" --query "AttachedPolicies[?PolicyName=='$policy']" --output text | grep -q "$policy"; then
            echo -e "${YELLOW}Policy ${policy} is already attached to user ${username}.${NC}"
        else
            # Attach the policy
            aws iam attach-user-policy --user-name "$username" --policy-arn "$policy_arn"
            echo -e "${GREEN}Successfully attached policy ${policy} to user ${username}.${NC}"
            ((attached++))
        fi
    done
    
    echo -e "${GREEN}Attached ${attached} new policies to user ${username}.${NC}"
}

# Function to check if a user has all required policies
function check_policies {
    local username=$1
    local missing_policies=()
    
    echo -e "${BLUE}Checking policies for user: ${username}${NC}"
    
    # Check if the user exists
    if ! aws iam get-user --user-name "$username" &> /dev/null; then
        echo -e "${RED}Error: User ${username} does not exist.${NC}"
        exit 1
    fi
    
    for policy in "${REQUIRED_POLICIES[@]}"; do
        # Get the policy ARN
        policy_arn=$(aws iam list-policies --query "Policies[?PolicyName=='$policy'].Arn" --output text)
        
        if [[ -z "$policy_arn" ]]; then
            echo -e "${RED}Policy ${policy} not found in your AWS account.${NC}"
            continue
        fi
        
        # Check if the policy is attached
        if ! aws iam list-attached-user-policies --user-name "$username" --query "AttachedPolicies[?PolicyName=='$policy']" --output text | grep -q "$policy"; then
            missing_policies+=("$policy")
        fi
    done
    
    if [[ ${#missing_policies[@]} -eq 0 ]]; then
        echo -e "${GREEN}User ${username} has all required policies.${NC}"
    else
        echo -e "${YELLOW}User ${username} is missing the following policies:${NC}"
        for policy in "${missing_policies[@]}"; do
            echo -e "- ${policy}"
        done
    fi
}

# Function to get current IAM user
function get_current_user {
    aws sts get-caller-identity --query "Arn" --output text | cut -d "/" -f 2
}

# Main execution
echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}     AWS IAM PERMISSIONS SETUP FOR CRYPTO TRADING BOT    ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Check for AWS CLI
check_aws_cli

# Just list policies if requested
if [[ "$LIST_ONLY" = true ]]; then
    list_policies
    exit 0
fi

# Determine the username if not specified
if [[ -z "$USERNAME" ]]; then
    USERNAME=$(get_current_user)
    echo -e "${YELLOW}No username specified. Using current user: ${USERNAME}${NC}"
fi

# Create a new user if requested
if [[ "$CREATE_USER" = true ]]; then
    create_iam_user "$USERNAME"
fi

# Check policies if requested
if [[ "$CHECK_ONLY" = true ]]; then
    check_policies "$USERNAME"
    exit 0
fi

# Attach policies
if [[ "$LIST_ONLY" = false && "$CHECK_ONLY" = false ]]; then
    attach_policies "$USERNAME"
    echo -e "${GREEN}======================================================${NC}"
    echo -e "${GREEN}             IAM PERMISSIONS SETUP COMPLETE             ${NC}"
    echo -e "${GREEN}======================================================${NC}"
    echo -e "User ${USERNAME} now has all necessary permissions for deploying and running the crypto trading bot."
    echo -e "You can now proceed with deploying the application using the deploy_enhanced_aws.sh script."
fi
