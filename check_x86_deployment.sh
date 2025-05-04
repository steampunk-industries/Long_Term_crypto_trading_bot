#!/bin/bash
# Script to check the status of the x86_64 CloudFormation deployment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STACK_NAME="crypto-trading-x86"

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}CHECKING X86_64 DEPLOYMENT STATUS${NC}"
echo -e "${BLUE}==================================================${NC}"

# Get stack status
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "STACK_NOT_FOUND")

if [[ "$STACK_STATUS" == "STACK_NOT_FOUND" ]]; then
    echo -e "Stack $STACK_NAME not found. Deployment may have failed to start."
    exit 1
fi

echo -e "Stack Status: ${YELLOW}$STACK_STATUS${NC}"

# If stack is complete, get outputs
if [[ "$STACK_STATUS" == "CREATE_COMPLETE" ]]; then
    echo -e "\n${GREEN}Deployment completed successfully!${NC}"
    
    # Get EC2 instance details
    INSTANCE_ID=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id EC2Instance --query "StackResources[0].PhysicalResourceId" --output text)
    EC2_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
    
    echo -e "\n${BLUE}EC2 Instance Details:${NC}"
    echo -e "Instance ID: $INSTANCE_ID"
    echo -e "Public IP: $EC2_PUBLIC_IP"
    
    # Get RDS details
    DB_INSTANCE=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME --logical-resource-id DBInstance --query "StackResources[0].PhysicalResourceId" --output text)
    DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE --query "DBInstances[0].Endpoint.Address" --output text)
    
    echo -e "\n${BLUE}Database Details:${NC}"
    echo -e "DB Instance: $DB_INSTANCE"
    echo -e "DB Endpoint: $DB_ENDPOINT"
    
    # Update deployment info with instance details
    cat >> DEPLOYMENT_INFO.md << ENDMSG

## Instance Details
- **EC2 Instance ID**: $INSTANCE_ID
- **EC2 Public IP**: $EC2_PUBLIC_IP
- **RDS Instance ID**: $DB_INSTANCE
- **RDS Endpoint**: $DB_ENDPOINT

## DNS Configuration
To configure your domain to point to the EC2 instance:
1. Log in to your domain registrar
2. Create an A record for steampunk.holdings pointing to $EC2_PUBLIC_IP
3. Wait for DNS propagation (can take up to 24-48 hours)
ENDMSG
    
    echo -e "\n${GREEN}Updated DEPLOYMENT_INFO.md with instance details${NC}"
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Configure DNS to point to $EC2_PUBLIC_IP"
    echo "2. Wait for DNS propagation"
    echo "3. Access your dashboard at https://steampunk.holdings"
    
elif [[ "$STACK_STATUS" == *"FAILED"* || "$STACK_STATUS" == *"ROLLBACK"* ]]; then
    echo -e "\n${YELLOW}Deployment encountered issues. Checking for errors...${NC}"
    
    # Get the stack events to find the failure reason
    aws cloudformation describe-stack-events --stack-name $STACK_NAME | grep -A 10 -B 10 "ResourceStatusReason" | head -30
    
    echo -e "\n${YELLOW}See AWS_DEPLOYMENT_TROUBLESHOOTING.md for common issues and solutions${NC}"
else
    echo -e "\n${YELLOW}Deployment is still in progress.${NC}"
    
    # Get the resources being created
    echo -e "\n${BLUE}Resources being created:${NC}"
    aws cloudformation describe-stack-resources --stack-name $STACK_NAME --query "StackResources[?ResourceStatus=='CREATE_IN_PROGRESS'].[LogicalResourceId,ResourceType,Timestamp]" --output table
    
    echo -e "\n${YELLOW}Run this script again later to check the status.${NC}"
    echo "Estimated completion time: 15-20 minutes from deployment start."
fi

echo -e "${BLUE}==================================================${NC}"
