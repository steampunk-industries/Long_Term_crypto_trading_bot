#!/usr/bin/env python3
"""
Setup script for the Crypto Trading Bot.
Creates necessary directories and initializes the database.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import init_db
from src.config import config
from loguru import logger

def create_directories():
    """
    Create necessary directories for the application.
    """
    directories = [
        'data',
        'logs',
        'src/dashboard/static/css',
        'src/dashboard/static/js',
        'src/dashboard/static/img',
        'src/dashboard/templates',
        'src/dashboard/templates/errors',
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def initialize_database():
    """
    Initialize the database.
    """
    if config.USE_SQLITE:
        # Ensure the data directory exists
        os.makedirs('data', exist_ok=True)
    
    # Initialize the database
    success = init_db()
    
    if success:
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database")

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Setup script for the Crypto Trading Bot')
    parser.add_argument('--skip-db', action='store_true', help='Skip database initialization')
    
    return parser.parse_args()

def main():
    """
    Main entry point for the setup script.
    """
    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Parse arguments
    args = parse_args()
    
    logger.info("Starting setup...")
    
    # Create directories
    create_directories()
    
    # Initialize database
    if not args.skip_db:
        initialize_database()
    else:
        logger.info("Skipping database initialization")
    
    logger.info("Setup completed successfully")

if __name__ == '__main__':
    main()
