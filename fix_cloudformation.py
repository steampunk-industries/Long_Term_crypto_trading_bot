#!/usr/bin/env python3
import re

with open('aws-cloudformation-enhanced.yml', 'r') as f:
    content = f.read()

# Fix the escaping of the ${DB_PASSWORD} variable
content = content.replace('DASHBOARD_PASSWORD=\\${DB_PASSWORD}', 'DASHBOARD_PASSWORD=${DBPassword}')

# Fix the append_dimensions section that may contain aws:InstanceId
content = content.replace('"InstanceId": "\\${aws:InstanceId}"', '"InstanceId": "${!aws:InstanceId}"')

with open('aws-cloudformation-enhanced.yml.fixed', 'w') as f:
    f.write(content)

print("Fixed CloudFormation template saved to aws-cloudformation-enhanced.yml.fixed")
