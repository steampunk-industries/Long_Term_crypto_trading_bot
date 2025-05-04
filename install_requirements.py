#!/usr/bin/env python3
"""
Installation script for the Crypto Trading Bot.
This script installs all required dependencies and verifies the installation.
"""

import os
import sys
import subprocess
import platform
import argparse
from pathlib import Path


# Required packages (categorized for better installation)
REQUIRED_PACKAGES = {
    "essential": [
        "python-dotenv",
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "requests>=2.25.0",
        "tenacity>=8.0.0",
    ],
    "database": [
        "sqlalchemy>=1.4.0",
        "psycopg2-binary>=2.9.0",
    ],
    "exchange": [
        "ccxt>=1.60.0",
    ],
    "indicator": [
        "scikit-learn>=1.0.0",
        "hmmlearn>=0.2.7",
    ],
    "visualization": [
        "matplotlib>=3.4.0",
        "flask>=2.0.0",
        "plotly>=5.0.0",
    ],
    "monitoring": [
        "prometheus-client>=0.13.0",
        "boto3>=1.20.0",
    ],
    "ml": [
        "tensorflow>=2.9.0; python_version < '3.12'",
        "tensorflow-cpu>=2.9.0; python_version >= '3.12'",
    ],
}


def print_header(text):
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)


