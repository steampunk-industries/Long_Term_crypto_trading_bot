"""
Status monitor for external services.
Monitors the availability of external services and notifies when they change status.
"""

import os
import time
import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional, Callable
from loguru import logger

from src.config import config

# Create a directory for storing status files
os.makedirs('data/status', exist_ok=True)


class ServiceStatusMonitor:
    """
    Monitors the status of external services.
    Tracks when services go down or come back online.
    """

    def __init__(
        self,
        check_interval: int = None,  # Default from config
        notification_callback: Optional[Callable] = None
    ):
        """
        Initialize the service status monitor.

        Args:
            check_interval: Interval between checks in seconds
            notification_callback: Function to call when a service changes status
        """
        # Use config value if not specified
        self.check_interval = check_interval or config.SERVICE_CHECK_INTERVAL
        self.notification_callback = notification_callback
        self.services = {}
        self.running = False
        self.monitor_thread = None
        self.last_status = {}

        # Load previous status if available
        self._load_status()

    def add_service(
        self,
        name: str,
        url: str,
        headers: Dict = None,
        timeout: int = 10,
        success_codes: List[int] = None
    ):
        """
        Add a service to monitor.

        Args:
            name: Name of the service
            url: URL to check for availability
            headers: Request headers
            timeout: Request timeout in seconds
            success_codes: HTTP status codes that indicate success (default: [200])
        """
        if success_codes is None:
            success_codes = [200]

        if headers is None:
            headers = {}

        self.services[name] = {
            "url": url,
            "headers": headers,
            "timeout": timeout,
            "success_codes": success_codes,
            "last_check": 0,
            "status": "unknown",
            "since": datetime.now().isoformat(),
            "failure_count": 0,
            "uptime_seconds": 0
        }

        logger.info(f"Added service {name} to monitor: {url}")

    def start(self):
        """
        Start monitoring services.
        """
        if self.running:
            logger.warning("Service monitor is already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        logger.info("Service status monitor started")

    def stop(self):
        """
        Stop monitoring services.
        """
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None

        logger.info("Service status monitor stopped")

    def get_status(self, service_name: str) -> Dict:
        """
        Get the current status of a service.

        Args:
            service_name: Name of the service

        Returns:
            Dict: Service status information
        """
        if service_name not in self.services:
            return {"status": "unknown", "error": "Service not found"}

        return self.services[service_name]

    def get_all_statuses(self) -> Dict:
        """
        Get the current status of all services.

        Returns:
            Dict: Status information for all services
        """
        return self.services

    def check_service_now(self, service_name: str) -> Dict:
        """
        Check the status of a service immediately.

        Args:
            service_name: Name of the service

        Returns:
            Dict: Service status information
        """
        if service_name not in self.services:
            return {"status": "unknown", "error": "Service not found"}

        service = self.services[service_name]
        return self._check_service(service_name, service)

    def report_service_failure(self, service_name: str, error_message: str, details: Dict = None) -> None:
        """
        Report a service failure.

        Args:
            service_name: Name of the service that failed
            error_message: Error message
            details: Additional details about the failure
        """
        if service_name not in self.services:
            # Add the service if it doesn't exist
            self.add_service(name=service_name, url=f"https://{service_name}")

        service = self.services[service_name]
        
        # Update failure count if status was up or unknown
        if service["status"] != "down":
            service["failure_count"] = 1
        else:
            service["failure_count"] += 1
            
        service["status"] = "down"
        service["last_error"] = error_message
        service["last_check"] = time.time()
        service["since"] = datetime.now().isoformat()
        
        # Reset uptime when a service goes down
        service["uptime_seconds"] = 0

        if details:
            service["details"] = details

        # Save status
        self._save_status()

        # Notify if failure count reaches threshold
        if service["failure_count"] >= config.ALERT_THRESHOLD:
            self._notify_status_change(service_name, "down", service["since"], 
                                      f"Service has failed {service['failure_count']} times in a row")

        logger.warning(f"Service {service_name} reported failure: {error_message}")

    def report_service_recovery(self, service_name: str) -> None:
        """
        Report a service recovery.

        Args:
            service_name: Name of the service that recovered
        """
        if service_name not in self.services:
            return

        service = self.services[service_name]

        # Only update if previously down
        if service["status"] == "down":
            service["status"] = "up"
            service["last_check"] = time.time()
            service["since"] = datetime.now().isoformat()
            service.pop("last_error", None)
            service["failure_count"] = 0
            
            # Start tracking uptime
            service["uptime_seconds"] = 0

            # Save status
            self._save_status()

            # Notify
            self._notify_status_change(service_name, "up", service["since"])

            logger.info(f"Service {service_name} recovered")

    def log_service_metrics(self):
        """Log service metrics for monitoring."""
        services = self.services
        
        for service_name, service in services.items():
            status = service.get('status', 'unknown')
            uptime = service.get('uptime_seconds', 0)
            failure_count = service.get('failure_count', 0)
            
            # Log in a format that can be easily parsed by monitoring tools
            logger.info(f"SERVICE_METRIC|{service_name}|status={status}|uptime={uptime}|failures={failure_count}")
            
            # Alert on persistent failures
            if status == 'down' and failure_count >= config.ALERT_THRESHOLD:
                logger.error(f"SERVICE_ALERT|{service_name}|Persistent failures detected: {failure_count}")

    def _monitor_loop(self):
        """
        Monitor loop that periodically checks the status of all services.
        """
        try:
            while self.running:
                # Check all services
                for service_name, service in list(self.services.items()):
                    try:
                        self._check_service(service_name, service)
                    except Exception as e:
                        logger.error(f"Error checking service {service_name}: {e}")
                
                # Log service metrics
                self.log_service_metrics()
                
                # Sleep until the next check
                time.sleep(self.check_interval)
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            self.running = False

    def _check_service(self, service_name: str, service: Dict) -> Dict:
        """
        Check if a service is available.

        Args:
            service_name: Name of the service
            service: Service configuration

        Returns:
            Dict: Updated service status
        """
        url = service["url"]
        headers = service["headers"]
        timeout = service["timeout"]
        success_codes = service["success_codes"]

        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            status_code = response.status_code

            # Update service status
            service["last_check"] = time.time()

            if status_code in success_codes:
                # Service is up
                if service["status"] != "up":
                    # Service was down, now it's up
                    service["status"] = "up"
                    service["since"] = datetime.now().isoformat()
                    service["failure_count"] = 0
                    service["uptime_seconds"] = 0
                    service.pop("last_error", None)

                    # Notify
                    self._notify_status_change(service_name, "up", service["since"])

                    logger.info(f"Service {service_name} is up")
                else:
                    # Service was already up, update uptime
                    service["uptime_seconds"] += self.check_interval
            else:
                # Service is down
                if service["status"] != "down":
                    # Service was up, now it's down
                    service["status"] = "down"
                    service["since"] = datetime.now().isoformat()
                    service["last_error"] = f"HTTP status code: {status_code}"
                    service["failure_count"] = 1
                    service["uptime_seconds"] = 0

                    # Notify
                    self._notify_status_change(service_name, "down", service["since"])

                    logger.warning(f"Service {service_name} is down: HTTP {status_code}")
                else:
                    # Service was already down, increment failure count
                    service["failure_count"] += 1
                    service["last_error"] = f"HTTP status code: {status_code}"
                    
                    # Alert if failure count reaches threshold
                    if service["failure_count"] == config.ALERT_THRESHOLD:
                        self._notify_status_change(service_name, "down", service["since"],
                                                 f"Service has failed {service['failure_count']} times in a row")
                        
                    logger.warning(f"Service {service_name} is still down: HTTP {status_code}")
        except requests.exceptions.RequestException as e:
            # Service is down
            service["last_check"] = time.time()

            if service["status"] != "down":
                # Service was up, now it's down
                service["status"] = "down"
                service["since"] = datetime.now().isoformat()
                service["last_error"] = str(e)
                service["failure_count"] = 1
                service["uptime_seconds"] = 0

                # Notify
                self._notify_status_change(service_name, "down", service["since"])

                logger.warning(f"Service {service_name} is down: {e}")
            else:
                # Service was already down, increment failure count
                service["failure_count"] += 1
                service["last_error"] = str(e)
                
                # Alert if failure count reaches threshold
                if service["failure_count"] == config.ALERT_THRESHOLD:
                    self._notify_status_change(service_name, "down", service["since"],
                                             f"Service has failed {service['failure_count']} times in a row")
                    
                logger.warning(f"Service {service_name} is still down: {e}")

        # Save status
        self._save_status()

        return service

    def _notify_status_change(self, service_name: str, status: str, since: str, message: str = None):
        """
        Notify when a service changes status.

        Args:
            service_name: Name of the service
            status: New status ('up' or 'down')
            since: Timestamp when the status changed
            message: Additional message
        """
        if self.notification_callback:
            self.notification_callback(service_name, status, since, message)

    def _save_status(self):
        """
        Save the current status to file.
        """
        try:
            status_file = "data/status/services.json"
            with open(status_file, "w") as f:
                import json
                json.dump(self.services, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving status: {e}")

    def _load_status(self):
        """
        Load the previous status from file.
        """
        try:
            status_file = "data/status/services.json"
            if os.path.exists(status_file):
                with open(status_file, "r") as f:
                    import json
                    self.services = json.load(f)
                logger.info(f"Loaded status for {len(self.services)} services")
        except Exception as e:
            logger.error(f"Error loading status: {e}")


# Global instance
_status_monitor = ServiceStatusMonitor()

def start_monitoring():
    """
    Start monitoring services.
    """
    _status_monitor.start()

def stop_monitoring():
    """
    Stop monitoring services.
    """
    _status_monitor.stop()

def add_service(name: str, url: str, headers: Dict = None, timeout: int = 10):
    """
    Add a service to monitor.
    """
    _status_monitor.add_service(name, url, headers, timeout)

def report_service_failure(service_name: str, error_message: str):
    """
    Report a service failure.
    """
    _status_monitor.report_service_failure(service_name, error_message)

def report_service_recovery(service_name: str):
    """
    Report a service recovery.
    """
    _status_monitor.report_service_recovery(service_name)

def get_service_status(service_name: str = None):
    """
    Get the current status of a service or all services.
    """
    if service_name:
        return _status_monitor.get_status(service_name)
    else:
        return _status_monitor.get_all_statuses()

# Start monitoring by default
start_monitoring()

# Export the status monitor instance with the name used in imports
service_monitor = _status_monitor
