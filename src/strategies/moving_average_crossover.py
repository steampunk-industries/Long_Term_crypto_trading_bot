from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.strategies.base_strategy import BaseStrategy

class MovingAverageCrossover(BaseStrategy):
    """
    Moving Average Crossover strategy.

    This strategy generates buy signals when the fast moving average crosses above the slow moving average,
    and sell signals when the fast moving average crosses below the slow moving average.
    """

    def __init__(
        self,
        exchange: BaseExchange,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        risk_level: str = "medium",
        fast_ma_period: int = 20,
        slow_ma_period: int = 50,
        ma_type: str = "sma",  # 'sma' or 'ema'
        **kwargs
    ):
        """
        Initialize the Moving Average Crossover strategy.

        Args:
            exchange: Exchange instance to use for trading
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for analysis (e.g., '1m', '5m', '1h', '1d')
            risk_level: Risk level ('low', 'medium', 'high')
            fast_ma_period: Period for the fast moving average
            slow_ma_period: Period for the slow moving average
            ma_type: Type of moving average ('sma' or 'ema')
            **kwargs: Additional parameters to pass to the parent class
        """
        super().__init__(exchange, symbol, timeframe, risk_level, **kwargs)

        self.fast_ma_period = fast_ma_period
        self.slow_ma_period = slow_ma_period
        self.ma_type = ma_type.lower()

        logger.info(f"Initialized MovingAverageCrossover strategy with fast_ma={fast_ma_period}, slow_ma={slow_ma_period}, ma_type={ma_type}")

    def _calculate_moving_averages(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate moving averages for the data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            pd.DataFrame: DataFrame with moving averages added
        """
        if self.ma_type == 'sma':
            data['fast_ma'] = data['close'].rolling(window=self.fast_ma_period).mean()
            data['slow_ma'] = data['close'].rolling(window=self.slow_ma_period).mean()
        elif self.ma_type == 'ema':
            data['fast_ma'] = data['close'].ewm(span=self.fast_ma_period, adjust=False).mean()
            data['slow_ma'] = data['close'].ewm(span=self.slow_ma_period, adjust=False).mean()
        else:
            raise ValueError(f"Unsupported MA type: {self.ma_type}")

        return data

    def generate_signals(self, data: pd.DataFrame) -> Tuple[str, float, Dict]:
        """
        Generate trading signals based on moving average crossovers.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Tuple[str, float, Dict]: Signal type ('buy', 'sell', 'hold'), confidence level, and metadata
        """
        # Calculate moving averages
        data = self._calculate_moving_averages(data)

        # Drop NaN values
        data = data.dropna()

        if len(data) < 2:
            return 'hold', 0.0, {'reason': 'Insufficient data'}

        # Get the last two rows
        current = data.iloc[-1]
        previous = data.iloc[-2]

        # Check for crossovers
        if current['fast_ma'] > current['slow_ma'] and previous['fast_ma'] <= previous['slow_ma']:
            # Bullish crossover (fast MA crosses above slow MA)
            signal_type = 'buy'
            # Calculate confidence based on the distance between MAs
            confidence = min(1.0, (current['fast_ma'] - current['slow_ma']) / current['close'] * 10)
            metadata = {
                'reason': 'Bullish crossover',
                'fast_ma': current['fast_ma'],
                'slow_ma': current['slow_ma'],
                'close': current['close'],
                'stop_loss': current['close'] * (1 - self.stop_loss_pct),  # Add stop loss
                'take_profit': current['close'] * (1 + self.take_profit_pct)  # Add take profit
            }
        elif current['fast_ma'] < current['slow_ma'] and previous['fast_ma'] >= previous['slow_ma']:
            # Bearish crossover (fast MA crosses below slow MA)
            signal_type = 'sell'
            # Calculate confidence based on the distance between MAs
            confidence = min(1.0, (current['slow_ma'] - current['fast_ma']) / current['close'] * 10)
            metadata = {
                'reason': 'Bearish crossover',
                'fast_ma': current['fast_ma'],
                'slow_ma': current['slow_ma'],
                'close': current['close']
            }
        else:
            # No crossover
            signal_type = 'hold'
            # Calculate confidence based on the trend strength
            if current['fast_ma'] > current['slow_ma']:
                # Bullish trend
                confidence = min(1.0, (current['fast_ma'] - current['slow_ma']) / current['close'] * 5)
                metadata = {
                    'reason': 'Bullish trend',
                    'fast_ma': current['fast_ma'],
                    'slow_ma': current['slow_ma'],
                    'close': current['close']
                }
            else:
                # Bearish trend
                confidence = min(1.0, (current['slow_ma'] - current['fast_ma']) / current['close'] * 5)
                metadata = {
                    'reason': 'Bearish trend',
                    'fast_ma': current['fast_ma'],
                    'slow_ma': current['slow_ma'],
                    'close': current['close']
                }

        return signal_type, confidence, metadata

    def run(self) -> Optional[Tuple[str, Dict]]:
        """
        Run the strategy once.

        This method:
        1. Gets historical data for the symbol
        2. Generates signals based on moving average crossovers
        3. Executes the signal if appropriate
        4. Applies risk management controls

        Returns:
            Optional[Tuple[str, Dict]]: Signal type and trade details if executed, None otherwise
        """
        try:
            # Get historical data
            data = self.get_historical_data()

            if data.empty:
                logger.warning(f"No historical data available for {self.symbol}")
                return None

            # Generate signals
            signal_type, confidence, metadata = self.generate_signals(data)

            # Apply risk management controls
            if signal_type == 'buy':
                # Apply stop loss and take profit
                current_price = float(data.iloc[-1]['close'])
                metadata['stop_loss'] = current_price * (1 - self.stop_loss_pct)
                metadata['take_profit'] = current_price * (1 + self.take_profit_pct)
                
                # Calculate dynamic position size based on trend strength
                # For stronger trends (larger MA distance), use more of allowed position size
                max_position_value = self.exchange.get_balance(self.symbol.split('/')[1]) * self.max_position_size
                
                # Get MA values for trend strength calculation
                fast_ma = float(data.iloc[-1]['fast_ma'])
                slow_ma = float(data.iloc[-1]['slow_ma'])
                
                # Calculate MA percentage difference as a trend strength indicator
                trend_strength = (fast_ma - slow_ma) / slow_ma
                
                # Adjust position size based on trend strength (0.2 to 1.0 of max position)
                position_size_multiplier = min(1.0, max(0.2, trend_strength * 5))
                adjusted_position = max_position_value * position_size_multiplier / current_price
                
                # Apply risk-based position sizing (don't risk more than 2% of account on this trade)
                risk_per_unit = current_price - metadata['stop_loss']
                if risk_per_unit > 0:
                    max_risk_amount = max_position_value * 0.02  # 2% max risk
                    risk_based_position = max_risk_amount / risk_per_unit
                    
                    # Use the smaller of trend-based or risk-based position size
                    position_size = min(adjusted_position, risk_based_position)
                    metadata['position_size'] = position_size
                    logger.info(f"Position size calculated: {position_size} units (trend: {trend_strength:.2f}, risk-based: {risk_based_position:.2f})")
                else:
                    # Fallback to default position sizing
                    position_size = self.calculate_position_size(current_price)
                    metadata['position_size'] = position_size
                    logger.warning(f"Using default position sizing: {position_size} units (invalid stop loss)")
            
            # Execute the signal if confidence is high enough
            confidence_threshold = 0.6  # Lower than RSI strategy since MA crossovers are more reliable
            if confidence > confidence_threshold:
                result = self.execute_signal(signal_type, confidence, metadata)
                if result:
                    logger.info(f"Successfully executed {signal_type} signal with confidence {confidence}")
                    return signal_type, metadata
                else:
                    logger.warning(f"Failed to execute {signal_type} signal with confidence {confidence}")
            else:
                logger.info(f"Signal {signal_type} not executed due to low confidence: {confidence}")
                # Log the signal anyway for tracking
                self._log_signal(signal_type, confidence, None, metadata)
            
            return None
            
        except Exception as e:
            logger.error(f"Error running MovingAverageCrossover strategy: {e}")
            return None
