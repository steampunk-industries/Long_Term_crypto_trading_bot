"""
Logging module for the crypto trading bot.
Provides a configured logger for the application with support for CloudWatch.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import boto3

from pythonjsonlogger import jsonlogger

from src.config import settings


def setup_logger(name: str = "crypto_bot") -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: The name of the logger.

    Returns:
        A configured logger instance.
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.logging.level))
    logger.propagate = False

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Create formatter
    json_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Create file handler
    log_file = Path(settings.logging.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Add CloudWatch handler if enabled
    log_to_cloudwatch = os.environ.get("LOG_TO_CLOUDWATCH", "false").lower() == "true"
    if log_to_cloudwatch:
        try:
            # Import watchtower only if CloudWatch logging is enabled
            import watchtower
            
            # Get AWS region from environment or use default
            aws_region = os.environ.get("AWS_REGION", "us-east-1")
            
            # Create CloudWatch handler
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group=f"/crypto-trading-bot/{name}",
                stream_name=f"{name}-{os.environ.get('ENVIRONMENT', 'dev')}",
                boto3_session=boto3.Session(region_name=aws_region),
                create_log_group=True,
            )
            cloudwatch_handler.setFormatter(json_formatter)
            logger.addHandler(cloudwatch_handler)
            
            logger.info("CloudWatch logging enabled")
        except ImportError:
            logger.warning("watchtower package not installed, CloudWatch logging disabled")
        except Exception as e:
            logger.error(f"Failed to set up CloudWatch logging: {e}")

    return logger


# Create a global logger instance
logger = setup_logger()
