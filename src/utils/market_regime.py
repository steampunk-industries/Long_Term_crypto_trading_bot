"""
Market regime detection module for the crypto trading bot.
Provides tools for identifying market regimes (trending, ranging, volatile).
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union

from src.utils.logging import logger


class MarketRegimeDetector:
    """Market regime detector for identifying market conditions."""

    def __init__(
        self,
        volatility_window: int = 20,
        trend_window: int = 50,
        volatility_threshold_high: float = 0.03,
        volatility_threshold_low: float = 0.01,
        trend_threshold: float = 0.5,
    ):
        """
        Initialize the market regime detector.

        Args:
            volatility_window: Window size for volatility calculation.
            trend_window: Window size for trend strength calculation.
            volatility_threshold_high: Threshold for high volatility.
            volatility_threshold_low: Threshold for low volatility.
            trend_threshold: Threshold for trend strength.
        """
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        self.volatility_threshold_high = volatility_threshold_high
        self.volatility_threshold_low = volatility_threshold_low
        self.trend_threshold = trend_threshold

    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Calculate price volatility.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Volatility as standard deviation of returns.
        """
        # Calculate returns
        returns = df["close"].pct_change().dropna()
        
        # Use the most recent window
        recent_returns = returns.iloc[-self.volatility_window:]
        
        # Calculate volatility
        volatility = recent_returns.std()
        
        return volatility

    def calculate_atr(self, df: pd.DataFrame) -> float:
        """
        Calculate Average True Range (ATR).

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            ATR value.
        """
        # Calculate True Range
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = tr.rolling(window=self.volatility_window).mean().iloc[-1]
        
        return atr

    def calculate_adx(self, df: pd.DataFrame) -> float:
        """
        Calculate Average Directional Index (ADX).

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            ADX value.
        """
        # Calculate +DM and -DM
        high = df["high"]
        low = df["low"]
        
        up_move = high.diff()
        down_move = low.diff(-1).abs()
        
        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Calculate True Range
        tr1 = high - low
        tr2 = (high - df["close"].shift(1)).abs()
        tr3 = (low - df["close"].shift(1)).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate smoothed values
        window = 14  # Standard ADX window
        
        tr_smoothed = tr.rolling(window=window).mean()
        pos_dm_smoothed = pd.Series(pos_dm).rolling(window=window).mean()
        neg_dm_smoothed = pd.Series(neg_dm).rolling(window=window).mean()
        
        # Calculate +DI and -DI
        pos_di = 100 * pos_dm_smoothed / tr_smoothed
        neg_di = 100 * neg_dm_smoothed / tr_smoothed
        
        # Calculate DX
        dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di)
        
        # Calculate ADX
        adx = dx.rolling(window=window).mean().iloc[-1]
        
        return adx

    def calculate_trend_strength(self, df: pd.DataFrame) -> Tuple[float, str]:
        """
        Calculate trend strength and direction.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Tuple of (trend_strength, trend_direction).
        """
        # Calculate EMAs
        ema_short = df["close"].ewm(span=20).mean()
        ema_long = df["close"].ewm(span=50).mean()
        
        # Calculate trend direction
        if ema_short.iloc[-1] > ema_long.iloc[-1]:
            trend_direction = "bullish"
        else:
            trend_direction = "bearish"
        
        # Calculate ADX for trend strength
        adx = self.calculate_adx(df)
        
        # Normalize ADX to 0-1 range
        trend_strength = min(adx / 100, 1.0)
        
        return trend_strength, trend_direction

    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect market regime from OHLCV data.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Dictionary with regime detection results.
        """
        try:
            # Ensure required columns exist
            required_columns = ["high", "low", "close", "volume"]
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column '{col}' not found in DataFrame")
            
            # Calculate volatility
            volatility = self.calculate_volatility(df)
            atr = self.calculate_atr(df)
            atr_pct = atr / df["close"].iloc[-1]  # ATR as percentage of price
            
            # Calculate trend strength
            trend_strength, trend_direction = self.calculate_trend_strength(df)
            
            # Determine regime
            if trend_strength > self.trend_threshold:
                if volatility > self.volatility_threshold_high:
                    regime = "volatile_trend"
                    regime_description = f"Volatile {trend_direction} trend"
                else:
                    regime = "stable_trend"
                    regime_description = f"Stable {trend_direction} trend"
            else:
                if volatility > self.volatility_threshold_high:
                    regime = "volatile_range"
                    regime_description = "Volatile range-bound market"
                elif volatility < self.volatility_threshold_low:
                    regime = "low_volatility_range"
                    regime_description = "Low volatility range-bound market"
                else:
                    regime = "normal_range"
                    regime_description = "Normal range-bound market"
            
            return {
                "regime": regime,
                "description": regime_description,
                "volatility": volatility,
                "atr": atr,
                "atr_pct": atr_pct,
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
            }
            
        except Exception as e:
            logger.error(f"Failed to detect market regime: {e}")
            return {
                "regime": "unknown",
                "description": "Failed to detect market regime",
                "error": str(e),
            }

    def get_regime_adjusted_parameters(
        self, 
        df: pd.DataFrame, 
        base_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get regime-adjusted parameters for trading strategies.

        Args:
            df: DataFrame with OHLCV data.
            base_params: Base parameters to adjust.

        Returns:
            Dictionary with adjusted parameters.
        """
        # Detect current regime
        regime_info = self.detect_regime(df)
        regime = regime_info["regime"]
        
        # Create a copy of base parameters
        adjusted_params = base_params.copy()
        
        # Adjust parameters based on regime
        if regime == "volatile_trend":
            # In volatile trends, increase position size for trend-following
            # but use tighter stop-loss
            if "position_size_pct" in adjusted_params:
                adjusted_params["position_size_pct"] *= 1.2
            if "stop_loss_pct" in adjusted_params:
                adjusted_params["stop_loss_pct"] *= 0.8
            if "take_profit_pct" in adjusted_params:
                adjusted_params["take_profit_pct"] *= 1.2
            
        elif regime == "stable_trend":
            # In stable trends, increase position size and use wider stops
            if "position_size_pct" in adjusted_params:
                adjusted_params["position_size_pct"] *= 1.5
            if "stop_loss_pct" in adjusted_params:
                adjusted_params["stop_loss_pct"] *= 1.2
            if "take_profit_pct" in adjusted_params:
                adjusted_params["take_profit_pct"] *= 1.5
            
        elif regime == "volatile_range":
            # In volatile ranges, reduce position size and use wider stops
            if "position_size_pct" in adjusted_params:
                adjusted_params["position_size_pct"] *= 0.7
            if "stop_loss_pct" in adjusted_params:
                adjusted_params["stop_loss_pct"] *= 1.3
            if "take_profit_pct" in adjusted_params:
                adjusted_params["take_profit_pct"] *= 0.8
            
        elif regime == "low_volatility_range":
            # In low volatility ranges, use smaller position sizes
            # and tighter take-profits
            if "position_size_pct" in adjusted_params:
                adjusted_params["position_size_pct"] *= 0.5
            if "take_profit_pct" in adjusted_params:
                adjusted_params["take_profit_pct"] *= 0.6
            
        # Add regime info to parameters
        adjusted_params["market_regime"] = regime
        adjusted_params["regime_description"] = regime_info["description"]
        adjusted_params["volatility"] = regime_info["volatility"]
        adjusted_params["trend_strength"] = regime_info["trend_strength"]
        
        return adjusted_params

    def get_regime_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        """
        Get trading signal based on market regime.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Tuple of (signal_strength, signal_type).
            Signal strength is between -1 and 1, where:
            - Negative values indicate bearish signals
            - Positive values indicate bullish signals
            - Magnitude indicates strength
            Signal type is a string description of the signal.
        """
        try:
            # Detect current regime
            regime_info = self.detect_regime(df)
            regime = regime_info["regime"]
            trend_direction = regime_info["trend_direction"]
            trend_strength = regime_info["trend_strength"]
            
            # Calculate signal strength based on regime and trend
            if "trend" in regime:
                # In trending markets, signal follows trend direction
                if trend_direction == "bullish":
                    signal_strength = trend_strength
                    signal_type = f"Strong bullish trend detected (strength: {trend_strength:.2f})"
                else:
                    signal_strength = -trend_strength
                    signal_type = f"Strong bearish trend detected (strength: {trend_strength:.2f})"
            else:
                # In ranging markets, signal is weaker and based on mean reversion
                # Calculate distance from recent mean
                recent_mean = df["close"].iloc[-20:].mean()
                current_price = df["close"].iloc[-1]
                
                # Calculate distance as percentage
                distance_pct = (current_price - recent_mean) / recent_mean
                
                # Mean reversion signal (opposite of distance)
                signal_strength = -distance_pct * 5  # Scale to get reasonable values
                
                # Clamp signal strength
                signal_strength = max(min(signal_strength, 1.0), -1.0)
                
                if signal_strength > 0:
                    signal_type = f"Mean reversion signal: Price below average in ranging market (bullish)"
                else:
                    signal_type = f"Mean reversion signal: Price above average in ranging market (bearish)"
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get regime signal: {e}")
            return 0, "Error analyzing market regime"

    def get_volatility_adjusted_position_size(
        self, 
        df: pd.DataFrame, 
        base_position_size: float,
        risk_factor: float = 1.0
    ) -> float:
        """
        Calculate volatility-adjusted position size.

        Args:
            df: DataFrame with OHLCV data.
            base_position_size: Base position size.
            risk_factor: Risk factor multiplier (higher = more risk).

        Returns:
            Adjusted position size.
        """
        try:
            # Calculate volatility
            volatility = self.calculate_volatility(df)
            
            # Calculate adjustment factor (inverse of volatility)
            # Higher volatility = smaller position size
            volatility_adjustment = 1.0 / (1.0 + volatility * 10)
            
            # Apply risk factor
            volatility_adjustment *= risk_factor
            
            # Calculate adjusted position size
            adjusted_position_size = base_position_size * volatility_adjustment
            
            return adjusted_position_size
            
        except Exception as e:
            logger.error(f"Failed to calculate volatility-adjusted position size: {e}")
            return base_position_size  # Return base size on error
