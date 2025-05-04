#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Fix the ECR policy name
content = content.replace('arn:aws:iam::aws:policy/AmazonECR-FullAccess', 
                         'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess')

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(content)

print("Fixed ECR policy name in CloudFormation template")
