#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Identify the FallbackSubnetId resource block
fallback_subnet_start = content.find('  FallbackSubnetId:')
if fallback_subnet_start == -1:
    print("FallbackSubnetId resource not found")
    exit(1)

# Find the next major resource (starts with 2 spaces followed by a word)
resource_pattern = '\n  [A-Za-z]'
next_resource_start = content.find(resource_pattern, fallback_subnet_start + 1)
if next_resource_start == -1:
    next_resource_start = len(content)
else:
    # Go back to the newline before this resource
    next_resource_start = content.rfind('\n', 0, next_resource_start)

# Extract the FallbackSubnetId resource block
fallback_subnet_block = content[fallback_subnet_start:next_resource_start]

# Replace with reference to an existing subnet
# We'll use the second subnet in the VPC (subnet-04c512506bad5184f)
new_fallback_subnet_block = '''  FallbackSubnetId:
    Type: String
    Default: subnet-01ddc43cba8ea1ca2
    Description: "Secondary subnet ID for RDS DB subnet group"'''

# Replace the block in the content
modified_content = content.replace(fallback_subnet_block, new_fallback_subnet_block)

# Write back to a new file
with open('aws-cloudformation-enhanced.fixed.yml', 'w') as f:
    f.write(modified_content)

print("Modified CloudFormation template saved to aws-cloudformation-enhanced.fixed.yml")
