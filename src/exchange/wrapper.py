"""
Exchange wrapper module for the crypto trading bot.
Provides a unified interface for interacting with different exchanges.
"""

import datetime
import time
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

import ccxt
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from src.config import settings
from src.utils.logging import logger
from src.utils.metrics import measure_latency, update_current_price, record_api_error


class ExchangeError(Exception):
    """Base class for exchange errors."""
    pass


class OrderNotFoundError(ExchangeError):
    """Raised when an order is not found."""
    pass


class InsufficientFundsError(ExchangeError):
    """Raised when there are insufficient funds."""
    pass


class RateLimitExceededError(ExchangeError):
    """Raised when the rate limit is exceeded."""
    pass


class ExchangeNotAvailableError(ExchangeError):
    """Raised when the exchange is not available."""
    pass


class AuthenticationError(ExchangeError):
    """Raised when authentication fails."""
    pass


class CircuitBreaker:
    """Circuit breaker for API calls."""

    def __init__(self, failure_threshold: int = 5, recovery_time: int = 60):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit.
            recovery_time: Time in seconds to wait before trying again.
        """
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def __call__(self, func: Callable) -> Callable:
        """
        Circuit breaker decorator.

        Args:
            func: The function to wrap.

        Returns:
            The wrapped function.
        """
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                # Check if recovery time has elapsed
                if time.time() - self.last_failure_time > self.recovery_time:
                    self.state = "HALF-OPEN"
                    logger.info("Circuit breaker state changed to HALF-OPEN")
                else:
                    raise ExchangeNotAvailableError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                
                # Reset failure count on success if in HALF-OPEN state
                if self.state == "HALF-OPEN":
                    self.failure_count = 0
                    self.state = "CLOSED"
                    logger.info("Circuit breaker state changed to CLOSED")
                
                return result
            
            except Exception as e:
                # Increment failure count
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # Open circuit if failure threshold is reached
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.warning(f"Circuit breaker state changed to OPEN after {self.failure_count} failures")
                
                raise e
        
        return wrapper


class ExchangeWrapper:
    """Wrapper for CCXT exchange."""

    def __init__(self, exchange_name: str = "binance"):
        """
        Initialize the exchange wrapper.

        Args:
            exchange_name: The name of the exchange.
        """
        self.exchange_name = exchange_name
        self.exchange = self._initialize_exchange()
        self.circuit_breaker = CircuitBreaker()

    def _initialize_exchange(self):
        """
        Initialize the exchange interface.

        Returns:
            Either a CCXT exchange instance or a MockExchange instance for paper trading.
        """
        # Check if we're in paper trading mode
        if settings.trading.paper_trading:
            logger.info(f"Initializing mock exchange for {self.exchange_name} in paper trading mode")
            # Import mock exchange here to avoid circular imports
            from src.exchange.mock_exchange import MockExchange
            
            # Create mock exchange that simulates the real exchange
            exchange = MockExchange(exchange_name=self.exchange_name)
            logger.info(f"Connected to mock exchange for {self.exchange_name} in paper trading mode")
            return exchange
        
        # Real trading mode
        if self.exchange_name not in settings.exchange.api_keys:
            raise ValueError(f"Exchange {self.exchange_name} not found in config.")

        if not settings.exchange.validate_api_keys(self.exchange_name):
            logger.warning(f"API keys for {self.exchange_name} are not set.")

        exchange_class = getattr(ccxt, self.exchange_name)
        creds = settings.exchange.api_keys[self.exchange_name]

        exchange = exchange_class({
            "apiKey": creds["apiKey"],
            "secret": creds["secret"],
            "enableRateLimit": True,
            "options": {
                "adjustForTimeDifference": True,
                "recvWindow": 60000,  # Increased timeout for requests
            },
            "timeout": 30000,  # 30 seconds timeout
        })

        # Load markets
        try:
            exchange.load_markets()
            logger.info(f"Connected to {self.exchange_name} exchange")
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error for {self.exchange_name} exchange: {e}")
            raise AuthenticationError(str(e))
        except ccxt.ExchangeNotAvailable as e:
            logger.error(f"Exchange {self.exchange_name} not available: {e}")
            raise ExchangeNotAvailableError(str(e))
        except ccxt.RequestTimeout as e:
            logger.error(f"Request timeout for {self.exchange_name} exchange: {e}")
            raise ExchangeNotAvailableError(str(e))
        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange_name} exchange: {e}")
            raise

        return exchange

    @measure_latency(exchange="binance", endpoint="fetch_balance")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout)),
    )
    def fetch_balance(self) -> Dict[str, Dict[str, float]]:
        """
        Fetch account balance.

        Returns:
            A dictionary of balances.
        """
        try:
            # Skip circuit breaker for mock exchange in paper trading mode
            if settings.trading.paper_trading:
                return self.exchange.fetch_balance()
            else:
                return self.circuit_breaker(self.exchange.fetch_balance)()
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "insufficient_funds")
            raise InsufficientFundsError(str(e))
        except ccxt.RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "rate_limit_exceeded")
            raise RateLimitExceededError(str(e))
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "authentication_error")
            raise AuthenticationError(str(e))
        except (ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as e:
            logger.error(f"Exchange not available: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "exchange_not_available")
            raise ExchangeNotAvailableError(str(e))
        except RetryError as e:
            logger.error(f"Retry error: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "retry_error")
            raise ExchangeNotAvailableError(f"Failed after multiple retries: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            record_api_error(self.exchange_name, "fetch_balance", "unknown_error")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_ticker")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout)),
    )
    def fetch_market_price(self, symbol: str) -> float:
        """
        Fetch the current market price.

        Args:
            symbol: The trading symbol.

        Returns:
            The current market price.
        """
        try:
            # Skip circuit breaker for mock exchange in paper trading mode
            if settings.trading.paper_trading:
                ticker = self.exchange.fetch_ticker(symbol)
            else:
                ticker = self.circuit_breaker(self.exchange.fetch_ticker)(symbol)
            price = ticker["last"]
            update_current_price(self.exchange_name, symbol, price)
            return price
        except ccxt.RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded: {e}")
            record_api_error(self.exchange_name, "fetch_ticker", "rate_limit_exceeded")
            raise RateLimitExceededError(str(e))
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            record_api_error(self.exchange_name, "fetch_ticker", "authentication_error")
            raise AuthenticationError(str(e))
        except (ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as e:
            logger.error(f"Exchange not available: {e}")
            record_api_error(self.exchange_name, "fetch_ticker", "exchange_not_available")
            raise ExchangeNotAvailableError(str(e))
        except RetryError as e:
            logger.error(f"Retry error: {e}")
            record_api_error(self.exchange_name, "fetch_ticker", "retry_error")
            raise ExchangeNotAvailableError(f"Failed after multiple retries: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch market price for {symbol}: {e}")
            record_api_error(self.exchange_name, "fetch_ticker", "unknown_error")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_ohlcv")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> List[List[float]]:
        """
        Fetch OHLCV data.

        Args:
            symbol: The trading symbol.
            timeframe: The timeframe.
            limit: The number of candles to fetch.

        Returns:
            A list of OHLCV candles.
        """
        try:
            # Skip circuit breaker for mock exchange in paper trading mode
            return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data for {symbol}: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="create_order")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def place_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            symbol: The trading symbol.
            side: The order side (buy/sell).
            amount: The order amount.
            price: The order price.

        Returns:
            The order details.
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="limit",
                side=side,
                amount=amount,
                price=price,
            )
            logger.info(
                f"Placed {side} limit order for {amount} {symbol} at {price}"
            )
            return order
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            raise InsufficientFundsError(str(e))
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="create_order")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def place_market_order(
        self, symbol: str, side: str, amount: float
    ) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            symbol: The trading symbol.
            side: The order side (buy/sell).
            amount: The order amount.

        Returns:
            The order details.
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
            )
            logger.info(f"Placed {side} market order for {amount} {symbol}")
            return order
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            raise InsufficientFundsError(str(e))
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="cancel_order")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_id: The order ID.
            symbol: The trading symbol.

        Returns:
            The cancellation details.
        """
        try:
            return self.exchange.cancel_order(order_id, symbol)
        except ccxt.OrderNotFound as e:
            logger.error(f"Order not found: {e}")
            raise OrderNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_order")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch an order.

        Args:
            order_id: The order ID.
            symbol: The trading symbol.

        Returns:
            The order details.
        """
        try:
            return self.exchange.fetch_order(order_id, symbol)
        except ccxt.OrderNotFound as e:
            logger.error(f"Order not found: {e}")
            raise OrderNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to fetch order: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_open_orders")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def fetch_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch open orders.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of open orders.
        """
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_closed_orders")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def fetch_closed_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch closed orders.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of closed orders.
        """
        try:
            return self.exchange.fetch_closed_orders(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch closed orders: {e}")
            raise

    @measure_latency(exchange="binance", endpoint="fetch_my_trades")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ccxt.NetworkError),
    )
    def fetch_my_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch my trades.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of trades.
        """
        try:
            return self.exchange.fetch_my_trades(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            raise

    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Cancel all open orders for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of cancellation details.
        """
        open_orders = self.fetch_open_orders(symbol)
        cancelled_orders = []

        for order in open_orders:
            cancelled_order = self.cancel_order(order["id"], symbol)
            cancelled_orders.append(cancelled_order)

        return cancelled_orders
