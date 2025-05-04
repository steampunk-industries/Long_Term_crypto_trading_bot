"""
Medium-risk strategy module for the crypto trading bot.
Implements an enhanced trend-following strategy with advanced indicators.
"""

import datetime
import time
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
# Replace talib with ta library
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator

from src.config import settings
from src.exchange.wrapper import ExchangeWrapper
from src.strategies.base import BaseStrategy
from src.utils.logging import logger
from src.utils.metrics import record_order_created, record_order_filled
from src.utils.market_regime import MarketRegimeDetector
from src.utils.volume_profile import VolumeProfileAnalyzer


class MediumRiskStrategy(BaseStrategy):
    """Medium-risk enhanced trend-following strategy."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = None,
        timeframe: str = "1h",
        ema_short: int = 50,
        ema_long: int = 200,
        rsi_period: int = 14,
        rsi_overbought: int = 70,
        rsi_oversold: int = 30,
        use_adx: bool = True,
        use_volume_profile: bool = True,
        use_market_regime: bool = True,
        adx_threshold: int = 25,
    ):
        """
        Initialize the strategy.

        Args:
            exchange_name: The name of the exchange.
            symbol: The trading symbol.
            timeframe: The timeframe for analysis.
            ema_short: Short EMA period.
            ema_long: Long EMA period.
            rsi_period: RSI period.
            rsi_overbought: RSI overbought threshold.
            rsi_oversold: RSI oversold threshold.
            use_adx: Whether to use ADX for trend confirmation.
            use_volume_profile: Whether to use volume profile analysis.
            use_market_regime: Whether to use market regime detection.
            adx_threshold: ADX threshold for trend strength.
        """
        super().__init__(exchange_name, symbol, "medium_risk")
        self.timeframe = timeframe
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.leverage = settings.trading.medium_risk_leverage
        self.use_adx = use_adx
        self.use_volume_profile = use_volume_profile
        self.use_market_regime = use_market_regime
        self.adx_threshold = adx_threshold
        
        # Initialize enhanced analysis components
        if self.use_volume_profile:
            self.volume_profile_analyzer = VolumeProfileAnalyzer()
            
        if self.use_market_regime:
            self.market_regime_detector = MarketRegimeDetector()
        
        # Initialize state
        if "in_position" not in self.state:
            self.state["in_position"] = False
        if "current_side" not in self.state:
            self.state["current_side"] = None
        if "entry_price" not in self.state:
            self.state["entry_price"] = None
        if "position_size" not in self.state:
            self.state["position_size"] = 0
        if "order_id" not in self.state:
            self.state["order_id"] = None
        if "last_analysis" not in self.state:
            self.state["last_analysis"] = None

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
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit)
            
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

    def analyze_market(self) -> Dict[str, Any]:
        """
        Analyze the market using enhanced technical indicators.

        Returns:
            Dictionary with analysis results.
        """
        try:
            # Fetch OHLCV data
            df = self.fetch_ohlcv_data()
            
            # Calculate basic indicators using ta library
            ema_short_indicator = EMAIndicator(close=df["close"], window=self.ema_short)
            ema_long_indicator = EMAIndicator(close=df["close"], window=self.ema_long)
            rsi_indicator = RSIIndicator(close=df["close"], window=self.rsi_period)
            
            df["ema_short"] = ema_short_indicator.ema_indicator()
            df["ema_long"] = ema_long_indicator.ema_indicator()
            df["rsi"] = rsi_indicator.rsi()
            
            # Calculate ADX for trend strength
            if self.use_adx:
                adx_indicator = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
                df["adx"] = adx_indicator.adx()
                df["plus_di"] = adx_indicator.adx_pos()
                df["minus_di"] = adx_indicator.adx_neg()
            
            # Get the latest values
            latest = df.iloc[-1]
            
            # Determine trend
            is_bullish = latest["ema_short"] > latest["ema_long"]
            
            # Determine RSI conditions
            is_oversold = latest["rsi"] < self.rsi_oversold
            is_overbought = latest["rsi"] > self.rsi_overbought
            
            # Determine trend strength if using ADX
            trend_strength = 0
            if self.use_adx:
                adx_value = latest["adx"]
                trend_strength = adx_value / 100  # Normalize to 0-1 range
                is_strong_trend = adx_value > self.adx_threshold
                trend_direction = "bullish" if latest["plus_di"] > latest["minus_di"] else "bearish"
            else:
                is_strong_trend = True  # Default to true if not using ADX
                trend_direction = "bullish" if is_bullish else "bearish"
            
            # Get volume profile analysis if enabled
            volume_profile_signal = 0
            volume_profile_levels = {}
            if self.use_volume_profile:
                try:
                    # Get volume profile signal
                    volume_profile_signal, _ = self.volume_profile_analyzer.get_volume_profile_signal(df, latest["close"])
                    
                    # Get support/resistance levels
                    volume_profile = self.volume_profile_analyzer.analyze(df)
                    closest_levels = self.volume_profile_analyzer.get_closest_levels(volume_profile, latest["close"])
                    volume_profile_levels = {
                        "support": closest_levels["support"],
                        "resistance": closest_levels["resistance"],
                    }
                except Exception as e:
                    logger.error(f"Failed to analyze volume profile: {e}")
            
            # Get market regime if enabled
            market_regime = {}
            if self.use_market_regime:
                try:
                    regime_info = self.market_regime_detector.detect_regime(df)
                    market_regime = {
                        "regime": regime_info["regime"],
                        "description": regime_info["description"],
                        "volatility": regime_info["volatility"],
                        "trend_strength": regime_info["trend_strength"],
                    }
                except Exception as e:
                    logger.error(f"Failed to detect market regime: {e}")
            
            # Calculate combined signal
            combined_signal = 0
            
            # Base signal from trend and RSI
            if is_bullish:
                combined_signal += 0.5
                if is_oversold:
                    combined_signal += 0.3
                if is_overbought:
                    combined_signal -= 0.2
            else:
                combined_signal -= 0.5
                if is_overbought:
                    combined_signal -= 0.3
                if is_oversold:
                    combined_signal += 0.2
            
            # Add ADX component if enabled
            if self.use_adx:
                if is_strong_trend:
                    if trend_direction == "bullish":
                        combined_signal += 0.2 * trend_strength
                    else:
                        combined_signal -= 0.2 * trend_strength
            
            # Add volume profile component if enabled
            if self.use_volume_profile:
                combined_signal += 0.2 * volume_profile_signal
            
            # Clamp signal to -1 to 1 range
            combined_signal = max(min(combined_signal, 1.0), -1.0)
            
            # Determine final signal
            if combined_signal > 0.3:
                signal = "buy"
            elif combined_signal < -0.3:
                signal = "sell"
            else:
                signal = "hold"
            
            # Store analysis in state
            analysis_result = {
                "timestamp": datetime.datetime.now().isoformat(),
                "price": latest["close"],
                "ema_short": latest["ema_short"],
                "ema_long": latest["ema_long"],
                "rsi": latest["rsi"],
                "is_bullish": is_bullish,
                "is_oversold": is_oversold,
                "is_overbought": is_overbought,
                "combined_signal": combined_signal,
                "signal": signal,
            }
            
            # Add ADX data if enabled
            if self.use_adx:
                analysis_result.update({
                    "adx": latest["adx"],
                    "plus_di": latest["plus_di"],
                    "minus_di": latest["minus_di"],
                    "is_strong_trend": is_strong_trend,
                    "trend_direction": trend_direction,
                    "trend_strength": trend_strength,
                })
            
            # Add volume profile data if enabled
            if self.use_volume_profile:
                analysis_result.update({
                    "volume_profile_signal": volume_profile_signal,
                    "support_levels": volume_profile_levels.get("support", []),
                    "resistance_levels": volume_profile_levels.get("resistance", []),
                })
            
            # Add market regime data if enabled
            if self.use_market_regime:
                analysis_result.update({
                    "market_regime": market_regime,
                })
            
            # Store in state
            self.state["last_analysis"] = analysis_result
            
            return analysis_result
        
        except Exception as e:
            logger.error(f"Failed to analyze market: {e}")
            # Return empty analysis if failed
            return {
                "error": str(e),
                "signal": "hold",  # Default to hold on error
            }

    def calculate_position_size(self, price: float) -> float:
        """
        Calculate the position size based on risk parameters.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        # Use a more aggressive portion of capital for each trade
        capital_to_use = settings.trading.initial_capital * 0.5  # 50% of capital
        
        # Apply leverage
        capital_with_leverage = capital_to_use * self.leverage
        
        # Convert to crypto amount
        position_size = capital_with_leverage / price
        
        # Round to appropriate precision
        return round(position_size, 6)

    def enter_position(self, side: str, price: float) -> None:
        """
        Enter a new position.

        Args:
            side: The position side (buy/sell).
            price: The entry price.
        """
        if self.state["in_position"]:
            logger.warning(f"Already in {self.state['current_side']} position, cannot enter {side}")
            return
        
        try:
            # Calculate position size
            position_size = self.calculate_position_size(price)
            
            # Place market order
            order = self.exchange.place_market_order(self.symbol, side, position_size)
            processed_order = self._process_order(order)
            
            # Update state
            self.state["in_position"] = True
            self.state["current_side"] = side
            self.state["entry_price"] = price
            self.state["position_size"] = position_size
            self.state["order_id"] = processed_order["id"]
            
            # Record metrics
            record_order_created(self.exchange_name, self.symbol, side, self.bot_type)
            record_order_filled(self.exchange_name, self.symbol, side, self.bot_type)
            
            logger.info(f"Entered {side} position at {price} with size {position_size}")
        
        except Exception as e:
            logger.error(f"Failed to enter {side} position: {e}")

    def exit_position(self, price: float) -> None:
        """
        Exit the current position.

        Args:
            price: The exit price.
        """
        if not self.state["in_position"]:
            logger.warning("Not in position, cannot exit")
            return
        
        try:
            # Determine exit side (opposite of entry)
            exit_side = "sell" if self.state["current_side"] == "buy" else "buy"
            
            # Place market order
            order = self.exchange.place_market_order(
                self.symbol, exit_side, self.state["position_size"]
            )
            processed_order = self._process_order(order)
            
            # Calculate profit/loss
            if self.state["current_side"] == "buy":
                pnl_pct = (price - self.state["entry_price"]) / self.state["entry_price"] * 100
            else:
                pnl_pct = (self.state["entry_price"] - price) / self.state["entry_price"] * 100
            
            # Apply leverage to PnL
            pnl_pct *= self.leverage
            
            # Update state
            self.state["in_position"] = False
            self.state["current_side"] = None
            self.state["entry_price"] = None
            self.state["position_size"] = 0
            self.state["order_id"] = None
            
            # Record metrics
            record_order_created(self.exchange_name, self.symbol, exit_side, self.bot_type)
            record_order_filled(self.exchange_name, self.symbol, exit_side, self.bot_type)
            
            logger.info(f"Exited position at {price} with PnL: {pnl_pct:.2f}%")
        
        except Exception as e:
            logger.error(f"Failed to exit position: {e}")

    def manage_risk(self) -> None:
        """Manage risk by checking for stop-loss conditions."""
        if not self.state["in_position"] or self.state["entry_price"] is None:
            return
        
        try:
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # Calculate dynamic stop-loss based on ATR
            try:
                # Fetch historical data
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=30)
                
                # Extract prices
                high_prices = [candle[2] for candle in ohlcv]
                low_prices = [candle[3] for candle in ohlcv]
                close_prices = [candle[4] for candle in ohlcv]
                
                # Calculate ATR
                atr = self.risk_manager.calculate_atr(high_prices, low_prices, close_prices, period=14)
                
                # Calculate stop-loss price using ATR
                stop_price = self.risk_manager.calculate_stop_loss(
                    entry_price=self.state["entry_price"],
                    side=self.state["current_side"],
                    volatility=atr,
                    atr_multiplier=2.0,  # Standard multiplier for medium-risk strategy
                    default_stop_pct=settings.trading.medium_risk_stop_loss,
                    min_stop_pct=0.015,  # Minimum 1.5% stop-loss
                    max_stop_pct=0.05    # Maximum 5% stop-loss
                )
                
                # Store the stop-loss price in state for reference
                self.state["stop_loss_price"] = stop_price
                
            except Exception as e:
                logger.error(f"Error calculating dynamic stop-loss: {e}")
                # Fall back to fixed stop-loss
                if self.state["current_side"] == "buy":
                    stop_price = self.state["entry_price"] * (1 - settings.trading.medium_risk_stop_loss)
                else:
                    stop_price = self.state["entry_price"] * (1 + settings.trading.medium_risk_stop_loss)
                self.state["stop_loss_price"] = stop_price
            
            # Check stop-loss
            if self.state["current_side"] == "buy":
                # For long positions, exit if price falls below stop-loss
                if current_price < stop_price:
                    logger.warning(f"Stop-loss triggered for LONG position at {current_price} (stop: {stop_price})")
                    self.exit_position(current_price)
            else:
                # For short positions, exit if price rises above stop-loss
                if current_price > stop_price:
                    logger.warning(f"Stop-loss triggered for SHORT position at {current_price} (stop: {stop_price})")
                    self.exit_position(current_price)
        
        except Exception as e:
            logger.error(f"Failed to manage risk: {e}")

    def check_correlation_risk(self, other_active_symbols: List[str]) -> bool:
        """
        Check if the current symbol is correlated with any active positions.
        
        Args:
            other_active_symbols: List of symbols with active positions.
            
        Returns:
            True if correlation risk is detected, False otherwise.
        """
        if not other_active_symbols:
            return False
            
        for other_symbol in other_active_symbols:
            if other_symbol == self.symbol:
                continue
                
            if self.correlation_manager.is_correlated(self.symbol, other_symbol, self.exchange):
                logger.warning(f"Correlation risk detected: {self.symbol} is correlated with {other_symbol}")
                return True
                
        return False

    def run_strategy(self) -> None:
        """Run the enhanced trend-following strategy."""
        try:
            # Analyze market with enhanced indicators
            analysis = self.analyze_market()
            
            # Get current price
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # Log analysis summary
            logger.info(f"Analysis: Signal={analysis['signal']}, "
                       f"Combined={analysis.get('combined_signal', 0):.2f}, "
                       f"RSI={analysis.get('rsi', 0):.1f}, "
                       f"Trend={'Bullish' if analysis.get('is_bullish', False) else 'Bearish'}")
            
            # If market regime detection is enabled, adjust strategy parameters
            if self.use_market_regime and "market_regime" in analysis:
                regime = analysis["market_regime"].get("regime", "unknown")
                
                # Log market regime
                logger.info(f"Market regime: {regime} - {analysis['market_regime'].get('description', '')}")
                
                # Adjust strategy parameters based on regime
                if regime == "volatile_trend":
                    # In volatile trends, use tighter stop-loss
                    self.state["stop_loss_multiplier"] = 0.8
                    self.state["take_profit_multiplier"] = 1.2
                elif regime == "stable_trend":
                    # In stable trends, use wider stop-loss
                    self.state["stop_loss_multiplier"] = 1.2
                    self.state["take_profit_multiplier"] = 1.5
                elif regime == "volatile_range":
                    # In volatile ranges, use wider stop-loss
                    self.state["stop_loss_multiplier"] = 1.3
                    self.state["take_profit_multiplier"] = 0.8
                elif regime == "low_volatility_range":
                    # In low volatility ranges, use tighter take-profit
                    self.state["stop_loss_multiplier"] = 1.0
                    self.state["take_profit_multiplier"] = 0.6
                else:
                    # Default values
                    self.state["stop_loss_multiplier"] = 1.0
                    self.state["take_profit_multiplier"] = 1.0
            
            # Manage existing position
            if self.state["in_position"]:
                # Check for exit conditions based on combined signal
                if (self.state["current_side"] == "buy" and analysis["signal"] == "sell") or \
                   (self.state["current_side"] == "sell" and analysis["signal"] == "buy"):
                    logger.info(f"Exit signal for {self.state['current_side']} position at {current_price}")
                    self.exit_position(current_price)
                else:
                    # Check stop-loss and take-profit
                    self.manage_risk()
            
            # Look for entry opportunities
            else:
                # Check for correlation risk with other active positions
                # This would typically be provided by a portfolio manager
                # For demonstration, we'll use a placeholder list
                other_active_symbols = self.state.get("other_active_symbols", [])
                
                # Skip entry if correlation risk is detected
                if self.check_correlation_risk(other_active_symbols):
                    logger.info(f"Skipping entry due to correlation risk for {self.symbol}")
                    return
                
                # Enter long if buy signal
                if analysis["signal"] == "buy":
                    # Additional confirmation for trend strength if using ADX
                    if not self.use_adx or (self.use_adx and analysis.get("is_strong_trend", False)):
                        logger.info(f"Entry signal for LONG position at {current_price}")
                        self.enter_position("buy", current_price)
                    else:
                        logger.info(f"Buy signal but trend not strong enough (ADX: {analysis.get('adx', 0):.1f})")
                
                # Enter short if sell signal
                elif analysis["signal"] == "sell":
                    # Additional confirmation for trend strength if using ADX
                    if not self.use_adx or (self.use_adx and analysis.get("is_strong_trend", False)):
                        logger.info(f"Entry signal for SHORT position at {current_price}")
                        self.enter_position("sell", current_price)
                    else:
                        logger.info(f"Sell signal but trend not strong enough (ADX: {analysis.get('adx', 0):.1f})")
        
        except Exception as e:
            logger.error(f"Error in trend-following strategy: {e}")
