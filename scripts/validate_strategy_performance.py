#!/usr/bin/env python3
"""
Strategy performance validation script for the crypto trading bot.
Validates a strategy's performance through backtesting.
"""

import argparse
import sys
import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategy modules
from src.config import settings
from src.backtesting.engine import BacktestEngine
from src.strategies.low_risk import LowRiskStrategy
from src.strategies.medium_risk import MediumRiskStrategy
from src.strategies.high_risk import HighRiskStrategy
from src.exchange.wrapper import ExchangeWrapper
from src.utils.logging import logger


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Crypto Trading Bot - Strategy Performance Validation")
    
    parser.add_argument(
        "--strategy", 
        type=str,
        required=True,
        choices=["low_risk", "medium_risk", "high_risk", "all"],
        help="Strategy to validate (low_risk, medium_risk, high_risk, or all)"
    )
    
    parser.add_argument(
        "--exchange", 
        type=str, 
        default="binance", 
        help="Exchange name (default: binance)"
    )
    
    parser.add_argument(
        "--symbol", 
        type=str, 
        default=None, 
        help=f"Trading symbol (default: {settings.trading.symbol})"
    )
    
    parser.add_argument(
        "--days", 
        type=int, 
        default=30, 
        help="Number of days to backtest (default: 30)"
    )
    
    parser.add_argument(
        "--initial-capital", 
        type=float, 
        default=settings.trading.initial_capital, 
        help=f"Initial capital for backtest (default: {settings.trading.initial_capital})"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default="results", 
        help="Output directory for results (default: results)"
    )
    
    parser.add_argument(
        "--plot", 
        action="store_true", 
        help="Generate performance plots"
    )
    
    return parser.parse_args()


def print_header(strategy: str, symbol: str, days: int, initial_capital: float) -> None:
    """
    Print header information about the backtest.
    
    Args:
        strategy: Strategy name.
        symbol: Trading symbol.
        days: Number of days to backtest.
        initial_capital: Initial capital.
    """
    print("\n" + "=" * 80)
    print(" CRYPTO TRADING BOT - STRATEGY PERFORMANCE VALIDATION ".center(80, "="))
    print("=" * 80)
    print(f"Strategy: {strategy}")
    print(f"Symbol: {symbol}")
    print(f"Period: {days} days")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


def get_strategy_instance(
    strategy_name: str,
    exchange_name: str,
    symbol: str
) -> Union[LowRiskStrategy, MediumRiskStrategy, HighRiskStrategy]:
    """
    Get a strategy instance.
    
    Args:
        strategy_name: Strategy name.
        exchange_name: Exchange name.
        symbol: Trading symbol.
        
    Returns:
        Strategy instance.
    """
    if strategy_name == "low_risk":
        return LowRiskStrategy(
            exchange_name=exchange_name,
            symbol=symbol,
            grid_levels=5,
            grid_spacing=0.5,
            use_dynamic_grids=True,
            use_volume_profile=True,
            use_market_regime=True,
        )
    elif strategy_name == "medium_risk":
        return MediumRiskStrategy(
            exchange_name=exchange_name,
            symbol=symbol,
            timeframe="1h",
            ema_short=50,
            ema_long=200,
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30,
            use_adx=True,
            use_volume_profile=True,
            use_market_regime=True,
            adx_threshold=25,
        )
    elif strategy_name == "high_risk":
        return HighRiskStrategy(
            exchange_name=exchange_name,
            symbol=symbol,
            timeframe="5m",
            sequence_length=60,
            prediction_horizon=5,
            use_on_chain=True,
            use_sentiment=True,
            use_volume_profile=True,
            use_market_regime=True,
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


def run_backtest(
    strategy_name: str,
    exchange_name: str,
    symbol: str,
    days: int,
    initial_capital: float
) -> Dict[str, Any]:
    """
    Run a backtest for a strategy.
    
    Args:
        strategy_name: Strategy name.
        exchange_name: Exchange name.
        symbol: Trading symbol.
        days: Number of days to backtest.
        initial_capital: Initial capital.
        
    Returns:
        Dictionary with backtest results.
    """
    print(f"\nRunning backtest for {strategy_name} strategy...")
    
    # Get strategy instance
    strategy = get_strategy_instance(strategy_name, exchange_name, symbol)
    
    # Create backtest engine
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        data_start_date=datetime.now() - timedelta(days=days),
        data_end_date=datetime.now(),
    )
    
    # Run backtest
    start_time = time.time()
    results = engine.run()
    end_time = time.time()
    
    # Calculate execution time
    execution_time = end_time - start_time
    
    # Add execution time to results
    results["execution_time"] = execution_time
    
    # Print summary
    print(f"\nBacktest completed in {execution_time:.2f} seconds")
    print(f"Final Balance: ${results['final_balance']:,.2f}")
    print(f"Return: {results['return_pct']:.2f}%")
    print(f"Annualized Return: {results['annualized_return_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Total Trades: {results['total_trades']}")
    
    return results


