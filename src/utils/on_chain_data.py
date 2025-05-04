"""
On-chain data analysis module for the crypto trading bot.
Provides integration with on-chain data providers like Glassnode.
"""

import os
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

import requests
import pandas as pd

from src.config import settings
from src.utils.logging import logger


class OnChainDataProvider:
    """Base class for on-chain data providers."""

    def __init__(self, api_key: str = None):
        """
        Initialize the on-chain data provider.

        Args:
            api_key: API key for the data provider.
        """
        self.api_key = api_key
        self.cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 3600  # 1 hour in seconds

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from the provider.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        raise NotImplementedError("Subclasses must implement get_data")

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if available and not expired.

        Args:
            cache_key: Cache key.

        Returns:
            Cached data or None if not available.
        """
        current_time = time.time()
        if cache_key in self.cache and current_time - self.cache_expiry.get(cache_key, 0) < self.cache_ttl:
            return self.cache[cache_key]
        return None

    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store data in cache.

        Args:
            cache_key: Cache key.
            data: Data to cache.
        """
        self.cache[cache_key] = data
        self.cache_expiry[cache_key] = time.time()


class GlassnodeProvider(OnChainDataProvider):
    """Glassnode on-chain data provider."""

    def __init__(self, api_key: str = None):
        """
        Initialize the Glassnode provider.

        Args:
            api_key: Glassnode API key.
        """
        super().__init__(api_key)
        self.base_url = "https://api.glassnode.com/v1"
        self.api_key = api_key or settings.on_chain.glassnode_api_key

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from Glassnode.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        params = params or {}
        params["api_key"] = self.api_key
        
        # Create cache key
        cache_key = f"glassnode_{endpoint}_{str(params)}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get data from Glassnode: {e}")
            return {}

    def get_exchange_inflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Get exchange inflow data.

        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with exchange inflow data.
        """
        params = {
            "a": asset,
            "i": interval,
        }
        
        if since:
            params["s"] = since
        if until:
            params["u"] = until
        
        data = self.get_data("metrics/transactions/transfers_volume_to_exchanges_sum", params)
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"t": "timestamp", "v": "inflow"}, inplace=True)
        df.set_index("timestamp", inplace=True)
        
        return df

    def get_exchange_outflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Get exchange outflow data.

        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with exchange outflow data.
        """
        params = {
            "a": asset,
            "i": interval,
        }
        
        if since:
            params["s"] = since
        if until:
            params["u"] = until
        
        data = self.get_data("metrics/transactions/transfers_volume_from_exchanges_sum", params)
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"t": "timestamp", "v": "outflow"}, inplace=True)
        df.set_index("timestamp", inplace=True)
        
        return df

    def get_miner_outflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Get miner outflow data.

        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with miner outflow data.
        """
        params = {
            "a": asset,
            "i": interval,
        }
        
        if since:
            params["s"] = since
        if until:
            params["u"] = until
        
        data = self.get_data("metrics/mining/volume_mined", params)
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"t": "timestamp", "v": "miner_outflow"}, inplace=True)
        df.set_index("timestamp", inplace=True)
        
        return df

    def get_sopr(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Get SOPR (Spent Output Profit Ratio) data.

        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with SOPR data.
        """
        params = {
            "a": asset,
            "i": interval,
        }
        
        if since:
            params["s"] = since
        if until:
            params["u"] = until
        
        data = self.get_data("metrics/indicators/sopr", params)
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"t": "timestamp", "v": "sopr"}, inplace=True)
        df.set_index("timestamp", inplace=True)
        
        return df


class CryptoQuantProvider(OnChainDataProvider):
    """CryptoQuant on-chain data provider."""

    def __init__(self, api_key: str = None):
        """
        Initialize the CryptoQuant provider.

        Args:
            api_key: CryptoQuant API key.
        """
        super().__init__(api_key)
        self.base_url = "https://api.cryptoquant.com/v1"
        self.api_key = api_key or settings.on_chain.cryptoquant_api_key

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from CryptoQuant.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        params = params or {}
        
        # Create cache key
        cache_key = f"cryptoquant_{endpoint}_{str(params)}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get data from CryptoQuant: {e}")
            return {}

    def get_exchange_netflow(self, asset: str, exchange: str = "all", window: str = "day") -> pd.DataFrame:
        """
        Get exchange netflow data.

        Args:
            asset: Asset symbol (e.g., BTC).
            exchange: Exchange name or "all".
            window: Time window (day, hour).

        Returns:
            DataFrame with exchange netflow data.
        """
        endpoint = f"metrics/exchange/netflow_{window}"
        params = {
            "asset": asset,
            "exchange": exchange,
        }
        
        data = self.get_data(endpoint, params)
        
        if not data or "result" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data["result"])
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        return df


