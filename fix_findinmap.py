#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Fix the syntax in the FindInMap reference - it has incorrect syntax
content = content.replace(
    "ImageId: !FindInMap [RegionMap !Ref \"AWS::Region\" AMI]",
    "ImageId: !FindInMap [RegionMap, !Ref \"AWS::Region\", AMI]"
)

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(content)

print("Fixed FindInMap syntax in CloudFormation template")
