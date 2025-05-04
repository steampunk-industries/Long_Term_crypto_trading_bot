#!/usr/bin/env python3
"""
Cleanup Analysis Script for Crypto Trading Bot

This script analyzes the codebase to identify:
1. Duplicate files
2. Empty files
3. Redundant script files
4. Similar files that could be consolidated
"""

import os
import sys
import hashlib
import re
from collections import defaultdict
import json
from datetime import datetime

# Directory to store reports
REPORT_DIR = "cleanup_reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def md5_hash(file_path):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None

def find_duplicate_files(directory):
    """Find duplicate files based on content hash."""
    hash_to_files = defaultdict(list)
    
    # Get list of all files
    all_files = []
    for root, _, files in os.walk(directory):
        # Skip virtual environments and hidden directories
        if any(d in root for d in ["/venv", "/.git", "/node_modules", "/aws_venv", "/crypto_venv", "/myenv"]):
            continue
        
        for file in files:
            all_files.append(os.path.join(root, file))
    
    print(f"Analyzing {len(all_files)} files for duplicates...")
    
    # Calculate hashes
    for file_path in all_files:
        file_hash = md5_hash(file_path)
        if file_hash:
            hash_to_files[file_hash].append(file_path)
    
    # Find duplicates
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    
    return duplicates

def find_empty_files(directory):
    """Find empty and nearly empty files."""
    empty_files = []
    nearly_empty_files = []
    
    for root, _, files in os.walk(directory):
        # Skip virtual environments and hidden directories
        if any(d in root for d in ["/venv", "/.git", "/node_modules", "/aws_venv", "/crypto_venv", "/myenv"]):
            continue
        
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                if size == 0:
                    empty_files.append(file_path)
                elif size < 10:
                    nearly_empty_files.append(file_path)
            except Exception as e:
                print(f"Error checking size of {file_path}: {e}")
    
    return empty_files, nearly_empty_files

def find_similar_scripts(directory):
    """Find similar shell scripts that could be consolidated."""
    # Group scripts by their type
    dashboard_scripts = []
    deployment_scripts = []
    aws_scripts = []
    testing_scripts = []
    other_scripts = []
    
    # Find all shell scripts
    for root, _, files in os.walk(directory):
        # Skip virtual environments and hidden directories
        if any(d in root for d in ["/venv", "/.git", "/node_modules", "/aws_venv", "/crypto_venv", "/myenv"]):
            continue
        
        for file in files:
            if file.endswith(".sh") or (not file.endswith(".py") and not file.endswith(".md") and "." not in file):
                file_path = os.path.join(root, file)
                
                # Try to read the first few lines to guess what it does
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(1000)  # Read first 1000 chars
                        
                        if any(term in content.lower() or term in file.lower() for term in ["dashboard", "web", "server"]):
                            dashboard_scripts.append(file_path)
                        elif any(term in content.lower() or term in file.lower() for term in ["deploy", "install"]):
                            deployment_scripts.append(file_path)
                        elif any(term in content.lower() or term in file.lower() for term in ["aws", "cloud"]):
                            aws_scripts.append(file_path)
                        elif any(term in content.lower() or term in file.lower() for term in ["test", "trading"]):
                            testing_scripts.append(file_path)
                        else:
                            other_scripts.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    other_scripts.append(file_path)
    
    return {
        "dashboard_scripts": dashboard_scripts,
        "deployment_scripts": deployment_scripts,
        "aws_scripts": aws_scripts,
        "testing_scripts": testing_scripts,
        "other_scripts": other_scripts
    }

def find_aws_deployment_files(directory):
    """Find AWS deployment related files that might be consolidated."""
    aws_files = []
    
    for root, _, files in os.walk(directory):
        # Skip virtual environments and hidden directories
        if any(d in root for d in ["/venv", "/.git", "/node_modules", "/aws_venv", "/crypto_venv", "/myenv"]):
            continue
        
        for file in files:
            if "aws" in file.lower() or "cloudformation" in file.lower():
                aws_files.append(os.path.join(root, file))
    
    return aws_files

