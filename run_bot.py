#!/usr/bin/env python3
"""
Convenience script to run the Crypto Trading Bot.
"""

import sys
import os
import argparse
from loguru import logger

from src.main import main as main_entry

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Run the Crypto Trading Bot')
    parser.add_argument('--dashboard-only', action='store_true', help='Run only the dashboard')
    parser.add_argument('--bot-only', action='store_true', help='Run only the trading bot')
    parser.add_argument('--interval', type=int, default=60, help='Interval between bot runs in minutes')
    parser.add_argument('--once', action='store_true', help='Run the bot once and exit')
    
    return parser.parse_args()

def main():
    """
    Main entry point for the run script.
    """
    # Parse arguments
    args = parse_args()
    
    # Prepare sys.argv for the main entry point
    sys.argv = [sys.argv[0]]  # Clear existing arguments
    
    if args.dashboard_only:
        sys.argv.append('dashboard')
    elif args.bot_only:
        sys.argv.append('bot')
        sys.argv.append('--interval')
        sys.argv.append(str(args.interval))
        if args.once:
            sys.argv.append('--once')
    else:
        # Default: run both
        sys.argv.append('both')
        sys.argv.append('--interval')
        sys.argv.append(str(args.interval))
    
    # Call the main entry point
    main_entry()

if __name__ == '__main__':
    main()
