#!/usr/bin/env python3

"""
Test script to verify that the MultiExchange implementation is working correctly
"""

from src.exchanges.exchange_factory import ExchangeFactory
from src.multi_currency_bot import MultiCurrencyBot
from loguru import logger
import time

def test_multi_exchange():
    """Test the MultiExchange implementation"""
    try:
        # Create a multi-exchange instance
        logger.info("Creating MultiExchange instance...")
        multi_exchange = ExchangeFactory.create_exchange('multi', paper_trading=True)
        
        if multi_exchange and multi_exchange.connect():
            logger.info("Successfully connected to MultiExchange")
            
            # Test get_top_symbols method
            logger.info("Testing get_top_symbols method...")
            symbols = multi_exchange.get_top_symbols(limit=5, quote='USDT')
            logger.info(f"Top symbols: {symbols}")
            
            # Test getting ticker data
            for symbol in symbols:
                logger.info(f"Getting ticker for {symbol}...")
                ticker = multi_exchange.get_ticker(symbol)
                logger.info(f"Ticker: {ticker}")
                time.sleep(1)  # Avoid API rate limits
            
            logger.info("MultiExchange test completed successfully!")
            return True
        else:
            logger.error("Failed to connect to MultiExchange")
            return False
    except Exception as e:
        logger.error(f"Error testing MultiExchange: {e}")
        return False

if __name__ == "__main__":
    test_multi_exchange()
