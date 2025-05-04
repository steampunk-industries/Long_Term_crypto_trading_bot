#!/usr/bin/env python3
"""
Virtual Environment Setup Script for the Crypto Trading Bot.
Creates and configures a Python virtual environment for isolated dependency management.
"""

import os
import sys
import subprocess
import platform
import venv
import argparse
from pathlib import Path

# Default virtual environment name
DEFAULT_VENV_NAME = "myenv"

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
        print(f"Creating virtual environment in: {venv_path}")
        venv.create(venv_path, with_pip=True)
        print(f"✅ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False


def install_requirements(venv_path):
    """
    Install requirements in the virtual environment.
    
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
        
        # Check if we have the install_requirements.py script
        if os.path.exists("install_requirements.py"):
            print("Installing dependencies using install_requirements.py...")
            
            # Get the python executable from the virtual environment
            if system == "windows":
                python_path = os.path.join(venv_path, "Scripts", "python")
            else:
                python_path = os.path.join(venv_path, "bin", "python")
            
            run_command(f'"{python_path}" install_requirements.py')
        else:
            # Fall back to installing from requirements.txt
            if os.path.exists("requirements.txt"):
                print("Installing dependencies from requirements.txt...")
                run_command(f'"{pip_path}" install -r requirements.txt')
            else:
                print("⚠️ Neither install_requirements.py nor requirements.txt found.")
                print("Please run the installation manually or create one of these files.")
                return False
        
        print(f"✅ Dependencies installed successfully in the virtual environment")
        return True
    except Exception as e:
        print(f"❌ Failed to install requirements: {e}")
        return False


def print_activation_instructions(venv_path):
    """
    Print instructions for activating the virtual environment.
    
    Args:
        venv_path: Path to the virtual environment.
    """
    system = platform.system().lower()
    
    print_header("Virtual Environment Activation Instructions")
    
    if system == "windows":
        print("To activate the virtual environment in Windows Command Prompt:")
        print(f"    {venv_path}\\Scripts\\activate.bat")
        print("\nTo activate in Windows PowerShell:")
        print(f"    {venv_path}\\Scripts\\Activate.ps1")
    else:  # Unix-like systems (Linux, macOS)
        print("To activate the virtual environment in Bash/Zsh:")
        print(f"    source {venv_path}/bin/activate")
        print("\nTo activate in Fish shell:")
        print(f"    source {venv_path}/bin/activate.fish")
    
    print("\nAfter activation, run:")
    print("    python check_compatibility.py")
    print("    python paper_trading.py")
    
    print("\nTo deactivate the virtual environment, simply run:")
    print("    deactivate")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Setup Virtual Environment for Crypto Trading Bot")
    
    parser.add_argument(
        "--venv-path", 
        type=str, 
        default=DEFAULT_VENV_NAME,
        help=f"Path for the virtual environment (default: {DEFAULT_VENV_NAME})"
    )
    
    parser.add_argument(
        "--requirements-only", 
        action="store_true",
        help="Only install requirements in an existing virtual environment"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n")
    print("=" * 80)
    print(" CRYPTO TRADING BOT VIRTUAL ENVIRONMENT SETUP ".center(80, "="))
    print("=" * 80)
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print("=" * 80)
    
    venv_path = args.venv_path
    venv_exists = os.path.exists(venv_path)
    
    if args.requirements_only:
        if not venv_exists:
            print(f"❌ Virtual environment not found at {venv_path}")
            print(f"Please create a virtual environment first or remove --requirements-only flag")
            return 1
        
        # Only install requirements
        if not install_requirements(venv_path):
            return 1
    else:
        # Check if virtual environment already exists
        if venv_exists:
            print(f"⚠️ Virtual environment already exists at {venv_path}")
            response = input("Do you want to overwrite it? (y/N): ").strip().lower()
            
            if response != 'y':
                print("Setup aborted")
                return 0
            
            try:
                import shutil
                shutil.rmtree(venv_path)
                print(f"Removed existing virtual environment at {venv_path}")
            except Exception as e:
                print(f"❌ Failed to remove existing virtual environment: {e}")
                return 1
        
        # Create virtual environment
        if not create_venv(venv_path):
            return 1
        
        # Install requirements
        if not install_requirements(venv_path):
            return 1
    
    # Print activation instructions
    print_activation_instructions(venv_path)
    
    print("\n")
    print("=" * 80)
    print(" SETUP COMPLETE ".center(80, "="))
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
