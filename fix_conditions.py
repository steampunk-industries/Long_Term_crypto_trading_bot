#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Add the missing Conditions section
if 'Conditions:' not in content:
    # Find a good place to add the Conditions section, after Mappings or Parameters
    mappings_end = content.find('\n\nResources:')
    if mappings_end == -1:
        print("Could not find a suitable location to add the Conditions section")
        exit(1)
    
    # Define the IsProduction condition
    conditions_section = """
Conditions:
  IsProduction: !Equals [!Ref EnvironmentName, 'prod']
"""
    
    # Insert the Conditions section into the content
    modified_content = content[:mappings_end] + conditions_section + content[mappings_end:]
else:
    # If Conditions section exists but IsProduction is missing, add it
    conditions_section = content.find('Conditions:')
    next_section = content.find('\n\n', conditions_section + 10)
    
    # Check if IsProduction condition is missing
    if 'IsProduction:' not in content[conditions_section:next_section]:
        isproduction_condition = "\n  IsProduction: !Equals [!Ref EnvironmentName, 'prod']"
        modified_content = content[:next_section] + isproduction_condition + content[next_section:]
    else:
        modified_content = content

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(modified_content)

print("Added IsProduction condition to CloudFormation template")
