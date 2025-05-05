import os
import time
import hmac
import hashlib
import json
import base64
import requests
from datetime import datetime, timedelta
import pandas as pd
import uuid
from typing import Dict, List, Optional, Any
from loguru import logger

from src.exchanges.base_exchange import BaseExchange

class CoinbaseExchange(BaseExchange):
    """
    Coinbase Exchange implementation for trading cryptocurrencies.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None
    ):
        """
        Initialize the Coinbase exchange.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            paper_trading: Whether to use paper trading mode
            initial_balance: Initial balance for paper trading
        """
        super().__init__(api_key, api_secret, paper_trading)
        self.base_url = "https://api.exchange.coinbase.com"
        self.default_symbol = "BTC-USD"

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
            "USD": 10000.0,
            "BTC": 0.0,
            "ETH": 0.0,
            "LTC": 0.0
        }
        
        # Override with provided initial balances if any
        if initial_balance:
            for currency, amount in initial_balance.items():
                self._paper_balances[currency] = amount
                
        logger.info(f"Initialized Coinbase paper trading with balances: {self._paper_balances}")
        
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
                logger.info("Connected to Coinbase exchange (paper trading mode)")
                return True

            # Make a request to get server time to test connection
            response = requests.get(f"{self.base_url}/time")
            response.raise_for_status()
            server_time = response.json()
            logger.info(f"Connected to Coinbase exchange, server time: {server_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Coinbase exchange: {e}")
            return False

    def get_balance(self, currency: str = "USD") -> float:
        """
        Get the available balance for a currency.

        Args:
            currency: Currency code (e.g., "BTC", "USD")

        Returns:
            Available balance
        """
        if self.paper_trading:
            return self._paper_balances.get(currency, 0.0)

        try:
            # Make authenticated request to get account info
            path = "/accounts"
            method = "GET"
            timestamp = str(int(time.time()))
            headers = self._generate_auth_headers(timestamp, method, path)

            response = requests.get(
                f"{self.base_url}{path}",
                headers=headers
            )
            response.raise_for_status()
            accounts = response.json()

            # Find the balance for the requested currency
            for account in accounts:
                if account["currency"] == currency:
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
            path = "/accounts"
            method = "GET"
            timestamp = str(int(time.time()))
            headers = self._generate_auth_headers(timestamp, method, path)

            response = requests.get(
                f"{self.base_url}{path}",
                headers=headers
            )
            response.raise_for_status()
            accounts = response.json()

            # Extract balances
            balances = {}
            for account in accounts:
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
            symbol: Trading pair symbol (e.g., "BTC-USD")

        Returns:
            Ticker information
        """
        try:
            # Format symbol for Coinbase API
            formatted_symbol = self._format_symbol(symbol)

            # Make request to get ticker info
            response = requests.get(
                f"{self.base_url}/products/{formatted_symbol}/ticker"
            )
            response.raise_for_status()
            ticker = response.json()

            # Also get 24h stats for high/low
            stats_response = requests.get(
                f"{self.base_url}/products/{formatted_symbol}/stats"
            )
            stats_response.raise_for_status()
            stats = stats_response.json()

            return {
                "symbol": symbol,
                "bid": float(ticker["bid"]),
                "ask": float(ticker["ask"]),
                "last": float(ticker["price"]),
                "high": float(stats["high"]),
                "low": float(stats["low"]),
                "volume": float(stats["volume"]),
                "timestamp": time.time()
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
            symbol: Trading pair symbol (e.g., "BTC-USD")
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
            # Format the parameters for the API
            formatted_symbol = self._format_symbol(symbol)
            lowercased_order_type = order_type.lower()
            lowercased_side = side.lower()

            # Prepare request parameters
            data = {
                "product_id": formatted_symbol,
                "side": lowercased_side,
                "type": lowercased_order_type,
                "size": str(amount)
            }

            # Add price for limit orders
            if lowercased_order_type == "limit":
                if price is None:
                    raise ValueError("Price is required for limit orders")
                data["price"] = str(price)
                data["time_in_force"] = "GTC"  # Good Till Cancelled

            # Make authenticated request to create order
            path = "/orders"
            method = "POST"
            timestamp = str(int(time.time()))
            body = json.dumps(data)
            headers = self._generate_auth_headers(timestamp, method, path, body)

            response = requests.post(
                f"{self.base_url}{path}",
                headers=headers,
                data=body
            )
            response.raise_for_status()
            order = response.json()

            # Format response
            return {
                "id": order["id"],
                "symbol": symbol,
                "type": order["type"],
                "side": order["side"],
                "amount": float(order["size"]),
                "executed": float(order.get("filled_size", 0)),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {}

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            symbol: Trading pair symbol (not required for Coinbase)

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
            path = f"/orders/{order_id}"
            method = "DELETE"
            timestamp = str(int(time.time()))
            headers = self._generate_auth_headers(timestamp, method, path)

            response = requests.delete(
                f"{self.base_url}{path}",
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
            symbol: Trading pair symbol (not required for Coinbase)

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
            path = f"/orders/{order_id}"
            method = "GET"
            timestamp = str(int(time.time()))
            headers = self._generate_auth_headers(timestamp, method, path)

            response = requests.get(
                f"{self.base_url}{path}",
                headers=headers
            )
            response.raise_for_status()
            order = response.json()

            # Format response
            symbol = order.get("product_id", "").replace("-", "/")
            return {
                "id": order["id"],
                "symbol": symbol,
                "type": order["type"],
                "side": order["side"],
                "amount": float(order["size"]),
                "executed": float(order.get("filled_size", 0)),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USD"), None for all symbols

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
            params = {}
            if symbol:
                params["product_id"] = self._format_symbol(symbol)

            # Make authenticated request to get open orders
            path = "/orders"
            if params:
                path = f"{path}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            method = "GET"
            timestamp = str(int(time.time()))
            headers = self._generate_auth_headers(timestamp, method, path)

            response = requests.get(
                f"{self.base_url}{path}",
                headers=headers
            )
            response.raise_for_status()
            orders = response.json()

            # Format response
            return [
                {
                    "id": order["id"],
                    "symbol": order["product_id"].replace("-", "/"),
                    "type": order["type"],
                    "side": order["side"],
                    "amount": float(order["size"]),
                    "executed": float(order.get("filled_size", 0)),
                    "price": float(order.get("price", 0)),
                    "status": order["status"].lower(),
                    "timestamp": time.time()
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
        since: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USD")
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")
            limit: Number of candles to retrieve
            since: Start time in ISO format

        Returns:
            DataFrame with OHLCV data
        """
        if symbol is None:
            symbol = self.default_symbol

        try:
            # Format symbol for Coinbase API
            formatted_symbol = self._format_symbol(symbol)

            # Convert timeframe to Coinbase granularity
            granularity = self._convert_timeframe(timeframe)

            # Calculate end time and start time
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(seconds=granularity * limit)

            if since:
                try:
                    start_time = datetime.fromisoformat(since.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Invalid since time format: {since}, using default")

            # Format times for API
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()

            # Make request to get candles data
            params = {
                "granularity": granularity,
                "start": start_str,
                "end": end_str
            }
            response = requests.get(
                f"{self.base_url}/products/{formatted_symbol}/candles",
                params=params
            )
            response.raise_for_status()
            candles = response.json()

            # Format response into DataFrame
            # Coinbase returns [time, low, high, open, close, volume]
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "low", "high", "open", "close", "volume"]
            )

            # Convert types and reorder columns
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

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
            symbol: Trading pair symbol (e.g., 'BTC/USD')
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
        cost = order["amount"] * execution_price
        fee = cost * 0.005  # 0.5% fee
        
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

    def _generate_auth_headers(
        self,
        timestamp: str,
        method: str,
        path: str,
        body: str = ""
    ) -> Dict[str, str]:
        """
        Generate authentication headers for API request.

        Args:
            timestamp: Request timestamp
            method: HTTP method
            path: Request path
            body: Request body

        Returns:
            Dictionary with authentication headers
        """
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message.encode("utf-8"),
            digestmod=hashlib.sha256
        )
        signature_b64 = base64.b64encode(signature.digest()).decode("utf-8")

        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature_b64,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": "",
            "Content-Type": "application/json"
        }

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol for Coinbase API.

        Args:
            symbol: Symbol in format "BTC/USD"

        Returns:
            Symbol in format "BTC-USD"
        """
        if symbol is None:
            symbol = self.default_symbol
            
        # If already in Coinbase format
        if "-" in symbol:
            return symbol
            
        return symbol.replace("/", "-")

    def _convert_timeframe(self, timeframe: str) -> int:
        """
        Convert timeframe to Coinbase granularity in seconds.

        Args:
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")

        Returns:
            Granularity in seconds
        """
        # Map of timeframes to seconds
        timeframe_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "6h": 21600,
            "1d": 86400
        }
        
        return timeframe_map.get(timeframe, 3600)
        
    def get_top_symbols(self, limit: int = 10, quote: str = "USDT") -> List[str]:
        """
        Get the top trading pairs by volume for Coinbase exchange.
        
        Args:
            limit: Maximum number of symbols to return
            quote: Quote currency (e.g., "USDT")
            
        Returns:
            List of trading pair symbols (e.g., ["BTC/USDT", "ETH/USDT"])
        """
        url = "https://api.exchange.coinbase.com/products"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            products = response.json()
            
            # Filter for the specified quote currency
            # Coinbase primarily uses USD, so we may need to fallback
            target_quote = quote
            filtered_pairs = [
                p['id'] for p in products
                if p.get('quote_currency') == target_quote and p.get('status') == 'online'
            ]
            
            # If no pairs found with specified quote, try USD as fallback if quote was USDT
            if not filtered_pairs and quote == "USDT":
                target_quote = "USD"
                filtered_pairs = [
                    p['id'] for p in products
                    if p.get('quote_currency') == target_quote and p.get('status') == 'online'
                ]
            
            # Get 24h stats for volume sorting
            pairs_with_volume = []
            for product_id in filtered_pairs[:min(25, len(filtered_pairs))]:  # Limit API calls
                try:
                    stats_url = f"{self.base_url}/products/{product_id}/stats"
                    stats_response = requests.get(stats_url, timeout=3)
                    stats_response.raise_for_status()
                    stats = stats_response.json()
                    volume = float(stats.get('volume', 0))
                    pairs_with_volume.append((product_id, volume))
                except Exception as e:
                    logger.debug(f"Could not get stats for {product_id}: {e}")
            
            # Sort by volume
            sorted_pairs = sorted(pairs_with_volume, key=lambda x: x[1], reverse=True)
            
            # Convert to standard format (e.g., "BTC-USD" to "BTC/USD")
            formatted_pairs = [p[0].replace("-", "/") for p in sorted_pairs[:limit]]
            
            logger.info(f"Retrieved {len(formatted_pairs)} top symbols from Coinbase with quote {target_quote}")
            return formatted_pairs
        except Exception as e:
            logger.warning(f"Failed to fetch Coinbase top symbols: {e}")
            # Return default pairs based on the requested quote currency
            if quote == "USDT":
                return ["BTC/USDT", "ETH/USDT"]
            else:
                return [f"BTC/{quote}", f"ETH/{quote}"]
