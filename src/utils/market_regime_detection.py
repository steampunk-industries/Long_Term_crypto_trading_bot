"""
Market Regime Detection module.
Detects different market states using various statistical methods including Hidden Markov Models.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum, auto
from datetime import datetime, timedelta
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from src.utils.logging import logger

class MarketRegime(Enum):
    """Enum for different market regimes."""
    UNKNOWN = auto()
    BULLISH_TREND = auto()
    BEARISH_TREND = auto()
    BULLISH_VOLATILE = auto()
    BEARISH_VOLATILE = auto()
    RANGING_LOW_VOL = auto()
    RANGING_HIGH_VOL = auto()
    
    @classmethod
    def to_string(cls, regime):
        """Convert regime enum to human-readable string."""
        mapping = {
            cls.UNKNOWN: "Unknown",
            cls.BULLISH_TREND: "Bullish Trend",
            cls.BEARISH_TREND: "Bearish Trend",
            cls.BULLISH_VOLATILE: "Bullish Volatile",
            cls.BEARISH_VOLATILE: "Bearish Volatile",
            cls.RANGING_LOW_VOL: "Ranging (Low Volatility)",
            cls.RANGING_HIGH_VOL: "Ranging (High Volatility)",
        }
        return mapping.get(regime, "Unknown")

class MarketRegimeDetector:
    """
    Market Regime Detector using Hidden Markov Models.
    
    This class uses HMM to detect different market regimes based on 
    price action, volatility, and other market indicators.
    """
    
    def __init__(
        self,
        n_regimes: int = 5,
        lookback_period: int = 60,
        min_data_points: int = 30,
        hmm_history_size: int = 500,
        refresh_period: int = 24,  # in hours
    ):
        """
        Initialize the Market Regime Detector.
        
        Args:
            n_regimes: Number of regimes to detect
            lookback_period: Number of recent data points to use for regime detection
            min_data_points: Minimum number of data points required for training
            hmm_history_size: Number of historical data points to keep for HMM training
            refresh_period: Period (in hours) after which to retrain the model
        """
        self.n_regimes = n_regimes
        self.lookback_period = lookback_period
        self.min_data_points = min_data_points
        self.hmm_history_size = hmm_history_size
        self.refresh_period = refresh_period
        
        # Initialize HMM model
        self.hmm_model = hmm.GaussianHMM(
            n_components=n_regimes,
            covariance_type="full",
            n_iter=100,
            random_state=42,
        )
        
        # Initialize state
        self.last_training_time = None
        self.is_trained = False
        self.historical_data = []
        self.historical_regimes = []
        self.feature_scaler = StandardScaler()
        self.regime_kmeans = KMeans(n_clusters=n_regimes, random_state=42)
        
        # Initialize logger
        self.logger = logging.getLogger("MarketRegimeDetector")
    
    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract features from OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            NumPy array of features
        """
        # Basic returns and volatility features
        returns = df['close'].pct_change().fillna(0).values
        log_returns = np.log(df['close'] / df['close'].shift(1)).fillna(0).values
        
        # Calculate volatility features
        rolling_std_5 = df['close'].pct_change().rolling(window=5).std().fillna(0).values
        rolling_std_15 = df['close'].pct_change().rolling(window=15).std().fillna(0).values
        
        # Calculate trend features (normalized price relative to moving averages)
        if len(df) >= 20:
            ma_20 = df['close'].rolling(window=20).mean().fillna(method='bfill').values
            price_to_ma_20 = (df['close'].values / ma_20) - 1
        else:
            price_to_ma_20 = np.zeros_like(returns)
            
        if len(df) >= 50:
            ma_50 = df['close'].rolling(window=50).mean().fillna(method='bfill').values
            price_to_ma_50 = (df['close'].values / ma_50) - 1
        else:
            price_to_ma_50 = np.zeros_like(returns)
        
        # Combine features
        features = np.column_stack([
            returns,
            log_returns,
            rolling_std_5,
            rolling_std_15,
            price_to_ma_20,
            price_to_ma_50,
        ])
        
        return features
    
    def _prepare_model_input(self, features: np.ndarray) -> np.ndarray:
        """
        Prepare features for HMM model by scaling and windowing.
        
        Args:
            features: Raw features
            
        Returns:
            Scaled and windowed features
        """
        # Scale features
        scaled_features = self.feature_scaler.transform(features)
        
        return scaled_features
    
    def train(self, df: pd.DataFrame) -> bool:
        """
        Train the HMM model on historical data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if training was successful, False otherwise
        """
        if len(df) < self.min_data_points:
            self.logger.warning(f"Not enough data points for training. Need at least {self.min_data_points}.")
            return False
        
        try:
            # Extract features
            features = self._extract_features(df)
            
            # Fit scaler
            self.feature_scaler.fit(features)
            
            # Prepare model input
            model_input = self._prepare_model_input(features)
            
            # Train HMM model
            self.hmm_model.fit(model_input)
            
            # Predict regimes
            regimes = self.hmm_model.predict(model_input)
            
            # Train K-means on the state space to cluster similar regimes
            state_means = self.hmm_model.means_
            self.regime_kmeans.fit(state_means)
            
            # Store historical data and regimes (limited to hmm_history_size)
            self.historical_data = model_input[-self.hmm_history_size:]
            self.historical_regimes = regimes[-self.hmm_history_size:]
            
            # Update state
            self.last_training_time = datetime.now()
            self.is_trained = True
            
            self.logger.info("Market regime model trained successfully.")
            return True
        
        except Exception as e:
            self.logger.error(f"Error training market regime model: {e}")
            return False
    
    def predict(self, df: pd.DataFrame) -> Tuple[List[MarketRegime], np.ndarray]:
        """
        Predict market regimes for the given data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (list of market regime enums, raw regime indices)
        """
        if not self.is_trained:
            self.logger.warning("Model not trained yet. Returning UNKNOWN regime.")
            return [MarketRegime.UNKNOWN] * len(df), np.zeros(len(df))
        
        try:
            # Check if we need to retrain
            if (self.last_training_time is None or 
                datetime.now() - self.last_training_time > timedelta(hours=self.refresh_period)):
                self.logger.info("Retraining market regime model...")
                self.train(df)
            
            # Extract features
            features = self._extract_features(df)
            
            # Prepare model input
            model_input = self._prepare_model_input(features)
            
            # Predict regimes
            raw_regimes = self.hmm_model.predict(model_input)
            
            # Map regimes to meaningful labels
            labeled_regimes = self._map_regimes_to_labels(raw_regimes, df)
            
            return labeled_regimes, raw_regimes
        
        except Exception as e:
            self.logger.error(f"Error predicting market regimes: {e}")
            return [MarketRegime.UNKNOWN] * len(df), np.zeros(len(df))
    
    def _map_regimes_to_labels(
        self, regimes: np.ndarray, df: pd.DataFrame
    ) -> List[MarketRegime]:
        """
        Map numerical regimes to meaningful labels based on price action.
        
        Args:
            regimes: Raw regime indices
            df: Original OHLCV data
            
        Returns:
            List of market regime enums
        """
        labeled_regimes = []
        
        # Calculate returns for each regime
        regime_returns = {}
        regime_volatility = {}
        
        returns = df['close'].pct_change().fillna(0)
        volatility = returns.rolling(window=5).std().fillna(0)
        
        for i, regime in enumerate(regimes):
            if regime not in regime_returns:
                regime_returns[regime] = []
                regime_volatility[regime] = []
            
            regime_returns[regime].append(returns.iloc[i])
            regime_volatility[regime].append(volatility.iloc[i])
        
        # Calculate average return and volatility for each regime
        regime_avg_return = {}
        regime_avg_volatility = {}
        
        for regime in regime_returns:
            if regime_returns[regime]:
                regime_avg_return[regime] = np.mean(regime_returns[regime])
                regime_avg_volatility[regime] = np.mean(regime_volatility[regime])
            else:
                regime_avg_return[regime] = 0
                regime_avg_volatility[regime] = 0
        
        # Map regimes to labels
        regime_labels = {}
        volatility_threshold = np.median([v for v in regime_avg_volatility.values()])
        
        for regime in regime_avg_return:
            avg_return = regime_avg_return[regime]
            avg_volatility = regime_avg_volatility[regime]
            
            if avg_return > 0.001:  # Bullish
                if avg_volatility > volatility_threshold:
                    regime_labels[regime] = MarketRegime.BULLISH_VOLATILE
                else:
                    regime_labels[regime] = MarketRegime.BULLISH_TREND
            elif avg_return < -0.001:  # Bearish
                if avg_volatility > volatility_threshold:
                    regime_labels[regime] = MarketRegime.BEARISH_VOLATILE
                else:
                    regime_labels[regime] = MarketRegime.BEARISH_TREND
            else:  # Ranging
                if avg_volatility > volatility_threshold:
                    regime_labels[regime] = MarketRegime.RANGING_HIGH_VOL
                else:
                    regime_labels[regime] = MarketRegime.RANGING_LOW_VOL
        
        # Convert raw regimes to labeled regimes
        for regime in regimes:
            labeled_regimes.append(regime_labels.get(regime, MarketRegime.UNKNOWN))
        
        return labeled_regimes
    
    def get_current_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Get the current market regime.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Current market regime
        """
        # Predict regimes
        regimes, _ = self.predict(df)
        
        # Get most recent regime
        if regimes:
            return regimes[-1]
        else:
            return MarketRegime.UNKNOWN
    
    def get_regime_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get statistics about each detected regime.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with regime statistics
        """
        if not self.is_trained:
            return {"error": "Model not trained yet."}
        
        # Predict regimes
        regimes, raw_regimes = self.predict(df)
        
        # Calculate statistics for each regime
        regime_stats = {}
        
        returns = df['close'].pct_change().fillna(0)
        
        for regime in MarketRegime:
            if regime == MarketRegime.UNKNOWN:
                continue
                
            # Get indices for this regime
            indices = [i for i, r in enumerate(regimes) if r == regime]
            
            if not indices:
                continue
                
            # Calculate statistics
            regime_returns = returns.iloc[indices]
            avg_return = regime_returns.mean()
            volatility = regime_returns.std()
            sharpe = avg_return / volatility if volatility > 0 else 0
            
            regime_stats[MarketRegime.to_string(regime)] = {
                "count": len(indices),
                "percentage": len(indices) / len(regimes) * 100,
                "avg_return": avg_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
            }
        
        return regime_stats
    
    def get_regime_transitions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get statistics about regime transitions.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with regime transition statistics
        """
        if not self.is_trained:
            return {"error": "Model not trained yet."}
        
        # Predict regimes
        regimes, _ = self.predict(df)
        
        # Calculate transition matrix
        transitions = {}
        
        for i in range(1, len(regimes)):
            from_regime = regimes[i - 1]
            to_regime = regimes[i]
            
            if from_regime not in transitions:
                transitions[from_regime] = {}
            
            if to_regime not in transitions[from_regime]:
                transitions[from_regime][to_regime] = 0
            
            transitions[from_regime][to_regime] += 1
        
        # Convert to human-readable form
        readable_transitions = {}
        
        for from_regime, to_regimes in transitions.items():
            from_str = MarketRegime.to_string(from_regime)
            readable_transitions[from_str] = {}
            
            total = sum(to_regimes.values())
            
            for to_regime, count in to_regimes.items():
                to_str = MarketRegime.to_string(to_regime)
                readable_transitions[from_str][to_str] = {
                    "count": count,
                    "probability": count / total,
                }
        
        return readable_transitions
