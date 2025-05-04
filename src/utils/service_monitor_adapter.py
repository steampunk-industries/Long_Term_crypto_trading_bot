"""
Service monitor adapter for reporting service failures and recoveries.
"""

from loguru import logger
from typing import Dict, Optional, Any
import time

# Import conditionally to handle circular imports
try:
    from src.utils.status_monitor import service_monitor
    HAS_SERVICE_MONITOR = True
except ImportError:
    HAS_SERVICE_MONITOR = False
    logger.warning("Could not import service_monitor, status reporting will be disabled")

def report_service_failure(service_name: str, error_message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Report a service failure to the status monitor.
    
    Args:
        service_name: Name of the service that failed
        error_message: Error message
        details: Additional details about the failure
    """
    if not HAS_SERVICE_MONITOR:
        logger.warning(f"Service failure: {service_name} - {error_message}")
        return
    
    try:
        service_monitor.report_service_failure(service_name, error_message, details)
    except Exception as e:
        logger.error(f"Failed to report service failure to status monitor: {e}")

def report_service_recovery(service_name: str) -> None:
    """
    Report a service recovery to the status monitor.
    
    Args:
        service_name: Name of the service that recovered
    """
    if not HAS_SERVICE_MONITOR:
        logger.info(f"Service recovery: {service_name}")
        return
    
    try:
        service_monitor.report_service_recovery(service_name)
    except Exception as e:
        logger.error(f"Failed to report service recovery to status monitor: {e}")
