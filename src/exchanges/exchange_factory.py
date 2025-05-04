from typing import Dict, List, Optional, Union
from loguru import logger

from src.config import config
from src.exchanges.base_exchange import BaseExchange
from src.exchanges.binance_exchange import BinanceExchange
from src.exchanges.coinbase_exchange import CoinbaseExchange
from src.exchanges.kucoin_exchange import KucoinExchange
from src.exchanges.gemini_exchange import GeminiExchange
from src.exchanges.kraken_exchange import KrakenExchange
from src.exchanges.multi_exchange import MultiExchange

class ExchangeFactory:
    """
    Factory class for creating exchange instances.
    """
    
    @staticmethod
    def create_exchange(
        exchange_name: str, 
        api_key: str = "", 
        api_secret: str = "", 
        paper_trading: bool = True,
        initial_balance: Dict[str, float] = None,
        **kwargs
    ) -> Optional[BaseExchange]:
        """
        Create an exchange instance based on the exchange name.
        
        Args:
            exchange_name: Name of the exchange ('coinbase', 'gemini', 'kucoin', 'kraken', 'binance', 'multi')
            api_key: API key for the exchange
            api_secret: API secret for the exchange
            paper_trading: Whether to use paper trading mode
            initial_balance: Initial balance for paper trading
            **kwargs: Additional arguments for specific exchanges
            
        Returns:
            BaseExchange: Exchange instance, or None if the exchange is not supported
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name == 'coinbase':
            return CoinbaseExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=paper_trading,
                initial_balance=initial_balance
            )
        elif exchange_name == 'gemini':
            return GeminiExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=paper_trading,
                initial_balance=initial_balance
            )
        elif exchange_name == 'kucoin':
            # Note: KucoinExchange doesn't accept passphrase parameter
            return KucoinExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=paper_trading,
                initial_balance=initial_balance
            )
        elif exchange_name == 'binance':
            return BinanceExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=paper_trading,
                initial_balance=initial_balance
            )
        elif exchange_name == 'kraken':
            # Note: Remove exchange_id parameter to fix type error
            return KrakenExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=paper_trading,
                initial_balance=initial_balance
            )
        elif exchange_name == 'multi':
            exchanges = kwargs.get('exchanges', None)
            use_steampunk_data = kwargs.get('use_steampunk_data', True)
            return MultiExchange(
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=True,  # Always paper trading for multi-exchange
                initial_balance=initial_balance,
                exchanges=exchanges,
                use_steampunk_data=use_steampunk_data
            )
        else:
            logger.error(f"Unsupported exchange: {exchange_name}")
            return None
    
    @staticmethod
    def create_exchange_from_config(exchange_name: str) -> Optional[BaseExchange]:
        """
        Create an exchange instance based on the exchange name using configuration.
        
        Args:
            exchange_name: Name of the exchange ('coinbase', 'gemini', 'kucoin', 'kraken', 'binance', 'multi')
            
        Returns:
            BaseExchange: Exchange instance, or None if the exchange is not supported
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name == 'coinbase':
            return ExchangeFactory.create_exchange(
                exchange_name='coinbase',
                api_key=config.COINBASE_API_KEY,
                api_secret=config.COINBASE_API_SECRET,
                paper_trading=config.PAPER_TRADING,
                initial_balance={"USDT": config.INITIAL_CAPITAL}
            )
        elif exchange_name == 'gemini':
            return ExchangeFactory.create_exchange(
                exchange_name='gemini',
                api_key=config.GEMINI_API_KEY,
                api_secret=config.GEMINI_API_SECRET,
                paper_trading=config.PAPER_TRADING,
                initial_balance={"USDT": config.INITIAL_CAPITAL}
            )
        elif exchange_name == 'kucoin':
            return ExchangeFactory.create_exchange(
                exchange_name='kucoin',
                api_key=config.KUCOIN_API_KEY,
                api_secret=config.KUCOIN_API_SECRET,
                paper_trading=config.PAPER_TRADING,
                initial_balance={"USDT": config.INITIAL_CAPITAL}
            )
        elif exchange_name == 'binance':
            return ExchangeFactory.create_exchange(
                exchange_name='binance',
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET,
                paper_trading=config.PAPER_TRADING,
                initial_balance={"USDT": config.INITIAL_CAPITAL}
            )
        elif exchange_name == 'kraken':
            return ExchangeFactory.create_exchange(
                exchange_name='kraken',
                api_key=config.KRAKEN_API_KEY,
                api_secret=config.KRAKEN_API_SECRET,
                paper_trading=config.PAPER_TRADING,
                initial_balance={"USDT": config.INITIAL_CAPITAL}
            )
        elif exchange_name == 'multi':
            # For multi-exchange, we'll use US-available exchanges
            return ExchangeFactory.create_exchange(
                exchange_name='multi',
                paper_trading=True,  # Always paper trading for multi-exchange
                initial_balance={"USDT": config.INITIAL_CAPITAL},
                exchanges=["coinbase", "gemini", "kucoin", "kraken"],
                use_steampunk_data=True
            )
        else:
            logger.error(f"Unsupported exchange: {exchange_name}")
            return None
