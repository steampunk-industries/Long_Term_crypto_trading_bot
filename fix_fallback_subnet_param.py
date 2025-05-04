#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# First, remove the FallbackSubnetId resource
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

# Remove the block in the content
modified_content = content.replace(fallback_subnet_block, '')

# Now, add the parameter to the Parameters section
parameters_section = "Parameters:"
parameters_end = modified_content.find("\n\n", modified_content.find(parameters_section))

new_parameter = """
  FallbackSubnetId:
    Type: AWS::EC2::Subnet::Id
    Description: "Secondary subnet ID for RDS DB subnet group (must be in a different AZ than primary subnet)"
"""

# Insert the new parameter at the end of the Parameters section
modified_content = modified_content[:parameters_end] + new_parameter + modified_content[parameters_end:]

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(modified_content)

print("Converted FallbackSubnetId to a parameter in CloudFormation template")
