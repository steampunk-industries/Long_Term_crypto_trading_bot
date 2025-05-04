import os
import time
import hashlib
import hmac
import base64
import json
import uuid
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from src.exchanges.base_exchange import BaseExchange

class KucoinExchange(BaseExchange):
    """
    KuCoin Exchange implementation for trading cryptocurrencies.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None
    ):
        """
        Initialize the KuCoin exchange.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            api_passphrase: API passphrase for KuCoin
            paper_trading: Whether to use paper trading mode
            initial_balance: Initial balance for paper trading
        """
        super().__init__(api_key, api_secret, paper_trading)
        self.api_passphrase = api_passphrase or os.environ.get("KUCOIN_API_PASSPHRASE", "")
        self.base_url = "https://api.kucoin.com"
        self.api_version = "v1"
        self.default_symbol = "BTC-USDT"

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
            "KCS": 0.0
        }
        
        # Override with provided initial balances if any
        if initial_balance:
            for currency, amount in initial_balance.items():
                self._paper_balances[currency] = amount
                
        logger.info(f"Initialized KuCoin paper trading with balances: {self._paper_balances}")
        
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
                logger.info("Connected to KuCoin exchange (paper trading mode)")
                return True

            # Make request to get server time
            response = requests.get(f"{self.base_url}/api/v1/timestamp")
            response.raise_for_status()
            server_time = response.json()["data"]
            logger.info(f"Connected to KuCoin exchange, server time: {server_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to KuCoin exchange: {e}")
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
            # Make authenticated request to get account info
            endpoint = "/api/v1/accounts"
            headers = self._generate_auth_headers("GET", endpoint)

            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            accounts = response.json()["data"]

            # Find the balance for the requested currency
            for account in accounts:
                if account["currency"] == currency and account["type"] == "trade":
                    return float(account["available"])

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
            # Make authenticated request to get account info
            endpoint = "/api/v1/accounts"
            headers = self._generate_auth_headers("GET", endpoint)

            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            accounts = response.json()["data"]

            # Extract balances
            balances = {}
            for account in accounts:
                if account["type"] == "trade":
                    available = float(account["available"])
                    if available > 0:
                        balances[account["currency"]] = available

            return balances
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT")

        Returns:
            Ticker information
        """
        try:
            # Format symbol for KuCoin API
            formatted_symbol = self._format_symbol(symbol)

            # Make request to get ticker info
            response = requests.get(
                f"{self.base_url}/api/v1/market/orderbook/level1",
                params={"symbol": formatted_symbol}
            )
            response.raise_for_status()
            ticker = response.json()["data"]

            # Get 24h stats
            stats_response = requests.get(
                f"{self.base_url}/api/v1/market/stats",
                params={"symbol": formatted_symbol}
            )
            stats_response.raise_for_status()
            stats = stats_response.json()["data"]

            return {
                "symbol": symbol,
                "bid": float(ticker["bestBid"]),
                "ask": float(ticker["bestAsk"]),
                "last": float(ticker["price"]),
                "high": float(stats["high"]),
                "low": float(stats["low"]),
                "volume": float(stats["vol"]),
                "timestamp": float(ticker["time"]) / 1000
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
            symbol: Trading pair symbol (e.g., "BTC-USDT")
            order_type: Order type ("limit" or "market")
            side: Order side ("buy" or "sell")
            amount: Order amount in base currency
            price: Order price (required for limit orders)

        Returns:
            Dictionary with order information
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
                "clientOid": str(uuid.uuid4()),
                "symbol": symbol,
                "type": order_type.lower(),
                "side": side.lower(),
                "size": amount,
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
            lowercased_order_type = order_type.lower()
            lowercased_side = side.lower()
            client_oid = str(uuid.uuid4())

            # Prepare request data
            data = {
                "clientOid": client_oid,
                "symbol": formatted_symbol,
                "side": lowercased_side,
                "type": lowercased_order_type,
                "size": str(amount)
            }

            # Add price for limit orders
            if lowercased_order_type == "limit":
                if price is None:
                    raise ValueError("Price is required for limit orders")
                data["price"] = str(price)
                data["timeInForce"] = "GTC"  # Good Till Cancelled

            # Make authenticated request to create order
            endpoint = "/api/v1/orders"
            headers = self._generate_auth_headers("POST", endpoint, data)

            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            order_id = response.json()["data"]["orderId"]

            # Get full order details
            order_details = self.get_order(order_id, symbol)
            return order_details
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {}

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            symbol: Trading pair symbol (optional for KuCoin)

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
            # Make authenticated request to cancel order
            endpoint = f"/api/v1/orders/{order_id}"
            headers = self._generate_auth_headers("DELETE", endpoint)

            response = requests.delete(
                f"{self.base_url}{endpoint}",
                headers=headers
            )
            response.raise_for_status()

            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        """
        Get information about an order.

        Args:
            order_id: ID of the order
            symbol: Trading pair symbol (optional for KuCoin)

        Returns:
            Dictionary with order information
        """
        if self.paper_trading:
            if order_id in self._paper_orders:
                return self._paper_orders[order_id]
            logger.warning(f"Order {order_id} not found")
            return {}

        try:
            # Make authenticated request to get order info
            endpoint = f"/api/v1/orders/{order_id}"
            headers = self._generate_auth_headers("GET", endpoint)

            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            order = response.json()["data"]

            # Format response
            return {
                "id": order["id"],
                "clientOid": order.get("clientOid", ""),
                "symbol": order["symbol"],
                "type": order["type"],
                "side": order["side"],
                "size": float(order["size"]),
                "dealSize": float(order.get("dealSize", 0)),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": time.time()  # KuCoin doesn't return timestamp in order details
            }
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT"), None for all symbols

        Returns:
            List of open orders
        """
        if self.paper_trading:
            orders = [
                order for order in self._paper_orders.values()
                if order["status"] == "open"
            ]
            
            # Filter by symbol if provided
            if symbol:
                formatted_symbol = self._format_symbol(symbol)
                orders = [
                    order for order in orders
                    if self._format_symbol(order["symbol"]) == formatted_symbol
                ]
                
            return orders

        try:
            # Prepare request parameters
            params = {"status": "active"}
            if symbol:
                params["symbol"] = self._format_symbol(symbol)

            # Make authenticated request to get open orders
            endpoint = "/api/v1/orders"
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint_with_params = f"{endpoint}?{query_string}"
            headers = self._generate_auth_headers("GET", endpoint_with_params)

            response = requests.get(
                f"{self.base_url}{endpoint_with_params}",
                headers=headers
            )
            response.raise_for_status()
            orders = response.json()["data"]["items"]

            # Format response
            return [
                {
                    "id": order["id"],
                    "clientOid": order.get("clientOid", ""),
                    "symbol": order["symbol"],
                    "type": order["type"],
                    "side": order["side"],
                    "size": float(order["size"]),
                    "dealSize": float(order.get("dealSize", 0)),
                    "price": float(order.get("price", 0)),
                    "status": order["status"].lower(),
                    "timestamp": time.time()  # KuCoin doesn't return timestamp in orders list
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    def get_historical_data(
        self,
        symbol: str = None,
        timeframe: str = "1hour",
        limit: int = 100,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT")
            timeframe: Timeframe (e.g., "1min", "1hour", "1day")
            limit: Number of candles to retrieve
            start: Start time in milliseconds
            end: End time in milliseconds

        Returns:
            DataFrame with OHLCV data
        """
        if symbol is None:
            symbol = self.default_symbol

        try:
            # Format symbol for KuCoin API
            formatted_symbol = self._format_symbol(symbol)

            # Convert timeframe to KuCoin type
            kucoin_timeframe = self._convert_timeframe(timeframe)

            # Prepare request parameters
            params = {
                "symbol": formatted_symbol,
                "type": kucoin_timeframe
            }

            # Add start and end times if provided
            if start:
                params["startAt"] = start
            if end:
                params["endAt"] = end

            # Make request to get klines (candlestick) data
            response = requests.get(
                f"{self.base_url}/api/v1/market/candles",
                params=params
            )
            response.raise_for_status()
            candles = response.json()["data"]

            # If no data returned
            if not candles:
                return pd.DataFrame()

            # Format response into DataFrame
            # KuCoin returns [timestamp, open, close, high, low, volume, turnover]
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "close", "high", "low", "volume", "turnover"]
            )

            # Convert types
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # Reorder columns to OHLCV format
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            
            # Limit rows
            df = df.head(limit)

            # Set timestamp as index
            df.set_index("timestamp", inplace=True)

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
            symbol: Trading pair symbol (e.g., 'BTC-USDT')
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
        base_currency, quote_currency = order["symbol"].split("-")
        
        # Get the current ticker
        ticker = self.get_ticker(order["symbol"])
        
        # Set the execution price
        if order["type"] == "market":
            execution_price = ticker["last"]
        else:
            execution_price = order["price"]
            
        # Calculate the cost
        cost = order["size"] * execution_price
        fee = cost * 0.001  # 0.1% fee
        
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
            self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) + order["size"]
            
        elif order["side"] == "sell":
            # Check if enough balance
            if self._paper_balances.get(base_currency, 0) < order["size"]:
                logger.warning(f"Insufficient {base_currency} balance for paper order")
                order["status"] = "rejected"
                return order
                
            # Deduct base currency
            self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) - order["size"]
            
            # Add quote currency
            self._paper_balances[quote_currency] = self._paper_balances.get(quote_currency, 0) + cost - fee
            
        # Update order status
        order["status"] = "done"
        order["dealSize"] = order["size"]
        order["fee"] = fee
        
        # Add to paper trades
        trade = {
            "id": str(uuid.uuid4()),
            "orderId": order["id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "size": order["size"],
            "price": execution_price,
            "cost": cost,
            "fee": fee,
            "timestamp": time.time()
        }
        self._paper_trades.append(trade)
        
        # Log the trade
        logger.info(f"Executed paper trade: {trade}")
        
        return order

    def _generate_auth_headers(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, str]:
        """
        Generate authentication headers for API request.

        Args:
            method: HTTP method
            endpoint: Endpoint path
            data: Request body (for POST requests)

        Returns:
            Dictionary with authentication headers
        """
        now = int(time.time() * 1000)
        str_to_sign = f"{now}{method}{endpoint}"
        
        if data:
            str_to_sign += json.dumps(data)
            
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                str_to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        passphrase = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                self.api_passphrase.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol for KuCoin API.

        Args:
            symbol: Symbol in format "BTC/USDT"

        Returns:
            Symbol in format "BTC-USDT"
        """
        if symbol is None:
            symbol = self.default_symbol
            
        # If already in KuCoin format
        if "-" in symbol:
            return symbol
            
        return symbol.replace("/", "-")

    def _convert_timeframe(self, timeframe: str) -> str:
        """
        Convert timeframe to KuCoin format.

        Args:
            timeframe: Timeframe (e.g., "1m", "1h", "1d")

        Returns:
            KuCoin timeframe format
        """
        # Map of timeframes to KuCoin intervals
        timeframe_map = {
            "1m": "1min",
            "3m": "3min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1hour",
            "2h": "2hour",
            "4h": "4hour",
            "6h": "6hour",
            "12h": "12hour",
            "1d": "1day",
            "1w": "1week"
        }
        
        return timeframe_map.get(timeframe, "1hour")
