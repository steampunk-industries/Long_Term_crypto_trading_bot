import time
import hmac
import hashlib
import json
import base64
import requests
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
import pandas as pd
from urllib.parse import urlencode

from loguru import logger

from src.exchanges.base_exchange import BaseExchange

class GeminiExchange(BaseExchange):
    """
    Gemini Exchange API wrapper.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None
    ):
        """
        Initialize Gemini exchange wrapper.

        Args:
            api_key: API key for authenticated requests
            api_secret: API secret for authenticated requests
            paper_trading: Whether to use paper trading mode
            initial_balance: Initial balance for paper trading
        """
        super().__init__(api_key, api_secret, paper_trading)
        self.base_url = "https://api.gemini.com"
        self.api_version = "v1"

        # Initialize paper trading data structures
        if self.paper_trading:
            self._init_paper_trading(initial_balance)

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
            "ETH": 0.0
        }
        
        # Override with provided initial balances if any
        if initial_balance:
            for currency, amount in initial_balance.items():
                self._paper_balances[currency] = amount
                
        self._paper_orders = {}
        self._paper_trades = []
        logger.info(f"Initialized Gemini paper trading mode with balances: {self._paper_balances}")

    def connect(self) -> bool:
        """
        Connect to the exchange and test the API.

        Returns:
            bool: True if connection is successful
        """
        try:
            # For paper trading, always return success
            if self.paper_trading:
                logger.info("Successfully connected to Gemini exchange (paper trading mode)")
                return True

            # Test connection by getting ticker
            self.get_ticker("BTC/USD")
            logger.info("Successfully connected to Gemini exchange")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gemini exchange: {e}")
            return False

    def _generate_signature(self, endpoint: str, payload: Dict) -> Tuple[str, Dict]:
        """
        Generate API request signature for authenticated endpoints.

        Args:
            endpoint: API endpoint (without base URL)
            payload: Request payload

        Returns:
            Tuple of (encoded payload, headers with signature)
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for authenticated endpoints")

        # Add required fields to payload
        payload["nonce"] = int(time.time() * 1000)
        payload["request"] = f"/{self.api_version}/{endpoint}"

        # Encode payload
        encoded_payload = base64.b64encode(json.dumps(payload).encode())

        # Generate signature
        signature = hmac.new(
            self.api_secret.encode(),
            encoded_payload,
            hashlib.sha384
        ).hexdigest()

        # Create headers
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": "0",
            "X-GEMINI-APIKEY": self.api_key,
            "X-GEMINI-PAYLOAD": encoded_payload.decode(),
            "X-GEMINI-SIGNATURE": signature,
            "Cache-Control": "no-cache"
        }

        return encoded_payload, headers

    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USD")

        Returns:
            Ticker information
        """
        # Gemini uses different symbol format (no slash)
        formatted_symbol = symbol.replace("/", "").lower()

        try:
            response = requests.get(f"{self.base_url}/v1/pubticker/{formatted_symbol}")
            response.raise_for_status()
            data = response.json()

            return {
                "symbol": symbol,
                "bid": float(data.get("bid", 0)),
                "ask": float(data.get("ask", 0)),
                "last": float(data.get("last", 0)),
                "volume": float(data.get("volume", {}).get("BTC", 0)),
                "timestamp": datetime.now().timestamp()
            }
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")

            if self.paper_trading:
                # Return simulated ticker in paper trading mode
                return {
                    "symbol": symbol,
                    "bid": 45000.0,
                    "ask": 45100.0,
                    "last": 45050.0,
                    "volume": 100.0,
                    "timestamp": datetime.now().timestamp()
                }
            return {}

    def get_balance(self, currency: str) -> float:
        """
        Get available balance for a currency.

        Args:
            currency: Currency code (e.g., "BTC")

        Returns:
            Available balance
        """
        if self.paper_trading:
            return self._paper_balances.get(currency, 0.0)

        try:
            payload = {}
            endpoint = "balances"
            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            balances = response.json()

            for balance in balances:
                if balance["currency"] == currency:
                    return float(balance["available"])

            return 0.0
        except Exception as e:
            logger.error(f"Error getting balance for {currency}: {e}")
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
            payload = {}
            endpoint = "balances"
            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            balances = response.json()

            result = {}
            for balance in balances:
                result[balance["currency"]] = float(balance["available"])

            return result
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return {}

    def create_order(self,
                    symbol: str,
                    order_type: str,
                    side: str,
                    amount: float,
                    price: Optional[float] = None) -> Dict:
        """
        Create a new order.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USD")
            order_type: Order type (market, limit)
            side: Order side (buy, sell)
            amount: Order amount
            price: Order price (required for limit orders)

        Returns:
            Order information
        """
        if order_type.lower() == "limit" and price is None:
            raise ValueError("Price is required for limit orders")

        formatted_symbol = symbol.replace("/", "").lower()

        if self.paper_trading:
            # Simulate order creation in paper trading mode
            order_id = str(uuid.uuid4())
            ticker = self.get_ticker(symbol)
            executed_price = price if price else ticker.get("last", 0)

            order = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type,
                "side": side,
                "amount": amount,
                "price": executed_price,
                "timestamp": datetime.now().timestamp(),
                "status": "open"
            }

            self._paper_orders[order_id] = order

            # Simulate immediate execution for market orders
            if order_type.lower() == "market":
                base_currency = symbol.split("/")[0]
                quote_currency = symbol.split("/")[1]

                if side.lower() == "buy":
                    # Calculate total
                    total = amount * executed_price

                    # Check if we have enough balance
                    if self._paper_balances.get(quote_currency, 0) >= total:
                        self._paper_balances[quote_currency] -= total
                        self._paper_balances[base_currency] = self._paper_balances.get(base_currency, 0) + amount
                        order["status"] = "filled"

                        # Add to trades
                        self._paper_trades.append({
                            "id": str(uuid.uuid4()),
                            "order_id": order_id,
                            "symbol": symbol,
                            "side": side,
                            "amount": amount,
                            "price": executed_price,
                            "timestamp": datetime.now().timestamp()
                        })
                    else:
                        order["status"] = "rejected"
                        logger.warning(f"Insufficient balance for paper order: {quote_currency}")
                else:  # sell
                    # Check if we have enough balance
                    if self._paper_balances.get(base_currency, 0) >= amount:
                        self._paper_balances[base_currency] -= amount
                        self._paper_balances[quote_currency] = self._paper_balances.get(quote_currency, 0) + (amount * executed_price)
                        order["status"] = "filled"

                        # Add to trades
                        self._paper_trades.append({
                            "id": str(uuid.uuid4()),
                            "order_id": order_id,
                            "symbol": symbol,
                            "side": side,
                            "amount": amount,
                            "price": executed_price,
                            "timestamp": datetime.now().timestamp()
                        })
                    else:
                        order["status"] = "rejected"
                        logger.warning(f"Insufficient balance for paper order: {base_currency}")

            return order

        try:
            # Different endpoint for different order types
            if order_type.lower() == "market":
                endpoint = "order/new"
                payload = {
                    "symbol": formatted_symbol,
                    "amount": str(amount),
                    "side": side,
                    "type": "exchange market"
                }
            else:  # limit
                endpoint = "order/new"
                payload = {
                    "symbol": formatted_symbol,
                    "amount": str(amount),
                    "price": str(price),
                    "side": side,
                    "type": "exchange limit"
                }

            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            order = response.json()

            return {
                "id": order.get("order_id"),
                "symbol": symbol,  # Use the original symbol, not the Gemini one
                "type": order_type,
                "side": side,
                "amount": amount,
                "price": price,
                "status": order.get("is_live", False) and "open" or "filled",
                "timestamp": order.get("timestampms", 0) / 1000
            }
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {}

    def place_order(self,
                    symbol: str,
                    order_type: str,
                    side: str,
                    amount: float,
                    price: Optional[float] = None) -> Dict:
        """
        Create a new order (alias for create_order for API consistency).
        """
        return self.create_order(symbol, order_type, side, amount, price)

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol (e.g., "BTC/USD"), not required for Gemini

        Returns:
            True if successful, False otherwise
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
                    logger.warning(f"Cannot cancel order {order_id} with status {order['status']}")
                    return False
            else:
                logger.warning(f"Order {order_id} not found")
                return False

        try:
            endpoint = "order/cancel"
            payload = {
                "order_id": order_id
            }

            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            return result.get("is_cancelled", False)
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False

    def get_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        """
        Get order information.

        Args:
            order_id: Order ID
            symbol: Trading pair symbol (not required for Gemini)

        Returns:
            Order information
        """
        if self.paper_trading:
            order = self._paper_orders.get(order_id, {})
            return order

        try:
            endpoint = "order/status"
            payload = {
                "order_id": order_id
            }

            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            order = response.json()

            # Get symbol in the right format
            formatted_symbol = order.get("symbol", "").upper()
            base_currency = formatted_symbol[0:3]
            quote_currency = formatted_symbol[3:]
            symbol = f"{base_currency}/{quote_currency}"

            return {
                "id": order.get("order_id"),
                "symbol": symbol,
                "type": "limit" if "limit" in order.get("type", "") else "market",
                "side": order.get("side"),
                "amount": float(order.get("original_amount", 0)),
                "filled": float(order.get("executed_amount", 0)),
                "price": float(order.get("price", 0)),
                "status": order.get("is_live", False) and "open" or "filled",
                "timestamp": order.get("timestampms", 0) / 1000
            }
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open orders.

        Args:
            symbol: Trading pair symbol (optional filter)

        Returns:
            List of open orders
        """
        if self.paper_trading:
            orders = list(self._paper_orders.values())
            return [o for o in orders if o.get("status") == "open" and (symbol is None or o.get("symbol") == symbol)]

        try:
            endpoint = "orders"
            payload = {}

            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            orders = response.json()

            result = []
            for order in orders:
                # Get symbol in the right format
                formatted_symbol = order.get("symbol", "").upper()
                base_currency = formatted_symbol[0:3]
                quote_currency = formatted_symbol[3:]
                order_symbol = f"{base_currency}/{quote_currency}"

                if symbol is None or order_symbol == symbol:
                    result.append({
                        "id": order.get("order_id"),
                        "symbol": order_symbol,
                        "type": "limit" if "limit" in order.get("type", "") else "market",
                        "side": order.get("side"),
                        "amount": float(order.get("original_amount", 0)),
                        "filled": float(order.get("executed_amount", 0)),
                        "price": float(order.get("price", 0)),
                        "status": "open",
                        "timestamp": order.get("timestampms", 0) / 1000
                    })

            return result
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    def get_order_book(self, symbol: str, limit: int = 50) -> Dict:
        """
        Get order book for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USD")
            limit: Maximum number of entries (default 50)

        Returns:
            Order book with bids and asks
        """
        formatted_symbol = symbol.replace("/", "").lower()

        try:
            params = {"limit_bids": limit, "limit_asks": limit}
            response = requests.get(
                f"{self.base_url}/v1/book/{formatted_symbol}",
                params=params
            )
            response.raise_for_status()
            book = response.json()

            return {
                "symbol": symbol,
                "bids": [[float(item["price"]), float(item["amount"])] for item in book.get("bids", [])],
                "asks": [[float(item["price"]), float(item["amount"])] for item in book.get("asks", [])],
                "timestamp": datetime.now().timestamp()
            }
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return {"symbol": symbol, "bids": [], "asks": []}

    def deposit_address(self, currency: str) -> str:
        """
        Get deposit address for a currency.

        Args:
            currency: Currency code (e.g., "BTC")

        Returns:
            Deposit address
        """
        if self.paper_trading:
            return f"paper_{currency.lower()}_address"

        try:
            endpoint = f"deposit/{currency}/newAddress"
            payload = {}

            _, headers = self._generate_signature(endpoint, payload)

            response = requests.post(
                f"{self.base_url}/{self.api_version}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            return result.get("address", "")
        except Exception as e:
            logger.error(f"Error getting deposit address for {currency}: {e}")
            return ""

    def get_historical_data(
        self,
        symbol: str = None,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USD")
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")
            since: Start time in milliseconds
            limit: Number of candles to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        if symbol is None:
            symbol = self.default_symbol

        # In paper trading mode, return simulated data
        if self.paper_trading:
            # Generate synthetic data
            end_time = datetime.now()
            if timeframe == "1m":
                start_time = end_time - timedelta(minutes=limit)
                freq = "1min"
            elif timeframe == "5m":
                start_time = end_time - timedelta(minutes=5*limit)
                freq = "5min"
            elif timeframe == "15m":
                start_time = end_time - timedelta(minutes=15*limit)
                freq = "15min"
            elif timeframe == "30m":
                start_time = end_time - timedelta(minutes=30*limit)
                freq = "30min"
            elif timeframe == "1h":
                start_time = end_time - timedelta(hours=limit)
                freq = "1H"
            elif timeframe == "4h":
                start_time = end_time - timedelta(hours=4*limit)
                freq = "4H"
            elif timeframe == "1d":
                start_time = end_time - timedelta(days=limit)
                freq = "1D"
            else:
                # Default to 1h
                start_time = end_time - timedelta(hours=limit)
                freq = "1H"

            # Use specified start time if provided
            if since:
                start_time = datetime.fromtimestamp(since / 1000)

            # Generate timestamps
            timestamps = pd.date_range(start=start_time, end=end_time, freq=freq)

            # Limit to requested number of candles
            if len(timestamps) > limit:
                timestamps = timestamps[-limit:]

            if not len(timestamps):
                return pd.DataFrame()

            # Generate price data with some randomness
            base_price = 45000 if "BTC" in symbol else 3000
            price_scale = 1000 if "BTC" in symbol else 100

            import numpy as np

            # Generate price series with random walk
            np.random.seed(42)  # For reproducibility
            returns = np.random.normal(0, 0.01, size=len(timestamps))
            price_changes = base_price * returns
            prices = base_price + np.cumsum(price_changes)

            # Ensure positive prices
            prices = np.maximum(prices, base_price * 0.5)

            data = {
                'timestamp': timestamps,
                'open': prices,
                'high': prices * (1 + np.random.uniform(0, 0.02, size=len(timestamps))),
                'low': prices * (1 - np.random.uniform(0, 0.02, size=len(timestamps))),
                'close': prices * (1 + np.random.uniform(-0.01, 0.01, size=len(timestamps))),
                'volume': np.random.uniform(10, 100, size=len(timestamps))
            }

            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)

            return df

        # For real API access
        try:
            # Gemini doesn't have a direct OHLCV endpoint, so we need to get trades and convert them
            formatted_symbol = symbol.replace("/", "").lower()

            # Calculate timestamp_from based on timeframe and limit
            seconds_map = {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "30m": 1800,
                "1h": 3600,
                "4h": 14400,
                "1d": 86400
            }

            seconds = seconds_map.get(timeframe, 3600)
            timestamp_from = int(time.time() - seconds * limit) * 1000

            if since:
                timestamp_from = since

            # Gemini API uses microseconds for timestamp
            timestamp_from_us = timestamp_from * 1000

            # Get trades from API
            response = requests.get(
                f"{self.base_url}/v1/trades/{formatted_symbol}",
                params={
                    "limit_trades": 1000,
                    "timestamp": timestamp_from_us
                }
            )
            response.raise_for_status()
            trades = response.json()

            if not trades:
                return pd.DataFrame()

            # Convert trades to OHLCV
            df = pd.DataFrame(trades)
            df['timestamp'] = pd.to_datetime(df['timestampms'], unit='ms')
            df['price'] = df['price'].astype(float)
            df['amount'] = df['amount'].astype(float)

            # Resample to get OHLCV
            ohlcv = df.set_index('timestamp').resample(freq).agg({
                'price': 'ohlc',
                'amount': 'sum'
            })

            # Flatten the multi-level columns
            ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']

            # Keep only the requested number of candles
            if len(ohlcv) > limit:
                ohlcv = ohlcv.iloc[-limit:]

            return ohlcv

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return pd.DataFrame()
