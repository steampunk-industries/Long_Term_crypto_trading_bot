#!/usr/bin/env python3

with open('aws-cloudformation-simplified.yml', 'r') as f:
    content = f.read()

# Update the AMI ID for us-east-1
content = content.replace(
    "us-east-1:\n      AMI: ami-0f3c7d07486cad139",
    "us-east-1:\n      AMI: ami-0b3377628d4878cc7"
)

with open('aws-cloudformation-simplified.yml', 'w') as f:
    f.write(content)

print("Updated AMI ID in CloudFormation template")