def generate_plots(
    results: Dict[str, Any],
    strategy_name: str,
    output_dir: str
) -> None:
    """
    Generate performance plots.
    
    Args:
        results: Backtest results.
        strategy_name: Strategy name.
        output_dir: Output directory.
    """
    if "equity_curve" not in results:
        print("No equity curve data available for plotting")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert equity curve to DataFrame
    equity_curve = pd.DataFrame(results["equity_curve"])
    equity_curve["timestamp"] = pd.to_datetime(equity_curve["timestamp"])
    equity_curve.set_index("timestamp", inplace=True)
    
    # Plot equity curve
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve["balance"])
    plt.title(f"{strategy_name} Strategy - Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Balance ($)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{strategy_name}_equity_curve.png"))
    
    # Plot drawdown
    if "drawdown" in equity_curve.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve["drawdown"] * 100)
        plt.title(f"{strategy_name} Strategy - Drawdown")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{strategy_name}_drawdown.png"))
    
    # Plot trade distribution if available
    if "trades" in results:
        trades = pd.DataFrame(results["trades"])
        if not trades.empty and "pnl_pct" in trades.columns:
            plt.figure(figsize=(12, 6))
            plt.hist(trades["pnl_pct"], bins=50)
            plt.title(f"{strategy_name} Strategy - Trade P&L Distribution")
            plt.xlabel("P&L (%)")
            plt.ylabel("Frequency")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{strategy_name}_pnl_distribution.png"))
    
    print(f"Plots generated in {output_dir} directory")


def save_results(
    results: Dict[str, Any],
    strategy_name: str,
    symbol: str,
    output_dir: str
) -> None:
    """
    Save backtest results.
    
    Args:
        results: Backtest results.
        strategy_name: Strategy name.
        symbol: Trading symbol.
        output_dir: Output directory.
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Format symbol for filename (replace / with _)
    symbol_formatted = symbol.replace("/", "_")
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{strategy_name}_{symbol_formatted}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Convert numpy types to Python types for JSON serialization
    results_copy = {}
    for key, value in results.items():
        if isinstance(value, np.integer):
            results_copy[key] = int(value)
        elif isinstance(value, np.floating):
            results_copy[key] = float(value)
        elif isinstance(value, np.ndarray):
            results_copy[key] = value.tolist()
        else:
            results_copy[key] = value
    
    # Write to JSON file
    import json
    with open(filepath, "w") as f:
        json.dump(results_copy, f, indent=2, default=str)
    
    print(f"Results saved to {filepath}")


def run_validation(args: argparse.Namespace) -> None:
    """
    Run strategy validation.
    
    Args:
        args: Command-line arguments.
    """
    # Resolve symbol
    symbol = args.symbol or settings.trading.symbol
    
    # Print header
    print_header(args.strategy, symbol, args.days, args.initial_capital)
    
    # Run backtest(s)
    if args.strategy == "all":
        strategies = ["low_risk", "medium_risk", "high_risk"]
        all_results = {}
        
        for strategy_name in strategies:
            results = run_backtest(
                strategy_name=strategy_name,
                exchange_name=args.exchange,
                symbol=symbol,
                days=args.days,
                initial_capital=args.initial_capital
            )
            
            all_results[strategy_name] = results
            
            # Generate plots if requested
            if args.plot:
                generate_plots(results, strategy_name, args.output)
            
            # Save results
            save_results(results, strategy_name, symbol, args.output)
            
        # Print comparison
        print("\n" + "=" * 80)
        print("STRATEGY COMPARISON".center(80, "="))
        print("=" * 80)
        print(f"{'Strategy':<15} {'Return %':<10} {'Annual %':<10} {'Sharpe':<10} {'Drawdown':<10} {'Win Rate':<10}")
        print("-" * 80)
        
        for strategy_name, results in all_results.items():
            print(
                f"{strategy_name:<15} "
                f"{results['return_pct']:<10.2f} "
                f"{results['annualized_return_pct']:<10.2f} "
                f"{results['sharpe_ratio']:<10.2f} "
                f"{results['max_drawdown_pct']:<10.2f} "
                f"{results['win_rate']:<10.2f}"
            )
        
        print("=" * 80)
    else:
        # Run single strategy backtest
        results = run_backtest(
            strategy_name=args.strategy,
            exchange_name=args.exchange,
            symbol=symbol,
            days=args.days,
            initial_capital=args.initial_capital
        )
        
        # Generate plots if requested
        if args.plot:
            generate_plots(results, args.strategy, args.output)
        
        # Save results
        save_results(results, args.strategy, symbol, args.output)


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    try:
        # Run validation
        run_validation(args)
    except KeyboardInterrupt:
        print("\nValidation stopped by user")
    except Exception as e:
        print(f"\nError during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
