# Multi-Currency Trading Bot

This extension to the original trading bot provides support for scanning and trading multiple cryptocurrencies simultaneously, based on the highest confidence trading signals.

## Features

- **Multi-Currency Support**: Dynamically scans and evaluates multiple trading pairs
- **Top Symbol Selection**: Fetches top trading pairs by volume from exchanges
- **Signal Ranking**: Ranks trading opportunities by signal confidence
- **Portfolio Management**: Limits the number of concurrent positions
- **Exchange Compatibility**: Works with KuCoin, Coinbase, Gemini, and Kraken
- **Paper Trading**: Test the strategy without risking real funds

## Implementation Details

The multi-currency trading bot consists of the following components:

1. **Exchange API Extensions**: Added `get_top_symbols()` method to all exchange classes
2. **Symbol Ranker**: New utility class to evaluate and rank trading pairs
3. **Multi-Currency Bot**: Core implementation that finds and executes the best opportunities
4. **Command-Line Runner**: Easy-to-use script to run the bot with various configuration options

## Usage

You can run the multi-currency trading bot with the provided runner script:

```bash
./run_multi_currency_bot.py --exchange kucoin --paper --max-positions 3
```

### Command-Line Options

- `--exchange`: Trading exchange to use (kucoin, coinbase, gemini, kraken)
- `--strategy`: Strategy to use for signal generation (default: rsi_strategy)
- `--paper`: Enable paper trading mode (simulated trading)
- `--dry-run`: Analyze opportunities but don't execute trades
- `--max-positions`: Maximum number of concurrent trading positions (default: 3)
- `--quote-currency`: Quote currency for trading pairs (default: USDT)
- `--min-confidence`: Minimum confidence threshold for trade execution (default: 0.4)
- `--once`: Run the bot once and exit
- `--interval`: Interval between trading cycles in minutes (default: 60)
- `--timeframe`: Timeframe for analysis (default: 1h)
- `--risk-level`: Risk level for trading (low, medium, high)

### Environment Variables

You can also configure the bot using environment variables:

```bash
# Set in .env file or export directly
export TRADING_EXCHANGE=kucoin
export PAPER_TRADING=true
export MAX_POSITIONS=3
export QUOTE_CURRENCY=USDT
export MIN_CONFIDENCE_THRESHOLD=0.4
export INTERVAL_MINUTES=60
export TIMEFRAME=1h
export RISK_LEVEL=medium
```

## How It Works

1. The bot fetches the top trading pairs by volume from the specified exchange
2. Each symbol is evaluated using the configured strategy (e.g., RSI)
3. Signals are ranked by confidence score
4. The highest confidence signals that meet the minimum threshold are executed
5. The bot tracks active positions and only opens new ones when slots are available
6. Portfolio snapshots are recorded to track performance

## Example Workflow

```
1. Bot starts and connects to KuCoin exchange
2. Fetches top 10 trading pairs by volume (BTC/USDT, ETH/USDT, SOL/USDT, etc.)
3. Evaluates each pair using RSI strategy
4. Finds strong buy signal for ETH/USDT with 0.75 confidence
5. Executes buy order for ETH/USDT
6. Continues monitoring all pairs at specified interval
7. Updates portfolio snapshot for performance tracking
```

## Extending the Bot

### Adding New Strategies

You can implement new strategies and use them with the multi-currency bot:

1. Create a new strategy class in `src/strategies/`
2. Register it in `StrategyFactory`
3. Run the bot with `--strategy your_new_strategy`

### ML Integration (Future)

The architecture is designed to accommodate machine learning enhancements:

1. Store historical signals and outcomes in the database
2. Train ML models to predict signal success likelihood
3. Integrate ML predictions into confidence scoring
4. Implement adaptive position sizing based on prediction strength

## Troubleshooting

- **No Trading Pairs Found**: Check if the exchange supports the specified quote currency
- **No Signals Generated**: Try lowering the minimum confidence threshold
- **Database Errors**: Ensure the database is properly initialized with `init_db()`
- **API Rate Limits**: Increase the interval between runs to avoid hitting rate limits
