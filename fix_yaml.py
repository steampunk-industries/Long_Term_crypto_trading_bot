#!/usr/bin/env python3

file_path = 'aws-cloudformation-enhanced.yml'

with open(file_path, 'r') as file:
    content = file.read()

# Replace the problematic line with fixed format
fixed_content = content.replace(
    "MultiAZ: !If [IsProduction true false]",
    "MultiAZ: !If [IsProduction, true, false]"
)

with open(file_path, 'w') as file:
    file.write(fixed_content)

print("Fixed problematic YAML syntax.")

# Verify the change
with open(file_path, 'r') as file:
    lines = file.readlines()
    for i, line in enumerate(lines):
        if "MultiAZ:" in line:
            print(f"Line {i+1}: {line.strip()}")
