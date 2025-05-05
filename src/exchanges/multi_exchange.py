"""
Multi-exchange implementation that aggregates data from multiple exchanges.
Provides a unified interface for paper trading using public APIs from multiple exchanges.
"""

from typing import Dict, List, Optional, Union, Any
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from loguru import logger

from src.config import config
from src.exchanges.base_exchange import BaseExchange
from src.integrations.steampunk_holdings import steampunk_integration


class MultiExchange(BaseExchange):
    """
    Multi-exchange implementation that aggregates data from multiple exchanges.
    Uses public APIs from multiple exchanges for paper trading.
    """
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None,
        exchanges: List[str] = None,
        use_steampunk_data: bool = True
    ):
        """
        Initialize the multi-exchange.
        
        Args:
            api_key: Not used for multi-exchange (for interface compatibility)
            api_secret: Not used for multi-exchange (for interface compatibility)
            paper_trading: Whether to use paper trading mode (always True for multi-exchange)
            initial_balance: Initial balance for paper trading
            exchanges: List of exchange names to use for data aggregation
            use_steampunk_data: Whether to use steampunk.holdings data when available
        """
        # Force paper trading for multi-exchange
        super().__init__(api_key, api_secret, True)
        
        # Set default exchanges if not provided
        if exchanges is None:
            # Get exchanges from environment variable or use default US-available exchanges
            env_exchanges = os.environ.get('MULTI_EXCHANGE_SOURCES', 'coinbase,gemini,kucoin,kraken')
            exchanges = env_exchanges.split(',')
        
        self.exchange_names = exchanges
        self.exchanges = {}
        self.use_steampunk_data = use_steampunk_data
        
        # Initialize CCXT exchange objects for each exchange
        for exchange_name in self.exchange_names:
            try:
                exchange_class = getattr(ccxt, exchange_name)
                self.exchanges[exchange_name] = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
                logger.info(f"Initialized {exchange_name} for data aggregation")
            except (AttributeError, ccxt.BaseError) as e:
                logger.warning(f"Failed to initialize {exchange_name}: {e}")
        
        # Initialize paper trading
        if initial_balance is None:
            initial_balance = {"USDT": config.INITIAL_CAPITAL}
        self._init_paper_trading(initial_balance)
        
        # Cache for market data to reduce API calls
        self._market_data_cache = {}
        self._ticker_cache = {}
        self._ticker_cache_time = {}
        self._ticker_cache_expiry = 60  # 60 seconds
        
        logger.info(f"Initialized multi-exchange with {len(self.exchanges)} exchanges")
    
    def connect(self) -> bool:
        """
        Connect to the exchange APIs.
        
        Returns:
            bool: True if at least one connection is successful, False otherwise
        """
        successful_connections = 0
        
        for name, exchange in self.exchanges.items():
            try:
                # Test connection by fetching the server time
                exchange.fetch_time()
                successful_connections += 1
                logger.info(f"Successfully connected to {name} API")
            except Exception as e:
                logger.warning(f"Failed to connect to {name} API: {e}")
        
        return successful_connections > 0
    
    def get_balance(self, currency: str = "USDT") -> float:
        """
        Get the balance of a specific currency.
        
        Args:
            currency: Currency symbol
            
        Returns:
            float: Balance amount
        """
        # Always use paper trading balance for multi-exchange
        return self._paper_balance.get(currency, 0.0)
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get the current ticker information for a symbol by aggregating data from multiple exchanges.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict: Ticker information including price
        """
        # Check cache first
        current_time = time.time()
        if symbol in self._ticker_cache and (current_time - self._ticker_cache_time.get(symbol, 0)) < self._ticker_cache_expiry:
            return self._ticker_cache[symbol]
        
        # Try to get data from steampunk.holdings first if enabled
        if self.use_steampunk_data:
            try:
                sentiment_data = steampunk_integration.api.get_sentiment_data(symbol)
                if "price" in sentiment_data and sentiment_data["price"] > 0:
                    ticker = {
                        "symbol": symbol,
                        "last": float(sentiment_data["price"]),
                        "bid": float(sentiment_data.get("bid", sentiment_data["price"])),
                        "ask": float(sentiment_data.get("ask", sentiment_data["price"])),
                        "volume": float(sentiment_data.get("volume", 0.0)),
                        "timestamp": int(time.time() * 1000),
                        "datetime": datetime.utcnow().isoformat(),
                        "source": "steampunk.holdings"
                    }
                    
                    # Update cache
                    self._ticker_cache[symbol] = ticker
                    self._ticker_cache_time[symbol] = current_time
                    
                    return ticker
            except Exception as e:
                logger.warning(f"Failed to get ticker from steampunk.holdings: {e}")
        
        # Aggregate data from multiple exchanges
        prices = []
        volumes = []
        bids = []
        asks = []
        
        for name, exchange in self.exchanges.items():
            try:
                # Check if this is a symbol that is known to be problematic for this exchange
                if name == "gemini" and not self._symbol_supported_on_gemini(symbol):
                    logger.debug(f"Skipping {symbol} for gemini - not supported")
                    continue
                    
                # Special handling for exchanges that require API keys
                if name == "coinbase" and (not hasattr(exchange, 'apiKey') or not exchange.apiKey):
                    # Try to use public API methods instead for coinbase
                    try:
                        # For coinbase, try to use the public API
                        symbol_parts = symbol.split('/')
                        if len(symbol_parts) == 2:
                            # Format like 'BTC-USDT' for coinbase public API
                            cb_symbol = f"{symbol_parts[0]}-{symbol_parts[1]}"
                            public_data = self._get_coinbase_public_price(cb_symbol)
                            if public_data and 'price' in public_data:
                                prices.append(float(public_data['price']))
                                # Estimate bid/ask as slight offsets from price
                                price = float(public_data['price'])
                                bids.append(price * 0.999)  # Estimate bid as 0.1% below price
                                asks.append(price * 1.001)  # Estimate ask as 0.1% above price
                                volumes.append(0)  # No volume data in public API
                        continue
                    except Exception as cb_err:
                        logger.debug(f"Failed to get public data for {symbol} from coinbase: {cb_err}")
                        continue
                
                ticker = exchange.fetch_ticker(symbol)
                
                if ticker and "last" in ticker and ticker["last"]:
                    prices.append(ticker["last"])
                
                if ticker and "volume" in ticker and ticker["volume"]:
                    volumes.append(ticker["volume"])
                
                if ticker and "bid" in ticker and ticker["bid"]:
                    bids.append(ticker["bid"])
                
                if ticker and "ask" in ticker and ticker["ask"]:
                    asks.append(ticker["ask"])
                
            except Exception as e:
                logger.debug(f"Failed to get ticker from {name}: {e}")
    
    def _symbol_supported_on_gemini(self, symbol: str) -> bool:
        """
        Check if a symbol is supported on Gemini exchange
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            bool: True if supported, False otherwise
        """
        # Common symbols not supported on Gemini
        unsupported = [
            'ADA/USDT', 'SOL/USDT', 'DOT/USDT', 'AVAX/USDT', 
            'MATIC/USDT', 'LINK/USDT', 'XRP/USDT', 'DOGE/USDT'
        ]
        
        if symbol in unsupported:
            return False
            
        # Try to use a more dynamic approach by checking previously failed symbols
        if not hasattr(self, '_gemini_unsupported_symbols'):
            self._gemini_unsupported_symbols = set(unsupported)
        
        if symbol in self._gemini_unsupported_symbols:
            return False
            
        return True
        
    def _get_coinbase_public_price(self, symbol: str) -> Dict:
        """
        Get price from Coinbase public API
        
        Args:
            symbol: Trading pair symbol with dash (e.g., 'BTC-USDT')
            
        Returns:
            Dict: Price data or empty dict if failed
        """
        try:
            # Use requests to fetch from public API
            import requests
            url = f"https://api.coinbase.com/v2/prices/{symbol}/spot"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {})
            return {}
        except Exception as e:
            logger.debug(f"Error fetching Coinbase public price for {symbol}: {e}")
            return {}
            
    def get_ticker(self, symbol: str) -> Dict:
        """Continued from above - fixes indentation error in the original implementation"""
        # Calculate aggregated values
        if not prices:
            logger.warning(f"Failed to get ticker for {symbol} from any exchange")
            return {"last": 0.0, "bid": 0.0, "ask": 0.0, "volume": 0.0}
        
        # Remove outliers (values more than 2 standard deviations from the mean)
        if len(prices) >= 3:
            mean_price = np.mean(prices)
            std_price = np.std(prices)
            prices = [p for p in prices if abs(p - mean_price) <= 2 * std_price]
        
        # Calculate median values (more robust than mean)
        last_price = np.median(prices) if prices else 0.0
        bid_price = np.median(bids) if bids else last_price * 0.999
        ask_price = np.median(asks) if asks else last_price * 1.001
        volume = np.sum(volumes) if volumes else 0.0
        
        # Create ticker
        ticker = {
            "symbol": symbol,
            "last": float(last_price),
            "bid": float(bid_price),
            "ask": float(ask_price),
            "volume": float(volume),
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.utcnow().isoformat(),
            "source": "aggregated"
        }
        
        # Update cache
        self._ticker_cache[symbol] = ticker
        self._ticker_cache_time[symbol] = current_time
        
        return ticker
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str = '1h', 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol by aggregating data from multiple exchanges.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to retrieve
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        # Check cache first
        cache_key = f"{symbol}_{timeframe}_{limit}"
        if cache_key in self._market_data_cache:
            cache_entry = self._market_data_cache[cache_key]
            cache_time = cache_entry.get("time", 0)
            cache_data = cache_entry.get("data", None)
            
            # Determine cache expiry based on timeframe
            expiry_seconds = 60  # Default 1 minute
            if timeframe.endswith('m'):
                expiry_seconds = int(timeframe[:-1]) * 60
            elif timeframe.endswith('h'):
                expiry_seconds = int(timeframe[:-1]) * 3600
            elif timeframe.endswith('d'):
                expiry_seconds = int(timeframe[:-1]) * 86400
            
            # Use cache if not expired
            if cache_data is not None and (time.time() - cache_time) < expiry_seconds:
                return cache_data
        
        # Try to get data from steampunk.holdings first if enabled
        if self.use_steampunk_data:
            try:
                df = steampunk_integration.get_market_data(symbol, timeframe, limit)
                if not df.empty:
                    # Update cache
                    self._market_data_cache[cache_key] = {
                        "time": time.time(),
                        "data": df
                    }
                    return df
            except Exception as e:
                logger.warning(f"Failed to get historical data from steampunk.holdings: {e}")
        
        # Collect data from all exchanges
        all_dfs = []
        
        for name, exchange in self.exchanges.items():
            try:
                # Fetch OHLCV data
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                if not ohlcv:
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Add exchange name
                df['exchange'] = name
                
                all_dfs.append(df)
                
            except Exception as e:
                logger.debug(f"Failed to get historical data from {name}: {e}")
        
        if not all_dfs:
            logger.warning(f"Failed to get historical data for {symbol} from any exchange")
            return pd.DataFrame()
        
        # Combine data from all exchanges
        combined_df = pd.concat(all_dfs)
        
        # Group by timestamp and aggregate
        grouped = combined_df.groupby('timestamp').agg({
            'open': 'mean',
            'high': 'max',
            'low': 'min',
            'close': 'mean',
            'volume': 'sum'
        })
        
        # Sort by timestamp
        result_df = grouped.sort_index()
        
        # Update cache
        self._market_data_cache[cache_key] = {
            "time": time.time(),
            "data": result_df
        }
        
        return result_df
    
    def create_order(
        self, 
        symbol: str, 
        order_type: str, 
        side: str, 
        amount: float, 
        price: Optional[float] = None
    ) -> Dict:
        """
        Create a new paper order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            order_type: Type of order ('limit', 'market')
            side: Order side ('buy', 'sell')
            amount: Order amount in base currency
            price: Order price (required for limit orders)
            
        Returns:
            Dict: Order information
        """
        # Create a paper order
        order = {
            "id": self._generate_order_id(),
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "amount": amount,
            "price": price,
            "status": "open",
            "filled": 0.0,
            "remaining": amount,
            "timestamp": int(time.time() * 1000),
            "datetime": None,
            "fee": None
        }
        
        # Execute the paper order immediately
        executed_order = self._execute_paper_order(order)
        
        # Sync with steampunk.holdings if enabled
        if self.use_steampunk_data:
            try:
                steampunk_integration.sync_trades([executed_order])
            except Exception as e:
                logger.warning(f"Failed to sync trade with steampunk.holdings: {e}")
        
        return executed_order
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an existing paper order.
        
        Args:
            order_id: ID of the order to cancel
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            bool: True if cancellation is successful, False otherwise
        """
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
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get information about a paper order.
        
        Args:
            order_id: ID of the order
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict: Order information
        """
        if order_id in self._paper_orders:
            return self._paper_orders[order_id]
        else:
            logger.warning(f"Order {order_id} not found")
            return {}
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open paper orders.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT'), or None for all symbols
            
        Returns:
            List[Dict]: List of open orders
        """
        open_orders = [
            order for order in self._paper_orders.values()
            if order["status"] == "open" and (symbol is None or order["symbol"] == symbol)
        ]
        return open_orders
    
    def get_top_symbols(self, limit: int = 10, quote: str = 'USDT') -> List[str]:
        """
        Get the top trading pairs by volume for a specific quote currency.
        This method is required by the BaseExchange abstract class.
        
        Args:
            limit: Maximum number of symbols to return
            quote: Quote currency to filter by (e.g., 'USDT')
            
        Returns:
            List[str]: List of symbol names sorted by volume
        """
        # Try to get markets from all exchanges
        all_symbols = set()
        symbol_volumes = {}
        
        for name, exchange in self.exchanges.items():
            try:
                # Get all markets for the exchange
                markets = exchange.fetch_markets()
                
                # Filter by quote currency
                filtered_markets = [
                    market for market in markets 
                    if market['quote'] == quote and market['active']
                ]
                
                # Get symbols
                symbols = [market['symbol'] for market in filtered_markets]
                all_symbols.update(symbols)
                
                # Get volumes for each symbol
                for symbol in symbols:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        if ticker and 'volume' in ticker and ticker['volume']:
                            if symbol not in symbol_volumes:
                                symbol_volumes[symbol] = 0
                            symbol_volumes[symbol] += ticker['volume']
                    except Exception as e:
                        logger.debug(f"Failed to get ticker for {symbol} from {name}: {e}")
                
            except Exception as e:
                logger.warning(f"Failed to get markets from {name}: {e}")
        
        # Sort symbols by volume
        sorted_symbols = sorted(
            symbol_volumes.keys(), 
            key=lambda s: symbol_volumes.get(s, 0), 
            reverse=True
        )
        
        # If we don't have enough symbols with volume data, add some defaults
        if len(sorted_symbols) < limit:
            # Common crypto symbols
            default_symbols = [
                f"BTC/{quote}", f"ETH/{quote}", f"SOL/{quote}", f"XRP/{quote}", 
                f"ADA/{quote}", f"DOT/{quote}", f"BNB/{quote}", f"AVAX/{quote}", 
                f"MATIC/{quote}", f"LINK/{quote}", f"DOGE/{quote}", f"UNI/{quote}"
            ]
            
            # Add defaults not already in the list
            for symbol in default_symbols:
                if symbol not in sorted_symbols and symbol in all_symbols:
                    sorted_symbols.append(symbol)
        
        return sorted_symbols[:limit]
        
    def clear_cache(self):
        """
        Clear all caches.
        """
        self._market_data_cache = {}
        self._ticker_cache = {}
        self._ticker_cache_time = {}
        logger.info("Cleared all caches")
