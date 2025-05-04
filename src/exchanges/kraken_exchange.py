"""
Kraken Exchange implementation.
"""

import os
import time
import hmac
import base64
import hashlib
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple
import json
import requests
import uuid
from datetime import datetime
from loguru import logger

import ccxt

from src.exchanges.base_exchange import BaseExchange


class KrakenExchange(BaseExchange):
    """
    Kraken Exchange implementation for trading cryptocurrencies.
    """

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        api_secret: Optional[str] = None, 
        paper_trading: bool = False,
        initial_balance: Dict[str, float] = None
    ):
        """
        Initialize the Kraken exchange.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            paper_trading: Whether to use paper trading
            initial_balance: Initial balance for paper trading
        """
        super().__init__(
            api_key=api_key or os.environ.get("KRAKEN_API_KEY", ""),
            api_secret=api_secret or os.environ.get("KRAKEN_API_SECRET", ""),
            paper_trading=paper_trading
        )

        # Initialize ccxt exchange
        self.exchange = ccxt.kraken({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
            }
        })

        # Special symbol mappings
        self.symbol_mapping = {
            "BTC/USD": "XBT/USD",
            "BTC/USDT": "XBT/USDT",
        }

        # Special symbol reverse mappings
        self.reverse_symbol_mapping = {v: k for k, v in self.symbol_mapping.items()}

        # Initialize paper trading data structures
        if self.paper_trading:
            self._init_paper_trading(initial_balance)

        logger.info(f"Initialized Kraken exchange with paper_trading={paper_trading}")

    def _init_paper_trading(self, initial_balance: Dict[str, float] = None):
        """
        Initialize paper trading data structures.
        
        Args:
            initial_balance: Dictionary of currency to initial balance amount
        """
        # Default initial balances
        self._paper_balances = {
            "USD": 10000.0,
            "BTC": 0.0,
            "ETH": 0.0,
            "USDT": 5000.0
        }
        
        # Override with provided initial balances if any
        if initial_balance:
            for currency, amount in initial_balance.items():
                self._paper_balances[currency] = amount
                
        self._paper_orders = {}
        self._paper_trades = []
        logger.info(f"Initialized Kraken paper trading mode with balances: {self._paper_balances}")

    def _get_paper_balance(self, currency: str) -> float:
        """Get paper trading balance for a currency."""
        return self._paper_balances.get(currency, 0.0)

    def connect(self) -> bool:
        """
        Connect to the exchange and test the API.

        Returns:
            bool: Whether the connection was successful
        """
        try:
            logger.info("Connecting to Kraken API...")
            if not self.paper_trading and (not self.api_key or not self.api_secret):
                logger.warning("No API credentials provided for real trading. Using public API only.")

            # Test connection
            self.exchange.fetch_time()

            logger.info("Successfully connected to Kraken API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kraken API: {e}")
            return False

    def get_balance(self, currency: str = "USD") -> float:
        """
        Get the available balance for a currency.

        Args:
            currency: Currency code, e.g., "USD", "BTC"

        Returns:
            Available balance
        """
        if self.paper_trading:
            return self._get_paper_balance(currency)

        try:
            balances = self.exchange.fetch_balance()
            return float(balances.get('free', {}).get(currency, 0))
        except Exception as e:
            logger.error(f"Failed to get balance for {currency}: {e}")
            return 0.0

    def get_balances(self) -> Dict[str, float]:
        """
        Get all available balances.

        Returns:
            Dictionary of currency to balance
        """
        if self.paper_trading:
            return self._paper_balances.copy()

        try:
            balances = self.exchange.fetch_balance()
            return {
                currency: float(balance)
                for currency, balance in balances.get('free', {}).items()
                if float(balance) > 0
            }
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading pair symbol, e.g., "BTC/USD"

        Returns:
            Ticker information
        """
        try:
            # Map symbol if needed
            mapped_symbol = self._map_symbol(symbol)
            ticker = self.exchange.fetch_ticker(mapped_symbol)

            return {
                "symbol": symbol,
                "bid": float(ticker["bid"]),
                "ask": float(ticker["ask"]),
                "last": float(ticker["last"]),
                "high": float(ticker["high"]),
                "low": float(ticker["low"]),
                "volume": float(ticker["baseVolume"]),
                "timestamp": ticker["timestamp"] / 1000
            }
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            
            if self.paper_trading:
                # Provide simulated data in paper trading mode
                return {
                    "symbol": symbol,
                    "bid": 45000.0,
                    "ask": 45100.0,
                    "last": 45050.0,
                    "high": 46000.0,
                    "low": 44000.0,
                    "volume": 1000.0,
                    "timestamp": time.time()
                }
            return {}

    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a new order.

        Args:
            symbol: Trading pair symbol, e.g., "BTC/USD"
            order_type: Order type ("limit", "market")
            side: Order side ("buy", "sell")
            amount: Order amount in base currency
            price: Order price (required for limit orders)

        Returns:
            Order information
        """
        if self.paper_trading:
            # Create a paper order
            order_id = str(uuid.uuid4())
            ticker = self.get_ticker(symbol)
            
            # Default price for paper trading
            if not price and order_type.lower() == "limit":
                price = ticker["last"]
            elif order_type.lower() == "market":
                price = ticker["last"]
                
            # Create order object
            order = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type.lower(),
                "side": side.lower(),
                "amount": amount,
                "price": price,
                "status": "open",
                "timestamp": time.time()
            }
            
            self._paper_orders[order_id] = order
            
            # Execute the paper order immediately
            return self._execute_paper_order(order)

        try:
            # Map symbol if needed
            mapped_symbol = self._map_symbol(symbol)
            
            # Normalize parameters
            order_type = order_type.lower()
            side = side.lower()

            # Create order
            if order_type == "limit":
                if price is None:
                    raise ValueError("Price is required for limit orders")
                order = self.exchange.create_limit_order(
                    symbol=mapped_symbol,
                    side=side,
                    amount=amount,
                    price=price
                )
            elif order_type == "market":
                order = self.exchange.create_market_order(
                    symbol=mapped_symbol,
                    side=side,
                    amount=amount
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Format order information
            return {
                "id": order["id"],
                "symbol": symbol,
                "type": order_type,
                "side": side,
                "amount": float(order["amount"]),
                "price": float(order.get("price", 0)),
                "status": order["status"],
                "timestamp": order["timestamp"] / 1000 if "timestamp" in order else time.time()
            }
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {}

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            symbol: Symbol of the order (not required for Kraken, but included for consistency)

        Returns:
            Whether the cancellation was successful
        """
        if self.paper_trading:
            if order_id in self._paper_orders:
                order = self._paper_orders[order_id]
                if order["status"] == "open":
                    order["status"] = "canceled"
                    self._paper_orders[order_id] = order
                    logger.info(f"Canceled paper order: {order_id}")
                    return True
                else:
                    logger.warning(f"Cannot cancel order with status {order['status']}")
                    return False
            logger.warning(f"Order {order_id} not found")
            return False

        try:
            self.exchange.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about an order.

        Args:
            order_id: ID of the order
            symbol: Symbol of the order (not required for Kraken, but included for consistency)

        Returns:
            Order information
        """
        if self.paper_trading:
            if order_id in self._paper_orders:
                return self._paper_orders[order_id]
            logger.warning(f"Order {order_id} not found")
            return {}

        try:
            order = self.exchange.fetch_order(order_id)
            
            # Map symbol back if needed
            original_symbol = self._map_symbol_reverse(order["symbol"])
            
            return {
                "id": order["id"],
                "symbol": original_symbol,
                "type": order["type"],
                "side": order["side"],
                "amount": float(order["amount"]),
                "price": float(order.get("price", 0)),
                "status": order["status"],
                "timestamp": order["timestamp"] / 1000 if "timestamp" in order else time.time()
            }
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.

        Args:
            symbol: Trading pair symbol, e.g., "BTC/USD" (optional)

        Returns:
            List of open orders
        """
        if self.paper_trading:
            orders = [
                order for order in self._paper_orders.values()
                if order["status"] == "open"
            ]
            
            if symbol:
                orders = [order for order in orders if order["symbol"] == symbol]
                
            return orders

        try:
            mapped_symbol = None
            if symbol:
                mapped_symbol = self._map_symbol(symbol)
                
            open_orders = self.exchange.fetch_open_orders(mapped_symbol)
            
            return [
                {
                    "id": order["id"],
                    "symbol": self._map_symbol_reverse(order["symbol"]),
                    "type": order["type"],
                    "side": order["side"],
                    "amount": float(order["amount"]),
                    "price": float(order.get("price", 0)),
                    "status": order["status"],
                    "timestamp": order["timestamp"] / 1000 if "timestamp" in order else time.time()
                }
                for order in open_orders
            ]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol, e.g., "BTC/USD"
            timeframe: Timeframe interval, e.g., "1m", "5m", "1h", "1d"
            limit: Number of candles to retrieve
            since: Timestamp in milliseconds for the start of the data

        Returns:
            List of OHLCV data
        """
        try:
            # Map symbol if needed
            mapped_symbol = self._map_symbol(symbol)
            
            # Get candles from exchange
            candles = self.exchange.fetch_ohlcv(
                symbol=mapped_symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            # Format candles
            return [
                {
                    "timestamp": candle[0] / 1000,
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                }
                for candle in candles
            ]
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []

    def place_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order (alias for create_order for API consistency).
        
        Args:
            symbol: Trading pair symbol, e.g., "BTC/USD"
            order_type: Order type ("limit", "market")
            side: Order side ("buy", "sell")
            amount: Order amount in base currency
            price: Order price (required for limit orders)
            
        Returns:
            Order information
        """
        return self.create_order(symbol, order_type, side, amount, price)

    def _map_symbol(self, symbol: str) -> str:
        """
        Map a standard symbol to a Kraken-specific symbol if needed.

        Args:
            symbol: Standard symbol format (e.g., "BTC/USD")

        Returns:
            Kraken-specific symbol format (e.g., "XBT/USD")
        """
        return self.symbol_mapping.get(symbol, symbol)

    def _map_symbol_reverse(self, symbol: str) -> str:
        """
        Map a Kraken-specific symbol back to a standard symbol if needed.

        Args:
            symbol: Kraken-specific symbol format (e.g., "XBT/USD")

        Returns:
            Standard symbol format (e.g., "BTC/USD")
        """
        return self.reverse_symbol_mapping.get(symbol, symbol)

    def _execute_paper_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a paper trading order.

        Args:
            order: Order information

        Returns:
            Updated order information
        """
        # Get the symbol parts
        base_currency, quote_currency = order["symbol"].split("/")
        
        # Get the current ticker
        ticker = self.get_ticker(order["symbol"])
        
        # Set the execution price
        if order["type"] == "market":
            execution_price = ticker["last"]
        else:
            execution_price = order["price"]
            
        # Calculate the cost
        cost = order["amount"] * execution_price
        fee = cost * 0.002  # 0.2% fee
        
        # Update balances based on order side
        if order["side"] == "buy":
            # Check if enough balance
            if self._paper_balances.get(quote_currency, 0) < cost + fee:
                logger.warning(f"Insufficient {quote_currency} balance for paper order")
                order["status"] = "rejected"
                return order
                
            # Deduct quote currency
            self._paper_balances[quote_currency] = self._paper_balances.get(quote_currency, 0) - cost - fee
            
            # Add base currency
            self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) + order["amount"]
            
        elif order["side"] == "sell":
            # Check if enough balance
            if self._paper_balances.get(base_currency, 0) < order["amount"]:
                logger.warning(f"Insufficient {base_currency} balance for paper order")
                order["status"] = "rejected"
                return order
                
            # Deduct base currency
            self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) - order["amount"]
            
            # Add quote currency
            self._paper_balances[quote_currency] = self._paper_balances.get(quote_currency, 0) + cost - fee
            
        # Update order status
        order["status"] = "closed"
        order["price"] = execution_price
        order["fee"] = fee
        
        # Add to paper trades
        trade = {
            "id": str(uuid.uuid4()),
            "order_id": order["id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "amount": order["amount"],
            "price": execution_price,
            "cost": cost,
            "fee": fee,
            "timestamp": time.time()
        }
        self._paper_trades.append(trade)
        
        # Log the trade
        logger.info(f"Executed paper trade: {trade}")
        
        return order
