"""
Steampunk Holdings integration module.
Provides functionality to integrate with steampunk.holdings platform.
"""

import os
import json
import time
import hmac
import hashlib
import uuid
import requests
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import pandas as pd
from loguru import logger

from src.config import config
from src.utils.service_monitor_adapter import report_service_failure, report_service_recovery


class SteampunkHoldingsAPI:
    """
    API client for steampunk.holdings platform.
    Handles authentication, data synchronization, and reporting.
    """
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = "https://api.steampunk.holdings/v1"
    ):
        """
        Initialize the Steampunk Holdings API client.
        
        Args:
            api_key: API key for steampunk.holdings
            api_secret: API secret for steampunk.holdings
            base_url: Base URL for the API
        """
        self.api_key = api_key or os.environ.get("STEAMPUNK_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("STEAMPUNK_API_SECRET", "")
        self.base_url = base_url
        self.session = requests.Session()
        
        # Add common headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Crypto-Trading-Bot/1.0"
        })
        
        logger.info("Initialized Steampunk Holdings API client")
    
    def _generate_signature(self, timestamp: int, method: str, endpoint: str, data: Dict = None) -> str:
        """
        Generate HMAC signature for API authentication.
        
        Args:
            timestamp: Current timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /trades)
            data: Request data for POST/PUT requests
            
        Returns:
            str: HMAC signature
        """
        if data is None:
            data = {}
        
        # Create signature payload
        payload = f"{timestamp}{method}{endpoint}"
        
        # Add sorted data to payload for POST/PUT requests
        if method in ["POST", "PUT"] and data:
            payload += json.dumps(data, sort_keys=True)
        
        # Generate HMAC signature
        signature = hmac.new(
            self.api_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict:
        """
        Make an authenticated request to the API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /trades)
            params: Query parameters for GET requests
            data: Request data for POST/PUT requests
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (will be exponentially increased)
            
        Returns:
            Dict: API response
        """
        if params is None:
            params = {}
        if data is None:
            data = {}
        
        # Generate timestamp and signature
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp, method, endpoint, data)
        
        # Add authentication headers
        headers = {
            "SH-API-KEY": self.api_key,
            "SH-API-TIMESTAMP": str(timestamp),
            "SH-API-SIGNATURE": signature
        }
        
        # Make the request with retry logic
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=30
                )
                
                # Check for errors
                response.raise_for_status()
                
                # Parse JSON response
                result = response.json()
                
                # Report service recovery
                report_service_recovery("steampunk.holdings")
                
                return result
                
            except requests.exceptions.ConnectionError as e:
                # Connection errors are often temporary
                logger.warning(f"Connection error on attempt {attempt+1}/{max_retries}: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts: {e}")
                    error_msg = f"Connection error: {str(e)}"
                    report_service_failure("steampunk.holdings", error_msg)
                    return {"error": error_msg}
                    
            except requests.exceptions.HTTPError as e:
                # Server errors (5xx) might be temporary, client errors (4xx) are not
                if 500 <= response.status_code < 600 and attempt < max_retries - 1:
                    logger.warning(f"Server error {response.status_code} on attempt {attempt+1}/{max_retries}: {e}")
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"HTTP error {response.status_code}: {e}")
                    error_msg = f"HTTP error {response.status_code}: {str(e)}"
                    report_service_failure("steampunk.holdings", error_msg)
                    return {"error": error_msg}
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout on attempt {attempt+1}/{max_retries}: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Request timed out after {max_retries} attempts: {e}")
                    error_msg = f"Timeout error: {str(e)}"
                    report_service_failure("steampunk.holdings", error_msg)
                    return {"error": error_msg}
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_msg = f"Unexpected error: {str(e)}"
                report_service_failure("steampunk.holdings", error_msg)
                return {"error": error_msg}
    
    def get_account_info(self) -> Dict:
        """
        Get account information from steampunk.holdings.
        
        Returns:
            Dict: Account information
        """
        return self._request("GET", "/account")
    
    def sync_trades(self, trades: List[Dict]) -> Dict:
        """
        Sync trades with steampunk.holdings platform.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dict: Sync result
        """
        return self._request("POST", "/trades/sync", data={"trades": trades})
    
    def sync_portfolio(self, portfolio: Dict) -> Dict:
        """
        Sync portfolio data with steampunk.holdings platform.
        
        Args:
            portfolio: Portfolio data dictionary
            
        Returns:
            Dict: Sync result
        """
        return self._request("POST", "/portfolio/sync", data=portfolio)
    
    def get_market_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[Dict]:
        """
        Get market data from steampunk.holdings platform.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to retrieve
            
        Returns:
            List[Dict]: Market data
        """
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit
        }
        
        response = self._request("GET", "/market-data", params=params)
        return response.get("data", [])
    
    def get_sentiment_data(self, symbol: str) -> Dict:
        """
        Get sentiment data from steampunk.holdings platform.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict: Sentiment data
        """
        params = {"symbol": symbol}
        return self._request("GET", "/sentiment", params=params)
    
    def report_error(self, error_type: str, error_message: str, metadata: Dict = None) -> Dict:
        """
        Report an error to steampunk.holdings platform.
        
        Args:
            error_type: Type of error
            error_message: Error message
            metadata: Additional metadata
            
        Returns:
            Dict: Report result
        """
        if metadata is None:
            metadata = {}
        
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "metadata": metadata,
            "timestamp": int(time.time() * 1000)
        }
        
        return self._request("POST", "/errors", data=data)


