"""
Adaptive Mean Reversion Strategy Module.
This strategy uses Bollinger Bands with adaptive parameters based on market volatility.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from src.strategies.base import BaseStrategy
from src.utils.logging import logger

class AdaptiveMeanReversionStrategy(BaseStrategy):
    """
    Adaptive Mean Reversion Strategy that adjusts parameters based on market volatility.
    Uses Bollinger Bands with dynamic lookback periods and standard deviation multipliers.
    """

    def __init__(
        self,
        exchange_name: str,
        symbol: str,
        base_lookback_period: int = 20,
        base_std_dev_multiplier: float = 2.0,
        position_size_pct: float = 0.1,
        max_open_positions: int = 3,
        profit_target_pct: float = 0.03,
        stop_loss_pct: float = 0.02,
    ):
        """
        Initialize the adaptive mean reversion strategy.

        Args:
            exchange_name: Name of the exchange to use
            symbol: Trading symbol (e.g., 'BTC/USDT')
            base_lookback_period: Base period for moving averages and bands calculation
            base_std_dev_multiplier: Base multiplier for standard deviation in Bollinger Bands
            position_size_pct: Position size as percentage of available balance
            max_open_positions: Maximum number of open positions
            profit_target_pct: Profit target as percentage
            stop_loss_pct: Stop loss as percentage
        """
        super().__init__(exchange_name, symbol)
        
        # Strategy parameters
        self.base_lookback_period = base_lookback_period
        self.base_std_dev_multiplier = base_std_dev_multiplier
        self.position_size_pct = position_size_pct
        self.max_open_positions = max_open_positions
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        
        # Initialize state
        self.state = {
            "open_positions": [],
            "open_orders": [],
            "last_price": None,
            "current_market_regime": "unknown",
            "current_lookback_period": base_lookback_period,
            "current_std_dev_multiplier": base_std_dev_multiplier,
            "last_update_time": None,
            "historical_performance": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit_loss": 0.0,
            },
        }
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{symbol}")

    def calculate_bollinger_bands(
        self, 
        prices: pd.Series, 
        window: int = 20, 
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands for a price series.

        Args:
            prices: Series of price data
            window: Window size for moving average
            num_std: Number of standard deviations for bands

        Returns:
            Tuple of (middle band, upper band, lower band)
        """
        # Calculate rolling mean and standard deviation
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        
        # Calculate upper and lower bands
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        
        return rolling_mean, upper_band, lower_band

    def calculate_adaptive_parameters(self, prices: pd.Series) -> Tuple[int, float]:
        """
        Calculate adaptive parameters based on recent market volatility.

        Args:
            prices: Series of price data

        Returns:
            Tuple of (lookback window, standard deviation multiplier)
        """
        # Calculate returns and volatility
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=self.base_lookback_period).std().iloc[-1]
        
        # Adjust parameters based on volatility
        if volatility > 0.03:  # High volatility
            window = max(10, int(self.base_lookback_period * 0.5))  # Shorter window
            num_std = min(3.0, self.base_std_dev_multiplier * 1.25)  # Wider bands
            
            self.logger.info(f"High volatility detected: {volatility:.4f}. Adjusting parameters: window={window}, std_dev={num_std:.2f}")
            
        elif volatility > 0.015:  # Medium volatility
            window = self.base_lookback_period  # Default window
            num_std = self.base_std_dev_multiplier  # Default bands
            
            self.logger.info(f"Medium volatility detected: {volatility:.4f}. Using base parameters: window={window}, std_dev={num_std:.2f}")
            
        else:  # Low volatility
            window = min(30, int(self.base_lookback_period * 1.5))  # Longer window
            num_std = max(1.5, self.base_std_dev_multiplier * 0.75)  # Tighter bands
            
            self.logger.info(f"Low volatility detected: {volatility:.4f}. Adjusting parameters: window={window}, std_dev={num_std:.2f}")
        
        return window, num_std

    def calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on available balance and position_size_pct.

        Args:
            price: Current market price

        Returns:
            Position size in base currency
        """
        # Get balance
        balance = self.exchange.fetch_balance()
        quote_currency = self.symbol.split('/')[1]
        available_balance = balance['free'].get(quote_currency, 0)
        
        # Calculate position size
        position_value = available_balance * self.position_size_pct
        position_size = position_value / price
        
        # Round to appropriate precision
        # This is a simplified version, in production you should use market info to determine precision
        position_size = round(position_size, 6)
        
        return position_size

    def execute_buy_signal(self, price: float) -> Dict[str, Any]:
        """
        Execute a buy order based on a signal.

        Args:
            price: Current market price

        Returns:
            Order information
        """
        # Check if we already have max positions
        if len(self.state["open_positions"]) >= self.max_open_positions:
            self.logger.info(f"Max open positions ({self.max_open_positions}) reached. Skipping buy signal.")
            return None
        
        # Calculate position size
        position_size = self.calculate_position_size(price)
        
        if position_size <= 0:
            self.logger.warning("Calculated position size is zero or negative. Skipping buy signal.")
            return None
        
        try:
            # Place market buy order
            order = self.exchange.place_market_order(self.symbol, "buy", position_size)
            
            # Log order
            self.logger.info(f"Buy order executed: {position_size} @ {price}")
            
            # Create position entry
            position = {
                "id": order["id"],
                "symbol": self.symbol,
                "type": "long",
                "entry_price": price,
                "amount": position_size,
                "timestamp": order["timestamp"],
                "profit_target": price * (1 + self.profit_target_pct),
                "stop_loss": price * (1 - self.stop_loss_pct),
            }
            
            # Add to open positions
            self.state["open_positions"].append(position)
            
            return order
        except Exception as e:
            self.logger.error(f"Error executing buy signal: {e}")
            return None

    def execute_sell_signal(self, price: float) -> Dict[str, Any]:
        """
        Execute a sell order based on a signal.

        Args:
            price: Current market price

        Returns:
            Order information
        """
        # Calculate position size
        position_size = self.calculate_position_size(price)
        
        if position_size <= 0:
            self.logger.warning("Calculated position size is zero or negative. Skipping sell signal.")
            return None
        
        try:
            # Place market sell order
            order = self.exchange.place_market_order(self.symbol, "sell", position_size)
            
            # Log order
            self.logger.info(f"Sell order executed: {position_size} @ {price}")
            
            return order
        except Exception as e:
            self.logger.error(f"Error executing sell signal: {e}")
            return None

    def manage_positions(self, current_price: float) -> None:
        """
        Manage existing positions, check for take profit or stop loss.

        Args:
            current_price: Current market price
        """
        remaining_positions = []
        
        for position in self.state["open_positions"]:
            # Check if position should be closed
            if position["type"] == "long":
                # Check take profit
                if current_price >= position["profit_target"]:
                    self.logger.info(f"Take profit triggered for position {position['id']} @ {current_price}")
                    
                    try:
                        # Place market sell order
                        order = self.exchange.place_market_order(
                            self.symbol, "sell", position["amount"]
                        )
                        
                        # Update performance stats
                        profit_pct = (current_price - position["entry_price"]) / position["entry_price"]
                        self.state["historical_performance"]["total_trades"] += 1
                        self.state["historical_performance"]["winning_trades"] += 1
                        self.state["historical_performance"]["total_profit_loss"] += profit_pct
                        
                        self.logger.info(f"Closed position with profit: {profit_pct:.2%}")
                    except Exception as e:
                        self.logger.error(f"Error closing position {position['id']}: {e}")
                        # Keep the position if there was an error closing it
                        remaining_positions.append(position)
                
                # Check stop loss
                elif current_price <= position["stop_loss"]:
                    self.logger.info(f"Stop loss triggered for position {position['id']} @ {current_price}")
                    
                    try:
                        # Place market sell order
                        order = self.exchange.place_market_order(
                            self.symbol, "sell", position["amount"]
                        )
                        
                        # Update performance stats
                        loss_pct = (current_price - position["entry_price"]) / position["entry_price"]
                        self.state["historical_performance"]["total_trades"] += 1
                        self.state["historical_performance"]["losing_trades"] += 1
                        self.state["historical_performance"]["total_profit_loss"] += loss_pct
                        
                        self.logger.info(f"Closed position with loss: {loss_pct:.2%}")
                    except Exception as e:
                        self.logger.error(f"Error closing position {position['id']}: {e}")
                        # Keep the position if there was an error closing it
                        remaining_positions.append(position)
                
                # Keep the position if no action was taken
                else:
                    remaining_positions.append(position)
        
        # Update open positions
        self.state["open_positions"] = remaining_positions

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of strategy performance.

        Returns:
            Dictionary with performance metrics
        """
        perf = self.state["historical_performance"]
        
        total_trades = perf["total_trades"]
        if total_trades > 0:
            win_rate = perf["winning_trades"] / total_trades
        else:
            win_rate = 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": perf["winning_trades"],
            "losing_trades": perf["losing_trades"],
            "win_rate": win_rate,
            "total_profit_loss_pct": perf["total_profit_loss"],
            "average_profit_loss_pct": perf["total_profit_loss"] / total_trades if total_trades > 0 else 0,
        }

    def run_strategy(self) -> None:
        """Execute the strategy."""
        try:
            # Fetch historical prices
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, timeframe="1h", limit=50
            )
            
            if not ohlcv or len(ohlcv) < self.base_lookback_period:
                self.logger.error(f"Not enough historical data. Need at least {self.base_lookback_period} candles.")
                return
            
            # Convert to dataframe
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            
            # Get current price
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # Update state
            self.state["last_price"] = current_price
            
            # Calculate adaptive parameters
            window, num_std = self.calculate_adaptive_parameters(df["close"])
            
            # Update state with current parameters
            self.state["current_lookback_period"] = window
            self.state["current_std_dev_multiplier"] = num_std
            
            # Calculate Bollinger Bands
            mean, upper, lower = self.calculate_bollinger_bands(df["close"], window, num_std)
            
            # Get latest values
            latest_mean = mean.iloc[-1]
            latest_upper = upper.iloc[-1]
            latest_lower = lower.iloc[-1]
            
            self.logger.info(f"Current price: {current_price}, Mean: {latest_mean:.2f}, Upper: {latest_upper:.2f}, Lower: {latest_lower:.2f}")
            
            # Manage existing positions
            self.manage_positions(current_price)
            
            # Trading logic
            if current_price < latest_lower:
                # Price below lower band - buy signal
                self.logger.info(f"Buy signal: Price ({current_price}) below lower band ({latest_lower:.2f})")
                self.execute_buy_signal(current_price)
            
            elif current_price > latest_upper:
                # Price above upper band - sell signal
                self.logger.info(f"Sell signal: Price ({current_price}) above upper band ({latest_upper:.2f})")
                self.execute_sell_signal(current_price)
            
            else:
                self.logger.info(f"No signal: Price ({current_price}) within bands")
        
        except Exception as e:
            self.logger.error(f"Error running strategy: {e}")
