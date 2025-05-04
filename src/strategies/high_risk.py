"""
High-risk strategy module for the crypto trading bot.
Implements an AI-powered scalping strategy with enhanced market analysis.
"""

import datetime
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
# Replace talib with ta library
from ta.trend import EMAIndicator, ADXIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
# Import necessary functions for CCI calculation
import pandas as pd
import numpy as np

from src.config import settings
from src.exchange.wrapper import ExchangeWrapper

# Try to import ScalpingModel, but don't fail if TensorFlow is missing
try:
    from src.models.scalping_model import ScalpingModel
    SCALPING_MODEL_AVAILABLE = True
except ImportError:
    SCALPING_MODEL_AVAILABLE = False
    print("TensorFlow not available, scalping model will be disabled")
from src.strategies.base import BaseStrategy
from src.utils.logging import logger
from src.utils.metrics import record_order_created, record_order_filled
from src.utils.on_chain_data import OnChainAnalyzer
from src.utils.sentiment_analysis import SentimentAnalyzer
from src.utils.volume_profile import VolumeProfileAnalyzer
from src.utils.market_regime import MarketRegimeDetector


class HighRiskStrategy(BaseStrategy):
    """High-risk AI-powered scalping strategy with enhanced market analysis."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = None,
        timeframe: str = "5m",
        model_path: Optional[str] = None,
        sequence_length: int = 60,
        prediction_horizon: int = 5,
        use_on_chain: bool = True,
        use_sentiment: bool = True,
        use_volume_profile: bool = True,
        use_market_regime: bool = True,
        use_alternative_data: bool = True,
    ):
        """
        Initialize the strategy.

        Args:
            exchange_name: The name of the exchange.
            symbol: The trading symbol.
            timeframe: The timeframe for analysis.
            model_path: Path to a saved model.
            sequence_length: Length of input sequences.
            prediction_horizon: Number of steps to predict ahead.
            use_on_chain: Whether to use on-chain data analysis.
            use_sentiment: Whether to use sentiment analysis.
            use_volume_profile: Whether to use volume profile analysis.
            use_market_regime: Whether to use market regime detection.
            use_alternative_data: Whether to use alternative data sources instead of expensive APIs.
        """
        super().__init__(exchange_name, symbol, "high_risk")
        self.timeframe = timeframe
        self.leverage = settings.trading.high_risk_leverage
        
        # Read environment configuration
        self.use_alternative_data = use_alternative_data or os.environ.get("USE_ALTERNATIVE_DATA", "true").lower() == "true"
        self.exchange_data_provider = os.environ.get("EXCHANGE_DATA_PROVIDER", "binance")
        
        # Check if ScalpingModel is available
        self.model_enabled = SCALPING_MODEL_AVAILABLE
        
        if self.model_enabled:
            # Initialize model
            model_dir = os.path.join("models", "scalping")
            os.makedirs(model_dir, exist_ok=True)
            
            if model_path is None:
                model_path = os.path.join(model_dir, f"{self.symbol.replace('/', '_')}_model")
            
            self.model = ScalpingModel(
                model_path=model_path if os.path.exists(model_path) else None,
                sequence_length=sequence_length,
                prediction_horizon=prediction_horizon,
            )
        else:
            logger.warning("ScalpingModel not available, using traditional technical analysis instead")
            self.model = None
        
        # Initialize enhanced analysis components
        self.use_on_chain = use_on_chain
        self.use_sentiment = use_sentiment
        self.use_volume_profile = use_volume_profile
        self.use_market_regime = use_market_regime
        
        if self.use_on_chain:
            # Use exchange data provider if specified
            if self.use_alternative_data:
                logger.info("Using exchange-based on-chain data simulation")
                self.on_chain_analyzer = OnChainAnalyzer(provider="exchange")
            else:
                self.on_chain_analyzer = OnChainAnalyzer(provider="glassnode")
            
        if self.use_sentiment:
            # Pass use_alternative_data setting to SentimentAnalyzer
            self.sentiment_analyzer = SentimentAnalyzer(use_alternative_data=self.use_alternative_data)
            
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
        if "last_prediction" not in self.state:
            self.state["last_prediction"] = None
        if "trades" not in self.state:
            self.state["trades"] = []
        if "model_trained" not in self.state:
            self.state["model_trained"] = False

    def fetch_and_prepare_data(self, limit: int = 500) -> pd.DataFrame:
        """
        Fetch OHLCV data and prepare it for the model with enhanced features.

        Args:
            limit: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV and enhanced indicator data.
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
            
            # Calculate basic indicators using the ta library
            # RSI
            rsi_indicator = RSIIndicator(close=df["close"], window=14)
            df["rsi"] = rsi_indicator.rsi()
            
            # EMAs
            ema_short_indicator = EMAIndicator(close=df["close"], window=9)
            ema_long_indicator = EMAIndicator(close=df["close"], window=21)
            df["ema_short"] = ema_short_indicator.ema_indicator()
            df["ema_long"] = ema_long_indicator.ema_indicator()
            
            # Calculate MACD
            macd_indicator = MACD(close=df["close"], window_fast=12, window_slow=26, window_sign=9)
            df["macd"] = macd_indicator.macd()
            df["macd_signal"] = macd_indicator.macd_signal()
            df["macd_hist"] = macd_indicator.macd_diff()
            
            # Calculate Bollinger Bands
            bollinger = BollingerBands(close=df["close"], window=20, window_dev=2)
            df["bb_upper"] = bollinger.bollinger_hband()
            df["bb_middle"] = bollinger.bollinger_mavg()
            df["bb_lower"] = bollinger.bollinger_lband()
            
            # Calculate ATR (Average True Range)
            atr_indicator = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
            df["atr"] = atr_indicator.average_true_range()
            
            # Calculate OBV (On-Balance Volume)
            obv_indicator = OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"])
            df["obv"] = obv_indicator.on_balance_volume()
            
            # Calculate ADX (Average Directional Index)
            adx_indicator = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
            df["adx"] = adx_indicator.adx()
            
            # Calculate CCI (Commodity Channel Index) manually
            # CCI = (Typical Price - SMA of Typical Price) / (0.015 * Mean Deviation)
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            tp_sma = typical_price.rolling(window=14).mean()
            # Calculate mean deviation
            mean_deviation = typical_price.rolling(window=14).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
            df["cci"] = (typical_price - tp_sma) / (0.015 * mean_deviation)
            
            # Calculate price and volume changes
            df["price_change"] = df["close"].pct_change(periods=1)
            df["volume_change"] = df["volume"].pct_change(periods=1)
            
            # Calculate price volatility (rolling standard deviation)
            df["price_volatility"] = df["close"].pct_change().rolling(window=14).std()
            
            # Drop NaN values
            df.dropna(inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to fetch and prepare data: {e}")
            raise

    def train_model(self, epochs: int = 50) -> None:
        """
        Train the model with historical data.

        Args:
            epochs: Number of training epochs.
        """
        try:
            # Fetch and prepare data
            df = self.fetch_and_prepare_data(limit=5000)  # Use more data for training
            
            if len(df) < 1000:
                logger.warning("Not enough data for training")
                return
            
            # Train model
            logger.info(f"Training model with {len(df)} data points")
            history = self.model.train(df, epochs=epochs)
            
            # Save model
            model_path = os.path.join("models", "scalping", f"{self.symbol.replace('/', '_')}_model")
            self.model.save_model(model_path)
            
            # Update state
            self.state["model_trained"] = True
            self.state["last_training"] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "epochs": epochs,
                "data_points": len(df),
                "final_accuracy": history["accuracy"][-1] if "accuracy" in history else None,
            }
            
            logger.info(f"Model trained and saved to {model_path}")
        
        except Exception as e:
            logger.error(f"Failed to train model: {e}")

    def _get_technical_prediction(self, df: pd.DataFrame) -> int:
        """
        Get prediction based on technical indicators when ML model is not available.
        
        Args:
            df: DataFrame with OHLCV and indicator data.
            
        Returns:
            Prediction: -1 (sell), 0 (hold), 1 (buy)
        """
        try:
            # Get the latest data point
            latest = df.iloc[-1]
            
            # Extract indicator values
            rsi = latest["rsi"]
            ema_short = latest["ema_short"]
            ema_long = latest["ema_long"]
            macd = latest["macd"]
            macd_signal = latest["macd_signal"]
            bb_upper = latest["bb_upper"]
            bb_lower = latest["bb_lower"]
            close = latest["close"]
            adx = latest["adx"]
            cci = latest["cci"]
            
            # Initialize signal counters
            buy_signals = 0
            sell_signals = 0
            
            # RSI signals (oversold/overbought)
            if rsi < 30:
                buy_signals += 1
            elif rsi > 70:
                sell_signals += 1
            
            # MACD signals (crossover)
            if macd > macd_signal:
                buy_signals += 1
            elif macd < macd_signal:
                sell_signals += 1
            
            # EMA signals (trend direction)
            if ema_short > ema_long:
                buy_signals += 1
            elif ema_short < ema_long:
                sell_signals += 1
            
            # Bollinger Bands signals (price breakout)
            if close > bb_upper:
                sell_signals += 1  # Potential reversal from overbought
            elif close < bb_lower:
                buy_signals += 1   # Potential reversal from oversold
            
            # ADX signal (trend strength)
            trend_strength = adx / 100  # Normalize to 0-1
            
            # CCI signals (momentum)
            if cci > 100:
                sell_signals += 1  # Overbought
            elif cci < -100:
                buy_signals += 1   # Oversold
            
            # Apply trend strength as a multiplier
            if adx > 25:  # Strong trend
                if ema_short > ema_long:  # Uptrend
                    buy_signals *= 1.5
                else:  # Downtrend
                    sell_signals *= 1.5
            
            # Make prediction based on signal balance
            if buy_signals > sell_signals * 1.5:
                return 1  # Strong buy
            elif sell_signals > buy_signals * 1.5:
                return -1  # Strong sell
            elif buy_signals > sell_signals:
                return 1  # Weak buy
            elif sell_signals > buy_signals:
                return -1  # Weak sell
            else:
                return 0  # Hold
                
        except Exception as e:
            logger.error(f"Error in technical prediction: {e}")
            return 0  # Default to hold on error
    
    def get_prediction(self) -> Tuple[int, Dict[str, Any]]:
        """
        Get a prediction from the model and enhanced analysis.

        Returns:
            Tuple of (prediction, analysis_results).
            Prediction: -1 (sell), 0 (hold), 1 (buy)
            analysis_results: Dictionary with analysis results.
        """
        try:
            # Fetch and prepare data
            df = self.fetch_and_prepare_data()
            
            # Get AI model prediction if available, otherwise use technical indicators
            if self.model_enabled and self.model is not None:
                model_prediction = self.model.predict(df)
            else:
                # Use technical indicators for prediction
                model_prediction = self._get_technical_prediction(df)
            
            # Initialize analysis results
            analysis_results = {
                "model_prediction": model_prediction,
                "on_chain_signal": 0,
                "sentiment_signal": 0,
                "volume_profile_signal": 0,
                "market_regime_signal": 0,
                "combined_signal": 0,
                "signal_details": {},
            }
            
            # Get current price
            current_price = df["close"].iloc[-1]
            
            # Get base currency from symbol (e.g., "BTC" from "BTC/USDT")
            base_currency = self.symbol.split('/')[0]
            
            # Get on-chain data signal
            if self.use_on_chain:
                try:
                    on_chain_signal, on_chain_details = self.on_chain_analyzer.get_combined_signal(base_currency)
                    analysis_results["on_chain_signal"] = on_chain_signal
                    analysis_results["signal_details"]["on_chain"] = on_chain_details
                    logger.info(f"On-chain analysis for {base_currency}: {on_chain_signal:.2f}")
                except Exception as e:
                    logger.error(f"Failed to get on-chain signal: {e}")
                    analysis_results["on_chain_signal"] = 0
                    analysis_results["signal_details"]["on_chain"] = f"Error: {str(e)}"
            
            # Get sentiment signal - uses alternative data if configured
            if self.use_sentiment:
                try:
                    sentiment_signal, sentiment_type = self.sentiment_analyzer.get_sentiment_signal(base_currency)
                    analysis_results["sentiment_signal"] = sentiment_signal
                    analysis_results["signal_details"]["sentiment"] = sentiment_type
                    logger.info(f"Sentiment analysis for {base_currency}: {sentiment_signal:.2f} ({sentiment_type})")
                except Exception as e:
                    logger.error(f"Failed to get sentiment signal: {e}")
                    analysis_results["sentiment_signal"] = 0
                    analysis_results["signal_details"]["sentiment"] = f"Error: {str(e)}"
            
            # Get volume profile signal
            if self.use_volume_profile:
                try:
                    volume_profile_signal, volume_profile_type = self.volume_profile_analyzer.get_volume_profile_signal(df, current_price)
                    analysis_results["volume_profile_signal"] = volume_profile_signal
                    analysis_results["signal_details"]["volume_profile"] = volume_profile_type
                except Exception as e:
                    logger.error(f"Failed to get volume profile signal: {e}")
            
            # Get market regime signal
            if self.use_market_regime:
                try:
                    market_regime_signal, market_regime_type = self.market_regime_detector.get_regime_signal(df)
                    analysis_results["market_regime_signal"] = market_regime_signal
                    analysis_results["signal_details"]["market_regime"] = market_regime_type
                    
                    # Get regime-adjusted parameters
                    regime_info = self.market_regime_detector.detect_regime(df)
                    analysis_results["signal_details"]["market_regime_info"] = regime_info
                except Exception as e:
                    logger.error(f"Failed to get market regime signal: {e}")
            
            # Calculate combined signal with weighted average
            # Adjust weights based on available data sources
            if self.use_alternative_data:
                weights = {
                    "model": 0.4,
                    "on_chain": 0.2,              # Increased from 0.15 since our simulated on-chain data is more reliable
                    "sentiment": 0.2,             # Increased from 0.15 since we have multiple sentiment sources
                    "volume_profile": 0.1,        # Decreased from 0.15 to give more weight to on-chain and sentiment
                    "market_regime": 0.1,         # Decreased from 0.15 to give more weight to on-chain and sentiment
                }
            else:
                weights = {
                    "model": 0.4,
                    "on_chain": 0.15,
                    "sentiment": 0.15,
                    "volume_profile": 0.15,
                    "market_regime": 0.15,
                }
            
            # Convert model prediction to signal strength
            model_signal = float(model_prediction)
            
            # Calculate combined signal
            combined_signal = (
                model_signal * weights["model"] +
                analysis_results["on_chain_signal"] * weights["on_chain"] +
                analysis_results["sentiment_signal"] * weights["sentiment"] +
                analysis_results["volume_profile_signal"] * weights["volume_profile"] +
                analysis_results["market_regime_signal"] * weights["market_regime"]
            )
            
            analysis_results["combined_signal"] = combined_signal
            analysis_results["weights"] = weights
            
            # Convert combined signal to prediction
            if combined_signal > 0.3:
                final_prediction = 1  # buy
            elif combined_signal < -0.3:
                final_prediction = -1  # sell
            else:
                final_prediction = 0  # hold
            
            # Update state
            self.state["last_prediction"] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "model_prediction": model_prediction,
                "final_prediction": final_prediction,
                "combined_signal": combined_signal,
                "price": current_price,
            }
            
            return final_prediction, analysis_results
        
        except Exception as e:
            logger.error(f"Failed to get prediction: {e}")
            return 0, {"error": str(e)}  # Default to hold

    def calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        # Use a more aggressive portion of capital for each trade (increased from 15% to 40%)
        capital_to_use = settings.trading.initial_capital * 0.40  # 40% of capital
        
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
            self.state["entry_time"] = datetime.datetime.now().isoformat()
            
            # Record metrics
            record_order_created(self.exchange_name, self.symbol, side, self.bot_type)
            record_order_filled(self.exchange_name, self.symbol, side, self.bot_type)
            
            logger.info(f"Entered {side} position at {price} with size {position_size}")
        
        except Exception as e:
            logger.error(f"Failed to enter {side} position: {e}")

    def exit_position(self, price: float, reason: str = "signal") -> None:
        """
        Exit the current position.

        Args:
            price: The exit price.
            reason: The reason for exiting.
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
            
            # Record trade
            trade = {
                "entry_time": self.state["entry_time"],
                "exit_time": datetime.datetime.now().isoformat(),
                "side": self.state["current_side"],
                "entry_price": self.state["entry_price"],
                "exit_price": price,
                "position_size": self.state["position_size"],
                "pnl_pct": pnl_pct,
                "reason": reason,
            }
            self.state["trades"].append(trade)
            
            # Update state
            self.state["in_position"] = False
            self.state["current_side"] = None
            self.state["entry_price"] = None
            self.state["position_size"] = 0
            self.state["order_id"] = None
            self.state["entry_time"] = None
            
            # Record metrics
            record_order_created(self.exchange_name, self.symbol, exit_side, self.bot_type)
            record_order_filled(self.exchange_name, self.symbol, exit_side, self.bot_type)
            
            logger.info(f"Exited position at {price} with PnL: {pnl_pct:.2f}% ({reason})")
        
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
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe="5m", limit=30)
                
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
                    atr_multiplier=3.0,  # Higher multiplier for high-risk strategy
                    default_stop_pct=settings.trading.high_risk_stop_loss,
                    min_stop_pct=0.02,  # Minimum 2% stop-loss
                    max_stop_pct=0.08   # Maximum 8% stop-loss
                )
                
                # Store the stop-loss price in state for reference
                self.state["stop_loss_price"] = stop_price
                
            except Exception as e:
                logger.error(f"Error calculating dynamic stop-loss: {e}")
                # Fall back to fixed stop-loss
                if self.state["current_side"] == "buy":
                    stop_price = self.state["entry_price"] * (1 - settings.trading.high_risk_stop_loss)
                else:
                    stop_price = self.state["entry_price"] * (1 + settings.trading.high_risk_stop_loss)
            
            # Check stop-loss
            if self.state["current_side"] == "buy":
                # For long positions, exit if price falls below stop-loss
                if current_price < stop_price:
                    logger.warning(f"Stop-loss triggered for LONG position at {current_price} (stop: {stop_price})")
                    self.exit_position(current_price, reason="stop_loss")
            else:
                # For short positions, exit if price rises above stop-loss
                if current_price > stop_price:
                    logger.warning(f"Stop-loss triggered for SHORT position at {current_price} (stop: {stop_price})")
                    self.exit_position(current_price, reason="stop_loss")
            
            # Calculate take-profit as a multiple of the distance to stop-loss
            if self.state["current_side"] == "buy":
                stop_distance = self.state["entry_price"] - stop_price
                take_profit_price = self.state["entry_price"] + (stop_distance * 2.5)  # 2.5:1 reward-to-risk ratio
                
                # For long positions, exit if price rises above take-profit
                if current_price > take_profit_price:
                    logger.info(f"Take-profit triggered for LONG position at {current_price} (target: {take_profit_price})")
                    self.exit_position(current_price, reason="take_profit")
            else:
                stop_distance = stop_price - self.state["entry_price"]
                take_profit_price = self.state["entry_price"] - (stop_distance * 2.5)  # 2.5:1 reward-to-risk ratio
                
                # For short positions, exit if price falls below take-profit
                if current_price < take_profit_price:
                    logger.info(f"Take-profit triggered for SHORT position at {current_price} (target: {take_profit_price})")
                    self.exit_position(current_price, reason="take_profit")
        
        except Exception as e:
            logger.error(f"Failed to manage risk: {e}")

    def check_for_arbitrage(self) -> None:
        """Check for arbitrage opportunities across exchanges."""
        try:
            # Skip arbitrage check if we're in a position
            if self.state["in_position"]:
                return
                
            # Define exchanges to check
            exchanges = ["binance", "coinbase", "kraken"]
            
            # Skip if we're not using one of these exchanges
            if self.exchange_name not in exchanges:
                return
                
            # Get current price on our exchange
            our_price = self.exchange.fetch_market_price(self.symbol)
            
            # Check prices on other exchanges
            prices = {}
            for exchange_name in exchanges:
                if exchange_name == self.exchange_name:
                    prices[exchange_name] = our_price
                    continue
                    
                try:
                    # Create temporary exchange wrapper
                    temp_exchange = ExchangeWrapper(exchange_name)
                    
                    # Get price
                    price = temp_exchange.fetch_market_price(self.symbol)
                    prices[exchange_name] = price
                except Exception as e:
                    logger.warning(f"Failed to get price from {exchange_name}: {e}")
            
            # Find min and max prices
            if len(prices) < 2:
                return
                
            min_exchange = min(prices, key=prices.get)
            max_exchange = max(prices, key=prices.get)
            min_price = prices[min_exchange]
            max_price = prices[max_exchange]
            
            # Calculate price difference
            price_diff_pct = (max_price - min_price) / min_price * 100
            
            # Check if arbitrage opportunity exists (accounting for fees)
            # Typically need at least 0.5% difference to cover fees
            if price_diff_pct > 0.5:
                logger.info(f"Arbitrage opportunity: Buy on {min_exchange} at {min_price}, sell on {max_exchange} at {max_price} ({price_diff_pct:.2f}% difference)")
                
                # In a real implementation, you would execute the trades here
                # This would involve:
                # 1. Checking available balances on both exchanges
                # 2. Placing a buy order on the cheaper exchange
                # 3. Placing a sell order on the more expensive exchange
                # 4. Managing the transfer of funds if needed
                
                # For now, just log the opportunity
                self.state["arbitrage_opportunities"] = self.state.get("arbitrage_opportunities", [])
                self.state["arbitrage_opportunities"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "direct",
                    "buy_exchange": min_exchange,
                    "buy_price": min_price,
                    "sell_exchange": max_exchange,
                    "sell_price": max_price,
                    "difference_pct": price_diff_pct,
                })
        
        except Exception as e:
            logger.error(f"Error checking for arbitrage: {e}")

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

    def should_retrain_model(self) -> bool:
        """
        Determine if the model should be retrained based on performance metrics.
        
        Returns:
            True if the model should be retrained, False otherwise.
        """
        # Check if model has been trained before
        if not self.state.get("model_trained", False):
            return True
            
        # Check if last training was too long ago (7 days)
        if "last_training" in self.state:
            last_training_time = datetime.datetime.fromisoformat(self.state["last_training"]["timestamp"])
            time_since_training = datetime.datetime.now() - last_training_time
            if time_since_training.days >= 7:
                logger.info(f"Model was last trained {time_since_training.days} days ago, scheduling retraining")
                return True
        
        # Check recent performance
        if "trades" in self.state and len(self.state["trades"]) >= 10:
            # Get last 10 trades
            recent_trades = self.state["trades"][-10:]
            
            # Calculate win rate
            profitable_trades = sum(1 for t in recent_trades if t.get("pnl_pct", 0) > 0)
            win_rate = profitable_trades / len(recent_trades)
            
            # If win rate is below 40%, retrain the model
            if win_rate < 0.4:
                logger.warning(f"Recent win rate is low ({win_rate:.2%}), scheduling model retraining")
                return True
        
        # Check prediction accuracy
        if "prediction_accuracy" in self.state and self.state["prediction_accuracy"] < 0.5:
            logger.warning(f"Prediction accuracy is low ({self.state['prediction_accuracy']:.2%}), scheduling model retraining")
            return True
            
        return False

    def update_prediction_accuracy(self, prediction: int, actual_movement: int) -> None:
        """
        Update prediction accuracy tracking.
        
        Args:
            prediction: The model's prediction (-1, 0, 1).
            actual_movement: The actual price movement (-1, 0, 1).
        """
        # Initialize prediction tracking if not present
        if "prediction_tracking" not in self.state:
            self.state["prediction_tracking"] = {
                "total": 0,
                "correct": 0,
                "predictions": []
            }
            
        # Update tracking
        self.state["prediction_tracking"]["total"] += 1
        if prediction == actual_movement:
            self.state["prediction_tracking"]["correct"] += 1
            
        # Store prediction and outcome
        self.state["prediction_tracking"]["predictions"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "prediction": prediction,
            "actual": actual_movement,
            "correct": prediction == actual_movement
        })
        
        # Keep only the last 100 predictions
        if len(self.state["prediction_tracking"]["predictions"]) > 100:
            self.state["prediction_tracking"]["predictions"].pop(0)
            
        # Calculate accuracy
        total = self.state["prediction_tracking"]["total"]
        correct = self.state["prediction_tracking"]["correct"]
        accuracy = correct / total if total > 0 else 0
        
        # Store accuracy
        self.state["prediction_accuracy"] = accuracy
        
        logger.info(f"Prediction accuracy: {accuracy:.2%} ({correct}/{total})")

    def run_strategy(self) -> None:
        """Run the enhanced AI-powered scalping strategy."""
        try:
            # Check if model should be retrained
            if self.should_retrain_model():
                self.train_model()
            
            # Get current price
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            # Get prediction with enhanced analysis
            prediction, analysis_results = self.get_prediction()
            
            # Log analysis results
            logger.info(f"Analysis results: Model: {analysis_results['model_prediction']}, "
                       f"On-chain: {analysis_results['on_chain_signal']:.2f}, "
                       f"Sentiment: {analysis_results['sentiment_signal']:.2f}, "
                       f"Volume Profile: {analysis_results['volume_profile_signal']:.2f}, "
                       f"Market Regime: {analysis_results['market_regime_signal']:.2f}, "
                       f"Combined: {analysis_results['combined_signal']:.2f}")
            
            # Track previous price for later accuracy calculation
            previous_price = self.state.get("previous_price")
            self.state["previous_price"] = current_price
            
            # If we have a previous price, calculate actual movement and update accuracy
            if previous_price is not None:
                price_change = (current_price - previous_price) / previous_price
                
                # Convert to classification: -1 (sell), 0 (hold), 1 (buy)
                if price_change > 0.005:  # 0.5% threshold for buy
                    actual_movement = 1  # buy
                elif price_change < -0.005:  # -0.5% threshold for sell
                    actual_movement = -1  # sell
                else:
                    actual_movement = 0  # hold
                    
                # Update prediction accuracy
                self.update_prediction_accuracy(
                    self.state.get("previous_prediction", 0),
                    actual_movement
                )
                
            # Store current prediction for next accuracy calculation
            self.state["previous_prediction"] = prediction
            
            # Adjust strategy based on market regime if enabled
            if self.use_market_regime and "market_regime_info" in analysis_results.get("signal_details", {}):
                regime_info = analysis_results["signal_details"]["market_regime_info"]
                regime = regime_info.get("regime", "unknown")
                
                # Log market regime
                logger.info(f"Detected market regime: {regime} - {regime_info.get('description', '')}")
                
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
                # Check for exit signal
                if (self.state["current_side"] == "buy" and prediction == -1) or \
                   (self.state["current_side"] == "sell" and prediction == 1):
                    logger.info(f"Exit signal for {self.state['current_side']} position at {current_price}")
                    self.exit_position(current_price, reason="signal")
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
                if prediction == 1:
                    logger.info(f"Entry signal for LONG position at {current_price}")
                    self.enter_position("buy", current_price)
                
                # Enter short if sell signal
                elif prediction == -1:
                    logger.info(f"Entry signal for SHORT position at {current_price}")
                    self.enter_position("sell", current_price)
            
            # Check for arbitrage opportunities
            self.check_for_arbitrage()
        
        except Exception as e:
            logger.error(f"Error in AI-powered scalping strategy: {e}")
