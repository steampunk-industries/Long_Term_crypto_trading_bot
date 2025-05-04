#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Find the VPCInfoLambda section
lambda_start = content.find("  VPCInfoLambda:")
if lambda_start == -1:
    print("VPCInfoLambda resource not found")
    exit(0)  # No need to modify if it doesn't exist

# Find where VPCInfoLambda ends and the next resource begins
next_resource_idx = content.find("\n  ", lambda_start + 5)
if next_resource_idx == -1:
    next_resource_idx = len(content)

# Remove the VPCInfoLambda section
before_lambda = content[:lambda_start]
after_lambda = content[next_resource_idx:]

# Combine the parts without the lambda
modified_content = before_lambda + after_lambda

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(modified_content)

print("Removed VPCInfoLambda resource from CloudFormation template")