class ExchangeDataProvider(OnChainDataProvider):
    """Exchange data provider that leverages CCXT library."""

    def __init__(self, exchange_name: str = "binance"):
        """Initialize the exchange data provider."""
        super().__init__(None)  # No API key needed, using the exchange wrapper
        self.exchange_name = exchange_name
        from src.exchange.wrapper import ExchangeWrapper
        self.exchange = ExchangeWrapper(exchange_name)
        
    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from the exchange.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        # This method is required by the parent class but not used directly
        return {}
        
    def get_exchange_inflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Simulate exchange inflow using volume and price change.
        
        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with simulated exchange inflow data.
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1d", limit=30)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Calculate price change percentage
            df["price_change"] = df["close"].pct_change()
            
            # Calculate volume change
            df["volume_change"] = df["volume"].pct_change()
            
            # Simulate inflow based on price and volume
            # Falling price + rising volume = inflow to exchanges (bearish)
            df["inflow"] = df["volume"] * -df["price_change"]
            
            # Set negative values to zero
            df["inflow"] = df["inflow"].apply(lambda x: max(x, 0))
            
            df.set_index("timestamp", inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Failed to get simulated exchange inflow data: {e}")
            return pd.DataFrame()

    def get_exchange_outflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Simulate exchange outflow using volume and price change.
        
        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with simulated exchange outflow data.
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1d", limit=30)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Calculate price change percentage
            df["price_change"] = df["close"].pct_change()
            
            # Calculate volume change
            df["volume_change"] = df["volume"].pct_change()
            
            # Simulate outflow based on price and volume
            # Rising price + rising volume = outflow from exchanges (bullish)
            df["outflow"] = df["volume"] * df["price_change"]
            
            # Set negative values to zero
            df["outflow"] = df["outflow"].apply(lambda x: max(x, 0))
            
            df.set_index("timestamp", inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Failed to get simulated exchange outflow data: {e}")
            return pd.DataFrame()

    def get_miner_outflow(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Simulate miner outflow using historical prices and hash rate trends.
        
        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with simulated miner outflow data.
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1d", limit=30)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Generate simulated miner outflow based on price
            # Miners tend to sell more when prices are high
            df["miner_outflow"] = df["close"] * df["volume"] * 0.001  # 0.1% of daily volume as proxy
            
            df.set_index("timestamp", inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Failed to get simulated miner outflow data: {e}")
            return pd.DataFrame()

    def get_sopr(self, asset: str, since: str = None, until: str = None, interval: str = "24h") -> pd.DataFrame:
        """
        Simulate SOPR using price changes.
        
        Args:
            asset: Asset symbol (e.g., BTC).
            since: Start date (YYYY-MM-DD).
            until: End date (YYYY-MM-DD).
            interval: Time interval.

        Returns:
            DataFrame with simulated SOPR data.
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1d", limit=60)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Calculate price change over different timeframes
            df["price_change_1d"] = df["close"].pct_change(1)
            df["price_change_7d"] = df["close"].pct_change(7)
            df["price_change_14d"] = df["close"].pct_change(14)
            
            # Simulate SOPR based on price changes
            # SOPR > 1 means people are selling at a profit
            # SOPR < 1 means people are selling at a loss
            # Calculate using weighted average of price changes
            df["sopr"] = 1 + (0.5 * df["price_change_1d"] + 0.3 * df["price_change_7d"] + 0.2 * df["price_change_14d"])
            
            df.set_index("timestamp", inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Failed to get simulated SOPR data: {e}")
            return pd.DataFrame()


class OnChainAnalyzer:
    """On-chain data analyzer for trading signals."""

    def __init__(self, provider: str = "exchange"):
        """
        Initialize the on-chain analyzer.

        Args:
            provider: On-chain data provider name.
        """
        if provider == "glassnode":
            self.provider = GlassnodeProvider()
        elif provider == "cryptoquant":
            self.provider = CryptoQuantProvider()
        elif provider == "exchange":
            self.provider = ExchangeDataProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_exchange_flow_signal(self, asset: str) -> Tuple[float, str]:
        """
        Get trading signal based on exchange flows.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (signal_strength, signal_type).
            Signal strength is between -1 and 1, where:
            - Negative values indicate bearish signals
            - Positive values indicate bullish signals
            - Magnitude indicates strength
            Signal type is a string description of the signal.
        """
        try:
            # Get exchange inflow and outflow data
            inflow_df = self.provider.get_exchange_inflow(asset)
            outflow_df = self.provider.get_exchange_outflow(asset)
            
            if inflow_df.empty or outflow_df.empty:
                return 0, "No data available"
            
            # Get the latest data points
            latest_inflow = inflow_df.iloc[-1]["inflow"]
            latest_outflow = outflow_df.iloc[-1]["outflow"]
            
            # Calculate net flow
            net_flow = latest_outflow - latest_inflow
            
            # Calculate historical average net flow (last 7 days)
            inflow_7d = inflow_df.iloc[-7:]["inflow"].mean()
            outflow_7d = outflow_df.iloc[-7:]["outflow"].mean()
            avg_net_flow = outflow_7d - inflow_7d
            
            # Calculate signal strength
            if avg_net_flow == 0:
                signal_strength = 0
            else:
                signal_strength = net_flow / abs(avg_net_flow)
                signal_strength = max(min(signal_strength, 1), -1)  # Clamp between -1 and 1
            
            # Determine signal type
            if signal_strength > 0.5:
                signal_type = "Strong outflow from exchanges (bullish)"
            elif signal_strength > 0.2:
                signal_type = "Moderate outflow from exchanges (slightly bullish)"
            elif signal_strength < -0.5:
                signal_type = "Strong inflow to exchanges (bearish)"
            elif signal_strength < -0.2:
                signal_type = "Moderate inflow to exchanges (slightly bearish)"
            else:
                signal_type = "Neutral exchange flow"
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get exchange flow signal: {e}")
            return 0, "Error analyzing exchange flows"

    def get_miner_behavior_signal(self, asset: str) -> Tuple[float, str]:
        """
        Get trading signal based on miner behavior.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (signal_strength, signal_type).
        """
        try:
            # Get miner outflow data
            miner_df = self.provider.get_miner_outflow(asset)
            
            if miner_df.empty:
                return 0, "No data available"
            
            # Get the latest data point
            latest_outflow = miner_df.iloc[-1]["miner_outflow"]
            
            # Calculate historical average (last 30 days)
            avg_outflow = miner_df.iloc[-30:]["miner_outflow"].mean()
            
            # Calculate signal strength
            if avg_outflow == 0:
                signal_strength = 0
            else:
                signal_strength = (avg_outflow - latest_outflow) / avg_outflow
                signal_strength = max(min(signal_strength, 1), -1)  # Clamp between -1 and 1
            
            # Determine signal type
            if signal_strength > 0.5:
                signal_type = "Miners holding (bullish)"
            elif signal_strength > 0.2:
                signal_type = "Miners slightly reducing sales (slightly bullish)"
            elif signal_strength < -0.5:
                signal_type = "Miners selling heavily (bearish)"
            elif signal_strength < -0.2:
                signal_type = "Miners increasing sales (slightly bearish)"
            else:
                signal_type = "Neutral miner behavior"
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get miner behavior signal: {e}")
            return 0, "Error analyzing miner behavior"

    def get_sopr_signal(self, asset: str) -> Tuple[float, str]:
        """
        Get trading signal based on SOPR (Spent Output Profit Ratio).

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (signal_strength, signal_type).
        """
        try:
            # Get SOPR data
            sopr_df = self.provider.get_sopr(asset)
            
            if sopr_df.empty:
                return 0, "No data available"
            
            # Get the latest data point
            latest_sopr = sopr_df.iloc[-1]["sopr"]
            
            # Calculate signal strength
            if latest_sopr > 1:
                # SOPR > 1 means people are selling at a profit (potentially bearish)
                signal_strength = -(latest_sopr - 1)  # Negative signal
            else:
                # SOPR < 1 means people are selling at a loss (potentially bullish)
                signal_strength = 1 - latest_sopr  # Positive signal
            
            # Clamp between -1 and 1
            signal_strength = max(min(signal_strength, 1), -1)
            
            # Determine signal type
            if signal_strength > 0.5:
                signal_type = "Strong capitulation (bullish)"
            elif signal_strength > 0.2:
                signal_type = "Moderate selling at a loss (slightly bullish)"
            elif signal_strength < -0.5:
                signal_type = "Strong profit-taking (bearish)"
            elif signal_strength < -0.2:
                signal_type = "Moderate profit-taking (slightly bearish)"
            else:
                signal_type = "Neutral SOPR"
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get SOPR signal: {e}")
            return 0, "Error analyzing SOPR"

    def get_combined_signal(self, asset: str) -> Tuple[float, List[str]]:
        """
        Get combined trading signal from all on-chain metrics.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (combined_signal_strength, signal_descriptions).
        """
        # Get individual signals
        exchange_signal, exchange_desc = self.get_exchange_flow_signal(asset)
        miner_signal, miner_desc = self.get_miner_behavior_signal(asset)
        sopr_signal, sopr_desc = self.get_sopr_signal(asset)
        
        # Calculate combined signal (weighted average)
        weights = {
            "exchange": 0.4,
            "miner": 0.3,
            "sopr": 0.3,
        }
        
        combined_signal = (
            exchange_signal * weights["exchange"] +
            miner_signal * weights["miner"] +
            sopr_signal * weights["sopr"]
        )
        
        # Compile signal descriptions
        signal_descriptions = [
            f"Exchange Flow: {exchange_desc} (signal: {exchange_signal:.2f})",
            f"Miner Behavior: {miner_desc} (signal: {miner_signal:.2f})",
            f"SOPR: {sopr_desc} (signal: {sopr_signal:.2f})",
            f"Combined Signal: {combined_signal:.2f}",
        ]
        
        return combined_signal, signal_descriptions
