"""
Multi-Currency Trading Bot: Trades multiple cryptocurrencies by finding the best opportunities.
"""

import time
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory
from src.exchanges.base_exchange import BaseExchange
from src.utils.symbol_ranker import SymbolRanker
from src.database.models import Trade, PortfolioSnapshot, get_session, init_db


class MultiCurrencyBot:
    """
    Trading bot that analyzes multiple currencies and trades the best opportunities.
    """
    
    def __init__(
        self,
        exchange_name: str = "kucoin",
        strategy_name: str = "rsi_strategy",
        paper_trading: bool = True,
        max_positions: int = 3,
        quote_currency: str = "USDT",
        min_confidence: float = 0.4,
        dry_run: bool = True,
        **strategy_params
    ):
        """
        Initialize the multi-currency trading bot.
        
        Args:
            exchange_name: Name of the exchange to use
            strategy_name: Name of the strategy to use for signal generation
            paper_trading: Whether to use paper trading mode
            max_positions: Maximum number of concurrent trading positions
            quote_currency: Quote currency for trading pairs (e.g., "USDT")
            min_confidence: Minimum confidence threshold for executing trades
            dry_run: If True, analyze opportunities but don't actually execute trades
            **strategy_params: Additional parameters to pass to the strategy
        """
        # Initialize database
        self.db_initialized = init_db()
        if not self.db_initialized:
            logger.error("Failed to initialize database. Exiting.")
            return
            
        # Initialize exchange
        self.exchange_name = exchange_name
        self.exchange = ExchangeFactory.create_exchange_from_config(exchange_name)
        if not self.exchange:
            logger.error(f"Failed to initialize {exchange_name} exchange. Exiting.")
            return
            
        # Initialize connection to exchange
        if not self.exchange.connect():
            logger.error(f"Failed to connect to {exchange_name} exchange. Exiting.")
            return
            
        # Initialize symbol ranker
        self.strategy_name = strategy_name
        self.symbol_ranker = SymbolRanker(
            exchange=self.exchange,
            strategy_name=strategy_name,
            **strategy_params
        )
        
        # Set trading parameters
        self.paper_trading = paper_trading
        self.max_positions = max_positions
        self.quote_currency = quote_currency
        self.min_confidence = min_confidence
        self.dry_run = dry_run
        
        # Initialize active positions tracking
        self.active_positions = []
        
        logger.info(f"Initialized Multi-Currency Trading Bot using {exchange_name} exchange and {strategy_name} strategy")
        logger.info(f"Trading parameters: paper_trading={paper_trading}, max_positions={max_positions}, " +
                   f"quote_currency={quote_currency}, min_confidence={min_confidence}, dry_run={dry_run}")
    
    def get_active_positions(self) -> int:
        """
        Get the number of currently active trading positions.
        
        Returns:
            Number of active positions
        """
        # TODO: Implement actual position tracking via exchange or database
        # For now, return a placeholder value
        return len(self.active_positions)
    
    def find_trading_opportunities(self) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Find the best trading opportunities across multiple cryptocurrencies.
        
        Returns:
            List of (symbol, signal, confidence, metadata) for best trading opportunities
        """
        # Calculate how many additional positions we can open
        active_positions = self.get_active_positions()
        available_positions = max(0, self.max_positions - active_positions)
        
        # If we're at max positions, don't look for new opportunities
        if available_positions == 0:
            logger.info(f"Already at maximum positions ({self.max_positions}). Skipping opportunity search.")
            return []
        
        # Find best opportunities
        opportunities = self.symbol_ranker.get_best_opportunities(
            limit=available_positions,
            quote=self.quote_currency,
            min_confidence=self.min_confidence
        )
        
        # Log the opportunities
        if opportunities:
            logger.info(f"Found {len(opportunities)} trading opportunities:")
            for symbol, signal, confidence, metadata in opportunities:
                logger.info(f"- {symbol}: {signal.upper()} signal with confidence {confidence:.4f}")
        else:
            logger.info("No trading opportunities found above minimum confidence threshold.")
            
        return opportunities
    
    def execute_opportunity(self, opportunity: Tuple[str, str, float, Dict[str, Any]]) -> bool:
        """
        Execute a trading opportunity.
        
        Args:
            opportunity: Tuple of (symbol, signal, confidence, metadata)
            
        Returns:
            Whether the trade was successfully executed
        """
        symbol, signal, confidence, metadata = opportunity
        
        # Log what we're about to do
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute {signal.upper()} for {symbol} with confidence {confidence:.4f}")
            return True
            
        try:
            # Get current price
            ticker = self.exchange.get_ticker(symbol)
            if not ticker:
                logger.error(f"Failed to get ticker for {symbol}")
                return False
                
            current_price = ticker["last"]
            
            # Calculate position size
            position_size = metadata.get('position_size')
            if not position_size:
                # Calculate position size based on current price and balance
                quote_currency = symbol.split('/')[1]
                available_balance = self.exchange.get_balance(quote_currency)
                
                # Use at most 20% of available balance per position
                max_position_value = available_balance * 0.2  
                position_size = max_position_value / current_price
            
            # Check if we have enough balance
            if signal == "buy":
                quote_currency = symbol.split('/')[1]
                available_balance = self.exchange.get_balance(quote_currency)
                required_balance = position_size * current_price
                
                if available_balance < required_balance:
                    logger.warning(f"Insufficient {quote_currency} balance for {symbol} {signal} trade. " +
                                  f"Required: {required_balance}, Available: {available_balance}")
                    return False
            elif signal == "sell":
                base_currency = symbol.split('/')[0]
                available_balance = self.exchange.get_balance(base_currency)
                
                if available_balance < position_size:
                    logger.warning(f"Insufficient {base_currency} balance for {symbol} {signal} trade. " +
                                  f"Required: {position_size}, Available: {available_balance}")
                    return False
            
            # Execute the trade
            order = self.exchange.create_order(
                symbol=symbol,
                order_type="market",
                side=signal,
                amount=position_size
            )
            
            if not order:
                logger.error(f"Failed to create order for {symbol} {signal}")
                return False
                
            # Update active positions tracking
            if signal == "buy":
                self.active_positions.append({
                    "symbol": symbol,
                    "entry_price": current_price,
                    "position_size": position_size,
                    "timestamp": datetime.now(),
                    "order_id": order.get("id")
                })
            
            # Log trade to database
            self._log_trade(symbol, signal, position_size, current_price, confidence, metadata)
            
            logger.info(f"Successfully executed {signal.upper()} for {symbol} at {current_price} " +
                       f"with position size {position_size}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing opportunity for {symbol}: {e}")
            return False
    
    def update_portfolio_snapshot(self):
        """
        Update the portfolio snapshot in the database.
        """
        try:
            session = get_session()
            
            # Calculate total portfolio value
            total_value = 0.0
            
            # Get all balances
            balances = self.exchange.get_balances()
            
            # Convert all balances to quote currency value
            for currency, amount in balances.items():
                if currency == self.quote_currency:
                    total_value += amount
                else:
                    try:
                        # Get current price for this currency
                        symbol = f"{currency}/{self.quote_currency}"
                        ticker = self.exchange.get_ticker(symbol)
                        if ticker:
                            total_value += amount * ticker["last"]
                    except Exception as e:
                        logger.debug(f"Could not convert {currency} to {self.quote_currency}: {e}")
            
            # Create snapshot
            snapshot = PortfolioSnapshot(
                total_value_usd=total_value,  # Assuming quote currency is USD or stablecoin
                is_paper=self.paper_trading
            )
            
            session.add(snapshot)
            session.commit()
            
            logger.info(f"Updated portfolio snapshot: total_value={total_value:.2f} {self.quote_currency}")
            
        except Exception as e:
            logger.error(f"Error updating portfolio snapshot: {e}")
    
    def _log_trade(self, symbol: str, side: str, amount: float, price: float, confidence: float, metadata: Dict[str, Any]):
        """
        Log a trade to the database.
        
        Args:
            symbol: Trading pair symbol
            side: Trade side ('buy' or 'sell')
            amount: Trade amount
            price: Trade price
            confidence: Confidence score
            metadata: Additional trade metadata
        """
        try:
            session = get_session()
            
            trade = Trade(
                exchange=self.exchange_name,
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                timestamp=datetime.now(),
                confidence=confidence,
                metadata=str(metadata),
                is_paper=self.paper_trading
            )
            
            session.add(trade)
            session.commit()
            
            logger.info(f"Logged trade to database: {symbol} {side} {amount} @ {price}")
            
        except Exception as e:
            logger.error(f"Error logging trade to database: {e}")
    
    def run_once(self):
        """
        Run the trading bot once, finding and executing trading opportunities.
        """
        logger.info("Running multi-currency trading bot cycle...")
        
        # Update portfolio snapshot
        self.update_portfolio_snapshot()
        
        # Find trading opportunities
        opportunities = self.find_trading_opportunities()
        
        # Execute the opportunities
        for opportunity in opportunities:
            self.execute_opportunity(opportunity)
        
        logger.info("Completed multi-currency trading bot cycle")
    
    def run_continuously(self, interval_minutes: int = 60):
        """
        Run the trading bot continuously at specified intervals.
        
        Args:
            interval_minutes: Interval between runs in minutes
        """
        logger.info(f"Starting multi-currency trading bot with {interval_minutes} minute intervals")
        
        while True:
            try:
                # Run once
                self.run_once()
                
                # Wait for the next interval
                logger.info(f"Waiting for {interval_minutes} minutes until next run...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Trading bot stopped by user")
                break
                
            except Exception as e:
                logger.error(f"Error in trading bot main loop: {e}")
                # Wait a bit before retrying
                time.sleep(60)


if __name__ == "__main__":
    # Configure settings from environment variables
    exchange_name = os.getenv("TRADING_EXCHANGE", "kucoin")
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    max_positions = int(os.getenv("MAX_POSITIONS", "3"))
    quote_currency = os.getenv("QUOTE_CURRENCY", "USDT")
    min_confidence = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.4"))
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    interval_minutes = int(os.getenv("INTERVAL_MINUTES", "60"))
    
    # Create and run the bot
    bot = MultiCurrencyBot(
        exchange_name=exchange_name,
        strategy_name="rsi_strategy",
        paper_trading=paper_trading,
        max_positions=max_positions,
        quote_currency=quote_currency,
        min_confidence=min_confidence,
        dry_run=dry_run,
        # Additional strategy parameters
        timeframe="1h",
        risk_level="medium"
    )
    
    # Run the bot once or continuously
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"
    if run_once:
        bot.run_once()
    else:
        bot.run_continuously(interval_minutes=interval_minutes)
