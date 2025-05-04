from typing import Dict, Optional
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.strategies.base_strategy import BaseStrategy
from src.strategies.moving_average_crossover import MovingAverageCrossover
from src.strategies.rsi_strategy import RSIStrategy

class StrategyFactory:
    """
    Factory class for creating strategy instances.
    """
    
    @staticmethod
    def create_strategy(
        strategy_name: str,
        exchange: BaseExchange,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        risk_level: str = "medium",
        **kwargs
    ) -> Optional[BaseStrategy]:
        """
        Create a strategy instance based on the strategy name.
        
        Args:
            strategy_name: Name of the strategy ('moving_average_crossover', 'rsi')
            exchange: Exchange instance to use for trading
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for analysis (e.g., '1m', '5m', '1h', '1d')
            risk_level: Risk level ('low', 'medium', 'high')
            **kwargs: Additional parameters for the specific strategy
            
        Returns:
            BaseStrategy: Strategy instance, or None if the strategy is not supported
        """
        strategy_name = strategy_name.lower()
        
        if strategy_name == 'moving_average_crossover' or strategy_name == 'ma_crossover':
            return MovingAverageCrossover(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                risk_level=risk_level,
                fast_ma_period=kwargs.get('fast_ma_period', 20),
                slow_ma_period=kwargs.get('slow_ma_period', 50),
                ma_type=kwargs.get('ma_type', 'sma')
            )
        elif strategy_name == 'rsi' or strategy_name == 'rsi_strategy':
            return RSIStrategy(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                risk_level=risk_level,
                rsi_period=kwargs.get('rsi_period', 14),
                oversold_threshold=kwargs.get('oversold_threshold', 30.0),
                overbought_threshold=kwargs.get('overbought_threshold', 70.0)
            )
        else:
            logger.error(f"Unsupported strategy: {strategy_name}")
            return None
