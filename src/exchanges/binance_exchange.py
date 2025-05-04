import os
import time
from typing import Dict, List, Optional, Tuple, Any
import uuid
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.config import config

class BinanceExchange(BaseExchange):
    """
    Binance Exchange implementation for trading cryptocurrencies.
    Supports both real trading and paper trading.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None
    ):
        """
        Initialize the Binance exchange.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            paper_trading: Whether to use paper trading mode
            initial_balance: Initial balance for paper trading
        """
        super().__init__(api_key, api_secret, paper_trading)
        self.base_url = "https://api.binance.com"
        self.api_version = "v3"
        self.default_symbol = "BTC/USDT"

        # Initialize paper trading if enabled
        if paper_trading:
            self._init_paper_trading(initial_balance)

    def _init_paper_trading(self, initial_balance: Dict[str, float] = None):
        """
        Initialize paper trading with optional initial balances.
        
        Args:
            initial_balance: Dictionary of currency to initial balance amount
        """
        # Default initial balances
        self._paper_balances = {
            "USDT": 10000.0,
            "BTC": 0.0,
            "ETH": 0.0,
            "BNB": 0.0
        }
        
        # Override with provided initial balances if any
        if initial_balance:
            for currency, amount in initial_balance.items():
                self._paper_balances[currency] = amount
                
        logger.info(f"Initialized Binance paper trading with balances: {self._paper_balances}")
        
        # Initialize other paper trading structures
        self._paper_orders = {}
        self._paper_trades = []

    def connect(self) -> bool:
        """
        Test connection to the exchange.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if self.paper_trading:
                logger.info("Connected to Binance exchange (paper trading mode)")
                return True

            # Test connection by getting server time
            response = requests.get(f"{self.base_url}/api/{self.api_version}/time")
            response.raise_for_status()
            server_time = response.json()["serverTime"]
            logger.info(f"Connected to Binance exchange, server time: {server_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Binance exchange: {e}")
            return False

    def get_balance(self, currency: str = "USDT") -> float:
        """
        Get the available balance for a currency.

        Args:
            currency: Currency code (e.g., "BTC", "USDT")

        Returns:
            Available balance
        """
        if self.paper_trading:
            return self._paper_balances.get(currency, 0.0)

        try:
            # Prepare request parameters
            timestamp = int(time.time() * 1000)
            params = {
                "timestamp": timestamp
            }
            params["signature"] = self._generate_signature(params)

            # Make request to get account info
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/account",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            account_info = response.json()

            # Find the balance for the requested currency
            for balance in account_info["balances"]:
                if balance["asset"] == currency:
                    return float(balance["free"])

            return 0.0
        except Exception as e:
            logger.error(f"Failed to get {currency} balance: {e}")
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
            # Prepare request parameters
            timestamp = int(time.time() * 1000)
            params = {
                "timestamp": timestamp
            }
            params["signature"] = self._generate_signature(params)

            # Make request to get account info
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/account",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            account_info = response.json()

            # Extract balances
            balances = {}
            for balance in account_info["balances"]:
                free_amount = float(balance["free"])
                if free_amount > 0:
                    balances[balance["asset"]] = free_amount

            return balances
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            Ticker information
        """
        try:
            # Format symbol for Binance API (BTC/USDT -> BTCUSDT)
            formatted_symbol = self._format_symbol(symbol)

            # Make request to get ticker info
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/ticker/24hr",
                params={"symbol": formatted_symbol}
            )
            response.raise_for_status()
            ticker = response.json()

            return {
                "symbol": symbol,
                "bid": float(ticker["bidPrice"]),
                "ask": float(ticker["askPrice"]),
                "last": float(ticker["lastPrice"]),
                "high": float(ticker["highPrice"]),
                "low": float(ticker["lowPrice"]),
                "volume": float(ticker["volume"]),
                "timestamp": int(ticker["closeTime"]) / 1000
            }
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            
            if self.paper_trading:
                # Return simulated ticker in paper trading mode
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
    ) -> Dict:
        """
        Create a new order.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            order_type: Order type ("LIMIT" or "MARKET")
            side: Order side ("BUY" or "SELL")
            amount: Order amount in base currency
            price: Order price (required for LIMIT orders)

        Returns:
            Dictionary with order information
        """
        if self.paper_trading:
            # Create a paper order
            order_id = str(uuid.uuid4())
            ticker = self.get_ticker(symbol)
            
            # Default price for paper trading
            if not price and order_type.upper() == "LIMIT":
                price = ticker["last"]
            elif order_type.upper() == "MARKET":
                price = ticker["last"]
                
            # Create order object
            order = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type.upper(),
                "side": side.upper(),
                "amount": amount,
                "price": price,
                "status": "open",
                "timestamp": time.time()
            }
            
            self._paper_orders[order_id] = order
            
            # Execute the paper order immediately
            return self._execute_paper_order(order)
            
        try:
            # Format the parameters for the API
            formatted_symbol = self._format_symbol(symbol)
            uppercased_order_type = order_type.upper()
            uppercased_side = side.upper()

            # Prepare request parameters
            params = {
                "symbol": formatted_symbol,
                "side": uppercased_side,
                "type": uppercased_order_type,
                "quantity": self._format_quantity(symbol, amount)
            }

            # Add price for LIMIT orders
            if uppercased_order_type == "LIMIT":
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                params["price"] = self._format_price(symbol, price)
                params["timeInForce"] = "GTC"  # Good Till Cancelled

            # Add timestamp and signature
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

            # Make request to create order
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/order",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            order = response.json()

            # Format response
            return {
                "id": order["orderId"],
                "symbol": symbol,
                "type": order["type"],
                "side": order["side"],
                "amount": float(order["origQty"]),
                "executed": float(order.get("executedQty", 0)),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": order["transactTime"] / 1000
            }
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {}

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            True if cancellation is successful, False otherwise
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
            # Format symbol for Binance API
            formatted_symbol = self._format_symbol(symbol)

            # Prepare request parameters
            params = {
                "symbol": formatted_symbol,
                "orderId": order_id,
                "timestamp": int(time.time() * 1000)
            }
            params["signature"] = self._generate_signature(params)

            # Make request to cancel order
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.delete(
                f"{self.base_url}/api/{self.api_version}/order",
                headers=headers,
                params=params
            )
            response.raise_for_status()

            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get information about an order.

        Args:
            order_id: ID of the order
            symbol: Trading pair symbol (e.g., "BTC/USDT")

        Returns:
            Dictionary with order information
        """
        if self.paper_trading:
            if order_id in self._paper_orders:
                return self._paper_orders[order_id]
            logger.warning(f"Order {order_id} not found")
            return {}

        try:
            # Format symbol for Binance API
            formatted_symbol = self._format_symbol(symbol)

            # Prepare request parameters
            params = {
                "symbol": formatted_symbol,
                "orderId": order_id,
                "timestamp": int(time.time() * 1000)
            }
            params["signature"] = self._generate_signature(params)

            # Make request to get order info
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/order",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            order = response.json()

            # Format response
            return {
                "id": order["orderId"],
                "symbol": symbol,
                "type": order["type"],
                "side": order["side"],
                "amount": float(order["origQty"]),
                "executed": float(order["executedQty"]),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": order["time"] / 1000
            }
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT"), None for all symbols

        Returns:
            List of open orders
        """
        if self.paper_trading:
            return [
                order for order in self._paper_orders.values()
                if order["status"] == "open" and (symbol is None or order["symbol"] == symbol)
            ]

        try:
            # Prepare request parameters
            params = {
                "timestamp": int(time.time() * 1000)
            }

            # Add symbol if provided
            if symbol:
                params["symbol"] = self._format_symbol(symbol)

            # Add signature
            params["signature"] = self._generate_signature(params)

            # Make request to get open orders
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/openOrders",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            orders = response.json()

            # Format response
            return [
                {
                    "id": order["orderId"],
                    "symbol": self._format_symbol_reverse(order["symbol"]),
                    "type": order["type"],
                    "side": order["side"],
                    "amount": float(order["origQty"]),
                    "executed": float(order["executedQty"]),
                    "price": float(order.get("price", 0)),
                    "status": order["status"].lower(),
                    "timestamp": order["time"] / 1000
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    def get_historical_data(
        self,
        symbol: str = None,
        timeframe: str = "1h",
        limit: int = 100,
        since: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Number of candles to retrieve
            since: Start time in milliseconds

        Returns:
            DataFrame with OHLCV data
        """
        if symbol is None:
            symbol = self.default_symbol

        try:
            # Format symbol for Binance API
            formatted_symbol = self._format_symbol(symbol)

            # Convert timeframe to Binance interval format
            interval = self._convert_timeframe(timeframe)

            # Prepare request parameters
            params = {
                "symbol": formatted_symbol,
                "interval": interval,
                "limit": limit
            }

            # Add start time if provided
            if since:
                params["startTime"] = since

            # Make request to get klines (candlestick) data
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/klines",
                params=params
            )
            response.raise_for_status()
            klines = response.json()

            # Format response into DataFrame
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_asset_volume", "number_of_trades",
                    "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
                ]
            )

            # Convert types
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # Set timestamp as index
            df.set_index("timestamp", inplace=True)

            # Keep only the OHLCV columns
            df = df[["open", "high", "low", "close", "volume"]]

            return df
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()

    def place_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        Place an order (alias for create_order for API consistency).
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            order_type: Type of order ('limit', 'market')
            side: Order side ('buy', 'sell')
            amount: Order amount in base currency
            price: Order price (required for limit orders)
            
        Returns:
            Dict: Order information
        """
        return self.create_order(symbol, order_type, side, amount, price)

    def _execute_paper_order(self, order: Dict) -> Dict:
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
        if order["type"] == "MARKET":
            execution_price = ticker["last"]
        else:
            execution_price = order["price"]
            
        # Calculate the cost
        cost = order["amount"] * execution_price
        fee = cost * 0.001  # 0.1% fee
        
        # Update balances based on order side
        if order["side"] == "BUY":
            # Check if enough balance
            if self._paper_balances.get(quote_currency, 0) < cost + fee:
                logger.warning(f"Insufficient {quote_currency} balance for paper order")
                order["status"] = "rejected"
                return order
                
            # Deduct quote currency
            self._paper_balances[quote_currency] = self._paper_balances.get(quote_currency, 0) - cost - fee
            
            # Add base currency
            self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) + order["amount"]
            
        elif order["side"] == "SELL":
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
        order["status"] = "filled"
        order["executed"] = order["amount"]
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

    def _generate_signature(self, params: Dict) -> str:
        """
        Generate signature for API request.

        Args:
            params: Request parameters

        Returns:
            Signature string
        """
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol for Binance API.

        Args:
            symbol: Symbol in format "BTC/USDT"

        Returns:
            Symbol in format "BTCUSDT"
        """
        if symbol is None:
            symbol = self.default_symbol
            
        # If already in Binance format
        if "/" not in symbol:
            return symbol
            
        return symbol.replace("/", "")

    def _format_symbol_reverse(self, formatted_symbol: str) -> str:
        """
        Convert Binance symbol format back to standard format.

        Args:
            formatted_symbol: Symbol in format "BTCUSDT"

        Returns:
            Symbol in format "BTC/USDT"
        """
        # Common quote currencies, check from longest to shortest
        quote_currencies = ["USDT", "BTC", "ETH", "BNB", "USD", "EUR"]
        
        for quote in quote_currencies:
            if formatted_symbol.endswith(quote):
                base = formatted_symbol[:-len(quote)]
                return f"{base}/{quote}"
                
        # Default case, assume 3-char quote currency
        return f"{formatted_symbol[:-3]}/{formatted_symbol[-3:]}"

    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """
        Format quantity for Binance API (with correct precision).

        Args:
            symbol: Trading pair symbol
            quantity: Quantity to format

        Returns:
            Formatted quantity string
        """
        # In a real implementation, this would get the correct precision from
        # exchange info API, but for simplicity we use a default precision
        # Example: exchange_info = self._get_exchange_info()
        return f"{quantity:.6f}".rstrip("0").rstrip(".")

    def _format_price(self, symbol: str, price: float) -> str:
        """
        Format price for Binance API (with correct precision).

        Args:
            symbol: Trading pair symbol
            price: Price to format

        Returns:
            Formatted price string
        """
        # In a real implementation, this would get the correct precision from
        # exchange info API, but for simplicity we use a default precision
        return f"{price:.2f}"

    def _convert_timeframe(self, timeframe: str) -> str:
        """
        Convert timeframe to Binance interval format.

        Args:
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")

        Returns:
            Binance interval format
        """
        # Map of timeframes to Binance intervals
        timeframe_map = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "2h": "2h",
            "4h": "4h",
            "6h": "6h",
            "8h": "8h",
            "12h": "12h",
            "1d": "1d",
            "3d": "3d",
            "1w": "1w",
            "1M": "1M"
        }
        
        return timeframe_map.get(timeframe, "1h")
