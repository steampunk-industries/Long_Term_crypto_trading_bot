#!/bin/bash
# Generated cleanup script - REVIEW BEFORE RUNNING
# This script will remove duplicate and empty files based on analysis

# Create backup directory
BACKUP_DIR="cleanup_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Duplicate files - keeping one copy and removing others
# Keeping: ./aws-cloudformation-enhanced.yml
cp "./aws-cloudformation-enhanced.yml.bak2" "$BACKUP_DIR/"
rm "./aws-cloudformation-enhanced.yml.bak2"  # Remove duplicate

# Keeping: ./tests/__init__.py
cp "./src/models/__init__.py" "$BACKUP_DIR/"
rm "./src/models/__init__.py"  # Remove duplicate
cp "./src/exchange/__init__.py" "$BACKUP_DIR/"
rm "./src/exchange/__init__.py"  # Remove duplicate

# Empty files
cp "./code_analysis_reports/crypto_security_issues.txt" "$BACKUP_DIR/"
rm "./code_analysis_reports/crypto_security_issues.txt"  # Remove empty file

echo "Cleanup completed. Backup created in $BACKUP_DIR"
