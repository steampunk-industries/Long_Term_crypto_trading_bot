"""
Mock exchange module for paper trading.
Provides a simulated exchange interface that doesn't require real API connections.
"""

import datetime
import time
import random
import json
import os
import math
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pathlib import Path

from src.config import settings
from src.utils.logging import logger


class MockExchange:
    """A mock exchange for paper trading without real API calls."""

    def __init__(self, exchange_name: str = "binance"):
        """
        Initialize the mock exchange.

        Args:
            exchange_name: The name of the exchange to simulate.
        """
        self.exchange_name = exchange_name
        self.symbol = settings.trading.symbol
        self.base_currency, self.quote_currency = self.symbol.split('/')
        
        # Initial balance based on settings
        self.balance = {
            self.quote_currency: settings.trading.initial_capital,
            self.base_currency: 0.0
        }
        
        # Order books and trade history
        self.orders = {}
        self.trades = []
        self.order_id_counter = 1000000
        
        # Price simulation parameters
        self.last_price = self._get_initial_price()
        self.volatility = 0.01  # 1% daily volatility
        self.trend = 0.0001  # Slight upward trend
        self.last_update_time = time.time()
        
        # Market data cache
        self.ohlcv_cache = {}
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Save state file path
        self.state_file = f'data/mock_exchange_state_{exchange_name}.json'
        
        # Load previous state if available
        self._load_state()
        
        logger.info(f"Initialized mock exchange for {exchange_name} with {self.symbol}")
        logger.info(f"Initial balance: {self.balance}")

    def _get_initial_price(self) -> float:
        """
        Get initial price for the trading pair.
        
        Returns:
            A realistic initial price for the symbol.
        """
        # Default prices for common trading pairs
        default_prices = {
            'BTC/USDT': 65000.0,
            'ETH/USDT': 3500.0,
            'BNB/USDT': 550.0,
            'SOL/USDT': 120.0,
            'XRP/USDT': 0.55,
        }
        
        # Return default price if available, otherwise a reasonable price
        if self.symbol in default_prices:
            return default_prices[self.symbol]
        
        # For other pairs, choose a reasonable price
        if self.symbol.endswith('/USDT'):
            # Major coins likely > $1, minor coins < $1
            if self.base_currency in ['BTC', 'ETH', 'BNB', 'SOL', 'AVAX', 'LINK']:
                return random.uniform(50, 5000)
            else:
                return random.uniform(0.01, 10)
        
        # For BTC pairs
        if self.symbol.endswith('/BTC'):
            return random.uniform(0.00001, 0.1)
        
        # Default price as fallback
        return 100.0

    def _load_state(self) -> None:
        """Load the previous state if available."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                    self.balance = state.get('balance', self.balance)
                    self.orders = state.get('orders', {})
                    self.trades = state.get('trades', [])
                    self.last_price = state.get('last_price', self.last_price)
                    self.order_id_counter = state.get('order_id_counter', self.order_id_counter)
                    
                    logger.info(f"Loaded previous state for {self.exchange_name}")
                    logger.info(f"Current balance: {self.balance}")
        except Exception as e:
            logger.error(f"Failed to load previous state: {e}")
            # Continue with default initialization

    def _save_state(self) -> None:
        """Save the current state."""
        try:
            state = {
                'balance': self.balance,
                'orders': self.orders,
                'trades': self.trades[-100:],  # Only keep last 100 trades
                'last_price': self.last_price,
                'order_id_counter': self.order_id_counter
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.debug(f"Saved state for {self.exchange_name}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _simulate_price_movement(self) -> float:
        """
        Simulate realistic price movement.
        
        Returns:
            The new current price.
        """
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        # Only update price if some time has passed
        if time_diff < 0.1:
            return self.last_price
            
        # Calculate price change based on time difference
        # Using Geometric Brownian Motion
        drift = self.trend * time_diff
        volatility_factor = self.volatility * math.sqrt(time_diff / 86400)  # Scale volatility to time frame
        random_factor = random.normalvariate(0, 1) * volatility_factor
        
        change_percent = drift + random_factor
        
        # Calculate new price
        new_price = self.last_price * (1 + change_percent)
        
        # Ensure price doesn't go negative or unrealistically low
        new_price = max(new_price, self.last_price * 0.9)
        
        # Update state
        self.last_price = new_price
        self.last_update_time = current_time
        
        return new_price

    def fetch_balance(self) -> Dict[str, Dict[str, float]]:
        """
        Fetch account balance.
        
        Returns:
            A dictionary of balances.
        """
        # Format balance in CCXT style
        result = {
            'free': self.balance.copy(),
            'used': {k: 0.0 for k in self.balance},
            'total': self.balance.copy()
        }
        
        # Calculate used balance from open orders
        for order_id, order in self.orders.items():
            if order['status'] == 'open':
                currency = self.base_currency if order['side'] == 'sell' else self.quote_currency
                
                if order['side'] == 'sell':
                    amount = order['amount']
                else:  # buy
                    amount = order['amount'] * order['price']
                    
                result['used'][currency] = result['used'].get(currency, 0.0) + amount
                result['free'][currency] = result['total'][currency] - result['used'][currency]
        
        return result

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the current ticker.
        
        Args:
            symbol: The trading symbol.
            
        Returns:
            A dictionary with ticker information.
        """
        if symbol != self.symbol:
            # Simulate data for other symbols with different price ranges
            base, quote = symbol.split('/')
            
            if base == 'BTC':
                price = 65000.0 * (1 + random.uniform(-0.01, 0.01))
            elif base == 'ETH':
                price = 3500.0 * (1 + random.uniform(-0.01, 0.01))
            elif base in ['USDT', 'USDC', 'DAI']:
                price = 1.0 * (1 + random.uniform(-0.001, 0.001))
            else:
                price = random.uniform(0.1, 1000.0)
        else:
            # Use our simulated price for the main symbol
            price = self._simulate_price_movement()
        
        # Simulate ticker data in CCXT format
        current_time = time.time() * 1000  # milliseconds
        ticker = {
            'symbol': symbol,
            'timestamp': current_time,
            'datetime': datetime.datetime.fromtimestamp(current_time / 1000).isoformat(),
            'high': price * (1 + random.uniform(0.001, 0.005)),
            'low': price * (1 - random.uniform(0.001, 0.005)),
            'bid': price * (1 - random.uniform(0.0001, 0.0005)),
            'bidVolume': random.uniform(1, 10),
            'ask': price * (1 + random.uniform(0.0001, 0.0005)),
            'askVolume': random.uniform(1, 10),
            'vwap': price * (1 + random.uniform(-0.001, 0.001)),
            'open': price * (1 - random.uniform(-0.005, 0.005)),
            'close': price,
            'last': price,
            'previousClose': price * (1 - random.uniform(-0.005, 0.005)),
            'change': price * random.uniform(-0.01, 0.01),
            'percentage': random.uniform(-1, 1),
            'average': price * (1 + random.uniform(-0.001, 0.001)),
            'baseVolume': random.uniform(100, 1000),
            'quoteVolume': random.uniform(100, 1000) * price,
            'info': {}
        }
        
        return ticker

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        """
        Fetch OHLCV data.
        
        Args:
            symbol: The trading symbol.
            timeframe: The timeframe.
            limit: Number of candles to fetch.
            
        Returns:
            A list of OHLCV candles.
        """
        # Check if we have cached data
        cache_key = f"{symbol}_{timeframe}_{limit}"
        if cache_key in self.ohlcv_cache:
            data = self.ohlcv_cache[cache_key]
            
            # Update the most recent candle
            current_price = self._simulate_price_movement()
            last_candle = data[-1]
            
            # Update the close price and high/low if needed
            last_candle[4] = current_price  # close
            last_candle[2] = max(last_candle[2], current_price)  # high
            last_candle[3] = min(last_candle[3], current_price)  # low
            
            return data
            
        # Generate realistic OHLCV data
        current_price = self._simulate_price_movement()
        
        # Determine timeframe in seconds
        timeframe_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '6h': 21600,
            '8h': 28800,
            '12h': 43200,
            '1d': 86400,
            '3d': 259200,
            '1w': 604800,
            '1M': 2592000,
        }.get(timeframe, 3600)  # Default to 1h
        
        # Generate timestamps
        end_time = int(time.time())
        timestamps = [(end_time - i * timeframe_seconds) * 1000 for i in range(limit)]
        timestamps.reverse()
        
        # Daily volatility scaled to the timeframe
        period_volatility = self.volatility * math.sqrt(timeframe_seconds / 86400)
        
        # Generate price data with a slight trend
        ohlcv_data = []
        
        # Start with the current price and work backwards
        simulated_close = current_price
        
        for i in range(limit):
            # Calculate the close price
            if i > 0:
                # Random walk with drift
                random_change = random.normalvariate(0, 1) * period_volatility
                trend_factor = self.trend * (timeframe_seconds / 86400)
                simulated_close = simulated_close * (1 + random_change + trend_factor)
            
            # Generate O, H, L values
            intra_period_volatility = period_volatility * 0.5
            open_price = simulated_close * (1 + random.normalvariate(0, 1) * intra_period_volatility)
            high_price = max(open_price, simulated_close) * (1 + abs(random.normalvariate(0, 1) * intra_period_volatility))
            low_price = min(open_price, simulated_close) * (1 - abs(random.normalvariate(0, 1) * intra_period_volatility))
            
            # Ensure high >= open, close and low <= open, close
            high_price = max(high_price, open_price, simulated_close)
            low_price = min(low_price, open_price, simulated_close)
            
            # Generate volume - higher on bigger price moves
            price_change_pct = abs((simulated_close - open_price) / open_price)
            volume_base = random.uniform(10, 100)  # Base volume
            volume = volume_base * (1 + price_change_pct * 10)  # Volume increases with price change
            
            # Create OHLCV candle
            candle = [
                timestamps[i],  # timestamp
                open_price,     # open
                high_price,     # high
                low_price,      # low
                simulated_close,# close
                volume          # volume
            ]
            
            ohlcv_data.append(candle)
        
        # Cache the data
        self.ohlcv_cache[cache_key] = ohlcv_data
        
        return ohlcv_data

    def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None) -> Dict[str, Any]:
        """
        Create an order.
        
        Args:
            symbol: The trading symbol.
            type: Order type (limit/market).
            side: Order side (buy/sell).
            amount: Order amount.
            price: Order price (for limit orders).
            
        Returns:
            The order details.
        """
        if symbol != self.symbol:
            logger.warning(f"Mock exchange only supports {self.symbol}, but {symbol} was requested")
        
        # Generate order ID
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        
        # Get current price
        current_price = self.last_price if type == 'market' else price
        
        # Check balance
        base_currency, quote_currency = symbol.split('/')
        
        if side == 'buy':
            required_balance = amount * current_price
            if self.balance.get(quote_currency, 0) < required_balance:
                raise Exception(f"Insufficient {quote_currency} balance")
        else:  # sell
            if self.balance.get(base_currency, 0) < amount:
                raise Exception(f"Insufficient {base_currency} balance")
        
        # Create order object
        timestamp = int(time.time() * 1000)
        order = {
            'id': order_id,
            'timestamp': timestamp,
            'datetime': datetime.datetime.fromtimestamp(timestamp / 1000).isoformat(),
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': current_price,
            'amount': amount,
            'filled': 0.0,
            'remaining': amount,
            'status': 'open',
            'fee': {
                'cost': 0.0,
                'currency': quote_currency if side == 'buy' else base_currency
            }
        }
        
        # Store order
        self.orders[order_id] = order
        
        # Execute market orders immediately
        if type == 'market':
            self._execute_order(order_id)
        
        # Save state after order creation
        self._save_state()
        
        return order

    def _execute_order(self, order_id: str) -> None:
        """
        Execute an order.
        
        Args:
            order_id: The order ID.
        """
        if order_id not in self.orders:
            return
            
        order = self.orders[order_id]
        
        # Skip already filled orders
        if order['status'] != 'open' or order['remaining'] <= 0:
            return
            
        # Get order details
        symbol = order['symbol']
        side = order['side']
        amount = order['remaining']
        price = order['price']
        base_currency, quote_currency = symbol.split('/')
        
        # Calculate fee
        fee_rate = settings.trading.taker_fee
        fee_amount = amount * price * fee_rate if side == 'buy' else amount * fee_rate
        fee_currency = quote_currency if side == 'buy' else base_currency
        
        # Update balances
        if side == 'buy':
            # Pay quote currency, receive base currency
            cost = amount * price
            self.balance[quote_currency] = self.balance.get(quote_currency, 0) - cost
            received_amount = amount * (1 - fee_rate) if fee_currency == base_currency else amount
            self.balance[base_currency] = self.balance.get(base_currency, 0) + received_amount
        else:  # sell
            # Pay base currency, receive quote currency
            self.balance[base_currency] = self.balance.get(base_currency, 0) - amount
            received_amount = amount * price * (1 - fee_rate) if fee_currency == quote_currency else amount * price
            self.balance[quote_currency] = self.balance.get(quote_currency, 0) + received_amount
        
        # Update order status
        order['filled'] = order['amount']
        order['remaining'] = 0.0
        order['status'] = 'closed'
        
        # Update fee
        order['fee'] = {
            'cost': fee_amount,
            'currency': fee_currency
        }
        
        # Create trade record
        timestamp = int(time.time() * 1000)
        trade = {
            'id': f"t{order_id}",
            'order': order_id,
            'timestamp': timestamp,
            'datetime': datetime.datetime.fromtimestamp(timestamp / 1000).isoformat(),
            'symbol': symbol,
            'type': order['type'],
            'side': side,
            'price': price,
            'amount': amount,
            'fee': order['fee'],
            'cost': amount * price
        }
        
        # Add trade to history
        self.trades.append(trade)
        
        # Log the execution
        logger.info(f"Executed {side} order for {amount} {base_currency} at {price} {quote_currency}")
        
        # Save state after execution
        self._save_state()

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
        
        # Can only cancel open orders
        if order['status'] != 'open':
            raise Exception(f"Order {order_id} is not open")
            
        # Cancel the order
        order['status'] = 'canceled'
        
        # Save state after cancellation
        self._save_state()
        
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
            
        # Process any pending limit orders that might match current price
        self._process_limit_orders()
            
        return self.orders[order_id]

    def fetch_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch open orders.
        
        Args:
            symbol: The trading symbol.
            
        Returns:
            A list of open orders.
        """
        # Process any pending limit orders first
        self._process_limit_orders()
        
        # Filter orders by symbol and status
        open_orders = [
            order for order in self.orders.values()
            if order['symbol'] == symbol and order['status'] == 'open'
        ]
        
        return open_orders

    def fetch_closed_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch closed orders.
        
        Args:
            symbol: The trading symbol.
            
        Returns:
            A list of closed orders.
        """
        # Process any pending limit orders first
        self._process_limit_orders()
        
        # Filter orders by symbol and status
        closed_orders = [
            order for order in self.orders.values()
            if order['symbol'] == symbol and order['status'] in ['closed', 'canceled']
        ]
        
        return closed_orders

    def fetch_my_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch my trades.
        
        Args:
            symbol: The trading symbol.
            
        Returns:
            A list of trades.
        """
        # Filter trades by symbol
        filtered_trades = [
            trade for trade in self.trades
            if trade['symbol'] == symbol
        ]
        
        return filtered_trades

    def _process_limit_orders(self) -> None:
        """Process limit orders that may have been filled."""
        current_price = self._simulate_price_movement()
        
        for order_id, order in list(self.orders.items()):
            # Skip non-open or non-limit orders
            if order['status'] != 'open' or order['type'] != 'limit':
                continue
                
            # Check if order price matches current price
            price_matches = False
            
            if order['side'] == 'buy' and current_price <= order['price']:
                # Buy orders are filled when price falls to or below order price
                price_matches = True
            elif order['side'] == 'sell' and current_price >= order['price']:
                # Sell orders are filled when price rises to or above order price
                price_matches = True
                
            if price_matches:
                # Execute the order
                self._execute_order(order_id)
