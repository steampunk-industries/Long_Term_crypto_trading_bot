#!/bin/bash

# Run Paper Trading with Public APIs
# This script sets up and runs the crypto trading bot in paper trading mode

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting Crypto Trading Bot Paper Trading Setup ===${NC}"

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo "Creating logs directory..."
    mkdir -p logs
fi

# Make sure scripts are executable
echo "Setting up executable permissions..."
chmod +x make_executable.sh
./make_executable.sh

# Initialize database
echo -e "${YELLOW}Initializing database and generating test data...${NC}"
python3 paper_trading_test_runner.py

# Restart the dashboard service
echo -e "${YELLOW}Restarting dashboard service...${NC}"
sudo systemctl restart crypto-dashboard.service

# Check if dashboard service started properly
sleep 3
if systemctl is-active --quiet crypto-dashboard.service; then
    echo -e "${GREEN}Dashboard service successfully started!${NC}"
else
    echo -e "${RED}Dashboard service failed to start. Check logs with: sudo journalctl -u crypto-dashboard.service${NC}"
fi

# Create a simple test to verify exchange connectivity
echo -e "${YELLOW}Testing exchange connectivity...${NC}"
cat > test_exchange_connection.py << 'EOL'
#!/usr/bin/env python3
"""
Simple test script to verify exchange connectivity and get market data
"""
import os
import sys
from datetime import datetime

# Set paper trading mode
os.environ["PAPER_TRADING"] = "true"
os.environ["USE_MULTI_EXCHANGE"] = "true"
os.environ["TRADING_EXCHANGE"] = "multi"

# Add project directory to path
sys.path.append(os.getcwd())

from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory

def test_exchanges():
    print("\n" + "=" * 50)
    print(" EXCHANGE CONNECTION TEST ".center(50, "="))
    print("=" * 50 + "\n")
    
    exchanges = ["binance", "coinbase", "gemini", "kucoin", "kraken", "multi"]
    results = {}
    
    for name in exchanges:
        print(f"Testing {name}...")
        exchange = ExchangeFactory.create_exchange_from_config(name)
        
        if not exchange:
            print(f"  ❌ Failed to create {name} exchange")
            continue
            
        # Test connection
        if exchange.connect():
            print(f"  ✅ Connected to {name}")
            
            # Get ticker
            try:
                ticker = exchange.get_ticker("BTC/USDT")
                price = ticker.get('last', 0)
                
                if price > 0:
                    print(f"  ✅ BTC Price: ${price:,.2f}")
                    results[name] = price
                else:
                    print(f"  ❌ Invalid price data")
            except Exception as e:
                print(f"  ❌ Error getting ticker: {e}")
        else:
            print(f"  ❌ Connection failed")
    
    # Print summary
    print("\n" + "=" * 50)
    print(" RESULTS SUMMARY ".center(50, "="))
    print("=" * 50)
    
    if results:
        for name, price in results.items():
            print(f"{name}: ${price:,.2f}")
    else:
        print("No successful connections to exchanges")
    
    return results

if __name__ == "__main__":
    # Run tests
    test_exchanges()
EOL

# Make the test script executable
chmod +x test_exchange_connection.py

# Run the exchange test
echo -e "${YELLOW}Running exchange connection test...${NC}"
python3 test_exchange_connection.py

# Attempt to start the trading bot in paper trading mode
echo -e "${YELLOW}Starting trading bot in paper trading mode...${NC}"
nohup python3 run_bot.py --bot-only --interval 5 &> logs/trading_bot.log &
BOT_PID=$!
echo -e "${GREEN}Trading bot started with PID: ${BOT_PID}${NC}"
echo $BOT_PID > .bot_pid

# Display access information
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo -e "${YELLOW}Access your trading dashboard at:${NC}"
echo -e "${BLUE}http://localhost${NC} or ${BLUE}http://steampunk.holdings${NC} (if properly configured)"
echo ""
echo -e "${YELLOW}Default Login:${NC}"
echo -e "Username: ${BLUE}admin${NC}"
echo -e "Password: ${BLUE}password${NC}"
echo ""
echo -e "${YELLOW}Notes:${NC}"
echo "- The system is running in paper trading mode with mock data"
echo "- Public APIs are being used for market data"
echo "- The trading bot is running in the background in paper trading mode"
echo "- You can update user settings and change password in the Settings tab"
echo "- To manually restart the dashboard: sudo systemctl restart crypto-dashboard.service"
echo "- To check the trading bot status: ps -p $(cat .bot_pid)"
echo "- To stop the trading bot: kill $(cat .bot_pid)"
