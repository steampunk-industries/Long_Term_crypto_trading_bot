"""
Low-risk strategy module for the crypto trading bot.
Implements an enhanced grid trading / market making strategy with dynamic grid levels.
"""

import datetime
import time
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import settings
from src.exchange.wrapper import ExchangeWrapper, OrderNotFoundError
from src.strategies.base import BaseStrategy
from src.utils.logging import logger
from src.utils.metrics import record_order_created, record_order_cancelled, record_order_filled
from src.utils.volume_profile import VolumeProfileAnalyzer
from src.utils.market_regime import MarketRegimeDetector


class LowRiskStrategy(BaseStrategy):
    """Low-risk enhanced grid trading / market making strategy."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = None,
        grid_levels: int = 5,
        grid_spacing: float = 0.5,
        max_drawdown: float = 0.1,
        max_position_size: float = 0.2,
        max_daily_loss: float = 0.05,
        use_dynamic_grids: bool = True,
        use_volume_profile: bool = True,
        use_market_regime: bool = True,
    ):
        """
        Initialize the strategy.

        Args:
            exchange_name: The name of the exchange.
            symbol: The trading symbol.
            grid_levels: Number of grid levels on each side.
            grid_spacing: Percentage spacing between grid levels.
            max_drawdown: Maximum allowed drawdown as a fraction of capital.
            max_position_size: Maximum position size as a fraction of capital.
            max_daily_loss: Maximum daily loss as a fraction of capital.
            use_dynamic_grids: Whether to use dynamic grid levels based on support/resistance.
            use_volume_profile: Whether to use volume profile for grid placement.
            use_market_regime: Whether to use market regime detection for risk management.
        """
        super().__init__(
            exchange_name, 
            symbol, 
            "low_risk",
            max_drawdown=max_drawdown,
            max_position_size=max_position_size,
            max_daily_loss=max_daily_loss,
        )
        self.grid_levels = grid_levels
        self.grid_spacing = grid_spacing
        self.base_capital = settings.trading.initial_capital
        self.use_dynamic_grids = use_dynamic_grids
        self.use_volume_profile = use_volume_profile
        self.use_market_regime = use_market_regime
        
        # Initialize enhanced analysis components
        if self.use_volume_profile:
            self.volume_profile_analyzer = VolumeProfileAnalyzer()
            
        if self.use_market_regime:
            self.market_regime_detector = MarketRegimeDetector()
        
        # Initialize state
        if "open_orders" not in self.state:
            self.state["open_orders"] = []
        if "last_price" not in self.state:
            self.state["last_price"] = None
        if "grid_prices" not in self.state:
            self.state["grid_prices"] = {"buy": [], "sell": []}
        if "stop_loss_price" not in self.state:
            self.state["stop_loss_price"] = None

    def calculate_position_size(self, price: float) -> float:
        """
        Calculate the position size for each grid level.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        try:
            # Get current balance
            balance = self.exchange.fetch_balance()
            base, quote = self.symbol.split('/')
            quote_balance = balance["free"].get(quote, 0)
            
            # Use risk manager to calculate safe position size
            safe_position_size = self.calculate_volatility_adjusted_position_size(price)
            
            # Calculate grid-specific position size with more aggressive allocation
            fraction = 1 / (1.5 * self.grid_levels)  # More aggressive allocation
            grid_position_size_usd = quote_balance * fraction
            grid_position_size = grid_position_size_usd / price
            
            # Use the smaller of the two position sizes for safety
            position_size = min(safe_position_size, grid_position_size)
            
            # Round to appropriate precision (usually 6 decimal places for crypto)
            return round(position_size, 6)
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Fallback to a more aggressive position size
            total_funds = self.base_capital
            fraction = 1 / (1.5 * self.grid_levels)  # More aggressive
            position_size_usd = total_funds * fraction
            position_size = position_size_usd / price
            return round(position_size, 6)

    def fetch_ohlcv_data(self, limit: int = 250) -> pd.DataFrame:
        """
        Fetch OHLCV data and convert to DataFrame.

        Args:
            limit: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV data.
        """
        try:
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, "1h", limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Set timestamp as index
            df.set_index("timestamp", inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            raise

    def _calculate_grid_prices(self, current_price: float) -> Dict[str, List[float]]:
        """
        Calculate grid prices based on the current price and market analysis.

        Args:
            current_price: The current market price.

        Returns:
            A dictionary with buy and sell grid prices.
        """
        grid_prices = {"buy": [], "sell": []}
        
        # If using dynamic grids based on volume profile
        if self.use_dynamic_grids and self.use_volume_profile:
            try:
                # Fetch OHLCV data
                df = self.fetch_ohlcv_data()
                
                # Analyze volume profile
                volume_profile = self.volume_profile_analyzer.analyze(df)
                
                # Calculate dynamic grid levels
                dynamic_levels = self.volume_profile_analyzer.calculate_dynamic_grid_levels(
                    volume_profile, current_price, self.grid_levels
                )
                
                # Use dynamic levels if available
                if dynamic_levels["buy"] and dynamic_levels["sell"]:
                    logger.info("Using volume profile-based dynamic grid levels")
                    return dynamic_levels
                
            except Exception as e:
                logger.error(f"Failed to calculate dynamic grid levels: {e}")
                # Fall back to standard grid calculation
        
        # Calculate volatility for dynamic grid spacing
        try:
            # Fetch historical data
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, timeframe="1h", limit=20
            )
            
            # Extract close prices
            close_prices = [candle[4] for candle in ohlcv]
            
            # Calculate volatility
            volatility = self.risk_manager.calculate_volatility(close_prices)
            
            # Adjust grid spacing based on volatility
            # Higher volatility = wider grid spacing
            adjusted_spacing = max(self.grid_spacing, self.grid_spacing * (1 + volatility * 10))
            
            logger.info(f"Volatility: {volatility:.4f}, Adjusted grid spacing: {adjusted_spacing:.2f}%")
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            adjusted_spacing = self.grid_spacing
        
        # Calculate buy grid levels below current price
        for i in range(1, self.grid_levels + 1):
            price_level = current_price * (1 - i * (adjusted_spacing / 100))
            grid_prices["buy"].append(round(price_level, 2))
        
        # Calculate sell grid levels above current price
        for i in range(1, self.grid_levels + 1):
            price_level = current_price * (1 + i * (adjusted_spacing / 100))
            grid_prices["sell"].append(round(price_level, 2))
        
        return grid_prices

    def _cancel_existing_orders(self) -> None:
        """Cancel all existing orders."""
        try:
            cancelled_orders = self.exchange.cancel_all_orders(self.symbol)
            for order in cancelled_orders:
                record_order_cancelled(
                    self.exchange_name, self.symbol, order["side"], self.bot_type
                )
                logger.info(f"Cancelled {order['side']} order at {order.get('price')}")
            
            # Clear the open orders list
            self.state["open_orders"] = []
        except Exception as e:
            logger.error(f"Failed to cancel existing orders: {e}")

    def _place_grid_orders(self, current_price: float) -> None:
        """
        Place grid orders around the current price.

        Args:
            current_price: The current market price.
        """
        # Calculate position size
        position_size = self.calculate_position_size(current_price)
        
        # Calculate grid prices
        grid_prices = self._calculate_grid_prices(current_price)
        self.state["grid_prices"] = grid_prices
        
        # Place buy orders
        for price in grid_prices["buy"]:
            try:
                order = self.exchange.place_limit_order(
                    self.symbol, "buy", position_size, price
                )
                processed_order = self._process_order(order)
                self.state["open_orders"].append(processed_order["id"])
                record_order_created(
                    self.exchange_name, self.symbol, "buy", self.bot_type
                )
                logger.info(f"Placed BUY order at {price}")
            except Exception as e:
                logger.error(f"Failed to place buy order at {price}: {e}")
        
        # Place sell orders
        for price in grid_prices["sell"]:
            try:
                order = self.exchange.place_limit_order(
                    self.symbol, "sell", position_size, price
                )
                processed_order = self._process_order(order)
                self.state["open_orders"].append(processed_order["id"])
                record_order_created(
                    self.exchange_name, self.symbol, "sell", self.bot_type
                )
                logger.info(f"Placed SELL order at {price}")
            except Exception as e:
                logger.error(f"Failed to place sell order at {price}: {e}")

    def _check_filled_orders(self) -> None:
        """Check for filled orders and replace them."""
        if not self.state["open_orders"]:
            return
        
        current_price = self.exchange.fetch_market_price(self.symbol)
        position_size = self.calculate_position_size(current_price)
        
        # Create a copy of the list to avoid modification during iteration
        open_orders = self.state["open_orders"].copy()
        
        for order_id in open_orders:
            try:
                order = self.exchange.fetch_order(order_id, self.symbol)
                
                # If order is filled, place a new order on the opposite side
                if order["status"] == "closed":
                    logger.info(f"Order {order_id} filled at {order.get('price')}")
                    record_order_filled(
                        self.exchange_name, self.symbol, order["side"], self.bot_type
                    )
                    
                    # Remove from open orders
                    self.state["open_orders"].remove(order_id)
                    
                    # Place a new order on the opposite side
                    new_side = "sell" if order["side"] == "buy" else "buy"
                    new_price = (
                        order["price"] * (1 + self.grid_spacing / 100)
                        if new_side == "sell"
                        else order["price"] * (1 - self.grid_spacing / 100)
                    )
                    
                    try:
                        new_order = self.exchange.place_limit_order(
                            self.symbol, new_side, position_size, new_price
                        )
                        processed_order = self._process_order(new_order)
                        self.state["open_orders"].append(processed_order["id"])
                        record_order_created(
                            self.exchange_name, self.symbol, new_side, self.bot_type
                        )
                        logger.info(f"Placed {new_side} order at {new_price}")
                    except Exception as e:
                        logger.error(f"Failed to place {new_side} order at {new_price}: {e}")
            
            except OrderNotFoundError:
                # Order not found, remove from open orders
                logger.warning(f"Order {order_id} not found, removing from open orders")
                if order_id in self.state["open_orders"]:
                    self.state["open_orders"].remove(order_id)
            
            except Exception as e:
                logger.error(f"Failed to check order {order_id}: {e}")

    def _should_reset_grid(self, current_price: float) -> bool:
        """
        Determine if the grid should be reset based on price movement.

        Args:
            current_price: The current market price.

        Returns:
            True if the grid should be reset, False otherwise.
        """
        if not self.state["last_price"]:
            return False
        
        # Calculate price change percentage
        price_change_pct = abs(current_price - self.state["last_price"]) / self.state["last_price"] * 100
        
        # Reset if price moved more than half the grid spacing * number of levels
        threshold = (self.grid_spacing * self.grid_levels) / 2
        return price_change_pct > threshold

    def manage_risk(self) -> None:
        """Manage risk by checking for stop-loss conditions."""
        try:
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # In a grid strategy, we use a combination of approaches:
            # 1. Circuit breaker for extreme market conditions
            # 2. Dynamic stop-loss based on volatility
            # 3. Maximum drawdown limits from risk manager
            
            # Check circuit breaker
            if "circuit_breaker_price" in self.state:
                circuit_breaker_price = self.state["circuit_breaker_price"]
                
                # Calculate dynamic stop-loss using the enhanced risk manager
                try:
                    # Fetch historical data
                    ohlcv = self.exchange.fetch_ohlcv(
                        self.symbol, timeframe="1h", limit=30
                    )
                    
                    # Extract prices
                    high_prices = [candle[2] for candle in ohlcv]
                    low_prices = [candle[3] for candle in ohlcv]
                    close_prices = [candle[4] for candle in ohlcv]
                    
                    # Calculate ATR
                    atr = self.risk_manager.calculate_atr(high_prices, low_prices, close_prices)
                    
                    # Calculate stop-loss price using ATR
                    stop_price = self.risk_manager.calculate_stop_loss(
                        entry_price=circuit_breaker_price,
                        side="buy",  # For circuit breaker, we're always concerned with downside risk
                        volatility=atr,
                        atr_multiplier=2.5,  # Conservative multiplier for low-risk strategy
                        default_stop_pct=settings.trading.low_risk_stop_loss,
                        min_stop_pct=0.01,  # Minimum 1% stop-loss
                        max_stop_pct=0.03   # Maximum 3% stop-loss for low-risk
                    )
                    
                    # Calculate stop percentage
                    stop_pct = (circuit_breaker_price - stop_price) / circuit_breaker_price
                    
                    # Store stop-loss price for reference
                    self.state["stop_loss_price"] = stop_price
                    
                except Exception as e:
                    logger.error(f"Error calculating dynamic stop-loss: {e}")
                    # Fall back to fixed stop-loss
                    stop_pct = settings.trading.low_risk_stop_loss
                    stop_price = circuit_breaker_price * (1 - stop_pct)
                    self.state["stop_loss_price"] = stop_price
                
                # If price drops below stop price, cancel all orders
                if current_price < stop_price:
                    logger.warning(f"Circuit breaker triggered at {current_price} (stop: {stop_price:.2f}, {stop_pct:.2%} from entry)")
                    self._cancel_existing_orders()
                    
                    # Set a flag to prevent immediate re-entry
                    self.state["circuit_breaker_triggered"] = True
                    self.state["circuit_breaker_time"] = datetime.datetime.now().timestamp()
            else:
                # Initialize circuit breaker price
                self.state["circuit_breaker_price"] = current_price
            
            # Check overall portfolio risk
            balance = self.exchange.fetch_balance()
            base, quote = self.symbol.split('/')
            total_value = balance["total"].get(quote, 0)
            
            if base in balance["total"]:
                total_value += balance["total"][base] * current_price
            
            # Check if we've hit maximum drawdown
            if "performance" in self.state:
                initial_capital = self.state["performance"]["initial_capital"]
                drawdown = (initial_capital - total_value) / initial_capital
                
                if drawdown > self.risk_manager.max_drawdown:
                    logger.warning(f"Maximum drawdown reached: {drawdown:.2%} > {self.risk_manager.max_drawdown:.2%}")
                    self._cancel_existing_orders()
                    
                    # Set a flag to prevent immediate re-entry
                    self.state["max_drawdown_triggered"] = True
                    self.state["max_drawdown_time"] = datetime.datetime.now().timestamp()
        
        except Exception as e:
            logger.error(f"Failed to manage risk: {e}")

    def analyze_market(self) -> Dict[str, Any]:
        """
        Analyze the market for enhanced grid trading.

        Returns:
            Dictionary with analysis results.
        """
        try:
            # Fetch OHLCV data
            df = self.fetch_ohlcv_data()
            
            # Initialize analysis results
            analysis_results = {
                "timestamp": datetime.datetime.now().isoformat(),
                "price": df["close"].iloc[-1],
            }
            
            # Get volume profile analysis if enabled
            if self.use_volume_profile:
                try:
                    # Analyze volume profile
                    volume_profile = self.volume_profile_analyzer.analyze(df)
                    
                    # Get key levels
                    analysis_results["point_of_control"] = volume_profile["point_of_control"]
                    analysis_results["value_area_high"] = volume_profile["value_area_high"]
                    analysis_results["value_area_low"] = volume_profile["value_area_low"]
                    
                    # Get support/resistance levels
                    current_price = df["close"].iloc[-1]
                    closest_levels = self.volume_profile_analyzer.get_closest_levels(volume_profile, current_price)
                    
                    analysis_results["support_levels"] = closest_levels["support"]
                    analysis_results["resistance_levels"] = closest_levels["resistance"]
                    
                    # Get volume profile signal
                    volume_profile_signal, signal_type = self.volume_profile_analyzer.get_volume_profile_signal(df, current_price)
                    analysis_results["volume_profile_signal"] = volume_profile_signal
                    analysis_results["volume_profile_signal_type"] = signal_type
                    
                except Exception as e:
                    logger.error(f"Failed to analyze volume profile: {e}")
            
            # Get market regime if enabled
            if self.use_market_regime:
                try:
                    # Detect market regime
                    regime_info = self.market_regime_detector.detect_regime(df)
                    
                    analysis_results["market_regime"] = regime_info["regime"]
                    analysis_results["market_regime_description"] = regime_info["description"]
                    analysis_results["volatility"] = regime_info["volatility"]
                    analysis_results["trend_strength"] = regime_info["trend_strength"]
                    analysis_results["trend_direction"] = regime_info["trend_direction"]
                    
                except Exception as e:
                    logger.error(f"Failed to detect market regime: {e}")
            
            # Calculate volatility
            returns = df["close"].pct_change().dropna()
            analysis_results["volatility"] = returns.std()
            
            # Store analysis in state
            self.state["last_analysis"] = analysis_results
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Failed to analyze market: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
            }

    def run_strategy(self) -> None:
        """Run the enhanced grid trading strategy."""
        try:
            # Fetch current price
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # Analyze market if using enhanced features
            if self.use_volume_profile or self.use_market_regime:
                analysis = self.analyze_market()
                
                # Log analysis summary
                if "market_regime" in analysis:
                    logger.info(f"Market regime: {analysis['market_regime']} - {analysis.get('market_regime_description', '')}")
                
                if "volume_profile_signal" in analysis:
                    logger.info(f"Volume profile signal: {analysis['volume_profile_signal']:.2f} - {analysis.get('volume_profile_signal_type', '')}")
                
                # Adjust strategy based on market regime
                if self.use_market_regime and "market_regime" in analysis:
                    regime = analysis["market_regime"]
                    
                    # Adjust grid spacing based on regime
                    if regime == "volatile_trend" or regime == "volatile_range":
                        # Wider grid spacing in volatile markets
                        self.state["grid_spacing_multiplier"] = 1.5
                    elif regime == "stable_trend":
                        # Normal grid spacing in stable trends
                        self.state["grid_spacing_multiplier"] = 1.0
                    elif regime == "low_volatility_range":
                        # Tighter grid spacing in low volatility
                        self.state["grid_spacing_multiplier"] = 0.8
                    else:
                        # Default
                        self.state["grid_spacing_multiplier"] = 1.0
            
            # Check if circuit breaker was triggered
            if self.state.get("circuit_breaker_triggered", False):
                # Wait for a cooldown period (e.g., 1 hour) before re-entering
                cooldown_period = 3600  # 1 hour in seconds
                current_time = datetime.datetime.now().timestamp()
                
                if current_time - self.state.get("circuit_breaker_time", 0) > cooldown_period:
                    logger.info("Circuit breaker cooldown period ended, resuming trading")
                    self.state["circuit_breaker_triggered"] = False
                    self.state["circuit_breaker_price"] = current_price
                else:
                    logger.info("Circuit breaker cooldown period active, not placing orders")
                    return
            
            # Check if maximum drawdown was triggered
            if self.state.get("max_drawdown_triggered", False):
                # Wait for a longer cooldown period (e.g., 24 hours) before re-entering
                cooldown_period = 86400  # 24 hours in seconds
                current_time = datetime.datetime.now().timestamp()
                
                if current_time - self.state.get("max_drawdown_time", 0) > cooldown_period:
                    logger.info("Maximum drawdown cooldown period ended, resuming trading")
                    self.state["max_drawdown_triggered"] = False
                else:
                    logger.info("Maximum drawdown cooldown period active, not placing orders")
                    return
            
            # Check if we need to reset the grid
            if not self.state["open_orders"] or self._should_reset_grid(current_price):
                logger.info(f"Resetting grid at price {current_price}")
                
                # Cancel existing orders
                self._cancel_existing_orders()
                
                # Place new grid orders
                self._place_grid_orders(current_price)
                
                # Update last price
                self.state["last_price"] = current_price
                
                # Update circuit breaker price
                self.state["circuit_breaker_price"] = current_price
            
            # Check for filled orders and replace them
            self._check_filled_orders()
            
            # Manage risk
            self.manage_risk()
            
            # Log performance metrics periodically (every hour)
            current_time = datetime.datetime.now()
            last_metrics_time = self.state.get("last_metrics_time")
            
            if not last_metrics_time or (current_time - datetime.datetime.fromisoformat(last_metrics_time)).total_seconds() > 3600:
                performance = self.get_performance_summary()
                logger.info(f"Performance metrics: Return: {performance['total_return_pct']}, Drawdown: {performance['max_drawdown_pct']}")
                self.state["last_metrics_time"] = current_time.isoformat()
            
        except Exception as e:
            logger.error(f"Error in grid strategy: {e}")
