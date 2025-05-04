#!/usr/bin/env python3

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Fix the syntax in the !If functions - they need commas between parameters
content = content.replace(
    "MultiAZ: !If [IsProduction true false]",
    "MultiAZ: !If [IsProduction, true, false]"
)

# Search for other !If functions and fix them too
import re
pattern = r'!If \[(.*?)\s+(.*?)\s+(.*?)\]'
matches = re.findall(pattern, content)

for match in matches:
    original = f'!If [{match[0]} {match[1]} {match[2]}]'
    fixed = f'!If [{match[0]}, {match[1]}, {match[2]}]'
    content = content.replace(original, fixed)

with open('aws-cloudformation-enhanced.yml', 'w') as f:
    f.write(content)

print("Fixed !If function syntax in CloudFormation template")
