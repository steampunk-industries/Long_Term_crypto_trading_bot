# Paper Trading with Public APIs and Steampunk.Holdings Integration

This guide explains how to use the crypto trading bot with paper trading functionality using public APIs from multiple exchanges and integration with steampunk.holdings.

## Overview

The enhanced paper trading functionality allows you to:

1. **Use public APIs from multiple exchanges** - Aggregate market data from Binance, Coinbase, KuCoin, Kraken, and more
2. **Trade with virtual funds** - Test strategies without risking real money
3. **Integrate with steampunk.holdings** - Sync your portfolio and trades with the steampunk.holdings platform

## Prerequisites

Before starting, ensure you have:

1. Python 3.8+ installed
2. Required Python packages installed (`pip install -r requirements.txt`)
3. A steampunk.holdings account (optional, for integration)

## Configuration

### 1. Environment Variables

The following environment variables can be set in the `.env` file:

```
# Paper Trading Configuration
PAPER_TRADING=true
USE_MULTI_EXCHANGE=true
TRADING_EXCHANGE=multi
TRADING_SYMBOL=BTC/USDT
INITIAL_CAPITAL=10000

# Steampunk Holdings API Keys (optional)
STEAMPUNK_API_KEY=your_api_key
STEAMPUNK_API_SECRET=your_api_secret
STEAMPUNK_API_URL=https://api.steampunk.holdings/v1
```

### 2. Exchange Selection

You can specify which exchanges to use for data aggregation:

- In the `.env` file: `MULTI_EXCHANGE_SOURCES=binance,coinbase,kucoin,kraken`
- Or via command-line arguments when running the scripts

## Testing the Setup

Before running the bot, you can test the paper trading functionality:

```bash
./test_paper_trading_with_public_apis.py --symbol BTC/USDT --exchanges binance,coinbase,kucoin,kraken --test-order
```

To test the steampunk.holdings integration (if configured):

```bash
./test_paper_trading_with_public_apis.py --symbol BTC/USDT --steampunk
```

## Running the Bot

To run the bot with paper trading and steampunk.holdings integration:

```bash
./run_paper_trading_with_steampunk.py --symbol BTC/USDT --interval 15 --initial-capital 10000
```

Command-line options:

- `--symbol`: Trading symbol (default: BTC/USDT)
- `--interval`: Run interval in minutes (default: 15)
- `--exchanges`: Comma-separated list of exchanges (default: binance,coinbase,kucoin,kraken)
- `--initial-capital`: Initial capital in USDT (default: 10000)
- `--dashboard-port`: Dashboard port (default: from .env)
- `--verbose`: Enable verbose logging

## How It Works

### Multi-Exchange Aggregation

The multi-exchange functionality:

1. Connects to multiple exchanges using public APIs
2. Aggregates market data (prices, order books, historical data)
3. Removes outliers and calculates consensus values
4. Caches data to reduce API calls and avoid rate limits

### Paper Trading

The paper trading functionality:

1. Simulates order execution with realistic slippage and fees
2. Tracks virtual balances across multiple currencies
3. Provides a realistic trading experience without real funds

### Steampunk.Holdings Integration

The steampunk.holdings integration:

1. Syncs your portfolio data with steampunk.holdings
2. Reports trades and performance metrics
3. Allows you to monitor your paper trading performance on the steampunk.holdings platform

## Dashboard

The web dashboard is available at `http://localhost:5001` (or the port specified in your configuration).

The dashboard provides:

1. Real-time portfolio value and performance metrics
2. Trade history and open positions
3. Market data and charts
4. Strategy performance analysis

## Troubleshooting

### API Rate Limits

If you encounter rate limit issues:

1. Reduce the frequency of bot runs (increase the interval)
2. Use fewer exchanges in the multi-exchange configuration
3. Implement a paid API plan for higher rate limits

### Steampunk.Holdings Connection Issues

If you have issues connecting to steampunk.holdings:

1. Verify your API keys are correct
2. Check your network connection
3. Ensure the steampunk.holdings API is available

## Advanced Usage

### Custom Strategies

You can create custom strategies in the `src/strategies/` directory. Each strategy should inherit from the `BaseStrategy` class.

### Data Sources

You can add additional data sources by implementing new exchange classes in the `src/exchanges/` directory.

### Performance Optimization

For better performance:

1. Use a local database for caching market data
2. Run the bot on a server with good internet connectivity
3. Optimize the strategies for fewer API calls

## Support

For support with steampunk.holdings integration, contact support@steampunk.holdings.

For issues with the bot itself, please open an issue on the GitHub repository.
