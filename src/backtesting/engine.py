"""
Backtesting engine module for the crypto trading bot.
Provides a framework for backtesting trading strategies on historical data.
"""

import datetime
import time
from typing import Dict, Any, List, Optional, Tuple, Union, Type, Callable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from src.strategies.base import BaseStrategy
from src.utils.logging import logger


class BacktestExchange:
    """Mock exchange for backtesting."""

    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: Dict[str, float] = None,
        maker_fee: float = 0.001,
        taker_fee: float = 0.001,
    ):
        """
        Initialize the backtest exchange.

        Args:
            data: DataFrame with OHLCV data.
            initial_balance: Initial balance for each currency.
            maker_fee: Maker fee as a fraction.
            taker_fee: Taker fee as a fraction.
        """
        self.data = data
        self.current_index = 0
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.balances = initial_balance or {"USDT": 10000.0, "BTC": 0.0}
        self.orders = {}
        self.next_order_id = 1
        self.trades = []
        self.symbol = "BTC/USDT"  # Default symbol
        self.base_currency = "BTC"
        self.quote_currency = "USDT"

    def set_current_time(self, timestamp: pd.Timestamp) -> None:
        """
        Set the current time for backtesting.

        Args:
            timestamp: The timestamp to set.
        """
        # Find the index closest to the timestamp
        self.current_index = self.data.index.get_indexer([timestamp], method="nearest")[0]

    def get_current_time(self) -> pd.Timestamp:
        """
        Get the current time for backtesting.

        Returns:
            The current timestamp.
        """
        return self.data.index[self.current_index]

    def get_current_price(self) -> float:
        """
        Get the current price.

        Returns:
            The current price.
        """
        return self.data.iloc[self.current_index]["close"]

    def get_current_bar(self) -> pd.Series:
        """
        Get the current OHLCV bar.

        Returns:
            The current OHLCV bar.
        """
        return self.data.iloc[self.current_index]

    def advance_time(self, periods: int = 1) -> None:
        """
        Advance time by a number of periods.

        Args:
            periods: Number of periods to advance.
        """
        self.current_index = min(self.current_index + periods, len(self.data) - 1)
        self._process_orders()

    def fetch_balance(self) -> Dict[str, Dict[str, float]]:
        """
        Fetch account balance.

        Returns:
            A dictionary of balances.
        """
        return {
            "free": self.balances.copy(),
            "used": {k: 0.0 for k in self.balances},
            "total": self.balances.copy(),
        }

    def fetch_market_price(self, symbol: str) -> float:
        """
        Fetch the current market price.

        Args:
            symbol: The trading symbol.

        Returns:
            The current market price.
        """
        return self.get_current_price()

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> List[List[float]]:
        """
        Fetch OHLCV data.

        Args:
            symbol: The trading symbol.
            timeframe: The timeframe.
            limit: The number of candles to fetch.

        Returns:
            A list of OHLCV candles.
        """
        # Get data up to current index
        end_idx = self.current_index + 1
        start_idx = max(0, end_idx - limit)
        
        # Extract OHLCV data
        ohlcv_data = []
        for i in range(start_idx, end_idx):
            bar = self.data.iloc[i]
            timestamp = int(self.data.index[i].timestamp() * 1000)
            ohlcv_data.append([
                timestamp,
                bar["open"],
                bar["high"],
                bar["low"],
                bar["close"],
                bar["volume"],
            ])
        
        return ohlcv_data

    def place_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            symbol: The trading symbol.
            side: The order side (buy/sell).
            amount: The order amount.
            price: The order price.

        Returns:
            The order details.
        """
        # Check if we have enough balance
        if side == "buy":
            cost = amount * price
            if self.balances.get(self.quote_currency, 0) < cost:
                raise Exception(f"Insufficient {self.quote_currency} balance")
            
            # Lock funds
            self.balances[self.quote_currency] -= cost
        else:
            if self.balances.get(self.base_currency, 0) < amount:
                raise Exception(f"Insufficient {self.base_currency} balance")
            
            # Lock funds
            self.balances[self.base_currency] -= amount
        
        # Create order
        order_id = str(self.next_order_id)
        self.next_order_id += 1
        
        order = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": "limit",
            "price": price,
            "amount": amount,
            "filled": 0,
            "status": "open",
            "timestamp": int(self.get_current_time().timestamp() * 1000),
            "datetime": self.get_current_time().isoformat(),
        }
        
        self.orders[order_id] = order
        
        return order

    def place_market_order(
        self, symbol: str, side: str, amount: float
    ) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            symbol: The trading symbol.
            side: The order side (buy/sell).
            amount: The order amount.

        Returns:
            The order details.
        """
        current_price = self.get_current_price()
        
        # Check if we have enough balance
        if side == "buy":
            cost = amount * current_price
            if self.balances.get(self.quote_currency, 0) < cost:
                raise Exception(f"Insufficient {self.quote_currency} balance")
        else:
            if self.balances.get(self.base_currency, 0) < amount:
                raise Exception(f"Insufficient {self.base_currency} balance")
        
        # Create order
        order_id = str(self.next_order_id)
        self.next_order_id += 1
        
        order = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": "market",
            "price": current_price,
            "amount": amount,
            "filled": amount,
            "status": "closed",
            "timestamp": int(self.get_current_time().timestamp() * 1000),
            "datetime": self.get_current_time().isoformat(),
        }
        
        self.orders[order_id] = order
        
        # Execute immediately
        self._execute_order(order)
        
        return order

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_id: The order ID.
            symbol: The trading symbol.

        Returns:
            The cancellation details.
        """
        if order_id not in self.orders:
            raise Exception(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        if order["status"] != "open":
            raise Exception(f"Order {order_id} is not open")
        
        # Update order status
        order["status"] = "canceled"
        
        # Return funds
        if order["side"] == "buy":
            cost = (order["amount"] - order["filled"]) * order["price"]
            self.balances[self.quote_currency] += cost
        else:
            amount = order["amount"] - order["filled"]
            self.balances[self.base_currency] += amount
        
        return order

    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch an order.

        Args:
            order_id: The order ID.
            symbol: The trading symbol.

        Returns:
            The order details.
        """
        if order_id not in self.orders:
            raise Exception(f"Order {order_id} not found")
        
        return self.orders[order_id]

    def fetch_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch open orders.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of open orders.
        """
        return [order for order in self.orders.values() if order["symbol"] == symbol and order["status"] == "open"]

    def fetch_closed_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch closed orders.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of closed orders.
        """
        return [order for order in self.orders.values() if order["symbol"] == symbol and order["status"] != "open"]

    def fetch_my_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch my trades.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of trades.
        """
        return [trade for trade in self.trades if trade["symbol"] == symbol]

    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Cancel all open orders for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A list of cancellation details.
        """
        cancelled_orders = []
        
        for order_id, order in list(self.orders.items()):
            if order["symbol"] == symbol and order["status"] == "open":
                cancelled_order = self.cancel_order(order_id, symbol)
                cancelled_orders.append(cancelled_order)
        
        return cancelled_orders

    def _process_orders(self) -> None:
        """Process open orders based on current price."""
        current_bar = self.get_current_bar()
        
        for order_id, order in list(self.orders.items()):
            if order["status"] != "open":
                continue
            
            # Check if limit order should be filled
            if order["type"] == "limit":
                if order["side"] == "buy" and current_bar["low"] <= order["price"]:
                    # Buy order filled
                    self._execute_order(order)
                elif order["side"] == "sell" and current_bar["high"] >= order["price"]:
                    # Sell order filled
                    self._execute_order(order)

    def _execute_order(self, order: Dict[str, Any]) -> None:
        """
        Execute an order.

        Args:
            order: The order to execute.
        """
        # Calculate execution price
        if order["type"] == "market":
            execution_price = self.get_current_price()
        else:
            execution_price = order["price"]
        
        # Calculate fee
        fee_rate = self.maker_fee if order["type"] == "limit" else self.taker_fee
        
        # Update balances
        if order["side"] == "buy":
            # Calculate cost and fee
            cost = (order["amount"] - order["filled"]) * execution_price
            fee = cost * fee_rate
            
            # Add base currency
            self.balances[self.base_currency] = self.balances.get(self.base_currency, 0) + (order["amount"] - order["filled"])
            
            # If it's a limit order, funds are already locked
            if order["type"] == "market":
                # Subtract quote currency
                self.balances[self.quote_currency] -= cost + fee
        else:
            # Calculate proceeds and fee
            proceeds = (order["amount"] - order["filled"]) * execution_price
            fee = proceeds * fee_rate
            
            # Add quote currency
            self.balances[self.quote_currency] = self.balances.get(self.quote_currency, 0) + proceeds - fee
            
            # If it's a limit order, funds are already locked
            if order["type"] == "market":
                # Subtract base currency
                self.balances[self.base_currency] -= (order["amount"] - order["filled"])
        
        # Create trade
        trade = {
            "id": f"t{order['id']}",
            "order": order["id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "price": execution_price,
            "amount": order["amount"] - order["filled"],
            "cost": (order["amount"] - order["filled"]) * execution_price,
            "fee": {
                "cost": (order["amount"] - order["filled"]) * execution_price * fee_rate,
                "currency": self.quote_currency,
            },
            "timestamp": int(self.get_current_time().timestamp() * 1000),
            "datetime": self.get_current_time().isoformat(),
        }
        
        self.trades.append(trade)
        
        # Update order
        order["filled"] = order["amount"]
        order["status"] = "closed"


class BacktestResult:
    """Class to store and analyze backtest results."""

    def __init__(
        self,
        strategy_name: str,
        trades: List[Dict[str, Any]],
        equity_curve: pd.Series,
        drawdowns: pd.Series,
        parameters: Dict[str, Any],
    ):
        """
        Initialize the backtest result.

        Args:
            strategy_name: The name of the strategy.
            trades: List of trades.
            equity_curve: Series of equity values over time.
            drawdowns: Series of drawdowns over time.
            parameters: Strategy parameters.
        """
        self.strategy_name = strategy_name
        self.trades = trades
        self.equity_curve = equity_curve
        self.drawdowns = drawdowns
        self.parameters = parameters
        
        # Calculate metrics
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics.

        Returns:
            A dictionary of metrics.
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "total_return": 0,
                "annualized_return": 0,
            }
        
        # Calculate trade metrics
        total_trades = len(self.trades)
        profitable_trades = sum(1 for t in self.trades if t.get("profit", 0) > 0)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Calculate profit factor
        gross_profit = sum(t.get("profit", 0) for t in self.trades if t.get("profit", 0) > 0)
        gross_loss = abs(sum(t.get("profit", 0) for t in self.trades if t.get("profit", 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate returns
        initial_equity = self.equity_curve.iloc[0]
        final_equity = self.equity_curve.iloc[-1]
        total_return = (final_equity - initial_equity) / initial_equity
        
        # Calculate annualized return
        days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        annualized_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        
        # Calculate Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = self.equity_curve.pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate maximum drawdown
        max_drawdown = self.drawdowns.max()
        
        return {
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate * 100:.2f}%",
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": f"{max_drawdown * 100:.2f}%",
            "total_return": total_return,
            "total_return_pct": f"{total_return * 100:.2f}%",
            "annualized_return": annualized_return,
            "annualized_return_pct": f"{annualized_return * 100:.2f}%",
        }

    def plot(self, figsize: Tuple[int, int] = (12, 8)) -> Figure:
        """
        Plot the backtest results.

        Args:
            figsize: Figure size.

        Returns:
            The matplotlib figure.
        """
        fig, axes = plt.subplots(3, 1, figsize=figsize, gridspec_kw={"height_ratios": [3, 1, 1]})
        
        # Plot equity curve
        axes[0].plot(self.equity_curve.index, self.equity_curve.values)
        axes[0].set_title(f"{self.strategy_name} - Equity Curve")
        axes[0].set_ylabel("Equity")
        axes[0].grid(True)
        
        # Plot drawdowns
        axes[1].fill_between(self.drawdowns.index, 0, self.drawdowns.values * 100, color="red", alpha=0.3)
        axes[1].set_title("Drawdowns")
        axes[1].set_ylabel("Drawdown (%)")
        axes[1].grid(True)
        
        # Plot trade markers on equity curve
        for trade in self.trades:
            timestamp = pd.to_datetime(trade["datetime"])
            if timestamp in self.equity_curve.index:
                equity = self.equity_curve.loc[timestamp]
                if trade["side"] == "buy":
                    axes[0].plot(timestamp, equity, "^", color="green", markersize=8)
                else:
                    axes[0].plot(timestamp, equity, "v", color="red", markersize=8)
        
        # Plot trade profits
        trade_times = [pd.to_datetime(t["datetime"]) for t in self.trades]
        trade_profits = [t.get("profit", 0) for t in self.trades]
        
        if trade_times and trade_profits:
            axes[2].bar(trade_times, trade_profits, color=["green" if p > 0 else "red" for p in trade_profits])
            axes[2].set_title("Trade Profits")
            axes[2].set_ylabel("Profit")
            axes[2].grid(True)
        
        # Add metrics as text
        metrics_text = "\n".join([
            f"Total Trades: {self.metrics['total_trades']}",
            f"Win Rate: {self.metrics['win_rate_pct']}",
            f"Profit Factor: {self.metrics['profit_factor']:.2f}",
            f"Sharpe Ratio: {self.metrics['sharpe_ratio']:.2f}",
            f"Max Drawdown: {self.metrics['max_drawdown_pct']}",
            f"Total Return: {self.metrics['total_return_pct']}",
            f"Annualized Return: {self.metrics['annualized_return_pct']}",
        ])
        
        # Add text box with metrics
        axes[0].text(
            0.02, 0.05, metrics_text,
            transform=axes[0].transAxes,
            bbox=dict(facecolor="white", alpha=0.7),
            verticalalignment="bottom",
            fontsize=10,
        )
        
        plt.tight_layout()
        return fig

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the backtest result to a dictionary.

        Returns:
            A dictionary representation of the backtest result.
        """
        return {
            "strategy_name": self.strategy_name,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "trades": self.trades,
        }

    def __str__(self) -> str:
        """
        Get a string representation of the backtest result.

        Returns:
            A string representation.
        """
        return (
            f"Backtest Result for {self.strategy_name}\n"
            f"Parameters: {self.parameters}\n"
            f"Metrics: {self.metrics}\n"
            f"Trades: {len(self.trades)}"
        )


class Backtester:
    """Backtesting engine for trading strategies."""

    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: Dict[str, float] = None,
        maker_fee: float = 0.001,
        taker_fee: float = 0.001,
    ):
        """
        Initialize the backtester.

        Args:
            data: DataFrame with OHLCV data.
            initial_balance: Initial balance for each currency.
            maker_fee: Maker fee as a fraction.
            taker_fee: Taker fee as a fraction.
        """
        self.data = data
        self.initial_balance = initial_balance or {"USDT": 10000.0, "BTC": 0.0}
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

    def run(
        self,
        strategy_class: Type[BaseStrategy],
        parameters: Dict[str, Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BacktestResult:
        """
        Run a backtest.

        Args:
            strategy_class: The strategy class to backtest.
            parameters: Strategy parameters.
            start_date: Start date for the backtest.
            end_date: End date for the backtest.

        Returns:
            The backtest result.
        """
        # Filter data by date range
        data = self.data.copy()
        if start_date:
            data = data[data.index >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data.index <= pd.to_datetime(end_date)]
        
        # Create backtest exchange
        exchange = BacktestExchange(
            data=data,
            initial_balance=self.initial_balance.copy(),
            maker_fee=self.maker_fee,
            taker_fee=self.taker_fee,
        )
        
        # Create strategy
        parameters = parameters or {}
        strategy = strategy_class(exchange_name="backtest", **parameters)
        
        # Replace exchange with backtest exchange
        strategy.exchange = exchange
        
        # Initialize equity curve and drawdowns
        equity_curve = pd.Series(index=data.index, dtype=float)
        drawdowns = pd.Series(index=data.index, dtype=float)
        peak_equity = 0
        
        # Run backtest
        for i, timestamp in enumerate(data.index):
            # Set current time
            exchange.set_current_time(timestamp)
            
            # Run strategy iteration
            try:
                strategy._run_iteration()
            except Exception as e:
                logger.error(f"Error in strategy iteration at {timestamp}: {e}")
            
            # Calculate equity
            balance = exchange.fetch_balance()
            base_amount = balance["total"].get(exchange.base_currency, 0)
            quote_amount = balance["total"].get(exchange.quote_currency, 0)
            current_price = exchange.get_current_price()
            
            equity = quote_amount + base_amount * current_price
            equity_curve[timestamp] = equity
            
            # Calculate drawdown
            peak_equity = max(peak_equity, equity)
            drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            drawdowns[timestamp] = drawdown
            
            # Advance time
            if i < len(data.index) - 1:
                exchange.advance_time()
        
        # Calculate trade profits
        trades = exchange.fetch_my_trades(exchange.symbol)
        
        # Group trades by order
        trades_by_order = {}
        for trade in trades:
            order_id = trade["order"]
            if order_id not in trades_by_order:
                trades_by_order[order_id] = []
            trades_by_order[order_id].append(trade)
        
        # Calculate profit for each trade
        for trade in trades:
            order = exchange.fetch_order(trade["order"], exchange.symbol)
            
            # Skip if we can't determine profit
            if "entry_price" not in strategy.state:
                continue
            
            # Calculate profit
            entry_price = strategy.state.get("entry_price", 0)
            exit_price = trade["price"]
            
            if order["side"] == "buy":
                # This is an entry trade
                pass
            else:
                # This is an exit trade
                profit = (exit_price - entry_price) * trade["amount"]
                trade["profit"] = profit
        
        # Create backtest result
        result = BacktestResult(
            strategy_name=strategy.__class__.__name__,
            trades=trades,
            equity_curve=equity_curve,
            drawdowns=drawdowns,
            parameters=parameters,
        )
        
        return result

    def optimize(
        self,
        strategy_class: Type[BaseStrategy],
        param_grid: Dict[str, List[Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        metric: str = "sharpe_ratio",
        maximize: bool = True,
        method: str = "grid",  # 'grid' or 'bayesian'
        n_trials: int = 50,    # Number of trials for Bayesian optimization
    ) -> Tuple[BacktestResult, Dict[str, Any]]:
        """
        Optimize strategy parameters.

        Args:
            strategy_class: The strategy class to optimize.
            param_grid: Grid of parameters to search.
            start_date: Start date for the backtest.
            end_date: End date for the backtest.
            metric: Metric to optimize.
            maximize: Whether to maximize or minimize the metric.
            method: Optimization method ('grid' or 'bayesian').
            n_trials: Number of trials for Bayesian optimization.

        Returns:
            The best backtest result and parameters.
        """
        if method == "grid":
            return self._grid_search_optimize(
                strategy_class=strategy_class,
                param_grid=param_grid,
                start_date=start_date,
                end_date=end_date,
                metric=metric,
                maximize=maximize,
            )
        elif method == "bayesian":
            try:
                # Check if scikit-optimize is installed
                import skopt
                from skopt import gp_minimize
                from skopt.space import Real, Integer, Categorical
                
                return self._bayesian_optimize(
                    strategy_class=strategy_class,
                    param_grid=param_grid,
                    start_date=start_date,
                    end_date=end_date,
                    metric=metric,
                    maximize=maximize,
                    n_trials=n_trials,
                )
            except ImportError:
                logger.warning("scikit-optimize not installed. Falling back to grid search.")
                return self._grid_search_optimize(
                    strategy_class=strategy_class,
                    param_grid=param_grid,
                    start_date=start_date,
                    end_date=end_date,
                    metric=metric,
                    maximize=maximize,
                )
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def _grid_search_optimize(
        self,
        strategy_class: Type[BaseStrategy],
        param_grid: Dict[str, List[Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        metric: str = "sharpe_ratio",
        maximize: bool = True,
    ) -> Tuple[BacktestResult, Dict[str, Any]]:
        """
        Optimize strategy parameters using grid search.

        Args:
            strategy_class: The strategy class to optimize.
            param_grid: Grid of parameters to search.
            start_date: Start date for the backtest.
            end_date: End date for the backtest.
            metric: Metric to optimize.
            maximize: Whether to maximize or minimize the metric.

        Returns:
            The best backtest result and parameters.
        """
        # Generate parameter combinations
        param_keys = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        best_result = None
        best_params = None
        best_metric_value = float("-inf") if maximize else float("inf")
        
        # Helper function to recursively generate parameter combinations
        def generate_params(index: int, current_params: Dict[str, Any]) -> None:
            nonlocal best_result, best_params, best_metric_value
            
            if index == len(param_keys):
                # Run backtest with current parameters
                result = self.run(
                    strategy_class=strategy_class,
                    parameters=current_params,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                # Check if this is the best result
                metric_value = result.metrics.get(metric, 0)
                
                if (maximize and metric_value > best_metric_value) or (not maximize and metric_value < best_metric_value):
                    best_result = result
                    best_params = current_params.copy()
                    best_metric_value = metric_value
                
                return
            
            # Try each value for the current parameter
            for value in param_values[index]:
                current_params[param_keys[index]] = value
                generate_params(index + 1, current_params)
        
        # Start parameter generation
        generate_params(0, {})
        
        return best_result, best_params
    
    def _bayesian_optimize(
        self,
        strategy_class: Type[BaseStrategy],
        param_grid: Dict[str, List[Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        metric: str = "sharpe_ratio",
        maximize: bool = True,
        n_trials: int = 50,
    ) -> Tuple[BacktestResult, Dict[str, Any]]:
        """
        Optimize strategy parameters using Bayesian optimization.

        Args:
            strategy_class: The strategy class to optimize.
            param_grid: Grid of parameters to search.
            start_date: Start date for the backtest.
            end_date: End date for the backtest.
            metric: Metric to optimize.
            maximize: Whether to maximize or minimize the metric.
            n_trials: Number of trials.

        Returns:
            The best backtest result and parameters.
        """
        import skopt
        from skopt import gp_minimize
        from skopt.space import Real, Integer, Categorical
        
        # Define search space
        space = []
        param_types = {}
        
        for param_name, param_values in param_grid.items():
            # Determine parameter type
            if all(isinstance(v, int) for v in param_values):
                # Integer parameter
                space.append(Integer(min(param_values), max(param_values), name=param_name))
                param_types[param_name] = "int"
            elif all(isinstance(v, float) for v in param_values):
                # Real parameter
                space.append(Real(min(param_values), max(param_values), name=param_name))
                param_types[param_name] = "float"
            else:
                # Categorical parameter
                space.append(Categorical(param_values, name=param_name))
                param_types[param_name] = "categorical"
        
        # Define objective function
        def objective(params):
            # Convert params to dictionary
            param_dict = {}
            for i, param_name in enumerate(param_grid.keys()):
                if param_types[param_name] == "int":
                    param_dict[param_name] = int(params[i])
                elif param_types[param_name] == "float":
                    param_dict[param_name] = float(params[i])
                else:
                    param_dict[param_name] = params[i]
            
            # Run backtest
            result = self.run(
                strategy_class=strategy_class,
                parameters=param_dict,
                start_date=start_date,
                end_date=end_date,
            )
            
            # Get metric value
            metric_value = result.metrics.get(metric, 0)
            
            # Store result if it's the best so far
            if not hasattr(objective, "best_result") or \
               (maximize and metric_value > objective.best_metric_value) or \
               (not maximize and metric_value < objective.best_metric_value):
                objective.best_result = result
                objective.best_params = param_dict
                objective.best_metric_value = metric_value
            
            # Return negative value if maximizing (gp_minimize minimizes)
            return -metric_value if maximize else metric_value
        
        # Initialize best values
        objective.best_result = None
        objective.best_params = None
        objective.best_metric_value = float("-inf") if maximize else float("inf")
        
        # Run Bayesian optimization
        logger.info(f"Running Bayesian optimization with {n_trials} trials")
        res = gp_minimize(
            objective,
            space,
            n_calls=n_trials,
            random_state=42,
            verbose=True,
        )
        
        return objective.best_result, objective.best_params

    def walk_forward(
        self,
        strategy_class: Type[BaseStrategy],
        train_size: int,
        test_size: int,
        param_grid: Dict[str, List[Any]],
        metric: str = "sharpe_ratio",
        maximize: bool = True,
    ) -> List[BacktestResult]:
        """
        Perform walk-forward optimization.

        Args:
            strategy_class: The strategy class to optimize.
            train_size: Size of training window in days.
            test_size: Size of test window in days.
            param_grid: Grid of parameters to search.
            metric: Metric to optimize.
            maximize: Whether to maximize or minimize the metric.

        Returns:
            List of backtest results for each test period.
        """
        # Convert index to datetime if it's not already
        if not isinstance(self.data.index, pd.DatetimeIndex):
            self.data.index = pd.to_datetime(self.data.index)
        
        # Sort data by index
        data = self.data.sort_index()
        
        # Calculate number of windows
        start_date = data.index[0]
        end_date = data.index[-1]
        total_days = (end_date - start_date).days
        
        if total_days < train_size + test_size:
            raise ValueError("Not enough data for walk-forward optimization")
        
        # Calculate window start dates
        window_starts = []
        current_date = start_date
        
        while current_date + pd.Timedelta(days=train_size + test_size) <= end_date:
            window_starts.append(current_date)
            current_date += pd.Timedelta(days=test_size)
        
        # Run walk-forward optimization
        results = []
        
        for start_date in window_starts:
            # Calculate train and test dates
            train_end = start_date + pd.Timedelta(days=train_size)
            test_end = train_end + pd.Timedelta(days=test_size)
            
            # Optimize on training data
            train_data = data[(data.index >= start_date) & (data.index < train_end)]
            train_backtester = Backtester(
                data=train_data,
                initial_balance=self.initial_balance.copy(),
                maker_fee=self.maker_fee,
                taker_fee=self.taker_fee,
            )
            
            _, best_params = train_backtester.optimize(
                strategy_class=strategy_class,
                param_grid=param_grid,
                metric=metric,
                maximize=maximize,
            )
            
            # Test on test data
            test_data = data[(data.index >= train_end) & (data.index < test_end)]
            test_backtester = Backtester(
                data=test_data,
                initial_balance=self.initial_balance.copy(),
                maker_fee=self.maker_fee,
                taker_fee=self.taker_fee,
            )
            
            # Run backtest with optimized parameters
            result = test_backtester.run(
                strategy_class=strategy_class,
                parameters=best_params,
            )
            
            # Add result to list
            results.append(result)
        
        return results
