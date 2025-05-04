from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
import time
from datetime import datetime
import pandas as pd
import requests
from loguru import logger

from src.config import config

class BaseExchange(ABC):
    """
    Abstract base class for all exchange implementations.
    Defines the interface that all exchange classes must implement.
    """

    def __init__(self, api_key: str = "", api_secret: str = "", paper_trading: bool = True):
        """
        Initialize the exchange with API credentials and trading mode.

        Args:
            api_key: API key for the exchange
            api_secret: API secret for the exchange
            paper_trading: Whether to use paper trading mode
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper_trading = paper_trading
        self.name = self.__class__.__name__

        # Paper trading state
        self._paper_balance: Dict[str, float] = {}
        self._paper_positions: Dict[str, Dict] = {}
        self._paper_orders: Dict[str, Dict] = {}
        self._order_id_counter = 1

        logger.info(f"Initialized {self.name} exchange with paper_trading={paper_trading}")
        
    def _init_paper_trading(self, initial_balance: Dict[str, float]):
        """
        Initialize paper trading with the specified initial balance.
        
        Args:
            initial_balance: Initial balance for paper trading (e.g., {"USDT": 10000.0})
        """
        self._paper_balance = initial_balance.copy()
        logger.info(f"Initialized paper trading with balance: {self._paper_balance}")

    def _execute_with_retry(self, func: Callable, *args, max_retries=None, retry_delay=None, **kwargs) -> Any:
        """
        Execute a function with retry logic for API calls.
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retries (defaults to config.API_MAX_RETRIES)
            retry_delay: Delay between retries in seconds (defaults to config.API_RETRY_DELAY)
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: The last exception encountered after all retries fail
        """
        # Use configuration values if not specified
        if max_retries is None:
            max_retries = config.API_MAX_RETRIES
        if retry_delay is None:
            retry_delay = config.API_RETRY_DELAY
            
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Executing {func.__name__} (attempt {attempt+1}/{max_retries})")
                result = func(*args, **kwargs)
                return result
            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(f"Connection error on attempt {attempt+1}/{max_retries}: {e}")
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"Timeout error on attempt {attempt+1}/{max_retries}: {e}")
            except requests.exceptions.HTTPError as e:
                # For HTTP errors, only retry server errors (5xx)
                if hasattr(e, 'response') and e.response and 500 <= e.response.status_code < 600:
                    last_error = e
                    logger.warning(f"Server error {e.response.status_code} on attempt {attempt+1}/{max_retries}: {e}")
                else:
                    # Don't retry client errors (4xx)
                    logger.error(f"Client error: {e}")
                    raise
            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Unexpected error: {e}")
                raise
            
            # If we got here, we need to retry
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
        
        # If we got here, all retries failed
        logger.error(f"All {max_retries} retry attempts failed")
        raise last_error or Exception(f"Failed after {max_retries} attempts")

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the exchange API.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    def get_balance(self, currency: str = "USDT") -> float:
        """
        Get the balance of a specific currency.

        Args:
            currency: Currency symbol

        Returns:
            float: Balance amount
        """
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get the current ticker information for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            Dict: Ticker information including price
        """
        pass

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to retrieve

        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        pass

    @abstractmethod
    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        Create a new order.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            order_type: Type of order ('limit', 'market')
            side: Order side ('buy', 'sell')
            amount: Order amount in base currency
            price: Order price (required for limit orders)

        Returns:
            Dict: Order information
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            symbol: Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            bool: True if cancellation is successful, False otherwise
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get information about an order.

        Args:
            order_id: ID of the order
            symbol: Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            Dict: Order information
        """
        pass

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get a list of open orders.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT'), None for all symbols

        Returns:
            List[Dict]: List of open orders
        """
        pass

    def calculate_position_size(self, current_price: float, available_balance: Optional[float] = None) -> float:
        """
        Calculate position size based on current price and available balance.

        Args:
            current_price: Current price of the asset
            available_balance: Available balance, if None, get from exchange

        Returns:
            float: Position size in base currency
        """
        if available_balance is None:
            # Get quote currency from default symbol (e.g., USDT from BTC/USDT)
            quote_currency = "USDT"
            if hasattr(self, 'default_symbol') and self.default_symbol:
                quote_currency = self.default_symbol.split('/')[1]
            
            # Get available balance
            available_balance = self.get_balance(quote_currency)

        # Calculate position size (use at most 20% of available balance)
        max_position_value = available_balance * config.MAX_POSITION_SIZE_PCT
        position_size = max_position_value / current_price

        return position_size