class SteampunkHoldingsIntegration:
    """
    Integration with steampunk.holdings platform.
    Handles data synchronization, reporting, and other integration tasks.
    """
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        sync_interval: int = 3600  # 1 hour by default
    ):
        """
        Initialize the Steampunk Holdings integration.
        
        Args:
            api_key: API key for steampunk.holdings
            api_secret: API secret for steampunk.holdings
            sync_interval: Interval between data syncs in seconds
        """
        self.api = SteampunkHoldingsAPI(api_key, api_secret)
        self.sync_interval = sync_interval
        self.last_sync_time = 0
        self.enabled = bool(api_key and api_secret)
        
        if self.enabled:
            logger.info("Steampunk Holdings integration enabled")
        else:
            logger.warning("Steampunk Holdings integration disabled (missing API credentials)")
    
    def sync_trades(self, trades: List[Dict]) -> bool:
        """
        Sync trades with steampunk.holdings platform.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            result = self.api.sync_trades(trades)
            if "error" in result:
                logger.error(f"Failed to sync trades: {result['error']}")
                self._store_trades_locally(trades)
                return False
            
            logger.info(f"Successfully synced {len(trades)} trades with steampunk.holdings")
            return True
        except Exception as e:
            logger.error(f"Error syncing trades: {e}")
            self._store_trades_locally(trades)
            return False
    
    def _store_trades_locally(self, trades: List[Dict]) -> None:
        """
        Store trades locally for later synchronization.
        
        Args:
            trades: List of trade dictionaries
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs("data/pending_sync", exist_ok=True)
            
            # Generate a unique filename
            filename = f"data/pending_sync/trades_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
            
            # Write trades to file
            with open(filename, "w") as f:
                json.dump(trades, f)
            
            logger.info(f"Stored {len(trades)} trades locally for later synchronization: {filename}")
        except Exception as e:
            logger.error(f"Failed to store trades locally: {e}")
    
    def sync_portfolio(self, portfolio_data: Dict) -> bool:
        """
        Sync portfolio data with steampunk.holdings platform.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        if not self.enabled:
            return False
        
        # Check if it's time to sync
        current_time = time.time()
        if current_time - self.last_sync_time < self.sync_interval:
            return True  # Skip sync if not enough time has passed
        
        try:
            result = self.api.sync_portfolio(portfolio_data)
            if "error" in result:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to sync portfolio: {error_msg}")
                report_service_failure("steampunk.holdings", f"Portfolio sync failed: {error_msg}")
                self._store_portfolio_locally(portfolio_data)
                return False
                
            # Report service recovery on success
            report_service_recovery("steampunk.holdings")
            
            self.last_sync_time = current_time
            logger.info("Successfully synced portfolio with steampunk.holdings")
            return True
        except Exception as e:
            logger.error(f"Error syncing portfolio: {e}")
            self._store_portfolio_locally(portfolio_data)
            return False
    
    def _store_portfolio_locally(self, portfolio: Dict) -> None:
        """
        Store portfolio data locally for later synchronization.
        
        Args:
            portfolio: Portfolio data dictionary
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs("data/pending_sync", exist_ok=True)
            
            # Generate a unique filename
            filename = f"data/pending_sync/portfolio_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
            
            # Write portfolio to file
            with open(filename, "w") as f:
                json.dump(portfolio, f)
            
            logger.info(f"Stored portfolio data locally for later synchronization: {filename}")
        except Exception as e:
            logger.error(f"Failed to store portfolio locally: {e}")
    
    def get_market_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
        """
        Get market data from steampunk.holdings platform.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to retrieve
            
        Returns:
            pd.DataFrame: Market data as DataFrame
        """
        if not self.enabled:
            return pd.DataFrame()
        
        try:
            data = self.api.get_market_data(symbol, timeframe, limit)
            
            if not data:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    def report_error(self, error_type: str, error_message: str, metadata: Dict = None) -> bool:
        """
        Report an error to steampunk.holdings platform.
        
        Args:
            error_type: Type of error
            error_message: Error message
            metadata: Additional metadata
            
        Returns:
            bool: True if report was successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            result = self.api.report_error(error_type, error_message, metadata)
            if "error" in result:
                logger.error(f"Failed to report error: {result['error']}")
                return False
            
            logger.info(f"Successfully reported error to steampunk.holdings: {error_type}")
            return True
        except Exception as e:
            logger.error(f"Error reporting error: {e}")
            return False
    
    def sync_pending_data(self) -> bool:
        """
        Sync pending data that was stored locally.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Check if pending_sync directory exists
            if not os.path.exists("data/pending_sync"):
                return True
            
            # Get all pending files
            pending_files = os.listdir("data/pending_sync")
            
            if not pending_files:
                return True
            
            logger.info(f"Found {len(pending_files)} pending files to sync")
            
            success_count = 0
            
            # Process each file
            for filename in pending_files:
                file_path = f"data/pending_sync/{filename}"
                
                try:
                    # Read file
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    # Sync data based on file type
                    if filename.startswith("trades_"):
                        result = self.api.sync_trades(data)
                    elif filename.startswith("portfolio_"):
                        result = self.api.sync_portfolio(data)
                    else:
                        logger.warning(f"Unknown file type: {filename}")
                        continue
                    
                    # Check result
                    if "error" in result:
                        logger.error(f"Failed to sync {filename}: {result['error']}")
                        continue
                    
                    # Delete file if sync was successful
                    os.remove(file_path)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}")
            
            logger.info(f"Successfully synced {success_count}/{len(pending_files)} pending files")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error syncing pending data: {e}")
            return False


# Create a singleton instance
steampunk_integration = SteampunkHoldingsIntegration(
    api_key=os.environ.get("STEAMPUNK_API_KEY", ""),
    api_secret=os.environ.get("STEAMPUNK_API_SECRET", "")
)
