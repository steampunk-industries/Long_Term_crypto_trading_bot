"""
Trading service microservice for the crypto trading bot.
Handles trading operations and strategy execution.
"""

import os
import json
import signal
import sys
import time
import logging
import threading
from typing import Dict, Any, List, Optional

from src.exchange.wrapper import ExchangeWrapper
from src.strategies.base import BaseStrategy
from src.strategies.low_risk import LowRiskStrategy
from src.strategies.medium_risk import MediumRiskStrategy
from src.strategies.high_risk import HighRiskStrategy
from src.utils.database import save_order, save_trade, save_balance, save_bot_state

from microservices.base_service import BaseService, HealthCheck


class TradingService(BaseService):
    """Trading service for executing trading strategies."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = "BTC/USDT",
        strategy_type: str = "low_risk",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
    ):
        """
        Initialize the trading service.

        Args:
            exchange_name: The name of the exchange.
            symbol: The trading symbol.
            strategy_type: The strategy type.
            rabbitmq_url: The URL of the RabbitMQ server.
        """
        super().__init__(
            service_name=f"trading_{strategy_type}",
            rabbitmq_url=rabbitmq_url,
            exchange_name="crypto_trading",
            exchange_type="topic",
            queue_name=f"trading_{strategy_type}_queue",
        )

        self.exchange_name = exchange_name
        self.symbol = symbol
        self.strategy_type = strategy_type
        self.strategy = None
        
        # Trading parameters
        self.active = False
        self.execution_interval = 60.0  # seconds
        self.last_execution = 0
        
        # Thread for strategy execution
        self.execution_thread = None
        
        # Health check
        self.health_check = HealthCheck(self)

    def run(self):
        """Run the trading service."""
        # Initialize the exchange and strategy
        self._initialize()
        
        # Subscribe to command topics
        self.subscribe("trading.command.*", self._handle_command)
        
        # Subscribe to market data topics
        self.subscribe("market.data.*", self._handle_market_data)
        
        # Subscribe to trading parameters topics
        self.subscribe("trading.params.*", self._handle_params)
        
        # Start execution thread
        self.execution_thread = threading.Thread(target=self._execution_loop)
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def _initialize(self):
        """Initialize the exchange and strategy."""
        try:
            # Initialize exchange
            self.exchange = ExchangeWrapper(self.exchange_name)
            
            # Initialize strategy based on type
            if self.strategy_type == "low_risk":
                self.strategy = LowRiskStrategy(
                    exchange_name=self.exchange_name,
                    symbol=self.symbol,
                )
            elif self.strategy_type == "medium_risk":
                self.strategy = MediumRiskStrategy(
                    exchange_name=self.exchange_name,
                    symbol=self.symbol,
                )
            elif self.strategy_type == "high_risk":
                self.strategy = HighRiskStrategy(
                    exchange_name=self.exchange_name,
                    symbol=self.symbol,
                )
            else:
                raise ValueError(f"Unknown strategy type: {self.strategy_type}")
            
            # Replace strategy's exchange with our instance
            self.strategy.exchange = self.exchange
            
            self.logger.info(f"Initialized {self.strategy_type} strategy for {self.symbol} on {self.exchange_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            raise

    def _execution_loop(self):
        """Thread for executing the strategy."""
        while not self.should_stop:
            try:
                # Check if it's time to execute
                if self.active and time.time() - self.last_execution >= self.execution_interval:
                    self._execute_strategy()
                    self.last_execution = time.time()
                
                # Sleep briefly
                time.sleep(1.0)
            except Exception as e:
                self.logger.error(f"Error in execution loop: {e}")

    def _execute_strategy(self):
        """Execute the trading strategy."""
        try:
            # Log execution
            self.logger.info(f"Executing {self.strategy_type} strategy")
            
            # Execute strategy
            self.strategy._run_iteration()
            
            # Publish status
            self._publish_status()
        except Exception as e:
            self.logger.error(f"Error executing strategy: {e}")
            
            # Publish error
            self.publish(
                f"trading.status.{self.strategy_type}.error",
                {
                    "timestamp": time.time(),
                    "error": str(e),
                    "strategy": self.strategy_type,
                    "symbol": self.symbol,
                    "exchange": self.exchange_name,
                },
            )

    def _publish_status(self):
        """Publish trading status."""
        try:
            # Get balance
            balance = self.exchange.fetch_balance()
            
            # Get current price
            price = self.exchange.fetch_market_price(self.symbol)
            
            # Extract base and quote currencies
            base, quote = self.symbol.split("/")
            
            # Calculate total value
            base_value = balance["total"].get(base, 0) * price
            quote_value = balance["total"].get(quote, 0)
            total_value = base_value + quote_value
            
            # Get performance summary if available
            performance = {}
            if hasattr(self.strategy, "get_performance_summary"):
                performance = self.strategy.get_performance_summary()
            
            # Publish status
            self.publish(
                f"trading.status.{self.strategy_type}",
                {
                    "timestamp": time.time(),
                    "strategy": self.strategy_type,
                    "symbol": self.symbol,
                    "exchange": self.exchange_name,
                    "price": price,
                    "balance": {
                        "base": balance["total"].get(base, 0),
                        "quote": balance["total"].get(quote, 0),
                        "total_value": total_value,
                    },
                    "state": self.strategy.state,
                    "performance": performance,
                    "active": self.active,
                },
            )
        except Exception as e:
            self.logger.error(f"Error publishing status: {e}")

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
        
        # Handle start command
        if command == "start":
            self.active = True
            self.logger.info("Trading started")
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "message": "Trading started",
                    },
                    correlation_id=properties.correlation_id,
                )
        
        # Handle stop command
        elif command == "stop":
            self.active = False
            self.logger.info("Trading stopped")
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "message": "Trading stopped",
                    },
                    correlation_id=properties.correlation_id,
                )
        
        # Handle status command
        elif command == "status":
            self._publish_status()
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                status = {
                    "active": self.active,
                    "strategy": self.strategy_type,
                    "symbol": self.symbol,
                    "exchange": self.exchange_name,
                    "state": self.strategy.state,
                }
                
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "status": status,
                    },
                    correlation_id=properties.correlation_id,
                )
        
        # Handle reset command
        elif command == "reset":
            # Reset strategy state
            self.strategy.state = {}
            self.logger.info("Strategy state reset")
            
            # Publish response if this is an RPC call
            if properties.reply_to and properties.correlation_id:
                self.publish(
                    properties.reply_to,
                    {
                        "success": True,
                        "message": "Strategy state reset",
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

    def _handle_market_data(self, topic: str, message: Dict[str, Any], properties):
        """
        Handle market data messages.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Extract data type from topic
        data_type = topic.split(".")[-1]
        
        # Handle price data
        if data_type == "price":
            # Store price in strategy state
            if "price" in message and message.get("symbol") == self.symbol:
                self.strategy.state["external_price"] = message["price"]
                self.logger.debug(f"Received price: {message['price']}")
        
        # Handle ohlcv data
        elif data_type == "ohlcv":
            # Process OHLCV data if applicable
            if message.get("symbol") == self.symbol:
                self.logger.debug(f"Received OHLCV data")
                
                # Store in strategy state if needed
                if "ohlcv" in message:
                    self.strategy.state["external_ohlcv"] = message["ohlcv"]
        
        # Handle unknown data type
        else:
            self.logger.debug(f"Received unknown market data type: {data_type}")

    def _handle_params(self, topic: str, message: Dict[str, Any], properties):
        """
        Handle parameter update messages.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Extract parameter from topic
        param = topic.split(".")[-1]
        
        # Handle execution interval update
        if param == "execution_interval":
            if "value" in message:
                self.execution_interval = float(message["value"])
                self.logger.info(f"Updated execution interval to {self.execution_interval} seconds")
        
        # Handle strategy parameters update
        elif param == "strategy_params":
            if "params" in message:
                # Update strategy parameters
                for key, value in message["params"].items():
                    if hasattr(self.strategy, key):
                        setattr(self.strategy, key, value)
                        self.logger.info(f"Updated strategy parameter {key} to {value}")
        
        # Handle unknown parameter
        else:
            self.logger.warning(f"Unknown parameter: {param}")

    def stop(self):
        """Stop the trading service."""
        # Stop strategy if it's running
        if self.strategy and hasattr(self.strategy, "stop"):
            self.strategy.stop()
        
        # Call parent's stop method
        super().stop()


if __name__ == "__main__":
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Trading service")
    parser.add_argument("--exchange", type=str, default="binance", help="Exchange name")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading symbol")
    parser.add_argument("--strategy", type=str, default="low_risk", help="Strategy type")
    parser.add_argument("--rabbitmq", type=str, default="amqp://guest:guest@localhost:5672/", help="RabbitMQ URL")
    
    args = parser.parse_args()
    
    # Create and start trading service
    service = TradingService(
        exchange_name=args.exchange,
        symbol=args.symbol,
        strategy_type=args.strategy,
        rabbitmq_url=args.rabbitmq,
    )
    
    service.start()