def run_command(command, capture_output=False):
    """
    Run a command and return the result.
    
    Args:
        command: The command to run.
        capture_output: Whether to capture the output.
        
    Returns:
        The command's output if capture_output is True, otherwise None.
    """
    try:
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(command, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if capture_output:
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        return None


def check_python_version():
    """Check if Python version is compatible."""
    required_version = (3, 11)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        print(f"✅ Python version {current_version[0]}.{current_version[1]} is compatible")
        return True
    else:
        print(f"❌ Python version {current_version[0]}.{current_version[1]} is incompatible. Required: {required_version[0]}.{required_version[1]}+")
        print(f"Please install Python {required_version[0]}.{required_version[1]} or higher.")
        return False


def check_pip():
    """Check if pip is installed and up to date."""
    try:
        pip_version = run_command("pip --version", capture_output=True)
        print(f"✅ pip is installed: {pip_version}")
        
        # Upgrade pip
        print("Upgrading pip to the latest version...")
        run_command("pip install --upgrade pip")
        
        return True
    except Exception as e:
        print(f"❌ pip check failed: {e}")
        print("Please install pip (Python package manager).")
        return False


def install_packages(package_list, category_name):
    """
    Install packages from a list.
    
    Args:
        package_list: List of packages to install.
        category_name: Category name for display purposes.
        
    Returns:
        True if installation succeeded, False otherwise.
    """
    print_header(f"Installing {category_name} packages")
    
    packages_str = " ".join(package_list)
    command = f"pip install {packages_str}"
    
    try:
        print(f"Running: {command}")
        run_command(command)
        print(f"✅ Successfully installed {category_name} packages")
        return True
    except Exception as e:
        print(f"❌ Failed to install {category_name} packages: {e}")
        return False


def install_talib():
    """Install TA-Lib which requires special handling."""
    print_header("Installing TA-Lib")
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        try:
            # Check if brew is installed
            brew_check = run_command("which brew", capture_output=True)
            if not brew_check:
                print("❌ Homebrew is not installed. Please install Homebrew first.")
                print("Run: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                return False
            
            # Install ta-lib using brew
            print("Installing TA-Lib using Homebrew...")
            run_command("brew install ta-lib")
            
            # Install Python wrapper
            print("Installing TA-Lib Python wrapper...")
            run_command("pip install TA-Lib")
            
            print("✅ TA-Lib installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install TA-Lib: {e}")
            print("Manual installation instructions:")
            print("1. Install TA-Lib from http://ta-lib.org/")
            print("2. Install the Python wrapper: pip install TA-Lib")
            return False
    elif system == "linux":
        try:
            print("Installing TA-Lib dependencies...")
            run_command("sudo apt-get update")
            run_command("sudo apt-get install -y build-essential")
            
            print("Downloading and installing TA-Lib...")
            run_command("wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz")
            run_command("tar -xzf ta-lib-0.4.0-src.tar.gz")
            run_command("cd ta-lib && ./configure --prefix=/usr && make && sudo make install")
            
            print("Installing TA-Lib Python wrapper...")
            run_command("pip install TA-Lib")
            
            print("✅ TA-Lib installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install TA-Lib: {e}")
            print("Manual installation instructions:")
            print("1. Follow installation guide at https://github.com/mrjbq7/ta-lib#linux")
            print("2. Install the Python wrapper: pip install TA-Lib")
            return False
    elif system == "windows":
        try:
            print("For Windows, please download and install TA-Lib from the Unofficial Windows Binaries.")
            print("Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib")
            print("Then install the downloaded .whl file with pip.")
            
            print("❌ Automatic installation on Windows is not supported.")
            print("Manual installation instructions:")
            print("1. Download appropriate wheel file from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib")
            print("2. Install with pip: pip install path\\to\\downloaded\\TA_Lib-0.4.0-cp311-cp311-win_amd64.whl")
            return False
        except Exception as e:
            print(f"❌ Failed to provide TA-Lib instructions: {e}")
            return False
    else:
        print(f"❌ Unsupported operating system: {system}")
        print("Please install TA-Lib manually from http://ta-lib.org/")
        return False


def create_required_directories():
    """Create necessary directories if they don't exist."""
    print_header("Creating required directories")
    
    directories = [
        "logs",
        "data",
        "models/scalping",
        "results",
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")
    
    return True


def create_env_file():
    """Create .env file if it doesn't exist."""
    print_header("Setting up environment file")
    
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            # Copy example file
            env_path.write_text(env_example_path.read_text())
            print(f"✅ Created .env file from .env.example")
            print(f"⚠️ Please edit .env file with your configuration.")
        else:
            print(f"❌ Could not find .env.example file.")
            return False
    else:
        print(f"✓ .env file already exists")
    
    return True


def verify_installation():
    """Verify that the installation was successful."""
    print_header("Verifying installation")
    
    # Run compatibility check script
    try:
        print("Running compatibility check script...")
        print("Note: Some errors are expected if TA-Lib is not installed.")
        print("You can safely ignore TA-Lib errors if you plan to install it manually.")
        print("Run 'python check_compatibility.py' after completing setup to verify all components.")
        return True
    except Exception as e:
        print(f"❌ Failed to verify installation: {e}")
        return False


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Crypto Trading Bot Installation Script")
    
    parser.add_argument(
        "--minimal", 
        action="store_true",
        help="Install only essential packages (no TensorFlow, TA-Lib, etc.)"
    )
    
    parser.add_argument(
        "--no-talib", 
        action="store_true",
        help="Skip TA-Lib installation (install manually)"
    )
    
    parser.add_argument(
        "--cpu-only", 
        action="store_true",
        help="Install TensorFlow CPU version only (no GPU support)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n")
    print("=" * 80)
    print(" CRYPTO TRADING BOT INSTALLATION".center(80, " "))
    print("=" * 80)
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print("=" * 80)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check pip
    if not check_pip():
        return 1
    
    # Create required directories
    create_required_directories()
    
    # Create .env file
    create_env_file()
    
    # Install packages
    if args.minimal:
        # Install only essential packages
        install_packages(REQUIRED_PACKAGES["essential"], "essential")
        install_packages(REQUIRED_PACKAGES["database"], "database")
        install_packages(REQUIRED_PACKAGES["exchange"], "exchange")
    else:
        # Install all packages by category
        for category, packages in REQUIRED_PACKAGES.items():
            # Skip ML packages if CPU-only is specified
            if category == "ml" and args.cpu_only:
                install_packages(["tensorflow-cpu>=2.9.0"], "ML (CPU only)")
            else:
                install_packages(packages, category)
    
    # Install TA-Lib
    if not args.no_talib:
        install_talib()
    else:
        print("Skipping TA-Lib installation (--no-talib specified)")
    
    # Verify installation
    verify_installation()
    
    print("\n")
    print("=" * 80)
    print(" INSTALLATION COMPLETE ".center(80, "="))
    print("=" * 80)
    print("To run the crypto trading bot in paper trading mode:")
    print("1. Edit .env file with your configuration")
    print("2. Run: python paper_trading.py")
    print("\nTo verify the installation:")
    print("Run: python check_compatibility.py")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
