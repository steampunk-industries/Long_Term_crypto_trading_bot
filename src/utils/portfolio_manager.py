"""
Portfolio management module for the crypto trading bot.
Provides tools for managing portfolio-level risk and capital allocation.
"""

import datetime
import time
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.config import settings
from src.exchange.wrapper import ExchangeWrapper
from src.strategies.base import CorrelationManager
from src.utils.logging import logger


class PortfolioManager:
    """Portfolio manager for managing risk across multiple strategies."""

    def __init__(
        self,
        exchange_name: str = "binance",
        max_portfolio_drawdown: float = 0.15,  # 15% maximum portfolio drawdown
        max_correlation: float = 0.7,  # 70% correlation threshold
        max_allocation_per_asset: float = 0.25,  # 25% maximum allocation per asset
        risk_free_rate: float = 0.02,  # 2% risk-free rate (annualized)
    ):
        """
        Initialize the portfolio manager.

        Args:
            exchange_name: The name of the exchange.
            max_portfolio_drawdown: Maximum allowed portfolio drawdown as a fraction of capital.
            max_correlation: Maximum allowed correlation between assets.
            max_allocation_per_asset: Maximum allocation per asset as a fraction of portfolio.
            risk_free_rate: Risk-free rate (annualized).
        """
        self.exchange_name = exchange_name
        self.exchange = ExchangeWrapper(exchange_name)
        self.max_portfolio_drawdown = max_portfolio_drawdown
        self.max_correlation = max_correlation
        self.max_allocation_per_asset = max_allocation_per_asset
        self.risk_free_rate = risk_free_rate
        
        # Initialize correlation manager
        self.correlation_manager = CorrelationManager(correlation_threshold=max_correlation)
        
        # Initialize portfolio state
        self.portfolio_state = {
            "total_capital": settings.trading.initial_capital,
            "peak_capital": settings.trading.initial_capital,
            "allocations": {},  # Symbol -> allocation amount
            "active_positions": {},  # Symbol -> position details
            "strategy_allocations": {},  # Strategy -> allocation percentage
            "performance": {
                "daily_returns": {},
                "drawdowns": {},
                "sharpe_ratio": None,
                "sortino_ratio": None,
            },
        }
        
        # Initialize risk budget
        self.risk_budget = {
            "total_risk": 1.0,  # 100% of risk budget
            "allocated_risk": 0.0,  # 0% allocated initially
            "strategy_risk": {},  # Strategy -> risk allocation
        }

    def update_portfolio_state(self) -> Dict[str, Any]:
        """
        Update portfolio state with current balances and positions.

        Returns:
            Updated portfolio state.
        """
        try:
            # Get current balance
            balance = self.exchange.fetch_balance()
            
            # Calculate total capital in USD
            total_capital = 0
            
            for currency, amount in balance["total"].items():
                if amount <= 0:
                    continue
                
                # Convert to USD
                try:
                    if currency == "USDT" or currency == "USD":
                        total_capital += amount
                    else:
                        # Try to get price for this currency
                        symbol = f"{currency}/USDT"
                        try:
                            price = self.exchange.fetch_market_price(symbol)
                            total_capital += amount * price
                        except Exception:
                            # Try alternative quote currency
                            symbol = f"{currency}/USD"
                            try:
                                price = self.exchange.fetch_market_price(symbol)
                                total_capital += amount * price
                            except Exception:
                                logger.warning(f"Could not convert {currency} to USD")
                except Exception as e:
                    logger.error(f"Error converting {currency} to USD: {e}")
            
            # Update portfolio state
            self.portfolio_state["total_capital"] = total_capital
            
            # Update peak capital
            if total_capital > self.portfolio_state["peak_capital"]:
                self.portfolio_state["peak_capital"] = total_capital
            
            # Calculate drawdown
            peak_capital = self.portfolio_state["peak_capital"]
            drawdown = (peak_capital - total_capital) / peak_capital if peak_capital > 0 else 0
            
            # Update daily performance
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            if "daily_capital" not in self.portfolio_state:
                self.portfolio_state["daily_capital"] = {}
            
            # If this is a new day, calculate return
            if today not in self.portfolio_state["daily_capital"]:
                # Get yesterday's date
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Calculate daily return if we have yesterday's data
                if yesterday in self.portfolio_state["daily_capital"]:
                    yesterday_capital = self.portfolio_state["daily_capital"][yesterday]
                    daily_return = (total_capital - yesterday_capital) / yesterday_capital
                    
                    # Store daily return
                    self.portfolio_state["performance"]["daily_returns"][today] = daily_return
                
                # Store today's capital
                self.portfolio_state["daily_capital"][today] = total_capital
            
            # Update drawdown history
            self.portfolio_state["performance"]["drawdowns"][today] = drawdown
            
            # Calculate risk metrics
            self._calculate_risk_metrics()
            
            return self.portfolio_state
            
        except Exception as e:
            logger.error(f"Failed to update portfolio state: {e}")
            return self.portfolio_state

    def _calculate_risk_metrics(self) -> None:
        """Calculate risk metrics for the portfolio."""
        try:
            # Get daily returns
            daily_returns = list(self.portfolio_state["performance"]["daily_returns"].values())
            
            if len(daily_returns) < 5:  # Need at least 5 days of data
                return
            
            # Calculate Sharpe ratio
            daily_returns_array = np.array(daily_returns)
            daily_risk_free = (1 + self.risk_free_rate) ** (1/365) - 1
            
            excess_returns = daily_returns_array - daily_risk_free
            sharpe_ratio = 0
            
            if np.std(excess_returns) > 0:
                sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            
            # Calculate Sortino ratio
            downside_returns = np.array([min(0, r - daily_risk_free) ** 2 for r in daily_returns])
            sortino_ratio = 0
            
            if np.mean(downside_returns) > 0:
                downside_deviation = np.sqrt(np.mean(downside_returns))
                sortino_ratio = np.mean(excess_returns) / downside_deviation * np.sqrt(252)
            
            # Update metrics
            self.portfolio_state["performance"]["sharpe_ratio"] = sharpe_ratio
            self.portfolio_state["performance"]["sortino_ratio"] = sortino_ratio
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")

    def check_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Check correlation between two symbols.

        Args:
            symbol1: First symbol.
            symbol2: Second symbol.

        Returns:
            Correlation coefficient.
        """
        return self.correlation_manager.get_correlation(symbol1, symbol2, self.exchange)

    def check_correlation_risk(self, symbol: str, active_symbols: List[str]) -> bool:
        """
        Check if a symbol is correlated with any active positions.

        Args:
            symbol: Symbol to check.
            active_symbols: List of symbols with active positions.

        Returns:
            True if correlation risk is detected, False otherwise.
        """
        for active_symbol in active_symbols:
            if active_symbol == symbol:
                continue
                
            correlation = self.check_correlation(symbol, active_symbol)
            
            if abs(correlation) > self.max_correlation:
                logger.warning(f"Correlation risk detected: {symbol} is correlated with {active_symbol} ({correlation:.2f})")
                return True
                
        return False

    def allocate_capital(
        self, 
        strategies: Dict[str, float], 
        total_capital: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Allocate capital to strategies based on performance and risk.

        Args:
            strategies: Dictionary of strategy names and their performance metrics.
            total_capital: Total capital to allocate (defaults to current portfolio capital).

        Returns:
            Dictionary of strategy allocations.
        """
        if total_capital is None:
            total_capital = self.portfolio_state["total_capital"]
        
        # Initialize allocations
        allocations = {}
        
        # Calculate strategy scores based on Sharpe ratio and drawdown
        strategy_scores = {}
        total_score = 0
        
        for strategy_name, metrics in strategies.items():
            # Get Sharpe ratio and max drawdown
            sharpe_ratio = metrics.get("sharpe_ratio", 0)
            max_drawdown = metrics.get("max_drawdown", 1)
            
            # Avoid division by zero
            if max_drawdown == 0:
                max_drawdown = 0.01
            
            # Calculate score (higher is better)
            # Sharpe ratio is positive factor, drawdown is negative factor
            score = (1 + sharpe_ratio) / max_drawdown
            
            strategy_scores[strategy_name] = score
            total_score += score
        
        # Allocate capital based on scores
        for strategy_name, score in strategy_scores.items():
            if total_score > 0:
                allocation_pct = score / total_score
            else:
                # Equal allocation if no scores
                allocation_pct = 1.0 / len(strategies)
            
            # Apply maximum allocation constraint
            allocation_pct = min(allocation_pct, self.max_allocation_per_asset)
            
            # Calculate allocation amount
            allocation_amount = total_capital * allocation_pct
            
            allocations[strategy_name] = allocation_amount
            
            # Update strategy allocations
            self.portfolio_state["strategy_allocations"][strategy_name] = allocation_pct
        
        return allocations

    def allocate_risk_budget(
        self, 
        strategies: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Allocate risk budget to strategies based on performance.

        Args:
            strategies: Dictionary of strategy names and their performance metrics.

        Returns:
            Dictionary of strategy risk allocations.
        """
        # Initialize risk allocations
        risk_allocations = {}
        
        # Calculate strategy scores based on Sharpe ratio and win rate
        strategy_scores = {}
        total_score = 0
        
        for strategy_name, metrics in strategies.items():
            # Get Sharpe ratio and win rate
            sharpe_ratio = metrics.get("sharpe_ratio", 0)
            win_rate = metrics.get("win_rate", 0.5)
            
            # Calculate score (higher is better)
            score = (1 + sharpe_ratio) * win_rate
            
            strategy_scores[strategy_name] = score
            total_score += score
        
        # Allocate risk based on scores
        allocated_risk = 0
        
        for strategy_name, score in strategy_scores.items():
            if total_score > 0:
                risk_pct = score / total_score
            else:
                # Equal allocation if no scores
                risk_pct = 1.0 / len(strategies)
            
            # Apply maximum allocation constraint
            risk_pct = min(risk_pct, 0.5)  # Max 50% of risk to any strategy
            
            # Calculate risk allocation
            risk_allocation = self.risk_budget["total_risk"] * risk_pct
            
            risk_allocations[strategy_name] = risk_allocation
            allocated_risk += risk_allocation
            
            # Update strategy risk allocations
            self.risk_budget["strategy_risk"][strategy_name] = risk_pct
        
        # Update allocated risk
        self.risk_budget["allocated_risk"] = allocated_risk
        
        return risk_allocations

    def calculate_position_size(
        self, 
        symbol: str, 
        strategy: str, 
        price: float, 
        volatility: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk budget and volatility.

        Args:
            symbol: Trading symbol.
            strategy: Strategy name.
            price: Current price.
            volatility: Price volatility (optional).

        Returns:
            Position size.
        """
        try:
            # Get strategy risk allocation
            risk_allocation = self.risk_budget["strategy_risk"].get(strategy, 0.1)  # Default 10%
            
            # Get strategy capital allocation
            capital_allocation = self.portfolio_state["strategy_allocations"].get(strategy, 0.1)  # Default 10%
            
            # Calculate capital for this position
            position_capital = self.portfolio_state["total_capital"] * capital_allocation
            
            # Adjust for volatility if provided
            if volatility:
                # Higher volatility = smaller position
                volatility_factor = 1.0 / (1.0 + volatility * 10)
                position_capital *= volatility_factor
            
            # Calculate position size
            position_size = position_capital / price
            
            # Check if this would exceed max allocation per asset
            max_capital = self.portfolio_state["total_capital"] * self.max_allocation_per_asset
            max_position_size = max_capital / price
            
            position_size = min(position_size, max_position_size)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            # Return a conservative position size
            return 0.01 * self.portfolio_state["total_capital"] / price

    def check_portfolio_risk(self) -> Dict[str, Any]:
        """
        Check portfolio risk metrics.

        Returns:
            Dictionary with risk check results.
        """
        # Update portfolio state
        self.update_portfolio_state()
        
        # Calculate current drawdown
        peak_capital = self.portfolio_state["peak_capital"]
        total_capital = self.portfolio_state["total_capital"]
        current_drawdown = (peak_capital - total_capital) / peak_capital if peak_capital > 0 else 0
        
        # Check if drawdown exceeds threshold
        drawdown_exceeded = current_drawdown > self.max_portfolio_drawdown
        
        # Get active positions
        active_positions = list(self.portfolio_state["active_positions"].keys())
        
        # Check correlation between active positions
        correlation_risks = []
        
        for i in range(len(active_positions)):
            for j in range(i + 1, len(active_positions)):
                symbol1 = active_positions[i]
                symbol2 = active_positions[j]
                
                correlation = self.check_correlation(symbol1, symbol2)
                
                if abs(correlation) > self.max_correlation:
                    correlation_risks.append({
                        "symbol1": symbol1,
                        "symbol2": symbol2,
                        "correlation": correlation,
                    })
        
        # Calculate risk metrics
        risk_metrics = {
            "sharpe_ratio": self.portfolio_state["performance"].get("sharpe_ratio"),
            "sortino_ratio": self.portfolio_state["performance"].get("sortino_ratio"),
        }
        
        return {
            "drawdown": current_drawdown,
            "drawdown_exceeded": drawdown_exceeded,
            "correlation_risks": correlation_risks,
            "risk_metrics": risk_metrics,
        }

    def register_position(
        self, 
        symbol: str, 
        strategy: str, 
        side: str, 
        entry_price: float, 
        position_size: float
    ) -> None:
        """
        Register a new position with the portfolio manager.

        Args:
            symbol: Trading symbol.
            strategy: Strategy name.
            side: Position side (buy/sell).
            entry_price: Entry price.
            position_size: Position size.
        """
        position_value = position_size * entry_price
        
        self.portfolio_state["active_positions"][symbol] = {
            "strategy": strategy,
            "side": side,
            "entry_price": entry_price,
            "position_size": position_size,
            "position_value": position_value,
            "entry_time": datetime.datetime.now().isoformat(),
        }
        
        logger.info(f"Registered {side} position for {symbol} with {strategy} strategy")

    def unregister_position(
        self, 
        symbol: str, 
        exit_price: float, 
        pnl: float
    ) -> None:
        """
        Unregister a position with the portfolio manager.

        Args:
            symbol: Trading symbol.
            exit_price: Exit price.
            pnl: Profit/loss amount.
        """
        if symbol in self.portfolio_state["active_positions"]:
            position = self.portfolio_state["active_positions"][symbol]
            
            # Record position result
            if "position_history" not in self.portfolio_state:
                self.portfolio_state["position_history"] = []
            
            self.portfolio_state["position_history"].append({
                "symbol": symbol,
                "strategy": position["strategy"],
                "side": position["side"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "position_size": position["position_size"],
                "pnl": pnl,
                "entry_time": position["entry_time"],
                "exit_time": datetime.datetime.now().isoformat(),
            })
            
            # Remove from active positions
            del self.portfolio_state["active_positions"][symbol]
            
            logger.info(f"Unregistered position for {symbol} with PnL: {pnl}")
        else:
            logger.warning(f"Attempted to unregister unknown position for {symbol}")

    def get_active_symbols(self) -> List[str]:
        """
        Get list of symbols with active positions.

        Returns:
            List of active symbols.
        """
        return list(self.portfolio_state["active_positions"].keys())

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio summary.

        Returns:
            Dictionary with portfolio summary.
        """
        # Update portfolio state
        self.update_portfolio_state()
        
        # Calculate asset allocation
        asset_allocation = {}
        total_allocated = 0
        
        for symbol, position in self.portfolio_state["active_positions"].items():
            position_value = position["position_value"]
            allocation_pct = position_value / self.portfolio_state["total_capital"]
            
            asset_allocation[symbol] = {
                "value": position_value,
                "percentage": allocation_pct,
            }
            
            total_allocated += position_value
        
        # Calculate cash allocation
        cash_value = self.portfolio_state["total_capital"] - total_allocated
        cash_pct = cash_value / self.portfolio_state["total_capital"] if self.portfolio_state["total_capital"] > 0 else 0
        
        asset_allocation["cash"] = {
            "value": cash_value,
            "percentage": cash_pct,
        }
        
        # Get risk metrics
        risk_check = self.check_portfolio_risk()
        
        return {
            "total_capital": self.portfolio_state["total_capital"],
            "peak_capital": self.portfolio_state["peak_capital"],
            "drawdown": risk_check["drawdown"],
            "asset_allocation": asset_allocation,
            "strategy_allocation": self.portfolio_state["strategy_allocations"],
            "active_positions": self.portfolio_state["active_positions"],
            "risk_metrics": risk_check["risk_metrics"],
            "correlation_risks": risk_check["correlation_risks"],
        }
