"""
Volume profile analysis module for the crypto trading bot.
Provides tools for analyzing volume distribution across price levels.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union

from src.utils.logging import logger


class VolumeProfileAnalyzer:
    """Volume profile analyzer for identifying key support/resistance levels."""

    def __init__(self, num_bins: int = 50, volume_threshold: float = 0.05):
        """
        Initialize the volume profile analyzer.

        Args:
            num_bins: Number of price bins for volume distribution.
            volume_threshold: Threshold for identifying high volume nodes (as fraction of max volume).
        """
        self.num_bins = num_bins
        self.volume_threshold = volume_threshold

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume profile from OHLCV data.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Dictionary with volume profile analysis results.
        """
        try:
            # Ensure required columns exist
            required_columns = ["high", "low", "close", "volume"]
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column '{col}' not found in DataFrame")
            
            # Calculate price range
            price_min = df["low"].min()
            price_max = df["high"].max()
            price_range = price_max - price_min
            
            # Create price bins
            bin_size = price_range / self.num_bins
            bins = np.linspace(price_min, price_max, self.num_bins + 1)
            
            # Initialize volume profile
            volume_profile = np.zeros(self.num_bins)
            
            # Distribute volume across price bins
            for _, row in df.iterrows():
                # Calculate price range for this candle
                candle_min = row["low"]
                candle_max = row["high"]
                candle_range = candle_max - candle_min
                
                # Skip candles with zero range
                if candle_range == 0:
                    continue
                
                # Find bins that overlap with this candle
                bin_indices = np.where((bins[:-1] < candle_max) & (bins[1:] > candle_min))[0]
                
                # Distribute volume proportionally across bins
                for bin_idx in bin_indices:
                    bin_min = bins[bin_idx]
                    bin_max = bins[bin_idx + 1]
                    
                    # Calculate overlap between candle and bin
                    overlap_min = max(candle_min, bin_min)
                    overlap_max = min(candle_max, bin_max)
                    overlap_range = overlap_max - overlap_min
                    
                    # Calculate proportion of candle volume for this bin
                    volume_proportion = overlap_range / candle_range
                    
                    # Add volume to bin
                    volume_profile[bin_idx] += row["volume"] * volume_proportion
            
            # Create result DataFrame
            result_df = pd.DataFrame({
                "price_min": bins[:-1],
                "price_max": bins[1:],
                "price_mid": (bins[:-1] + bins[1:]) / 2,
                "volume": volume_profile,
            })
            
            # Calculate relative volume (as percentage of max)
            max_volume = result_df["volume"].max()
            if max_volume > 0:
                result_df["relative_volume"] = result_df["volume"] / max_volume
            else:
                result_df["relative_volume"] = 0
            
            # Identify high volume nodes (HVNs)
            hvn_threshold = max_volume * self.volume_threshold
            hvn_df = result_df[result_df["volume"] > hvn_threshold].copy()
            
            # Identify low volume nodes (LVNs)
            lvn_df = result_df[result_df["volume"] <= hvn_threshold].copy()
            
            # Identify point of control (POC) - price level with highest volume
            poc_idx = result_df["volume"].argmax()
            poc_price = result_df.iloc[poc_idx]["price_mid"]
            
            # Identify value area (70% of volume)
            result_df = result_df.sort_values("volume", ascending=False)
            cumulative_volume = result_df["volume"].cumsum()
            total_volume = cumulative_volume.iloc[-1]
            value_area_df = result_df[cumulative_volume <= total_volume * 0.7].copy()
            
            if not value_area_df.empty:
                value_area_high = value_area_df["price_mid"].max()
                value_area_low = value_area_df["price_mid"].min()
            else:
                value_area_high = poc_price
                value_area_low = poc_price
            
            # Identify support and resistance levels
            support_resistance = self._identify_support_resistance(result_df, df["close"].iloc[-1])
            
            return {
                "volume_profile": result_df.sort_values("price_mid").to_dict(orient="records"),
                "high_volume_nodes": hvn_df.sort_values("price_mid").to_dict(orient="records"),
                "low_volume_nodes": lvn_df.sort_values("price_mid").to_dict(orient="records"),
                "point_of_control": poc_price,
                "value_area_high": value_area_high,
                "value_area_low": value_area_low,
                "support_levels": support_resistance["support"],
                "resistance_levels": support_resistance["resistance"],
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze volume profile: {e}")
            return {
                "error": str(e),
                "volume_profile": [],
                "high_volume_nodes": [],
                "low_volume_nodes": [],
                "point_of_control": None,
                "value_area_high": None,
                "value_area_low": None,
                "support_levels": [],
                "resistance_levels": [],
            }

    def _identify_support_resistance(self, volume_profile_df: pd.DataFrame, current_price: float) -> Dict[str, List[float]]:
        """
        Identify support and resistance levels from volume profile.

        Args:
            volume_profile_df: DataFrame with volume profile data.
            current_price: Current market price.

        Returns:
            Dictionary with support and resistance levels.
        """
        # Sort by volume in descending order
        sorted_df = volume_profile_df.sort_values("volume", ascending=False)
        
        # Take top 20% of bins by volume
        top_volume_df = sorted_df.head(int(len(sorted_df) * 0.2))
        
        # Separate into support and resistance
        support_levels = top_volume_df[top_volume_df["price_mid"] < current_price]["price_mid"].tolist()
        resistance_levels = top_volume_df[top_volume_df["price_mid"] > current_price]["price_mid"].tolist()
        
        # Sort by price
        support_levels.sort(reverse=True)  # Highest support first
        resistance_levels.sort()  # Lowest resistance first
        
        return {
            "support": support_levels,
            "resistance": resistance_levels,
        }

    def get_closest_levels(self, analysis_result: Dict[str, Any], current_price: float, num_levels: int = 3) -> Dict[str, List[float]]:
        """
        Get closest support and resistance levels to current price.

        Args:
            analysis_result: Result from analyze() method.
            current_price: Current market price.
            num_levels: Number of levels to return.

        Returns:
            Dictionary with closest support and resistance levels.
        """
        support_levels = analysis_result["support_levels"]
        resistance_levels = analysis_result["resistance_levels"]
        
        # Filter and sort support levels
        support_levels = [level for level in support_levels if level < current_price]
        support_levels.sort(reverse=True)  # Highest support first
        
        # Filter and sort resistance levels
        resistance_levels = [level for level in resistance_levels if level > current_price]
        resistance_levels.sort()  # Lowest resistance first
        
        return {
            "support": support_levels[:num_levels],
            "resistance": resistance_levels[:num_levels],
        }

    def calculate_dynamic_grid_levels(self, analysis_result: Dict[str, Any], current_price: float, num_levels: int = 5) -> Dict[str, List[float]]:
        """
        Calculate dynamic grid levels based on volume profile.

        Args:
            analysis_result: Result from analyze() method.
            current_price: Current market price.
            num_levels: Number of grid levels on each side.

        Returns:
            Dictionary with buy and sell grid levels.
        """
        closest_levels = self.get_closest_levels(analysis_result, current_price, num_levels)
        
        # Use support levels for buy grid
        buy_levels = closest_levels["support"]
        
        # Use resistance levels for sell grid
        sell_levels = closest_levels["resistance"]
        
        # If we don't have enough levels, add evenly spaced levels
        if len(buy_levels) < num_levels:
            # Get lowest support level or use a percentage below current price
            lowest_support = buy_levels[-1] if buy_levels else current_price * 0.95
            
            # Calculate additional levels
            additional_levels = num_levels - len(buy_levels)
            step = (current_price - lowest_support) / (additional_levels + 1)
            
            for i in range(additional_levels):
                level = current_price - (i + 1) * step
                buy_levels.append(level)
            
            # Sort levels
            buy_levels.sort(reverse=True)
        
        if len(sell_levels) < num_levels:
            # Get highest resistance level or use a percentage above current price
            highest_resistance = sell_levels[-1] if sell_levels else current_price * 1.05
            
            # Calculate additional levels
            additional_levels = num_levels - len(sell_levels)
            step = (highest_resistance - current_price) / (additional_levels + 1)
            
            for i in range(additional_levels):
                level = current_price + (i + 1) * step
                sell_levels.append(level)
            
            # Sort levels
            sell_levels.sort()
        
        return {
            "buy": buy_levels[:num_levels],
            "sell": sell_levels[:num_levels],
        }

    def get_volume_profile_signal(self, df: pd.DataFrame, current_price: float) -> Tuple[float, str]:
        """
        Get trading signal based on volume profile analysis.

        Args:
            df: DataFrame with OHLCV data.
            current_price: Current market price.

        Returns:
            Tuple of (signal_strength, signal_type).
            Signal strength is between -1 and 1, where:
            - Negative values indicate bearish signals
            - Positive values indicate bullish signals
            - Magnitude indicates strength
            Signal type is a string description of the signal.
        """
        try:
            # Analyze volume profile
            analysis = self.analyze(df)
            
            # Get key levels
            poc = analysis["point_of_control"]
            vah = analysis["value_area_high"]
            val = analysis["value_area_low"]
            
            # Get closest support and resistance
            closest_levels = self.get_closest_levels(analysis, current_price, 1)
            closest_support = closest_levels["support"][0] if closest_levels["support"] else None
            closest_resistance = closest_levels["resistance"][0] if closest_levels["resistance"] else None
            
            # Calculate distances
            if closest_support:
                support_distance = (current_price - closest_support) / current_price
            else:
                support_distance = float('inf')
                
            if closest_resistance:
                resistance_distance = (closest_resistance - current_price) / current_price
            else:
                resistance_distance = float('inf')
            
            # Calculate signal strength based on position relative to value area
            if current_price > vah:
                # Above value area (potentially bearish)
                signal_strength = -0.5
                signal_type = "Price above value area (bearish)"
                
                # If very close to resistance, stronger bearish signal
                if resistance_distance < 0.01:  # Within 1%
                    signal_strength = -0.8
                    signal_type = "Price at strong resistance (strongly bearish)"
                
            elif current_price < val:
                # Below value area (potentially bullish)
                signal_strength = 0.5
                signal_type = "Price below value area (bullish)"
                
                # If very close to support, stronger bullish signal
                if support_distance < 0.01:  # Within 1%
                    signal_strength = 0.8
                    signal_type = "Price at strong support (strongly bullish)"
                
            else:
                # Inside value area (neutral with bias)
                if current_price > poc:
                    # Upper half of value area
                    signal_strength = -0.2
                    signal_type = "Price in upper half of value area (slightly bearish)"
                elif current_price < poc:
                    # Lower half of value area
                    signal_strength = 0.2
                    signal_type = "Price in lower half of value area (slightly bullish)"
                else:
                    # At point of control
                    signal_strength = 0
                    signal_type = "Price at point of control (neutral)"
            
            # Adjust signal based on relative distances to support/resistance
            if support_distance != float('inf') and resistance_distance != float('inf'):
                # If much closer to support than resistance, more bullish
                if support_distance < resistance_distance * 0.3:
                    signal_strength = min(signal_strength + 0.3, 1.0)
                    signal_type += " and close to support"
                
                # If much closer to resistance than support, more bearish
                elif resistance_distance < support_distance * 0.3:
                    signal_strength = max(signal_strength - 0.3, -1.0)
                    signal_type += " and close to resistance"
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get volume profile signal: {e}")
            return 0, "Error analyzing volume profile"
