#!/usr/bin/env python3
"""
AWS Virtual Environment Setup Script for the Crypto Trading Bot.
Creates and configures a Python virtual environment with AWS-specific dependencies
for deploying and managing AWS resources.
"""

import os
import sys
import subprocess
import platform
import venv
import argparse
import json
from pathlib import Path

# Default virtual environment name for AWS
DEFAULT_AWS_VENV_NAME = "aws_venv"

# AWS-specific requirements
AWS_REQUIREMENTS = [
    "boto3>=1.26.0",             # AWS SDK for Python
    "awscli>=1.27.0",            # AWS Command Line Interface
    "aws-cdk-lib>=2.72.1",       # AWS Cloud Development Kit
    "cfn-lint>=0.77.0",          # CloudFormation linting
    "troposphere>=4.4.0",        # Library to create CloudFormation descriptions
    "sceptre>=4.0.0",            # CloudFormation deployment tool
    "aws-sam-cli>=1.83.0",       # AWS Serverless Application Model
    "moto>=4.1.0",               # Mock AWS services
    "pycfmodel>=0.21.0",         # CloudFormation parser
    "pyyaml>=6.0",               # YAML parser for CloudFormation
    "jmespath>=1.0.1",           # JSON querying language
]

def print_header(text):
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)


def run_command(command, capture_output=False, venv_dir=None):
    """
    Run a command and return the result.
    
    Args:
        command: The command to run.
        capture_output: Whether to capture the output.
        venv_dir: Virtual environment directory (for activating the environment).
        
    Returns:
        The command's output if capture_output is True, otherwise None.
    """
    try:
        env = os.environ.copy()
        
        # If a virtual environment is specified, modify the command to run within it
        if venv_dir:
            system = platform.system().lower()
            
            if system == "windows":
                python_path = os.path.join(venv_dir, "Scripts", "python.exe")
                pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
            else:  # Unix-like systems (Linux, macOS)
                python_path = os.path.join(venv_dir, "bin", "python")
                pip_path = os.path.join(venv_dir, "bin", "pip")
            
            # Replace 'python' or 'python3' with the venv python path
            if command.startswith(("python ", "python3 ")):
                command = f"{python_path} {command.split(' ', 1)[1]}"
            # Replace 'pip' with the venv pip path
            elif command.startswith("pip "):
                command = f"{pip_path} {command[4:]}"
        
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                env=env
            )
            return result.stdout.strip()
        else:
            subprocess.run(command, shell=True, check=True, env=env)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if capture_output:
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        return None


def create_venv(venv_path):
    """
    Create a virtual environment.
    
    Args:
        venv_path: Path to create the virtual environment in.
        
    Returns:
        True if creation was successful, False otherwise.
    """
    try:
        print(f"Creating AWS virtual environment in: {venv_path}")
        venv.create(venv_path, with_pip=True)
        print(f"✅ AWS virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create AWS virtual environment: {e}")
        return False


def install_aws_requirements(venv_path):
    """
    Install AWS-specific requirements in the virtual environment.
    
    Args:
        venv_path: Path to the virtual environment.
        
    Returns:
        True if installation was successful, False otherwise.
    """
    try:
        system = platform.system().lower()
        
        if system == "windows":
            pip_path = os.path.join(venv_path, "Scripts", "pip")
        else:  # Unix-like systems (Linux, macOS)
            pip_path = os.path.join(venv_path, "bin", "pip")
        
        print("Upgrading pip...")
        run_command(f'"{pip_path}" install --upgrade pip')
        
        # Install base project requirements
        if os.path.exists("requirements.txt"):
            print("Installing base project dependencies from requirements.txt...")
            run_command(f'"{pip_path}" install -r requirements.txt')
        
        # Install AWS-specific requirements
        print("Installing AWS-specific dependencies...")
        for req in AWS_REQUIREMENTS:
            print(f"  Installing {req}")
            run_command(f'"{pip_path}" install {req}')
        
        print(f"✅ AWS dependencies installed successfully in the virtual environment")
        return True
    except Exception as e:
        print(f"❌ Failed to install AWS requirements: {e}")
        return False


