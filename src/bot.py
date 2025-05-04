import time
import os
import json
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import schedule
from loguru import logger

from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory
from src.exchanges.base_exchange import BaseExchange
from src.strategies.strategy_factory import StrategyFactory
from src.strategies.base_strategy import BaseStrategy
from src.database.models import Trade, Balance, PortfolioSnapshot, init_db, get_session
from src.integrations.steampunk_holdings import steampunk_integration
from src.utils.status_monitor import service_monitor

class TradingBot:
    """
    Main trading bot class that coordinates exchanges, strategies, and database operations.
    """
    
    def __init__(self):
        """
        Initialize the trading bot.
        """
        # Initialize database
        self.db_initialized = init_db()
        if not self.db_initialized:
            logger.error("Failed to initialize database. Exiting.")
            return
        
        # Initialize exchanges
        self.exchanges = {}
        self._init_exchanges()
        
        # Initialize strategies
        self.strategies = {}
        self._init_strategies()
        
        # Initialize portfolio tracking
        self.last_portfolio_snapshot = None
        self.initial_portfolio_value = None
        
        # Initialize service monitoring
        service_monitor.add_service(
            name="steampunk.holdings",
            url="https://api.steampunk.holdings/v1/health",
            success_codes=[200, 204]
        )
        service_monitor.start()
        
        logger.info("Trading bot initialized")
    
    def _init_exchanges(self):
        """
        Initialize exchange connections.
        """
        # Check if multi-exchange is enabled
        if config.USE_MULTI_EXCHANGE or config.TRADING_EXCHANGE == 'multi':
            # Initialize multi-exchange
            exchange = ExchangeFactory.create_exchange_from_config('multi')
            if exchange and exchange.connect():
                self.exchanges['multi'] = exchange
                logger.info("Connected to multi-exchange aggregator")
            else:
                logger.error("Failed to initialize multi-exchange aggregator")
        else:
            # Create exchange instances for each supported exchange (US-compatible)
            for exchange_name in ['coinbase', 'gemini', 'kucoin', 'kraken']:
                exchange = ExchangeFactory.create_exchange_from_config(exchange_name)
                if exchange:
                    # Test connection
                    if exchange.connect():
                        self.exchanges[exchange_name] = exchange
                        logger.info(f"Connected to {exchange_name} exchange")
                    else:
                        logger.warning(f"Failed to connect to {exchange_name} exchange")
    
    def _init_strategies(self):
        """
        Initialize trading strategies.
        """
        # For now, we'll create a simple set of strategies for each exchange and symbol
        # In a real application, this would be configurable
        
        # Define the symbols to trade
        symbols = [config.TRADING_SYMBOL]  # For now, just use the one from config
        
        # Define the strategies to use
        strategy_configs = [
            {
                'name': 'moving_average_crossover',
                'params': {
                    'fast_ma_period': 20,
                    'slow_ma_period': 50,
                    'ma_type': 'ema'
                }
            },
            {
                'name': 'rsi_strategy',
                'params': {
                    'rsi_period': 14,
                    'oversold_threshold': 30.0,
                    'overbought_threshold': 70.0
                }
            }
        ]
        
        # Create strategies for each exchange and symbol
        for exchange_name, exchange in self.exchanges.items():
            for symbol in symbols:
                for strategy_config in strategy_configs:
                    strategy_key = f"{exchange_name}_{symbol}_{strategy_config['name']}"
                    strategy = StrategyFactory.create_strategy(
                        strategy_name=strategy_config['name'],
                        exchange=exchange,
                        symbol=symbol,
                        timeframe='1h',  # Default timeframe
                        risk_level='medium',  # Default risk level
                        **strategy_config['params']
                    )
                    
                    if strategy:
                        self.strategies[strategy_key] = strategy
                        logger.info(f"Initialized strategy: {strategy_key}")
    
    def run_strategies(self):
        """
        Run all strategies once.
        """
        results = []
        
        for strategy_key, strategy in self.strategies.items():
            logger.info(f"Running strategy: {strategy_key}")
            try:
                trade = strategy.run()
                if trade:
                    results.append({
                        'strategy': strategy_key,
                        'trade': trade
                    })
                    logger.info(f"Strategy {strategy_key} executed a trade: {trade}")
            except Exception as e:
                logger.error(f"Error running strategy {strategy_key}: {e}")
        
        return results
    
    def update_portfolio_snapshot(self):
        """
        Update the portfolio snapshot with current balances and performance metrics.
        """
        try:
            session = get_session()
            
            # Calculate total portfolio value in USD
            total_value_usd = 0.0
            
            # Get balances for all exchanges
            for exchange_name, exchange in self.exchanges.items():
                # Get all balances
                if exchange.paper_trading:
                    balances = exchange._paper_balance
                else:
                    # For real trading, we'd need to fetch all balances and convert to USD
                    # This is simplified for now
                    balances = {}
                    quote_currencies = ['USDT', 'USD', 'BUSD', 'USDC']
                    for currency in quote_currencies:
                        balance = exchange.get_balance(currency)
                        if balance > 0:
                            balances[currency] = balance
                
                # Save balances to database
                for currency, amount in balances.items():
                    if amount > 0:
                        balance = Balance(
                            exchange=exchange_name,
                            currency=currency,
                            amount=amount,
                            is_paper=exchange.paper_trading
                        )
                        session.add(balance)
                        
                        # Add to total value (assuming all are in USD for simplicity)
                        if currency in ['USDT', 'USD', 'BUSD', 'USDC']:
                            total_value_usd += amount
                        else:
                            # For other currencies, convert to USD using current price
                            try:
                                ticker = exchange.get_ticker(f"{currency}/USDT")
                                price = ticker['last']
                                total_value_usd += amount * price
                            except Exception as e:
                                logger.warning(f"Failed to convert {currency} to USD: {e}")
            
            # Calculate PnL metrics
            pnl_daily = None
            pnl_weekly = None
            pnl_monthly = None
            pnl_all_time = None
            drawdown = None
            
            # Get previous snapshots
            now = datetime.utcnow()
            
            # Daily PnL
            yesterday = now - timedelta(days=1)
            daily_snapshot = session.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.timestamp >= yesterday
            ).order_by(PortfolioSnapshot.timestamp.asc()).first()
            
            if daily_snapshot:
                pnl_daily = (total_value_usd - daily_snapshot.total_value_usd) / daily_snapshot.total_value_usd
            
            # Weekly PnL
            week_ago = now - timedelta(days=7)
            weekly_snapshot = session.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.timestamp >= week_ago
            ).order_by(PortfolioSnapshot.timestamp.asc()).first()
            
            if weekly_snapshot:
                pnl_weekly = (total_value_usd - weekly_snapshot.total_value_usd) / weekly_snapshot.total_value_usd
            
            # Monthly PnL
            month_ago = now - timedelta(days=30)
            monthly_snapshot = session.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.timestamp >= month_ago
            ).order_by(PortfolioSnapshot.timestamp.asc()).first()
            
            if monthly_snapshot:
                pnl_monthly = (total_value_usd - monthly_snapshot.total_value_usd) / monthly_snapshot.total_value_usd
            
            # All-time PnL
            if self.initial_portfolio_value is None:
                # Get the first snapshot or use the current value
                first_snapshot = session.query(PortfolioSnapshot).order_by(
                    PortfolioSnapshot.timestamp.asc()
                ).first()
                
                if first_snapshot:
                    self.initial_portfolio_value = first_snapshot.total_value_usd
                else:
                    self.initial_portfolio_value = total_value_usd
            
            pnl_all_time = (total_value_usd - self.initial_portfolio_value) / self.initial_portfolio_value
            
            # Calculate drawdown
            highest_value = session.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.total_value_usd.desc()
            ).first()
            
            if highest_value and highest_value.total_value_usd > total_value_usd:
                drawdown = (highest_value.total_value_usd - total_value_usd) / highest_value.total_value_usd
            
            # Create and save the snapshot
            snapshot = PortfolioSnapshot(
                total_value_usd=total_value_usd,
                pnl_daily=pnl_daily,
                pnl_weekly=pnl_weekly,
                pnl_monthly=pnl_monthly,
                pnl_all_time=pnl_all_time,
                drawdown=drawdown,
                is_paper=config.PAPER_TRADING
            )
            
            session.add(snapshot)
            session.commit()
            
            self.last_portfolio_snapshot = snapshot
            
            logger.info(f"Updated portfolio snapshot: total_value_usd={total_value_usd}, pnl_daily={pnl_daily}, drawdown={drawdown}")
            
            # Sync with steampunk.holdings if integration is enabled
            if steampunk_integration.enabled:
                try:
                    # Prepare portfolio data for steampunk.holdings
                    portfolio_data = {
                        "total_value_usd": total_value_usd,
                        "pnl_daily": pnl_daily,
                        "pnl_weekly": pnl_weekly,
                        "pnl_monthly": pnl_monthly,
                        "pnl_all_time": pnl_all_time,
                        "drawdown": drawdown,
                        "timestamp": int(time.time() * 1000),
                        "balances": {}
                    }
                    
                    # Add balances
                    for exchange_name, exchange in self.exchanges.items():
                        if exchange.paper_trading:
                            for currency, amount in exchange._paper_balance.items():
                                if currency not in portfolio_data["balances"]:
                                    portfolio_data["balances"][currency] = 0
                                portfolio_data["balances"][currency] += amount
                    
                    # Sync with steampunk.holdings
                    steampunk_integration.sync_portfolio(portfolio_data)
                    
                except Exception as e:
                    logger.error(f"Failed to sync portfolio with steampunk.holdings: {e}")
            
            return snapshot
        except Exception as e:
            logger.error(f"Error updating portfolio snapshot: {e}")
            return None
    
    def run_once(self):
        """
        Run the trading bot once, executing all strategies and updating portfolio.
        """
        logger.info("Running trading bot...")
        
        # Update portfolio snapshot
        self.update_portfolio_snapshot()
        
        # Run all strategies
        results = self.run_strategies()
        
        # Sync trades with steampunk.holdings if integration is enabled
        if steampunk_integration.enabled and results:
            try:
                trades_to_sync = []
                for result in results:
                    if 'trade' in result and result['trade']:
                        trades_to_sync.append(result['trade'])
                
                if trades_to_sync:
                    steampunk_integration.sync_trades(trades_to_sync)
            except Exception as e:
                logger.error(f"Failed to sync trades with steampunk.holdings: {e}")
        
        logger.info("Trading bot run completed")
    
    def run_continuously(self, interval_minutes=60):
        """
        Run the trading bot continuously at specified intervals.
        
        Args:
            interval_minutes: Interval between runs in minutes
        """
        logger.info(f"Starting trading bot with {interval_minutes} minute intervals")
        
        # Run once immediately
        self.run_once()
        
        # Schedule regular runs
        schedule.every(interval_minutes).minutes.do(self.run_once)
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Trading bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in trading bot main loop: {e}")
                time.sleep(60)  # Wait a bit before retrying
