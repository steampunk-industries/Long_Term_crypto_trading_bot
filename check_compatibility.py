#!/usr/bin/env python3
"""
Compatibility checker for the crypto trading bot.
This script verifies all dependencies and module imports to ensure everything works correctly.
"""

import sys
import os
import importlib
import time
import traceback

# Required packages
REQUIRED_PACKAGES = [
    "numpy",
    "pandas",
    "tensorflow",
    "sqlalchemy",
    "ccxt",
    "talib",
    "sklearn",
    "hmmlearn",
    "requests",
    "tenacity",
]

# Required modules from the project
PROJECT_MODULES = [
    "src.config",
    "src.exchange.wrapper",
    "src.strategies.base",
    "src.strategies.low_risk",
    "src.strategies.medium_risk",
    "src.strategies.high_risk",
    "src.models.scalping_model",
    "src.utils.database",
    "src.utils.dashboard",
    "src.utils.logging",
    "src.utils.metrics",
    "src.utils.market_regime",
    "src.utils.market_regime_detection",
    "src.utils.volume_profile",
    "src.utils.on_chain_data",
    "src.utils.sentiment_analysis",
    "src.utils.profit_withdrawal",
    "src.utils.portfolio_manager",
    "src.backtesting.engine",
]

def print_header(text):
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)

def print_result(name, status, message=""):
    """Print a result with the given name, status, and message."""
    if status:
        print(f"✅ {name}: OK {message}")
    else:
        print(f"❌ {name}: FAILED {message}")

def check_python_version():
    """Check the Python version."""
    print_header("Checking Python Version")
    required_version = (3, 11)
    current_version = sys.version_info[:2]
    
    status = current_version >= required_version
    message = f"Required: {required_version[0]}.{required_version[1]}, Current: {current_version[0]}.{current_version[1]}"
    print_result("Python Version", status, message)
    
    return status

def check_packages():
    """Check required packages."""
    print_header("Checking Required Packages")
    
    all_ok = True
    for package in REQUIRED_PACKAGES:
        try:
            imported = importlib.import_module(package)
            version = getattr(imported, "__version__", "unknown")
            print_result(package, True, f"Version: {version}")
        except ImportError as e:
            print_result(package, False, str(e))
            all_ok = False
    
    return all_ok

def check_project_modules():
    """Check project modules."""
    print_header("Checking Project Modules")
    
    all_ok = True
    for module in PROJECT_MODULES:
        try:
            importlib.import_module(module)
            print_result(module, True)
        except Exception as e:
            print_result(module, False, str(e))
            traceback.print_exc()
            all_ok = False
    
    return all_ok

def check_tensorflow_gpu():
    """Check TensorFlow GPU support."""
    print_header("Checking TensorFlow GPU Support")
    
    try:
        import tensorflow as tf
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                print(f"Found GPU: {gpu}")
            status = True
            message = f"Found {len(gpus)} GPU(s)"
        else:
            status = False
            message = "No GPU found, TensorFlow will use CPU"
        
        print_result("TensorFlow GPU", status, message)
        return status
    except Exception as e:
        print_result("TensorFlow GPU", False, str(e))
        return False

def check_database_connection():
    """Check database connection."""
    print_header("Checking Database Connection")
    
    try:
        from src.utils.database import health_check
        
        status = health_check()
        print_result("Database Connection", status)
        return status
    except Exception as e:
        print_result("Database Connection", False, str(e))
        return False

def check_market_regime_consistency():
    """Check consistency between market regime implementations."""
    print_header("Checking Market Regime Implementations")
    
    try:
        from src.utils.market_regime import MarketRegimeDetector as MRD1
        from src.utils.market_regime_detection import MarketRegimeDetector as MRD2
        
        # Check if both modules have key methods
        mrd1_methods = set(dir(MRD1))
        mrd2_methods = set(dir(MRD2))
        
        common_methods = mrd1_methods.intersection(mrd2_methods)
        required_methods = {"detect_regime", "calculate_volatility", "calculate_trend_strength"}
        
        if required_methods.issubset(common_methods):
            print_result("Market Regime Consistency", True, "Both implementations have required methods")
            print(f"Warning: Having two similar implementations might cause confusion")
            return True
        else:
            missing = required_methods - common_methods
            print_result("Market Regime Consistency", False, f"Missing methods: {missing}")
            return False
    except Exception as e:
        print_result("Market Regime Consistency", False, str(e))
        return False

def check_exchange_wrapper():
    """Check exchange wrapper with dummy API keys."""
    print_header("Checking Exchange Wrapper")
    
    try:
        from src.exchange.wrapper import ExchangeWrapper
        
        # Create a wrapper with dummy keys (should work in some read-only endpoints)
        wrapper = ExchangeWrapper()
        
        # Try to access basic exchange info without auth
        try:
            wrapper.exchange.load_markets()
            print_result("Exchange Markets Loaded", True)
            return True
        except Exception as e:
            print_result("Exchange Markets Loaded", False, str(e))
            return False
    except Exception as e:
        print_result("Exchange Wrapper", False, str(e))
        return False

def main():
    """Run all checks."""
    print("\n\n=== CRYPTO TRADING BOT COMPATIBILITY CHECKER ===\n")
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Python Path: {sys.executable}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    results.append(("Python Version", check_python_version()))
    results.append(("Required Packages", check_packages()))
    results.append(("Project Modules", check_project_modules()))
    results.append(("TensorFlow GPU", check_tensorflow_gpu()))
    results.append(("Database Connection", check_database_connection()))
    results.append(("Market Regime Consistency", check_market_regime_consistency()))
    results.append(("Exchange Wrapper", check_exchange_wrapper()))
    
    print_header("Summary")
    
    all_ok = True
    for name, status in results:
        print_result(name, status)
        all_ok = all_ok and status
    
    if all_ok:
        print("\n✅ All checks passed! The crypto trading bot should work correctly.")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues before running the bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
