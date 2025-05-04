# Paper Trading Guide for Crypto Trading Bot

This guide provides detailed instructions for setting up and running the crypto trading bot in paper trading mode. Paper trading allows you to test the bot with real market data but without risking actual funds.

## Prerequisites

Before starting, ensure you have:

1. Python 3.11 installed (required for TensorFlow 2.13 compatibility)
2. PostgreSQL database set up
3. All required Python packages installed
4. API keys from your preferred exchange (even for paper trading)

## Setup Process

### 1. Clone the Repository

If you haven't already, clone the repository:

```bash
git clone https://github.com/your-username/crypto_trading_bot.git
cd crypto_trading_bot
```

### 2. Create and Activate a Virtual Environment

For proper dependency isolation, it's highly recommended to use a virtual environment. You can set up a virtual environment in two ways:

#### Option 1: Using the setup script (Recommended)

```bash
# Create and set up a virtual environment automatically
python setup_venv.py

# Activate the environment
# On Windows
myenv\Scripts\activate
# On macOS/Linux
source myenv/bin/activate
```

#### Option 2: Manual setup

```bash
# Create the environment
python -m venv myenv

# Activate the environment
# On Windows
myenv\Scripts\activate
# On macOS/Linux
source myenv/bin/activate
```

### 3. Install Dependencies

There are two ways to install the required dependencies:

#### Option 1: Using the installation script (Recommended)

```bash
# Make sure your virtual environment is activated
python install_requirements.py
```

This script will:
- Install all required packages
- Handle special cases like TA-Lib installation
- Set up necessary directories
- Provide detailed error messages if something goes wrong

#### Option 2: Using requirements.txt

```bash
pip install -r requirements.txt
```

Note: This method may require additional manual steps for packages like TA-Lib.

#### Verifying the Installation

After installing dependencies, run the compatibility checker:

```bash
python check_compatibility.py
```

This will verify that all required packages are properly installed and functioning.

### 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

- Set exchange API keys (required even for paper trading)
- Configure database settings
- **Important**: Ensure `PAPER_TRADING=true` is set

### 5. Initialize the Database

```bash
python -c "from src.utils.database import init_db; init_db()"
```

## Running in Paper Trading Mode

### Basic Paper Trading

To start paper trading with default settings:

```bash
python paper_trading.py
```

### Advanced Options

The paper trading script supports several options:

```bash
python paper_trading.py --exchange binance --symbol BTC/USDT --all
```

Available options:
- `--exchange`: Specify which exchange to use (default: binance)
- `--symbol`: Trading pair to use (default: BTC/USDT)
- `--low-risk`: Run the low-risk strategy
- `--medium-risk`: Run the medium-risk strategy
- `--high-risk`: Run the high-risk strategy
- `--all`: Run all strategies (default if no strategy is specified)

## Monitoring Your Paper Trading

### Web Dashboard

The bot includes a web dashboard for monitoring performance:

1. Access the dashboard at `http://localhost:5000`
2. Login with credentials configured in your `.env` file
3. Monitor real-time performance, trades, and portfolio metrics

### Log Files

Monitor the log file for detailed information:

```bash
tail -f logs/crypto_bot.log
```

## Strategy Explanation

The bot includes three trading strategies with different risk profiles:

### Low-Risk Strategy

- Enhanced grid trading/market making
- Places buy and sell orders at regular intervals around the current price
- Profits from price oscillations within a range
- Least aggressive, most conservative approach
- Target: 10-20% annual return

### Medium-Risk Strategy

- Trend-following using technical indicators
- Uses EMA crossovers, RSI, and ADX for trend confirmation
- More aggressive with moderate leverage (2x)
- Target: 30-70% annual return

### High-Risk Strategy

- AI-powered scalping strategy with machine learning predictions
- Incorporates on-chain data and sentiment analysis
- Uses higher leverage (5x) for amplified returns
- Most aggressive strategy with highest potential returns but also highest risk
- Target: 80-150%+ annual return

## Customizing Strategies

You can customize strategy parameters in the `.env` file:

```
# Risk parameters
LOW_RISK_STOP_LOSS=0.02
MEDIUM_RISK_STOP_LOSS=0.03
HIGH_RISK_STOP_LOSS=0.05

# Leverage
MEDIUM_RISK_LEVERAGE=2.0
HIGH_RISK_LEVERAGE=5.0
```

## Portfolio Management

The bot includes sophisticated portfolio management:

- Dynamic capital allocation based on strategy performance
- Global risk management with maximum drawdown limits
- Automatic profit withdrawal when reaching thresholds

## Backtesting

To validate strategy performance before paper trading:

```bash
python -m scripts.validate_strategy_performance --strategy low_risk --symbol BTC/USDT
```

## Troubleshooting

### Common Issues

1. **API Rate Limits**: Most exchanges impose rate limits. If you see rate limit errors, reduce the bot's activity or request frequency.

2. **Database Connection Issues**: Make sure PostgreSQL is running and your connection details are correct in the `.env` file.

3. **TensorFlow GPU Issues**: If you're using GPU for the high-risk strategy, make sure you have compatible CUDA and cuDNN versions installed.

### Compatibility Check

Run the compatibility checker script to verify your setup:

```bash
python check_compatibility.py
```

This will check your Python version, required packages, and system configuration.

## Advanced Usage

### Adding Custom Indicators

The modular design allows you to add custom indicators in `src/utils/` and incorporate them into strategies.

### Creating Custom Strategies

You can create your own strategy by:

1. Creating a new file in the `src/strategies/` directory
2. Inheriting from the `BaseStrategy` class
3. Implementing the required methods

See the existing strategies for examples.

## Moving to Live Trading

Once you're confident in your paper trading results:

1. Set `PAPER_TRADING=false` in your `.env` file
2. Ensure you have sufficient funds in your exchange account
3. Start with smaller position sizes than you used in paper trading
4. Gradually increase as you gain confidence

**IMPORTANT**: Live trading involves real financial risk. Start with small amounts and never invest more than you can afford to lose.

## Additional Resources

- Review `README.md` for general bot information
- See `DEPLOYMENT_GUIDE.md` for AWS cloud deployment instructions
- Examine `STEP_BY_STEP_GUIDE.md` for a complete walkthrough

## Safety Precautions

Always remember:
- Paper trading performance does not guarantee live trading results
- Market conditions change rapidly
- The bot includes risk management features but cannot eliminate all risks
- Always monitor the bot's activity, especially when first moving to live trading
