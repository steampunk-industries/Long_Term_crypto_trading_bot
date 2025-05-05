from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import json
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.database.models import Trade, SignalLog, get_session

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Defines the interface that all strategy classes must implement.
    """
    
    def __init__(
        self, 
        exchange: BaseExchange, 
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        risk_level: str = "medium",
        max_position_size: float = 0.25,  # 25% of available balance
        stop_loss_pct: float = 0.03,  # 3% stop loss
        take_profit_pct: float = 0.06,  # 6% take profit
    ):
        """
        Initialize the strategy with an exchange and parameters.
        
        Args:
            exchange: Exchange instance to use for trading
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for analysis (e.g., '1m', '5m', '1h', '1d')
            risk_level: Risk level ('low', 'medium', 'high')
            max_position_size: Maximum position size as a fraction of available balance
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
        """
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.risk_level = risk_level
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.name = self.__class__.__name__
        
        # Adjust risk parameters based on risk level
        self._adjust_risk_parameters()
        
        logger.info(f"Initialized {self.name} strategy for {symbol} on {timeframe} timeframe with {risk_level} risk")
    
    def _adjust_risk_parameters(self):
        """
        Adjust risk parameters based on the risk level.
        """
        from src.config import config
        
        if self.risk_level == "low":
            self.stop_loss_pct = config.LOW_RISK_STOP_LOSS
            self.take_profit_pct = config.LOW_RISK_STOP_LOSS * 2
            self.max_position_size = 0.1  # 10% of available balance
        elif self.risk_level == "medium":
            self.stop_loss_pct = config.MEDIUM_RISK_STOP_LOSS
            self.take_profit_pct = config.MEDIUM_RISK_STOP_LOSS * 2
            self.max_position_size = 0.25  # 25% of available balance
        elif self.risk_level == "high":
            self.stop_loss_pct = config.HIGH_RISK_STOP_LOSS
            self.take_profit_pct = config.HIGH_RISK_STOP_LOSS * 2
            self.max_position_size = 0.5  # 50% of available balance
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> Tuple[str, float, Dict]:
        """
        Generate trading signals based on market data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Tuple[str, float, Dict]: Signal type ('buy', 'sell', 'hold'), confidence level, and metadata
        """
        pass
    
    def get_historical_data(self, limit: int = 100) -> pd.DataFrame:
        """
        Get historical OHLCV data for the symbol.
        
        Args:
            limit: Number of candles to retrieve
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        return self.exchange.get_historical_data(self.symbol, self.timeframe, limit)
    
    def calculate_position_size(self, price: float) -> float:
        """
        Calculate the position size based on available balance and risk parameters.
        
        Args:
            price: Current price of the asset
            
        Returns:
            float: Position size in base currency
        """
        # Get the quote currency (e.g., 'USDT' from 'BTC/USDT')
        quote_currency = self.symbol.split('/')[1]
        
        # Get the available balance
        balance = self.exchange.get_balance(quote_currency)
        
        # Calculate the maximum amount to use
        max_amount = balance * self.max_position_size
        
        # Calculate the position size in base currency
        position_size = max_amount / price
        
        return position_size
    
    def execute_signal(self, signal_type: str, confidence: float, metadata: Dict) -> Optional[Trade]:
        """
        Execute a trading signal.
        
        Args:
            signal_type: Signal type ('buy', 'sell', 'hold')
            confidence: Confidence level (0.0 to 1.0)
            metadata: Additional metadata about the signal
            
        Returns:
            Optional[Trade]: Trade object if a trade was executed, None otherwise
        """
        if signal_type == 'hold':
            logger.info(f"Hold signal generated with confidence {confidence}")
            self._log_signal(signal_type, confidence, None, metadata)
            return None
        
        # Get current ticker
        ticker = self.exchange.get_ticker(self.symbol)
        current_price = ticker['last']
        
        # Calculate position size
        position_size = self.calculate_position_size(current_price)
        
        if position_size <= 0:
            logger.warning(f"Insufficient balance to execute {signal_type} signal")
            return None
        
        try:
            # Execute the order
            order = self.exchange.create_order(
                symbol=self.symbol,
                order_type='market',
                side=signal_type,
                amount=position_size
            )
            
            # Log the signal and trade
            trade = Trade.from_order(
                order=order,
                exchange_name=self.exchange.name,
                is_paper=self.exchange.paper_trading,
                strategy=self.name
            )
            
            # Save the trade to the database
            session = get_session()
            session.add(trade)
            session.commit()
            
            # Log the signal
            self._log_signal(signal_type, confidence, trade.id, metadata)
            
            logger.info(f"Executed {signal_type} order for {position_size} {self.symbol} at {current_price}")
            
            return trade
        except Exception as e:
            logger.error(f"Failed to execute {signal_type} signal: {e}")
            self._log_signal(signal_type, confidence, None, metadata)
            return None
    
    def _log_signal(self, signal_type: str, confidence: float, trade_id: Optional[int], metadata: Dict):
        """
        Log a trading signal to the database.
        
        Args:
            signal_type: Signal type ('buy', 'sell', 'hold')
            confidence: Confidence level (0.0 to 1.0)
            trade_id: ID of the trade if executed, None otherwise
            metadata: Additional metadata about the signal
        """
        try:
            # Get current ticker
            ticker = self.exchange.get_ticker(self.symbol)
            current_price = ticker['last']
            
            # Add trade_id to metadata if it exists
            metadata_copy = metadata.copy()  # Create a copy to avoid modifying the original
            if trade_id is not None:
                metadata_copy['trade_id'] = trade_id
            
            # Create the signal log
            signal_log = SignalLog(
                symbol=self.symbol,
                strategy=self.name,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                executed=(trade_id is not None),
                signal_metadata=json.dumps(metadata_copy)  # Use json.dumps for proper serialization
            )
            
            # Save the signal log to the database
            session = get_session()
            session.add(signal_log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
    
    def run(self) -> Optional[Trade]:
        """
        Run the strategy once.
        
        Returns:
            Optional[Trade]: Trade object if a trade was executed, None otherwise
        """
        try:
            # Get historical data
            data = self.get_historical_data()
            
            if data.empty:
                logger.warning(f"No historical data available for {self.symbol}")
                return None
            
            # Generate signals
            signal_type, confidence, metadata = self.generate_signals(data)
            
            # Execute the signal
            return self.execute_signal(signal_type, confidence, metadata)
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            return None
