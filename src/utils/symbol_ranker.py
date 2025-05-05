"""
SymbolRanker: Evaluates and ranks trading symbols across exchanges.
"""

from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from src.exchanges.base_exchange import BaseExchange
from src.strategies.base_strategy import BaseStrategy
from src.strategies.strategy_factory import StrategyFactory


class SymbolRanker:
    """
    Evaluates and ranks trading symbols based on confidence scores from strategies.
    
    This utility class helps select the best trading opportunities across multiple
    symbols and exchanges by generating signals for each symbol and ranking them.
    """
    
    def __init__(self, exchange: BaseExchange, strategy_name: str = "rsi_strategy", **strategy_params):
        """
        Initialize the SymbolRanker.
        
        Args:
            exchange: Exchange instance to use for evaluating symbols
            strategy_name: Strategy to use for evaluation (default: "rsi_strategy")
            **strategy_params: Parameters to pass to the strategy
        """
        self.exchange = exchange
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params
        
        logger.info(f"Initialized SymbolRanker with {strategy_name} strategy")
    
    def get_top_symbols(self, limit: int = 10, quote: str = "USDT") -> List[str]:
        """
        Get top trading pairs from the exchange.
        
        Args:
            limit: Maximum number of symbols to return
            quote: Quote currency (e.g., "USDT")
            
        Returns:
            List of trading pair symbols (e.g., ["BTC/USDT", "ETH/USDT"])
        """
        try:
            symbols = self.exchange.get_top_symbols(limit=limit, quote=quote)
            logger.info(f"Retrieved {len(symbols)} top symbols from {self.exchange.__class__.__name__}")
            return symbols
        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            return [f"BTC/{quote}", f"ETH/{quote}"]
    
    def evaluate_symbol(self, symbol: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Evaluate a symbol using the configured strategy.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Tuple of (signal type, confidence, metadata)
        """
        try:
            # Create strategy for this symbol
            strategy = StrategyFactory.create_strategy(
                strategy_name=self.strategy_name,
                exchange=self.exchange,
                symbol=symbol,
                **self.strategy_params
            )
            
            # Get historical data
            data = strategy.get_historical_data()
            
            # Generate signals
            signal, confidence, metadata = strategy.generate_signals(data)
            
            logger.info(f"Evaluated {symbol}: {signal} signal with confidence {confidence:.4f}")
            return signal, confidence, metadata
        except Exception as e:
            logger.error(f"Error evaluating {symbol}: {e}")
            return "hold", 0.0, {"error": str(e)}
    
    def rank_symbols(self, symbols: List[str]) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Evaluate and rank a list of symbols by confidence score.
        
        Args:
            symbols: List of trading pair symbols to evaluate
            
        Returns:
            List of tuples (symbol, signal type, confidence, metadata) sorted by confidence
        """
        results = []
        
        for symbol in symbols:
            try:
                signal, confidence, metadata = self.evaluate_symbol(symbol)
                
                # Only include actionable signals (buy/sell) with positive confidence
                if signal in ("buy", "sell") and confidence > 0:
                    results.append((symbol, signal, confidence, metadata))
                    
            except Exception as e:
                logger.error(f"Error ranking {symbol}: {e}")
        
        # Sort by confidence (descending)
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results
    
    def get_best_opportunities(self, limit: int = 5, quote: str = "USDT", min_confidence: float = 0.3) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Get the best trading opportunities across multiple symbols.
        
        This method:
        1. Gets top symbols from the exchange
        2. Evaluates each symbol using the configured strategy
        3. Returns the highest confidence signals
        
        Args:
            limit: Maximum number of opportunities to return
            quote: Quote currency (e.g., "USDT")
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of (symbol, signal type, confidence, metadata) sorted by confidence
        """
        # Get top symbols from exchange (request more symbols than we need to ensure we find enough good opportunities)
        symbols = self.get_top_symbols(limit=max(limit * 3, 10), quote=quote)
        
        # Rank symbols by confidence
        ranked_symbols = self.rank_symbols(symbols)
        
        # Filter by minimum confidence
        qualified_opportunities = [
            (symbol, signal, confidence, metadata)
            for symbol, signal, confidence, metadata in ranked_symbols
            if confidence >= min_confidence
        ]
        
        # Return top N opportunities
        return qualified_opportunities[:limit]
