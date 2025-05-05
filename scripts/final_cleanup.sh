#!/bin/bash
echo "🚨 Running final cleanup of unused and audit-flagged files..."

# Delete legacy simple_ scripts
rm -f simple_dashboard_server.py simple_mock_trading.py simple_trading_dashboard.py

# Delete empty or placeholder test stub
rm -f tests/__init__.py
rm -f tests/test_gunicorn_setup.sh

# Delete flagged unused modules (manually verified first!)
rm -f src/utils/market_regime_detection.py
rm -f src/utils/dashboard_simplified.py
rm -f src/strategies/adaptive_mean_reversion.py

echo "✅ Cleanup complete. You’re running lean."