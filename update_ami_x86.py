#!/usr/bin/env python3

with open('aws-cloudformation-simplified.yml', 'r') as f:
    content = f.read()

# Update the AMI ID for us-east-1 to use x86_64 architecture
content = content.replace(
    "us-east-1:\n      AMI: ami-0b3377628d4878cc7",
    "us-east-1:\n      AMI: ami-0651e7743c2ad304f"
)

with open('aws-cloudformation-simplified.yml', 'w') as f:
    f.write(content)

print("Updated AMI ID to x86_64 architecture in CloudFormation template")
