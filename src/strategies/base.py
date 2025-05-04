"""
Base strategy module for the crypto trading bot.
Provides a base class for all trading strategies.
"""

import abc
import datetime
import time
import math
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.config import settings
from src.exchange.wrapper import ExchangeWrapper, ExchangeNotAvailableError
from src.utils.logging import logger
from src.utils.metrics import measure_bot_iteration, update_balance, update_position_size
from src.utils.database import save_order, save_trade, save_balance, save_bot_state, get_bot_state


class RiskManager:
    """Risk management class for trading strategies."""

    def __init__(
        self,
        max_drawdown: float = 0.1,  # 10% maximum drawdown
        max_position_size: float = 0.2,  # 20% of capital in a single position
        max_daily_loss: float = 0.05,  # 5% maximum daily loss
        volatility_lookback: int = 20,  # 20 periods for volatility calculation
    ):
        """
        Initialize the risk manager.

        Args:
            max_drawdown: Maximum allowed drawdown as a fraction of capital.
            max_position_size: Maximum position size as a fraction of capital.
            max_daily_loss: Maximum daily loss as a fraction of capital.
            volatility_lookback: Number of periods to look back for volatility calculation.
        """
        self.max_drawdown = max_drawdown
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.volatility_lookback = volatility_lookback
        self.peak_capital = None
        self.daily_start_capital = None
        self.daily_start_time = None

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        volatility: float = None,
        risk_per_trade: float = 0.01,  # 1% risk per trade
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            capital: Available capital.
            price: Current price.
            volatility: Price volatility (standard deviation of returns).
            risk_per_trade: Risk per trade as a fraction of capital.

        Returns:
            Position size in base currency.
        """
        # Initialize peak capital if not set
        if self.peak_capital is None:
            self.peak_capital = capital
        else:
            self.peak_capital = max(self.peak_capital, capital)

        # Initialize daily tracking
        current_time = datetime.datetime.now()
        if (
            self.daily_start_time is None
            or current_time.date() != self.daily_start_time.date()
        ):
            self.daily_start_capital = capital
            self.daily_start_time = current_time

        # Check for drawdown limit
        drawdown = (self.peak_capital - capital) / self.peak_capital
        if drawdown > self.max_drawdown:
            logger.warning(
                f"Drawdown limit reached: {drawdown:.2%} > {self.max_drawdown:.2%}"
            )
            return 0

        # Check for daily loss limit
        if self.daily_start_capital:
            daily_loss = (self.daily_start_capital - capital) / self.daily_start_capital
            if daily_loss > self.max_daily_loss:
                logger.warning(
                    f"Daily loss limit reached: {daily_loss:.2%} > {self.max_daily_loss:.2%}"
                )
                return 0

        # Calculate position size based on risk
        risk_amount = capital * risk_per_trade

        # If volatility is provided, use it to adjust position size
        if volatility:
            # Higher volatility = smaller position
            position_size_usd = risk_amount / volatility
        else:
            # Default to fixed percentage of capital
            position_size_usd = risk_amount

        # Convert to base currency
        position_size = position_size_usd / price

        # Apply maximum position size limit
        max_position_usd = capital * self.max_position_size
        max_position = max_position_usd / price
        position_size = min(position_size, max_position)

        # Round to appropriate precision (usually 6 decimal places for crypto)
        return round(position_size, 6)

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        volatility: float = None,
        atr_multiplier: float = 2.0,
        default_stop_pct: float = 0.02,  # 2% default stop loss
        min_stop_pct: float = 0.01,      # 1% minimum stop loss
        max_stop_pct: float = 0.05,      # 5% maximum stop loss
    ) -> float:
        """
        Calculate stop loss price based on volatility.

        Args:
            entry_price: Entry price.
            side: Position side (buy/sell).
            volatility: Price volatility or ATR.
            atr_multiplier: Multiplier for ATR-based stop loss.
            default_stop_pct: Default stop loss percentage if volatility is not provided.
            min_stop_pct: Minimum stop loss percentage.
            max_stop_pct: Maximum stop loss percentage.

        Returns:
            Stop loss price.
        """
        if volatility:
            # Use ATR-based stop loss
            stop_distance = volatility * atr_multiplier
            stop_pct = stop_distance / entry_price
            
            # Ensure stop loss is within reasonable bounds
            stop_pct = max(min_stop_pct, min(stop_pct, max_stop_pct))
            
            logger.info(f"Dynamic stop-loss: {stop_pct:.2%} (ATR-based)")
        else:
            # Use default percentage stop loss
            stop_pct = default_stop_pct
            logger.info(f"Using default stop-loss: {stop_pct:.2%}")

        if side == "buy":
            stop_price = entry_price * (1 - stop_pct)
        else:
            stop_price = entry_price * (1 + stop_pct)

        return round(stop_price, 2)

    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        risk_reward_ratio: float = 2.0,
        stop_loss_price: float = None,
        default_tp_pct: float = 0.04,  # 4% default take profit
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio.

        Args:
            entry_price: Entry price.
            side: Position side (buy/sell).
            risk_reward_ratio: Risk-reward ratio.
            stop_loss_price: Stop loss price.
            default_tp_pct: Default take profit percentage if stop loss is not provided.

        Returns:
            Take profit price.
        """
        if stop_loss_price:
            # Calculate take profit based on risk-reward ratio
            if side == "buy":
                stop_distance = entry_price - stop_loss_price
                take_profit_price = entry_price + (stop_distance * risk_reward_ratio)
            else:
                stop_distance = stop_loss_price - entry_price
                take_profit_price = entry_price - (stop_distance * risk_reward_ratio)
        else:
            # Use default percentage take profit
            if side == "buy":
                take_profit_price = entry_price * (1 + default_tp_pct)
            else:
                take_profit_price = entry_price * (1 - default_tp_pct)

        return round(take_profit_price, 2)

    def calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate price volatility.

        Args:
            prices: List of prices.

        Returns:
            Volatility (standard deviation of returns).
        """
        if len(prices) < 2:
            return 0

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns)

        return volatility

    def calculate_atr(
        self, high_prices: List[float], low_prices: List[float], close_prices: List[float], period: int = 14
    ) -> float:
        """
        Calculate Average True Range (ATR).

        Args:
            high_prices: List of high prices.
            low_prices: List of low prices.
            close_prices: List of close prices.
            period: ATR period.

        Returns:
            ATR value.
        """
        if len(high_prices) < period + 1:
            return 0

        # Calculate true ranges
        tr_values = []
        for i in range(1, len(close_prices)):
            tr1 = high_prices[i] - low_prices[i]
            tr2 = abs(high_prices[i] - close_prices[i - 1])
            tr3 = abs(low_prices[i] - close_prices[i - 1])
            tr_values.append(max(tr1, tr2, tr3))

        # Calculate ATR
        atr = sum(tr_values[-period:]) / period

        return atr


class CorrelationManager:
    """Correlation management class for trading strategies."""
    
    def __init__(self, correlation_threshold: float = 0.7):
        """
        Initialize the correlation manager.
        
        Args:
            correlation_threshold: Threshold above which assets are considered correlated.
        """
        self.correlation_threshold = correlation_threshold
        self.correlation_cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 86400  # 24 hours in seconds
    
    def calculate_correlation(self, prices1: List[float], prices2: List[float]) -> float:
        """
        Calculate correlation between two price series.
        
        Args:
            prices1: First price series.
            prices2: Second price series.
            
        Returns:
            Correlation coefficient.
        """
        if len(prices1) != len(prices2):
            min_len = min(len(prices1), len(prices2))
            prices1 = prices1[-min_len:]
            prices2 = prices2[-min_len:]
        
        # Calculate returns
        returns1 = np.diff(prices1) / prices1[:-1]
        returns2 = np.diff(prices2) / prices2[:-1]
        
        # Calculate correlation
        correlation = np.corrcoef(returns1, returns2)[0, 1]
        
        return correlation
    
    def get_correlation(self, symbol1: str, symbol2: str, exchange: ExchangeWrapper) -> float:
        """
        Get correlation between two symbols.
        
        Args:
            symbol1: First symbol.
            symbol2: Second symbol.
            exchange: Exchange wrapper.
            
        Returns:
            Correlation coefficient.
        """
        # Create a unique key for the symbol pair
        key = f"{symbol1}_{symbol2}"
        
        # Check if we have a cached value that's not expired
        current_time = time.time()
        if key in self.correlation_cache and current_time - self.cache_expiry.get(key, 0) < self.cache_ttl:
            return self.correlation_cache[key]
        
        try:
            # Fetch historical data
            ohlcv1 = exchange.fetch_ohlcv(symbol1, timeframe="1d", limit=30)
            ohlcv2 = exchange.fetch_ohlcv(symbol2, timeframe="1d", limit=30)
            
            # Extract close prices
            prices1 = [candle[4] for candle in ohlcv1]
            prices2 = [candle[4] for candle in ohlcv2]
            
            # Calculate correlation
            correlation = self.calculate_correlation(prices1, prices2)
            
            # Cache the result
            self.correlation_cache[key] = correlation
            self.cache_expiry[key] = current_time
            
            return correlation
            
        except Exception as e:
            logger.error(f"Failed to calculate correlation between {symbol1} and {symbol2}: {e}")
            return 0.0
    
    def is_correlated(self, symbol1: str, symbol2: str, exchange: ExchangeWrapper) -> bool:
        """
        Check if two symbols are correlated.
        
        Args:
            symbol1: First symbol.
            symbol2: Second symbol.
            exchange: Exchange wrapper.
            
        Returns:
            True if symbols are correlated, False otherwise.
        """
        correlation = self.get_correlation(symbol1, symbol2, exchange)
        return abs(correlation) > self.correlation_threshold


class BaseStrategy(abc.ABC):
    """Base class for all trading strategies."""

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = None,
        bot_type: str = "base",
        max_drawdown: float = 0.1,
        max_position_size: float = 0.2,
        max_daily_loss: float = 0.05,
        correlation_threshold: float = 0.7,
    ):
        """
        Initialize the strategy.

        Args:
            exchange_name: The name of the exchange.
            symbol: The trading symbol.
            bot_type: The bot type.
            max_drawdown: Maximum allowed drawdown as a fraction of capital.
            max_position_size: Maximum position size as a fraction of capital.
            max_daily_loss: Maximum daily loss as a fraction of capital.
            correlation_threshold: Threshold above which assets are considered correlated.
        """
        self.exchange_name = exchange_name
        self.symbol = symbol or settings.trading.symbol
        self.bot_type = bot_type
        self.exchange = ExchangeWrapper(exchange_name)
        self.running = False
        self.state = self._load_state()
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            max_drawdown=max_drawdown,
            max_position_size=max_position_size,
            max_daily_loss=max_daily_loss,
        )
        
        # Initialize correlation manager
        self.correlation_manager = CorrelationManager(
            correlation_threshold=correlation_threshold
        )
        
        # Initialize performance tracking
        if "performance" not in self.state:
            self.state["performance"] = {
                "initial_capital": settings.trading.initial_capital,
                "current_capital": settings.trading.initial_capital,
                "peak_capital": settings.trading.initial_capital,
                "trades": [],
                "daily_results": {},
            }

    def _load_state(self) -> Dict[str, Any]:
        """
        Load the bot state from the database.

        Returns:
            The bot state.
        """
        bot_state = get_bot_state(self.bot_type)
        if bot_state and bot_state.state:
            logger.info(f"Loaded state for {self.bot_type} bot")
            
            # Update risk manager with peak capital
            if "performance" in bot_state.state and "peak_capital" in bot_state.state["performance"]:
                self.risk_manager.peak_capital = bot_state.state["performance"]["peak_capital"]
            
            return bot_state.state
        return {}

    def _save_state(self) -> None:
        """Save the bot state to the database."""
        save_bot_state(
            self.bot_type,
            {
                "is_running": self.running,
                "last_run": datetime.datetime.now(),
                "state": self.state,
            },
        )
        logger.info(f"Saved state for {self.bot_type} bot")

    def _update_metrics(self) -> None:
        """Update metrics."""
        try:
            # Update balance
            balance = self.exchange.fetch_balance()
            
            # Calculate total capital in USD
            total_capital_usd = 0
            base, quote = self.symbol.split('/')
            
            # Get current price
            current_price = self.exchange.fetch_market_price(self.symbol)
            
            for currency, amount in balance["total"].items():
                if amount > 0:
                    # Update balance metrics
                    update_balance(
                        self.exchange_name, currency, amount, self.bot_type
                    )
                    
                    # Save balance to database
                    save_balance(
                        {
                            "exchange": self.exchange_name,
                            "currency": currency,
                            "free": balance["free"].get(currency, 0),
                            "used": balance["used"].get(currency, 0),
                            "total": amount,
                            "timestamp": datetime.datetime.now(),
                            "bot_type": self.bot_type,
                        }
                    )
                    
                    # Calculate USD value
                    if currency == quote:
                        total_capital_usd += amount
                    elif currency == base:
                        total_capital_usd += amount * current_price
            
            # Update performance tracking
            if "performance" in self.state:
                self.state["performance"]["current_capital"] = total_capital_usd
                self.state["performance"]["peak_capital"] = max(
                    self.state["performance"]["peak_capital"], total_capital_usd
                )
                
                # Update risk manager peak capital
                self.risk_manager.peak_capital = self.state["performance"]["peak_capital"]
                
                # Update daily results
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                if today not in self.state["performance"]["daily_results"]:
                    self.state["performance"]["daily_results"][today] = {
                        "start_capital": total_capital_usd,
                        "end_capital": total_capital_usd,
                        "trades": 0,
                        "profitable_trades": 0,
                    }
                else:
                    self.state["performance"]["daily_results"][today]["end_capital"] = total_capital_usd

            # Update position size (if applicable)
            if "position_size" in self.state:
                update_position_size(
                    self.exchange_name,
                    self.symbol,
                    self.state["position_size"],
                    self.bot_type,
                )
        except ExchangeNotAvailableError as e:
            logger.warning(f"Exchange not available, skipping metrics update: {e}")
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    def _process_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an order and save it to the database.

        Args:
            order: The order data.

        Returns:
            The processed order.
        """
        try:
            # Save order to database
            order_data = {
                "exchange": self.exchange_name,
                "symbol": self.symbol,
                "order_id": order["id"],
                "side": order["side"],
                "type": order["type"],
                "amount": order["amount"],
                "price": order.get("price"),
                "status": order["status"],
                "filled": order.get("filled", 0),
                "cost": order.get("cost"),
                "fee": order.get("fee", {}).get("cost") if order.get("fee") else None,
                "created_at": datetime.datetime.fromtimestamp(order["timestamp"] / 1000)
                if order.get("timestamp")
                else datetime.datetime.now(),
                "updated_at": datetime.datetime.now(),
                "bot_type": self.bot_type,
                "raw_data": order,
            }
            save_order(order_data)
            logger.info(f"Saved order {order['id']} to database")
            return order
        except Exception as e:
            logger.error(f"Failed to process order: {e}")
            return order

    def _process_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a trade and save it to the database.

        Args:
            trade: The trade data.

        Returns:
            The processed trade.
        """
        try:
            # Save trade to database
            trade_data = {
                "exchange": self.exchange_name,
                "symbol": self.symbol,
                "trade_id": trade["id"],
                "order_id": trade.get("order"),
                "side": trade["side"],
                "amount": trade["amount"],
                "price": trade["price"],
                "cost": trade["cost"],
                "fee": trade.get("fee", {}).get("cost") if trade.get("fee") else None,
                "fee_currency": trade.get("fee", {}).get("currency")
                if trade.get("fee")
                else None,
                "timestamp": datetime.datetime.fromtimestamp(trade["timestamp"] / 1000)
                if trade.get("timestamp")
                else datetime.datetime.now(),
                "bot_type": self.bot_type,
                "raw_data": trade,
            }
            save_trade(trade_data)
            logger.info(f"Saved trade {trade['id']} to database")
            
            # Update performance tracking
            if "performance" in self.state and "entry_price" in self.state:
                # Calculate profit/loss
                entry_price = self.state["entry_price"]
                exit_price = trade["price"]
                side = self.state.get("current_side")
                
                if side == "buy":
                    pnl_pct = (exit_price - entry_price) / entry_price
                elif side == "sell":
                    pnl_pct = (entry_price - exit_price) / entry_price
                else:
                    pnl_pct = 0
                
                # Record trade in performance history
                trade_record = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "amount": trade["amount"],
                    "pnl_pct": pnl_pct,
                    "pnl_amount": trade["amount"] * exit_price * pnl_pct,
                }
                self.state["performance"]["trades"].append(trade_record)
                
                # Update daily statistics
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                if today in self.state["performance"]["daily_results"]:
                    self.state["performance"]["daily_results"][today]["trades"] += 1
                    if pnl_pct > 0:
                        self.state["performance"]["daily_results"][today]["profitable_trades"] += 1
            
            return trade
        except Exception as e:
            logger.error(f"Failed to process trade: {e}")
            return trade

    def start(self) -> None:
        """Start the strategy."""
        if self.running:
            logger.warning(f"{self.bot_type} bot is already running")
            return

        logger.info(f"Starting {self.bot_type} bot")
        self.running = True
        self._save_state()

        try:
            while self.running:
                self._run_iteration()
                time.sleep(1)  # Prevent CPU hogging
        except KeyboardInterrupt:
            logger.info(f"Stopping {self.bot_type} bot")
        except Exception as e:
            logger.error(f"Error in {self.bot_type} bot: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the strategy."""
        if not self.running:
            logger.warning(f"{self.bot_type} bot is already stopped")
            return

        logger.info(f"Stopping {self.bot_type} bot")
        self.running = False
        self._save_state()

    @measure_bot_iteration(bot_type="base")
    def _run_iteration(self) -> None:
        """Run a single iteration of the strategy."""
        try:
            # Update metrics
            self._update_metrics()

            # Run the strategy
            self.run_strategy()

            # Save state
            self._save_state()
        except ExchangeNotAvailableError as e:
            logger.warning(f"Exchange not available, skipping iteration: {e}")
            # Wait longer before next attempt
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in {self.bot_type} bot iteration: {e}")

    def calculate_volatility_adjusted_position_size(self, price: float) -> float:
        """
        Calculate position size adjusted for volatility.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        try:
            # Fetch historical data
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, timeframe="1h", limit=self.risk_manager.volatility_lookback + 1
            )
            
            # Extract close prices
            close_prices = [candle[4] for candle in ohlcv]
            
            # Calculate volatility
            volatility = self.risk_manager.calculate_volatility(close_prices)
            
            # Get current capital
            balance = self.exchange.fetch_balance()
            base, quote = self.symbol.split('/')
            capital = balance["total"].get(quote, 0)
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                capital=capital,
                price=price,
                volatility=volatility,
            )
            
            return position_size
        
        except Exception as e:
            logger.error(f"Failed to calculate volatility-adjusted position size: {e}")
            # Fall back to a conservative position size
            return self.calculate_position_size(price)

    @abc.abstractmethod
    def run_strategy(self) -> None:
        """
        Run the strategy. This method must be implemented by subclasses.
        """
        pass

    @abc.abstractmethod
    def calculate_position_size(self, price: float) -> float:
        """
        Calculate the position size.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        pass

    @abc.abstractmethod
    def manage_risk(self) -> None:
        """
        Manage risk.
        """
        pass
    
    def calculate_sharpe_ratio(self, daily_returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            daily_returns: List of daily returns.
            risk_free_rate: Risk-free rate (annualized).
            
        Returns:
            Sharpe ratio.
        """
        if not daily_returns:
            return 0.0
            
        # Convert risk-free rate to daily
        daily_risk_free = (1 + risk_free_rate) ** (1/365) - 1
        
        # Calculate excess returns
        excess_returns = [r - daily_risk_free for r in daily_returns]
        
        # Calculate mean and standard deviation
        mean_excess_return = sum(excess_returns) / len(excess_returns)
        std_excess_return = (sum((r - mean_excess_return) ** 2 for r in excess_returns) / len(excess_returns)) ** 0.5
        
        if std_excess_return == 0:
            return 0.0
            
        # Calculate daily Sharpe ratio
        daily_sharpe = mean_excess_return / std_excess_return
        
        # Annualize (multiply by sqrt(252) for trading days in a year)
        annual_sharpe = daily_sharpe * (252 ** 0.5)
        
        return annual_sharpe
    
    def calculate_sortino_ratio(self, daily_returns: List[float], risk_free_rate: float = 0.0, target_return: float = 0.0) -> float:
        """
        Calculate Sortino ratio.
        
        Args:
            daily_returns: List of daily returns.
            risk_free_rate: Risk-free rate (annualized).
            target_return: Target return (annualized).
            
        Returns:
            Sortino ratio.
        """
        if not daily_returns:
            return 0.0
            
        # Convert rates to daily
        daily_risk_free = (1 + risk_free_rate) ** (1/365) - 1
        daily_target = (1 + target_return) ** (1/365) - 1
        
        # Calculate excess returns
        excess_returns = [r - daily_risk_free for r in daily_returns]
        
        # Calculate mean excess return
        mean_excess_return = sum(excess_returns) / len(excess_returns)
        
        # Calculate downside deviation (only negative returns below target)
        downside_returns = [min(0, r - daily_target) ** 2 for r in daily_returns]
        downside_deviation = (sum(downside_returns) / len(downside_returns)) ** 0.5
        
        if downside_deviation == 0:
            return 0.0
            
        # Calculate daily Sortino ratio
        daily_sortino = mean_excess_return / downside_deviation
        
        # Annualize
        annual_sortino = daily_sortino * (252 ** 0.5)
        
        return annual_sortino

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the strategy's performance.

        Returns:
            A dictionary with performance metrics.
        """
        if "performance" not in self.state:
            return {"error": "Performance tracking not initialized"}
        
        perf = self.state["performance"]
        
        # Calculate overall metrics
        initial_capital = perf["initial_capital"]
        current_capital = perf["current_capital"]
        total_return = (current_capital - initial_capital) / initial_capital
        
        # Calculate trade metrics
        trades = perf["trades"]
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Calculate average profit/loss
        avg_profit = sum(t.get("pnl_pct", 0) for t in trades if t.get("pnl_pct", 0) > 0) / profitable_trades if profitable_trades > 0 else 0
        avg_loss = sum(abs(t.get("pnl_pct", 0)) for t in trades if t.get("pnl_pct", 0) < 0) / (total_trades - profitable_trades) if (total_trades - profitable_trades) > 0 else 0
        
        # Calculate profit factor
        profit_factor = sum(t.get("pnl_amount", 0) for t in trades if t.get("pnl_pct", 0) > 0) / abs(sum(t.get("pnl_amount", 0) for t in trades if t.get("pnl_pct", 0) < 0)) if abs(sum(t.get("pnl_amount", 0) for t in trades if t.get("pnl_pct", 0) < 0)) > 0 else float('inf')
        
        # Calculate drawdown
        peak_capital = perf["peak_capital"]
        max_drawdown = (peak_capital - current_capital) / peak_capital if current_capital < peak_capital else 0
        
        # Calculate daily metrics
        daily_results = perf["daily_results"]
        profitable_days = sum(1 for day, data in daily_results.items() if data["end_capital"] > data["start_capital"])
        total_days = len(daily_results)
        
        # Calculate daily returns for risk-adjusted metrics
        daily_returns = []
        sorted_days = sorted(daily_results.keys())
        
        for i in range(1, len(sorted_days)):
            prev_day = sorted_days[i-1]
            curr_day = sorted_days[i]
            
            prev_capital = daily_results[prev_day]["end_capital"]
            curr_capital = daily_results[curr_day]["end_capital"]
            
            if prev_capital > 0:
                daily_return = (curr_capital - prev_capital) / prev_capital
                daily_returns.append(daily_return)
        
        # Calculate risk-adjusted metrics
        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns)
        sortino_ratio = self.calculate_sortino_ratio(daily_returns)
        
        return {
            "initial_capital": initial_capital,
            "current_capital": current_capital,
            "total_return": total_return,
            "total_return_pct": f"{total_return * 100:.2f}%",
            "peak_capital": peak_capital,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": f"{max_drawdown * 100:.2f}%",
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate * 100:.2f}%",
            "avg_profit": avg_profit,
            "avg_profit_pct": f"{avg_profit * 100:.2f}%",
            "avg_loss": avg_loss,
            "avg_loss_pct": f"{avg_loss * 100:.2f}%",
            "profit_factor": profit_factor,
            "total_days": total_days,
            "profitable_days": profitable_days,
            "daily_win_rate": profitable_days / total_days if total_days > 0 else 0,
            "daily_win_rate_pct": f"{(profitable_days / total_days) * 100:.2f}%" if total_days > 0 else "0.00%",
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
        }

    @abc.abstractmethod
    def run_strategy(self) -> None:
        """
        Run the strategy. This method must be implemented by subclasses.
        """
        pass

    @abc.abstractmethod
    def calculate_position_size(self, price: float) -> float:
        """
        Calculate the position size.

        Args:
            price: The current price.

        Returns:
            The position size.
        """
        pass

    @abc.abstractmethod
    def manage_risk(self) -> None:
        """
        Manage risk.
        """
        pass
