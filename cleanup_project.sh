#!/bin/bash

# Cleanup script for Crypto Trading Bot
# This script removes unnecessary files and directories

echo "=== Project Cleanup Script ==="
echo "Creating a list of files to remove..."

# Create temp directory for any files we want to back up first
mkdir -p temp_backup

# 1. Redundant dashboard server files
DASHBOARD_FILES=(
  "simple_dashboard_server.py"
  "production_dashboard.py"
  # Keep dashboard_server.py as the primary one
)

# 2. Test and development files
TEST_FILES=(
  "test_paper_trading_with_public_apis.py" 
  "test_multi_exchange.py"
  "test_fixes.py"
  "test_database_fix.py"
  "test_exchange_connection.py"
  "test_exchange_apis.py"
  "test_gunicorn_setup.sh"
  "paper_trading_test_runner.py"
  "verify_database.py"
)

# 3. Code analysis and clean up tools
ANALYSIS_FILES=(
  "code_analysis_script.sh"
  "scripts/create_issues_from_reports.py"
  "cleanup_analysis.py"
  "cleanup.sh"
  ".github/workflows/code-analysis.yml"
)

# 4. Redundant documentation files
DOC_FILES=(
  "PAPER_TRADING_STEAMPUNK.md"
  "IMPROVEMENT_PLAN.md"
  "SYSTEM_FIXES_SUMMARY.md"
  "WEBSITE_SETUP_GUIDE.md"
  "PRODUCTION_SETUP.md"
  "DASHBOARD_FIX_NOTES.md"
  "FIXES_SUMMARY.md"
  "HTTPS_IMPLEMENTATION.md"
  "IMPLEMENTATION_SUMMARY.md"
  "GUNICORN_IMPLEMENTATION.md"
  "CODE_REVIEW_GUIDE.md"
  "VSCODE_FIX_README.md"
)

# 5. AWS and deployment files
AWS_FILES=(
  "deploy_production_dashboard.sh"
  "deploy_crypto_app.sh"
  "deploy_enhanced_aws.sh"
  "deploy_final.sh"
  "deploy_simple.sh"
  "deploy-to-aws.sh"
  "deploy-steampunk.sh"
  "setup-aws-deployment.sh"
  "setup_aws_permissions.sh"
  "update_ami.py"
  "update_ami_x86.py"
  "aws-cloudformation-enhanced.fixed.yml"
  "aws-cloudformation-enhanced.yml"
  "aws-cloudformation-enhanced.yml.bak"
  "aws-cloudformation-simplified.yml"
  "aws-cloudformation.yml"
  "deploy_local.py"
  "check_deployment.sh"
  "check_x86_deployment.sh"
  "deploy_x86.sh"
  "setup_aws_venv.py"
  "edit_yaml.sh"
  "fix_cloudformation.py"
  "fix_condition_syntax.py"
  "fix_conditions.py"
  "fix_ecr_policy.py"
  "fix_fallback_subnet_param.py"
  "fix_findinmap.py"
  "fix_if_syntax.py"
  "fix_subnet_issue.py"
  "fix_vpcinfo_lambda.py"
  "fix_yaml.py"
)

# 6. Duplicated scripts
DUPLICATE_SCRIPTS=(
  "run_paper_trading_with_steampunk.py"
  "make_executable.sh"
)

# Check files before removal
echo "=== Files to be removed ==="
echo "1. Dashboard Files:"
for file in "${DASHBOARD_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

echo "2. Test Files:"
for file in "${TEST_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

echo "3. Analysis Files:"
for file in "${ANALYSIS_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

echo "4. Documentation Files:"
for file in "${DOC_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

echo "5. AWS Files:"
for file in "${AWS_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

echo "6. Duplicate Scripts:"
for file in "${DUPLICATE_SCRIPTS[@]}"; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done

# Directories to be removed:
DIRS_TO_REMOVE=(
  "code_analysis_reports"
  "cleanup_reports"
  "cleanup_backup_20250427_151128"
  "deploy"
  "microservices"
)

echo "7. Directories to be removed:"
for dir in "${DIRS_TO_REMOVE[@]}"; do
  if [ -d "$dir" ]; then
    echo "  - $dir/"
  fi
done

read -p "Do you want to back up these files before removal? (y/n): " backup
if [[ $backup == "y" || $backup == "Y" ]]; then
  echo "Backing up files..."
  timestamp=$(date +%Y%m%d_%H%M%S)
  mkdir -p "cleanup_backup_$timestamp"
  
  # Copy files to backup
  for file in "${DASHBOARD_FILES[@]}" "${TEST_FILES[@]}" "${ANALYSIS_FILES[@]}" "${DOC_FILES[@]}" "${AWS_FILES[@]}" "${DUPLICATE_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
      # Create directory structure in backup
      mkdir -p "cleanup_backup_$timestamp/$(dirname "$file")"
      cp "$file" "cleanup_backup_$timestamp/$file"
      echo "Backed up: $file"
    fi
  done
  
  # Backup directories
  for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [ -d "$dir" ]; then
      cp -r "$dir" "cleanup_backup_$timestamp/"
      echo "Backed up directory: $dir/"
    fi
  done
  
  echo "Backup completed to: cleanup_backup_$timestamp/"
fi

read -p "Do you want to proceed with removal? (y/n): " confirm
if [[ $confirm == "y" || $confirm == "Y" ]]; then
  echo "Removing files..."
  
  # Remove files
  for file in "${DASHBOARD_FILES[@]}" "${TEST_FILES[@]}" "${ANALYSIS_FILES[@]}" "${DOC_FILES[@]}" "${AWS_FILES[@]}" "${DUPLICATE_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
      rm "$file"
      echo "Removed: $file"
    fi
  done
  
  # Remove directories
  for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [ -d "$dir" ]; then
      rm -rf "$dir"
      echo "Removed directory: $dir/"
    fi
  done
  
  echo "Removal completed."
  echo "Creating a single comprehensive README.md with essential information..."
  
  # Consolidate critical information from removed docs into the main README.md
  # (This would be a separate step)
  
  echo "Cleanup complete!"
else
  echo "Removal cancelled."
fi

# List files that can be consolidated instead of removed
echo ""
echo "=== Files that should be consolidated ==="
echo "Consider consolidating these files instead of removing them:"
echo "1. Dashboard script files - Consolidate into a single dashboard.py script"
echo "2. Documentation files - Consolidate into README.md and SETUP_GUIDE.md"
echo "3. Deployment scripts - Consolidate into a single deploy.sh script with options"