def configure_aws_credentials(venv_path):
    """
    Configure AWS credentials based on environment variables.
    
    Args:
        venv_path: Path to the virtual environment.
    
    Returns:
        True if configuration was successful, False otherwise.
    """
    try:
        # Check if AWS credentials are already in the environment
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # If not in environment, try to read from .env file
        if not aws_access_key or not aws_secret_key:
            if os.path.exists('.env'):
                print("Reading AWS credentials from .env file...")
                with open('.env', 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            if key == 'AWS_ACCESS_KEY_ID':
                                aws_access_key = value
                            elif key == 'AWS_SECRET_ACCESS_KEY':
                                aws_secret_key = value
                            elif key == 'AWS_REGION':
                                aws_region = value
        
        # Check if we have credentials now
        if aws_access_key and aws_secret_key:
            print("AWS credentials found. Configuring AWS CLI...")
            
            # Get the AWS CLI path from the virtual environment
            system = platform.system().lower()
            if system == "windows":
                aws_cli_path = os.path.join(venv_path, "Scripts", "aws")
            else:  # Unix-like systems (Linux, macOS)
                aws_cli_path = os.path.join(venv_path, "bin", "aws")
            
            # Configure AWS CLI
            run_command(f'"{aws_cli_path}" configure set aws_access_key_id {aws_access_key}')
            run_command(f'"{aws_cli_path}" configure set aws_secret_access_key {aws_secret_key}')
            run_command(f'"{aws_cli_path}" configure set region {aws_region}')
            run_command(f'"{aws_cli_path}" configure set output json')
            
            print(f"✅ AWS credentials configured successfully for region {aws_region}")
            return True
        else:
            print("⚠️ AWS credentials not found. You'll need to configure them manually.")
            print("To configure AWS credentials manually, activate the virtual environment and run:")
            print("    aws configure")
            return False
    except Exception as e:
        print(f"❌ Failed to configure AWS credentials: {e}")
        return False


def test_aws_connectivity(venv_path):
    """
    Test AWS connectivity by making a simple API call.
    
    Args:
        venv_path: Path to the virtual environment.
    
    Returns:
        True if connectivity test was successful, False otherwise.
    """
    try:
        system = platform.system().lower()
        if system == "windows":
            aws_cli_path = os.path.join(venv_path, "Scripts", "aws")
            python_path = os.path.join(venv_path, "Scripts", "python")
        else:  # Unix-like systems (Linux, macOS)
            aws_cli_path = os.path.join(venv_path, "bin", "aws")
            python_path = os.path.join(venv_path, "bin", "python")
        
        print("Testing AWS connectivity...")
        
        # Create a simple test script to run with boto3
        test_script = """
import boto3
from botocore.exceptions import ClientError
import json

try:
    # Just list the AWS regions to test connectivity
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions()
    print(json.dumps({
        'status': 'success',
        'message': f'Successfully connected to AWS. Found {len(regions["Regions"])} regions.'
    }))
except ClientError as e:
    print(json.dumps({
        'status': 'error',
        'message': str(e)
    }))
except Exception as e:
    print(json.dumps({
        'status': 'error',
        'message': f'Unexpected error: {str(e)}'
    }))
"""
        
        # Write the test script to a temporary file
        with open('aws_connectivity_test.py', 'w') as f:
            f.write(test_script)
        
        # Run the test script
        output = run_command(f'"{python_path}" aws_connectivity_test.py', capture_output=True)
        
        # Clean up
        os.remove('aws_connectivity_test.py')
        
        if output:
            try:
                result = json.loads(output)
                if result['status'] == 'success':
                    print(f"✅ {result['message']}")
                    return True
                else:
                    print(f"❌ AWS connectivity test failed: {result['message']}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ Failed to parse test output: {output}")
                return False
        else:
            print("❌ AWS connectivity test failed: No output from test script")
            return False
    except Exception as e:
        print(f"❌ Failed to test AWS connectivity: {e}")
        return False


def print_activation_instructions(venv_path):
    """
    Print instructions for activating the AWS virtual environment.
    
    Args:
        venv_path: Path to the virtual environment.
    """
    system = platform.system().lower()
    
    print_header("AWS Virtual Environment Activation Instructions")
    
    if system == "windows":
        print("To activate the AWS virtual environment in Windows Command Prompt:")
        print(f"    {venv_path}\\Scripts\\activate.bat")
        print("\nTo activate in Windows PowerShell:")
        print(f"    {venv_path}\\Scripts\\Activate.ps1")
    else:  # Unix-like systems (Linux, macOS)
        print("To activate the AWS virtual environment in Bash/Zsh:")
        print(f"    source {venv_path}/bin/activate")
        print("\nTo activate in Fish shell:")
        print(f"    source {venv_path}/bin/activate.fish")
    
    print("\nAfter activation, you can use AWS commands directly:")
    print("    aws s3 ls")
    print("    aws ec2 describe-instances")
    
    print("\nYou can also use boto3 in Python scripts:")
    print("    python -c \"import boto3; print(boto3.client('s3').list_buckets())\"")
    
    print("\nTo deploy the application to AWS:")
    print("    ./deploy-steampunk.sh")
    
    print("\nTo deactivate the virtual environment, simply run:")
    print("    deactivate")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Setup AWS Virtual Environment for Crypto Trading Bot")
    
    parser.add_argument(
        "--venv-path", 
        type=str, 
        default=DEFAULT_AWS_VENV_NAME,
        help=f"Path for the AWS virtual environment (default: {DEFAULT_AWS_VENV_NAME})"
    )
    
    parser.add_argument(
        "--requirements-only", 
        action="store_true",
        help="Only install AWS requirements in an existing virtual environment"
    )
    
    parser.add_argument(
        "--no-connectivity-test", 
        action="store_true",
        help="Skip AWS connectivity test"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n")
    print("=" * 80)
    print(" CRYPTO TRADING BOT AWS ENVIRONMENT SETUP ".center(80, "="))
    print("=" * 80)
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print("=" * 80)
    
    venv_path = args.venv_path
    venv_exists = os.path.exists(venv_path)
    
    if args.requirements_only:
        if not venv_exists:
            print(f"❌ AWS virtual environment not found at {venv_path}")
            print(f"Please create an AWS virtual environment first or remove --requirements-only flag")
            return 1
        
        # Only install requirements
        if not install_aws_requirements(venv_path):
            return 1
    else:
        # Check if virtual environment already exists
        if venv_exists:
            print(f"⚠️ AWS virtual environment already exists at {venv_path}")
            response = input("Do you want to overwrite it? (y/N): ").strip().lower()
            
            if response != 'y':
                print("Setup aborted")
                return 0
            
            try:
                import shutil
                shutil.rmtree(venv_path)
                print(f"Removed existing AWS virtual environment at {venv_path}")
            except Exception as e:
                print(f"❌ Failed to remove existing AWS virtual environment: {e}")
                return 1
        
        # Create virtual environment
        if not create_venv(venv_path):
            return 1
        
        # Install AWS requirements
        if not install_aws_requirements(venv_path):
            return 1
        
        # Configure AWS credentials
        configure_aws_credentials(venv_path)
        
        # Test AWS connectivity
        if not args.no_connectivity_test:
            test_aws_connectivity(venv_path)
    
    # Print activation instructions
    print_activation_instructions(venv_path)
    
    print("\n")
    print("=" * 80)
    print(" AWS ENVIRONMENT SETUP COMPLETE ".center(80, "="))
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
