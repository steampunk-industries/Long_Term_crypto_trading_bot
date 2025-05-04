# Paper Trading Deployment Guide (Fixed Version)

This guide provides updated instructions for deploying the crypto trading bot in paper trading mode without requiring real exchange connectivity. The bot now uses a mock exchange implementation that simulates market data locally, allowing it to run even when access to exchanges is restricted.

## Overview of Fixes

The following issues have been addressed:

1. **Geo-restriction bypass**: The bot no longer requires actual API connectivity to exchanges when in paper trading mode, allowing it to run from restricted locations.
2. **Circuit breaker resilience**: Mock exchanges are immune to circuit breaker issues that occur with real exchanges.
3. **True simulation**: All market data is simulated locally with realistic price movements, volatility, and trends.
4. **Persistent state**: Trades, balances, and orders are saved between sessions.

## Deployment Steps

### 1. Ensure Your Environment is Set Up

Make sure you have the basic requirements:

```bash
# Clone the repository if you haven't already
git clone https://github.com/your-username/crypto_trading_bot.git
cd crypto_trading_bot

# Create and activate virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure for Paper Trading

Create/edit your `.env` file to ensure paper trading is enabled:

```bash
# Copy example file if you don't have a .env file
cp .env.example .env
```

Edit the `.env` file and make sure these settings are present:

```
# CRITICAL: This must be set to true for paper trading
PAPER_TRADING=true

# Trading configuration
TRADING_SYMBOL=BTC/USDT
INITIAL_CAPITAL=10000

# Database configuration - Use SQLite for simplicity
DATABASE_URL=sqlite:///data/crypto_bot.db
```

The API keys are no longer required for paper trading, but you can leave them as placeholders:

```
# API Keys (not used in paper trading mode with mock exchange)
BINANCE_API_KEY=papertrading
BINANCE_API_SECRET=papertrading
```

### 3. Initialize the Database

```bash
# Create necessary directories
mkdir -p data logs

# Initialize the database
python -c "from src.utils.database import init_db; init_db()"
```

### 4. Run the Bot

Start the bot in paper trading mode:

```bash
python paper_trading.py
```

You can also run specific strategies:

```bash
# Run only low-risk strategy
python paper_trading.py --low-risk

# Run high-risk strategy with more verbose logging
python paper_trading.py --high-risk --verbose
```

## Monitoring

Access the dashboard to monitor your paper trading:

```
Dashboard URL: http://localhost:5000
Username: admin
Password: admin (or as configured in your .env file)
```

View logs to see what's happening:

```bash
tail -f logs/crypto_bot.log
```

## How the Mock Exchange Works

The mock exchange implementation:

1. Simulates realistic price movements using random walk with drift
2. Processes orders (market and limit) with realistic execution
3. Tracks balances and positions
4. Maintains order and trade history
5. Persists state between sessions

All trading activities happen locally without connecting to any external exchange APIs.

## Customizing the Simulation

You can customize the mock exchange behavior by editing `src/exchange/mock_exchange.py`:

- Adjust volatility by modifying the `self.volatility` value
- Change the trend direction by changing `self.trend` (positive for uptrend, negative for downtrend)
- Edit initial prices in the `_get_initial_price()` method

## Transitioning to Live Trading

Once you're satisfied with your paper trading results:

1. Make sure you have valid API keys for your chosen exchange
2. Test with small amounts initially
3. Set `PAPER_TRADING=false` in your `.env` file

## Troubleshooting

### Mock Exchange State Reset

If you need to reset the mock exchange state:

```bash
# Remove the state files
rm data/mock_exchange_state_*.json
```

### Database Issues

If you encounter database issues, you can reset the database:

```bash
# Remove the SQLite database file
rm data/crypto_bot.db

# Re-initialize the database
python -c "from src.utils.database import init_db; init_db()"
```

### Logs Showing Previous Errors

Old errors in the log file? Clear the logs:

```bash
> logs/crypto_bot.log
```

## Additional Resources

- See the original `PAPER_TRADING_GUIDE.md` for detailed explanations of strategies
- Refer to `README.md` for general bot information
