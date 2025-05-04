#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Find a good place to add the Mappings section, after Parameters or Conditions
parameters_end = content.find('\n\nConditions:')
if parameters_end == -1:
    parameters_end = content.find('\nResources:')
    if parameters_end == -1:
        print("Could not find a suitable location to add the Mappings section")
        exit(1)

# Define the RegionMap with the latest Ubuntu 22.04 LTS AMIs for each region
region_map = """
Mappings:
  RegionMap:
    us-east-1:
      AMI: ami-0f3c7d07486cad139  # Ubuntu 22.04 LTS in us-east-1
    us-east-2:
      AMI: ami-024e6efaf93d85776  # Ubuntu 22.04 LTS in us-east-2
    us-west-1:
      AMI: ami-0f8e81a3da6e2510a  # Ubuntu 22.04 LTS in us-west-1
    us-west-2:
      AMI: ami-03f65b8614a860c29  # Ubuntu 22.04 LTS in us-west-2
    eu-west-1:
      AMI: ami-01dd271720c1ba44f  # Ubuntu 22.04 LTS in eu-west-1
    eu-central-1:
      AMI: ami-0d497a49e7d359666  # Ubuntu 22.04 LTS in eu-central-1
    ap-northeast-1:
      AMI: ami-0d52744d6551d851e  # Ubuntu 22.04 LTS in ap-northeast-1
    ap-southeast-1:
      AMI: ami-0df7a207adb9748c7  # Ubuntu 22.04 LTS in ap-southeast-1
    ap-southeast-2:
      AMI: ami-0310483fb2b488153  # Ubuntu 22.04 LTS in ap-southeast-2
"""

# Insert the RegionMap into the content
modified_content = content[:parameters_end] + region_map + content[parameters_end:]

# Fix the syntax in the FindInMap reference
modified_content = modified_content.replace(
    "!FindInMap [RegionMap !Ref \"AWS::Region\" AMI]",
    "!FindInMap [RegionMap, !Ref \"AWS::Region\", AMI]"
)

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(modified_content)

print("Added RegionMap to CloudFormation template")
