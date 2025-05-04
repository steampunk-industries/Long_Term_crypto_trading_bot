#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Fix the syntax in the Condition - it's missing a comma
content = content.replace(
    "IsProduction: !Equals [!Ref EnvironmentName 'prod']",
    "IsProduction: !Equals [!Ref EnvironmentName, 'prod']"
)

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(content)

print("Fixed Condition syntax in CloudFormation template")