def generate_report(duplicates, empty_files, nearly_empty_files, similar_scripts, aws_files):
    """Generate a cleanup report with findings."""
    report_path = os.path.join(REPORT_DIR, "cleanup_analysis_report.md")
    
    with open(report_path, "w") as f:
        f.write("# Crypto Trading Bot Cleanup Analysis\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary
        f.write("## Summary\n\n")
        duplicate_count = sum(len(files) - 1 for files in duplicates.values())
        f.write(f"- **Duplicate Files**: {duplicate_count} ({len(duplicates)} sets)\n")
        f.write(f"- **Empty Files**: {len(empty_files)}\n")
        f.write(f"- **Nearly Empty Files**: {len(nearly_empty_files)}\n")
        f.write(f"- **Dashboard Scripts**: {len(similar_scripts['dashboard_scripts'])}\n")
        f.write(f"- **Deployment Scripts**: {len(similar_scripts['deployment_scripts'])}\n")
        f.write(f"- **AWS Scripts**: {len(similar_scripts['aws_scripts'])}\n")
        f.write(f"- **Testing Scripts**: {len(similar_scripts['testing_scripts'])}\n")
        f.write(f"- **Other Scripts**: {len(similar_scripts['other_scripts'])}\n")
        f.write(f"- **AWS Deployment Files**: {len(aws_files)}\n\n")
        
        # Duplicate Files
        f.write("## Duplicate Files\n\n")
        if duplicates:
            for hash_val, files in duplicates.items():
                f.write(f"- **Set with {len(files)} identical files**:\n")
                for file in files:
                    f.write(f"  - `{file}`\n")
                f.write("\n")
        else:
            f.write("No duplicate files found.\n\n")
        
        # Empty Files
        f.write("## Empty Files\n\n")
        if empty_files:
            for file in empty_files:
                f.write(f"- `{file}`\n")
        else:
            f.write("No empty files found.\n\n")
            
        f.write("\n## Nearly Empty Files (< 10 bytes)\n\n")
        if nearly_empty_files:
            for file in nearly_empty_files:
                f.write(f"- `{file}`\n")
        else:
            f.write("No nearly empty files found.\n\n")
        
        # Similar Scripts
        f.write("\n## Dashboard Scripts\n\n")
        if similar_scripts["dashboard_scripts"]:
            for file in similar_scripts["dashboard_scripts"]:
                f.write(f"- `{file}`\n")
        else:
            f.write("No dashboard scripts found.\n\n")
            
        f.write("\n## Deployment Scripts\n\n")
        if similar_scripts["deployment_scripts"]:
            for file in similar_scripts["deployment_scripts"]:
                f.write(f"- `{file}`\n")
        else:
            f.write("No deployment scripts found.\n\n")
            
        f.write("\n## AWS Scripts\n\n")
        if similar_scripts["aws_scripts"]:
            for file in similar_scripts["aws_scripts"]:
                f.write(f"- `{file}`\n")
        else:
            f.write("No AWS scripts found.\n\n")
            
        f.write("\n## Testing Scripts\n\n")
        if similar_scripts["testing_scripts"]:
            for file in similar_scripts["testing_scripts"]:
                f.write(f"- `{file}`\n")
        else:
            f.write("No testing scripts found.\n\n")
            
        f.write("\n## AWS Deployment Files\n\n")
        if aws_files:
            for file in aws_files:
                f.write(f"- `{file}`\n")
        else:
            f.write("No AWS deployment files found.\n\n")
        
        # Cleanup Recommendations
        f.write("\n## Cleanup Recommendations\n\n")
        
        # Duplicate files
        if duplicates:
            f.write("### Duplicate Files\n\n")
            f.write("For each set of duplicate files, keep only one copy. Suggested approach:\n\n")
            for hash_val, files in duplicates.items():
                # Keep the first file (usually the one with the shortest path)
                files_sorted = sorted(files, key=lambda x: len(x))
                keep = files_sorted[0]
                remove = files_sorted[1:]
                
                f.write(f"- Keep: `{keep}`\n")
                f.write("  Remove:\n")
                for file in remove:
                    f.write(f"  - `{file}`\n")
                f.write("\n")
        
        # Empty files
        if empty_files:
            f.write("### Empty Files\n\n")
            f.write("Consider removing these empty files if they serve no purpose:\n\n")
            for file in empty_files:
                f.write(f"- `{file}`\n")
            f.write("\n")
        
        # Script consolidation
        if len(similar_scripts["dashboard_scripts"]) > 1:
            f.write("### Dashboard Script Consolidation\n\n")
            f.write("Consider consolidating these dashboard-related scripts into a single script with parameters:\n\n")
            for file in similar_scripts["dashboard_scripts"]:
                f.write(f"- `{file}`\n")
            f.write("\n")
        
        if len(similar_scripts["deployment_scripts"]) > 1:
            f.write("### Deployment Script Consolidation\n\n")
            f.write("Consider consolidating these deployment scripts into a single script with parameters:\n\n")
            for file in similar_scripts["deployment_scripts"]:
                f.write(f"- `{file}`\n")
            f.write("\n")
        
        if len(similar_scripts["aws_scripts"]) > 1:
            f.write("### AWS Script Consolidation\n\n")
            f.write("Consider consolidating these AWS-related scripts into a single script with parameters:\n\n")
            for file in similar_scripts["aws_scripts"]:
                f.write(f"- `{file}`\n")
            f.write("\n")
        
        if len(aws_files) > 1:
            f.write("### AWS Deployment Files\n\n")
            f.write("Consider consolidating or organizing these AWS deployment files:\n\n")
            for file in aws_files:
                f.write(f"- `{file}`\n")
            f.write("\n")
        
        # General recommendation
        f.write("### General Organization\n\n")
        f.write("1. Create a dedicated `deploy/` directory for all deployment scripts\n")
        f.write("2. Create a dedicated `scripts/` directory for utility scripts\n")
        f.write("3. Consolidate similar functionality into single parameterized scripts\n")
        f.write("4. Improve documentation for each script to clarify its purpose\n")
        
    print(f"Report generated at {report_path}")
    
    # Generate JSON files for each category for easier processing
    json_report_duplicates = os.path.join(REPORT_DIR, "duplicate_files.json")
    with open(json_report_duplicates, "w") as f:
        # Convert to a format that's JSON serializable
        json_duplicates = {k: v for k, v in duplicates.items()}
        json.dump(json_duplicates, f, indent=2)
    
    json_report_empty = os.path.join(REPORT_DIR, "empty_files.json")
    with open(json_report_empty, "w") as f:
        json.dump({"empty": empty_files, "nearly_empty": nearly_empty_files}, f, indent=2)
    
    json_report_scripts = os.path.join(REPORT_DIR, "similar_scripts.json")
    with open(json_report_scripts, "w") as f:
        json.dump(similar_scripts, f, indent=2)
    
    json_report_aws = os.path.join(REPORT_DIR, "aws_files.json")
    with open(json_report_aws, "w") as f:
        json.dump(aws_files, f, indent=2)
    
    # Create a cleanup script template
    cleanup_script_path = os.path.join(REPORT_DIR, "cleanup_script.sh")
    with open(cleanup_script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Generated cleanup script - REVIEW BEFORE RUNNING\n")
        f.write("# This script will remove duplicate and empty files based on analysis\n\n")
        
        f.write("# Create backup directory\n")
        f.write("BACKUP_DIR=\"cleanup_backup_$(date +%Y%m%d_%H%M%S)\"\n")
        f.write("mkdir -p \"$BACKUP_DIR\"\n\n")
        
        # Backup and remove duplicate files
        if duplicates:
            f.write("# Duplicate files - keeping one copy and removing others\n")
            for hash_val, files in duplicates.items():
                files_sorted = sorted(files, key=lambda x: len(x))
                keep = files_sorted[0]
                remove = files_sorted[1:]
                
                f.write(f"# Keeping: {keep}\n")
                for file in remove:
                    f.write(f"cp \"{file}\" \"$BACKUP_DIR/\"\n")
                    f.write(f"rm \"{file}\"  # Remove duplicate\n")
                f.write("\n")
        
        # Backup and remove empty files
        if empty_files:
            f.write("# Empty files\n")
            for file in empty_files:
                f.write(f"cp \"{file}\" \"$BACKUP_DIR/\"\n")
                f.write(f"rm \"{file}\"  # Remove empty file\n")
            f.write("\n")
        
        f.write("echo \"Cleanup completed. Backup created in $BACKUP_DIR\"\n")
    
    # Make it executable
    os.chmod(cleanup_script_path, 0o755)
    print(f"Cleanup script template generated at {cleanup_script_path}")
    
    return report_path, cleanup_script_path

def main():
    """Main entry point."""
    print("Starting cleanup analysis...")
    
    # Use current directory if none specified
    directory = "."
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    # Find duplicate files
    duplicates = find_duplicate_files(directory)
    print(f"Found {sum(len(files) - 1 for files in duplicates.values())} duplicate files in {len(duplicates)} sets")
    
    # Find empty files
    empty_files, nearly_empty_files = find_empty_files(directory)
    print(f"Found {len(empty_files)} empty files and {len(nearly_empty_files)} nearly empty files")
    
    # Find similar scripts
    similar_scripts = find_similar_scripts(directory)
    print(f"Found {len(similar_scripts['dashboard_scripts'])} dashboard scripts")
    print(f"Found {len(similar_scripts['deployment_scripts'])} deployment scripts")
    print(f"Found {len(similar_scripts['aws_scripts'])} AWS scripts")
    print(f"Found {len(similar_scripts['testing_scripts'])} testing scripts")
    
    # Find AWS deployment files
    aws_files = find_aws_deployment_files(directory)
    print(f"Found {len(aws_files)} AWS deployment files")
    
    # Generate report
    report_path, cleanup_script_path = generate_report(
        duplicates, empty_files, nearly_empty_files, similar_scripts, aws_files
    )
    
    print(f"\nAnalysis complete!")
    print(f"Report: {report_path}")
    print(f"Cleanup script: {cleanup_script_path}")
    print("\nReview the report and cleanup script before taking any action.")

if __name__ == "__main__":
    main()
