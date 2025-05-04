#!/usr/bin/env python3

with open('deploy_enhanced_aws.sh', 'r') as f:
    content = f.read()

# Add fallback-subnet-id to the variables section
variables_section = "# Configuration variables with defaults"
variables_line = "FALLBACK_SUBNET_ID=${FALLBACK_SUBNET_ID:-\"\"}"
if variables_line not in content:
    variables_section_end = content.find("\n\n", content.find(variables_section))
    updated_content = content[:variables_section_end] + "\n" + variables_line + content[variables_section_end:]
    content = updated_content

# Add fallback-subnet-id to the usage section
usage_section = "function display_usage {"
usage_line = "  echo \"  --fallback-subnet-id SUBNET_ID   Secondary subnet ID for RDS DB subnet group (required)\""
if usage_line not in content:
    usage_section_end = content.find("  echo \"  --help", content.find(usage_section))
    updated_content = content[:usage_section_end] + usage_line + "\n" + content[usage_section_end:]
    content = updated_content

# Add fallback-subnet-id to the parameter parsing section
parse_section = "# Parse command line arguments"
parse_line = "    --fallback-subnet-id) FALLBACK_SUBNET_ID=\"$2\"; shift 2 ;;"
if parse_line not in content:
    parse_section_end = content.find("    --help", content.find(parse_section))
    updated_content = content[:parse_section_end] + "    " + parse_line + "\n" + content[parse_section_end:]
    content = updated_content

# Add fallback-subnet-id parameter to the CloudFormation create-stack command
cf_section = "# Deploy the CloudFormation stack"
cf_param_line = "ParameterKey=FallbackSubnetId,ParameterValue='$FALLBACK_SUBNET_ID'"
if cf_param_line not in content:
    cf_section_end = content.find("    --capabilities", content.find(cf_section))
    cf_section_prev_param_end = content.rfind("'", 0, cf_section_end)
    updated_content = (
        content[:cf_section_prev_param_end+1] + 
        " \\\n    ParameterKey=FallbackSubnetId,ParameterValue='$FALLBACK_SUBNET_ID'" + 
        content[cf_section_prev_param_end+1:]
    )
    content = updated_content

# Add fallback-subnet-id validation
validate_section = "# Validate inputs"
validate_lines = '''
# Check if fallback subnet ID is provided
if [[ -z "$FALLBACK_SUBNET_ID" ]]; then
  echo -e "${RED}Error:${NC} Fallback subnet ID is required."
  display_usage
  exit 1
fi
'''
if "if [[ -z \"$FALLBACK_SUBNET_ID\" ]]; then" not in content:
    validate_section_end = content.find("# Check if EC2 key pair exists", content.find(validate_section))
    updated_content = content[:validate_section_end] + validate_lines + "\n" + content[validate_section_end:]
    content = updated_content

with open('deploy_enhanced_aws.sh', 'w') as f:
    f.write(content)

print("Updated deploy_enhanced_aws.sh with fallback-subnet-id parameter")
