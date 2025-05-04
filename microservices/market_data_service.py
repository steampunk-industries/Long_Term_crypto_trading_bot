"""
Market data service microservice for the crypto trading bot.
Fetches and distributes market data to other services.
"""

import os
import json
import signal
import sys
import time
import logging
import threading
from typing import Dict, Any, List, Optional
import datetime

from src.exchange.wrapper import ExchangeWrapper
from src.utils.database import save_order, save_trade, save_balance, save_bot_state

from microservices.base_service import BaseService, HealthCheck


class MarketDataService(BaseService):
    """Market data service for fetching and distributing market data."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbols: List[str] = ["BTC/USDT"],
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        fetch_intervals: Dict[str, int] = None,
    ):
        """
        Initialize the market data service.

        Args:
            exchange_name: The name of the exchange.
            symbols: List of trading symbols.
            rabbitmq_url: The URL of the RabbitMQ server.
            fetch_intervals: Dictionary of fetch intervals for different data types (in seconds).
        """
        super().__init__(
            service_name="market_data",
            rabbitmq_url=rabbitmq_url,
            exchange_name="crypto_trading",
            exchange_type="topic",
            queue_name="market_data_queue",
        )

        self.exchange_name = exchange_name
        self.symbols = symbols if isinstance(symbols, list) else [s.strip() for s in symbols.split(",")]
        
        # Default fetch intervals (in seconds)
        self.fetch_intervals = {
            "price": 10,           # Price data every 10 seconds
            "ticker": 30,          # Ticker data every 30 seconds
            "orderbook": 30,       # Orderbook data every 30 seconds
            "ohlcv_1m": 60,        # 1-minute OHLCV data every 60 seconds
            "ohlcv_5m": 300,       # 5-minute OHLCV data every 5 minutes
            "ohlcv_15m": 300,      # 15-minute OHLCV data every 5 minutes
            "ohlcv_1h": 600,       # 1-hour OHLCV data every 10 minutes
            "ohlcv_4h": 1800,      # 4-hour OHLCV data every 30 minutes
            "ohlcv_1d": 3600,      # 1-day OHLCV data every hour
        }
        
        # Override default intervals if provided
        if fetch_intervals:
            for key, value in fetch_intervals.items():
                if key in self.fetch_intervals:
                    self.fetch_intervals[key] = value
        
        # Last fetch timestamps
        self.last_fetch = {key: 0 for key in self.fetch_intervals}
        
        # Thread for fetching data
        self.fetch_thread = None
        
        # Health check
        self.health_check = HealthCheck(self)

    def run(self):
        """Run the market data service."""
        # Initialize the exchange
        self._initialize()
        
        # Subscribe to command topics
        self.subscribe("market.command.*", self._handle_command)
        
        # Start fetch thread
        self.fetch_thread = threading.Thread(target=self._fetch_loop)
        self.fetch_thread.daemon = True
        self.fetch_thread.start()
        
        self.logger.info(f"Market data service started for {self.symbols} on {self.exchange_name}")

    def _initialize(self):
        """Initialize the exchange."""
        try:
            # Initialize exchange
            self.exchange = ExchangeWrapper(self.exchange_name)
            
            self.logger.info(f"Initialized exchange {self.exchange_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange: {e}")
            raise

    def _fetch_loop(self):
        """Thread for fetching market data."""
        while not self.should_stop:
            try:
                # Check if it's time to fetch data for each type
                current_time = time.time()
                
                # Price data
                if current_time - self.last_fetch["price"] >= self.fetch_intervals["price"]:
                    self._fetch_and_publish_prices()
                    self.last_fetch["price"] = current_time
                
                # Ticker data
                if current_time - self.last_fetch["ticker"] >= self.fetch_intervals["ticker"]:
                    self._fetch_and_publish_tickers()
                    self.last_fetch["ticker"] = current_time
                
                # Orderbook data
                if current_time - self.last_fetch["orderbook"] >= self.fetch_intervals["orderbook"]:
                    self._fetch_and_publish_orderbooks()
                    self.last_fetch["orderbook"] = current_time
                
                # OHLCV data for different timeframes
                for timeframe in ["1m", "5m", "15m", "1h", "4h", "1d"]:
                    key = f"ohlcv_{timeframe}"
                    if current_time - self.last_fetch[key] >= self.fetch_intervals[key]:
                        self._fetch_and_publish_ohlcv(timeframe)
                        self.last_fetch[key] = current_time
                
                # Sleep briefly
                time.sleep(1.0)
            except Exception as e:
                self.logger.error(f"Error in fetch loop: {e}")

    def _fetch_and_publish_prices(self):
        """Fetch and publish price data."""
        for symbol in self.symbols:
            try:
                # Fetch price
                price = self.exchange.fetch_market_price(symbol)
                
                # Publish price
                self.publish(
                    f"market.data.price",
                    {
                        "timestamp": time.time(),
                        "exchange": self.exchange_name,
                        "symbol": symbol,
                        "price": price,
                    },
                )
                
                self.logger.debug(f"Published price for {symbol}: {price}")
            except Exception as e:
                self.logger.error(f"Error fetching price for {symbol}: {e}")

    def _fetch_and_publish_tickers(self):
        """Fetch and publish ticker data."""
        for symbol in self.symbols:
            try:
                # Fetch ticker
                ticker = self.exchange.exchange.fetchTicker(symbol)
                
                # Extract relevant data
                data = {
                    "timestamp": time.time(),
                    "exchange": self.exchange_name,
                    "symbol": symbol,
                    "last": ticker.get("last"),
                    "bid": ticker.get("bid"),
                    "ask": ticker.get("ask"),
                    "high": ticker.get("high"),
                    "low": ticker.get("low"),
                    "volume": ticker.get("volume"),
                    "change": ticker.get("change"),
                    "percentage": ticker.get("percentage"),
                    "vwap": ticker.get("vwap"),
                }
                
                # Publish ticker
                self.publish(
                    f"market.data.ticker",
                    data,
                )
                
                self.logger.debug(f"Published ticker for {symbol}")
            except Exception as e:
                self.logger.error(f"Error fetching ticker for {symbol}: {e}")

    def _fetch_and_publish_orderbooks(self):
        """Fetch and publish orderbook data."""
        for symbol in self.symbols:
            try:
                # Fetch orderbook
                orderbook = self.exchange.exchange.fetchOrderBook(symbol, limit=20)
                
                # Extract relevant data
                data = {
                    "timestamp": time.time(),
                    "exchange": self.exchange_name,
                    "symbol": symbol,
                    "bids": orderbook.get("bids", [])[:20],  # Top 20 bids
                    "asks": orderbook.get("asks", [])[:20],  # Top 20 asks
                }
                
                # Publish orderbook
                self.publish(
                    f"market.data.orderbook",
                    data,
                )
                
                self.logger.debug(f"Published orderbook for {symbol}")
            except Exception as e:
                self.logger.error(f"Error fetching orderbook for {symbol}: {e}")

    def _fetch_and_publish_ohlcv(self, timeframe):
        """
        Fetch and publish OHLCV data.
        
        Args:
            timeframe: The timeframe (e.g., "1m", "5m", "15m", "1h", "4h", "1d").
        """
        for symbol in self.symbols:
            try:
                # Fetch OHLCV data
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
                
                # Convert to list of dictionaries for easier processing
                ohlcv_data = []
                for candle in ohlcv:
                    timestamp, open_price, high, low, close, volume = candle
                    ohlcv_data.append({
                        "timestamp": timestamp,
                        "datetime": datetime.datetime.fromtimestamp(timestamp / 1000).isoformat(),
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                    })
                
                # Publish OHLCV data
                self.publish(
                    f"market.data.ohlcv.{timeframe}",
                    {
                        "timestamp": time.time(),
                        "exchange": self.exchange_name,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "data": ohlcv_data,
                    },
                )
                
                self.logger.debug(f"Published {timeframe} OHLCV data for {symbol}")
            except Exception as e:
                self.logger.error(f"Error fetching {timeframe} OHLCV data for {symbol}: {e}")

    def _handle_command(self, topic: str, message: Dict[str, Any], properties):
        """
        Handle command messages.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Extract command from topic
        command = topic.split(".")[-1]
        
        self.logger.info(f"Received command: {command}")
        
        # Handle fetch command
        if command == "fetch":
            # Extract data type from message
            data_type = message.get("data_type", "price")
            symbols = message.get("symbols", self.symbols)
            
            # Fetch the requested data
            if data_type == "price":
                for symbol in symbols:
                    try:
                        price = self.exchange.fetch_market_price(symbol)
                        
                        # Publish price
                        self.publish(
                            f"market.data.price",
                            {
                                "timestamp": time.time(),
                                "exchange": self.exchange_name,
                                "symbol": symbol,
                                "price": price,
                            },
                        )
                    except Exception as e:
                        self.logger.error(f"Error fetching price for {symbol}: {e}")
            
            elif data_type.startswith("ohlcv_"):
                timeframe = data_type.split("_")[1]
                self._fetch_and_publish_ohlcv(timeframe)
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "message": f"Fetched {data_type} data for {symbols}",
                    },
                    correlation_id=properties.correlation_id,
                )
        
        # Handle update_intervals command
        elif command == "update_intervals":
            # Extract intervals from message
            intervals = message.get("intervals", {})
            
            # Update intervals
            for key, value in intervals.items():
                if key in self.fetch_intervals:
                    self.fetch_intervals[key] = value
                    self.logger.info(f"Updated {key} fetch interval to {value} seconds")
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "message": "Fetch intervals updated",
                        "intervals": self.fetch_intervals,
                    },
                    correlation_id=properties.correlation_id,
                )
        
        # Handle add_symbol command
        elif command == "add_symbol":
            # Extract symbol from message
            symbol = message.get("symbol")
            
            if symbol and symbol not in self.symbols:
                self.symbols.append(symbol)
                self.logger.info(f"Added symbol: {symbol}")
                
                # Publish response if this is an RPC call
                if properties.reply_to and properties.correlation_id:
                    self.publish(
                        properties.reply_to,
                        {
                            "success": True,
                            "message": f"Added symbol: {symbol}",
                            "symbols": self.symbols,
                        },
                        correlation_id=properties.correlation_id,
                    )
            else:
                # Publish response if this is an RPC call
                if properties.reply_to and properties.correlation_id:
                    self.publish(
                        properties.reply_to,
                        {
                            "success": False,
                            "message": f"Symbol already exists or is invalid: {symbol}",
                            "symbols": self.symbols,
                        },
                        correlation_id=properties.correlation_id,
                    )
        
        # Handle remove_symbol command
        elif command == "remove_symbol":
            # Extract symbol from message
            symbol = message.get("symbol")
            
            if symbol and symbol in self.symbols:
                self.symbols.remove(symbol)
                self.logger.info(f"Removed symbol: {symbol}")
                
                # Publish response if this is an RPC call
                if properties.reply_to and properties.correlation_id:
                    self.publish(
                        properties.reply_to,
                        {
                            "success": True,
                            "message": f"Removed symbol: {symbol}",
                            "symbols": self.symbols,
                        },
                        correlation_id=properties.correlation_id,
                    )
            else:
                # Publish response if this is an RPC call
                if properties.reply_to and properties.correlation_id:
                    self.publish(
                        properties.reply_to,
                        {
                            "success": False,
                            "message": f"Symbol not found: {symbol}",
                            "symbols": self.symbols,
                        },
                        correlation_id=properties.correlation_id,
                    )
        
        # Handle unknown command
        else:
            self.logger.warning(f"Unknown command: {command}")
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": False,
                        "message": f"Unknown command: {command}",
                    },
                    correlation_id=properties.correlation_id,
                )

    def stop(self):
        """Stop the market data service."""
        self.logger.info("Stopping market data service")
        super().stop()


if __name__ == "__main__":
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Market data service")
    parser.add_argument("--exchange", type=str, default="binance", help="Exchange name")
    parser.add_argument("--symbols", type=str, default="BTC/USDT", help="Comma-separated list of trading symbols")
    parser.add_argument("--rabbitmq", type=str, default="amqp://guest:guest@localhost:5672/", help="RabbitMQ URL")
    
    args = parser.parse_args()
    
    # Create and start market data service
    service = MarketDataService(
        exchange_name=args.exchange,
        symbols=args.symbols,
        rabbitmq_url=args.rabbitmq,
    )
    
    service.start()
