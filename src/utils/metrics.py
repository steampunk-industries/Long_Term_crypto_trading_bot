"""
Metrics module for the crypto trading bot.
Provides Prometheus metrics for monitoring the application.
"""

import time
from typing import Callable, Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Define metrics
ORDERS_CREATED = Counter(
    "orders_created_total", "Total number of orders created", ["exchange", "symbol", "side", "bot_type"]
)
ORDERS_FILLED = Counter(
    "orders_filled_total", "Total number of orders filled", ["exchange", "symbol", "side", "bot_type"]
)
ORDERS_CANCELLED = Counter(
    "orders_cancelled_total", "Total number of orders cancelled", ["exchange", "symbol", "side", "bot_type"]
)

BALANCE = Gauge(
    "account_balance", "Account balance", ["exchange", "currency", "bot_type"]
)
POSITION_SIZE = Gauge(
    "position_size", "Position size", ["exchange", "symbol", "bot_type"]
)
CURRENT_PRICE = Gauge(
    "current_price", "Current price", ["exchange", "symbol"]
)

API_LATENCY = Histogram(
    "api_request_latency_seconds", "API request latency in seconds", ["exchange", "endpoint"]
)
BOT_ITERATION_TIME = Histogram(
    "bot_iteration_time_seconds", "Bot iteration time in seconds", ["bot_type"]
)

# Error metrics
API_ERRORS = Counter(
    "api_errors_total", "Total number of API errors", ["exchange", "endpoint", "error_type"]
)


def start_metrics_server(port: int = 8000) -> None:
    """
    Start the Prometheus metrics server.

    Args:
        port: The port to listen on.
    """
    start_http_server(port)


def measure_latency(
    exchange: str, endpoint: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to measure API latency.

    Args:
        exchange: The exchange name.
        endpoint: The API endpoint.

    Returns:
        A decorator function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            latency = time.time() - start_time
            API_LATENCY.labels(exchange=exchange, endpoint=endpoint).observe(latency)
            return result

        return wrapper

    return decorator


def measure_bot_iteration(
    bot_type: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to measure bot iteration time.

    Args:
        bot_type: The bot type.

    Returns:
        A decorator function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            iteration_time = time.time() - start_time
            BOT_ITERATION_TIME.labels(bot_type=bot_type).observe(iteration_time)
            return result

        return wrapper

    return decorator


def record_order_created(
    exchange: str, symbol: str, side: str, bot_type: str
) -> None:
    """
    Record an order creation.

    Args:
        exchange: The exchange name.
        symbol: The trading symbol.
        side: The order side (buy/sell).
        bot_type: The bot type.
    """
    ORDERS_CREATED.labels(
        exchange=exchange, symbol=symbol, side=side, bot_type=bot_type
    ).inc()


def record_order_filled(
    exchange: str, symbol: str, side: str, bot_type: str
) -> None:
    """
    Record an order fill.

    Args:
        exchange: The exchange name.
        symbol: The trading symbol.
        side: The order side (buy/sell).
        bot_type: The bot type.
    """
    ORDERS_FILLED.labels(
        exchange=exchange, symbol=symbol, side=side, bot_type=bot_type
    ).inc()


def record_order_cancelled(
    exchange: str, symbol: str, side: str, bot_type: str
) -> None:
    """
    Record an order cancellation.

    Args:
        exchange: The exchange name.
        symbol: The trading symbol.
        side: The order side (buy/sell).
        bot_type: The bot type.
    """
    ORDERS_CANCELLED.labels(
        exchange=exchange, symbol=symbol, side=side, bot_type=bot_type
    ).inc()


def update_balance(
    exchange: str, currency: str, amount: float, bot_type: str
) -> None:
    """
    Update the account balance.

    Args:
        exchange: The exchange name.
        currency: The currency.
        amount: The balance amount.
        bot_type: The bot type.
    """
    BALANCE.labels(exchange=exchange, currency=currency, bot_type=bot_type).set(amount)


def update_position_size(
    exchange: str, symbol: str, size: float, bot_type: str
) -> None:
    """
    Update the position size.

    Args:
        exchange: The exchange name.
        symbol: The trading symbol.
        size: The position size.
        bot_type: The bot type.
    """
    POSITION_SIZE.labels(exchange=exchange, symbol=symbol, bot_type=bot_type).set(size)


def update_current_price(exchange: str, symbol: str, price: float) -> None:
    """
    Update the current price.

    Args:
        exchange: The exchange name.
        symbol: The trading symbol.
        price: The current price.
    """
    CURRENT_PRICE.labels(exchange=exchange, symbol=symbol).set(price)


def record_api_error(exchange: str, endpoint: str, error_type: str) -> None:
    """
    Record an API error.

    Args:
        exchange: The exchange name.
        endpoint: The API endpoint.
        error_type: The type of error.
    """
    API_ERRORS.labels(exchange=exchange, endpoint=endpoint, error_type=error_type).inc()
