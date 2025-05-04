import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to load and provide access to environment variables."""

    # Exchange API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', '')
    COINBASE_API_SECRET = os.getenv('COINBASE_API_SECRET', '')
    KUCOIN_API_KEY = os.getenv('KUCOIN_API_KEY', '')
    KUCOIN_API_SECRET = os.getenv('KUCOIN_API_SECRET', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_API_SECRET = os.getenv('GEMINI_API_SECRET', '')
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY', '')
    KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET', '')

    # Steampunk Holdings API Keys
    STEAMPUNK_API_KEY = os.getenv('STEAMPUNK_API_KEY', '')
    STEAMPUNK_API_SECRET = os.getenv('STEAMPUNK_API_SECRET', '')
    STEAMPUNK_API_URL = os.getenv('STEAMPUNK_API_URL', 'https://api.steampunk.holdings/v1')

    # On-Chain Data API Keys
    GLASSNODE_API_KEY = os.getenv('GLASSNODE_API_KEY', '')
    CRYPTOQUANT_API_KEY = os.getenv('CRYPTOQUANT_API_KEY', '')

    # Sentiment Analysis API Keys
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY', '')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET', '')
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')

    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'crypto_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

    # Trading Configuration
    TRADING_SYMBOL = os.getenv('TRADING_SYMBOL', 'BTC/USDT')
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 10000))
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    USE_MULTI_EXCHANGE = os.getenv('USE_MULTI_EXCHANGE', 'false').lower() == 'true'
    TRADING_EXCHANGE = os.getenv('TRADING_EXCHANGE', 'binance').lower()

    # Risk Parameters
    LOW_RISK_STOP_LOSS = float(os.getenv('LOW_RISK_STOP_LOSS', 0.02))
    MEDIUM_RISK_STOP_LOSS = float(os.getenv('MEDIUM_RISK_STOP_LOSS', 0.03))
    HIGH_RISK_STOP_LOSS = float(os.getenv('HIGH_RISK_STOP_LOSS', 0.05))

    # Strategy Parameters
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.6'))  # Threshold for signal execution
    RISK_PER_TRADE_PCT = float(os.getenv('RISK_PER_TRADE_PCT', '0.02'))    # 2% risk per trade
    MAX_POSITION_SIZE_PCT = float(os.getenv('MAX_POSITION_SIZE_PCT', '0.2'))  # 20% max position size

    # API Retry Parameters
    API_MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))
    API_RETRY_DELAY = float(os.getenv('API_RETRY_DELAY', '1.0'))  # Initial delay in seconds
    
    # Service Monitoring
    SERVICE_CHECK_INTERVAL = int(os.getenv('SERVICE_CHECK_INTERVAL', '60'))  # seconds
    ALERT_THRESHOLD = int(os.getenv('ALERT_THRESHOLD', '3'))  # failures before alert

    # Leverage
    MEDIUM_RISK_LEVERAGE = float(os.getenv('MEDIUM_RISK_LEVERAGE', 2))
    HIGH_RISK_LEVERAGE = float(os.getenv('HIGH_RISK_LEVERAGE', 5))

    # Exchange Fees
    TAKER_FEE = float(os.getenv('TAKER_FEE', 0.0004))
    MAKER_FEE = float(os.getenv('MAKER_FEE', 0.0002))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_TO_CLOUDWATCH = os.getenv('LOG_TO_CLOUDWATCH', 'false').lower() == 'true'

    # Portfolio Management
    MAX_PORTFOLIO_DRAWDOWN = float(os.getenv('MAX_PORTFOLIO_DRAWDOWN', 0.15))
    MAX_CORRELATION = float(os.getenv('MAX_CORRELATION', 0.7))
    MAX_ALLOCATION_PER_ASSET = float(os.getenv('MAX_ALLOCATION_PER_ASSET', 0.25))
    RISK_FREE_RATE = float(os.getenv('RISK_FREE_RATE', 0.02))

    # Profit Withdrawal Settings
    PROFIT_THRESHOLD = float(os.getenv('PROFIT_THRESHOLD', 50000))
    PROFIT_WITHDRAWAL_PERCENTAGE = float(os.getenv('PROFIT_WITHDRAWAL_PERCENTAGE', 0.5))

    # Market Regime Detection
    VOLATILITY_WINDOW = int(os.getenv('VOLATILITY_WINDOW', 20))
    TREND_WINDOW = int(os.getenv('TREND_WINDOW', 50))
    VOLATILITY_THRESHOLD_HIGH = float(os.getenv('VOLATILITY_THRESHOLD_HIGH', 0.03))
    VOLATILITY_THRESHOLD_LOW = float(os.getenv('VOLATILITY_THRESHOLD_LOW', 0.01))
    TREND_THRESHOLD = float(os.getenv('TREND_THRESHOLD', 0.5))

    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', '')

    # Web Dashboard
    DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 5000))
    DASHBOARD_USERNAME = os.getenv('DASHBOARD_USERNAME', 'admin')
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', 'password')

    # TensorFlow Configuration
    TF_ENABLE_GPU = os.getenv('TF_ENABLE_GPU', 'false').lower() == 'true'
    TF_GPU_MEMORY_LIMIT = int(os.getenv('TF_GPU_MEMORY_LIMIT', 4096))

    @classmethod
    def validate(cls):
        """Validate the configuration and log warnings for missing required values."""
        if cls.PAPER_TRADING:
            logger.info("Running in PAPER TRADING mode")

            # Check if multi-exchange is enabled
            if cls.USE_MULTI_EXCHANGE or cls.TRADING_EXCHANGE == 'multi':
                logger.info("Using multi-exchange aggregation for paper trading")

# Create a global config instance for convenience
config = Config()
