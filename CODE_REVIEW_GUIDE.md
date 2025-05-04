# Crypto Trading Bot Code Review Guide

This guide documents the standards, best practices, and common issues to check during code reviews for this crypto trading bot project.

## Recent Improvements

The following improvements have been made to ensure API consistency, enhance risk management, and improve system stability:

1. **Exchange API Consistency**
   - Added `place_order` method to GeminiExchange as an alias for `create_order` to maintain consistent API
   - Fixed `cancel_order` method in KrakenExchange to properly handle paper trading mode
   - Ensured all exchange implementations follow the same interface pattern

2. **Risk Management Improvements**
   - Added stop-loss and take-profit calculations to trading strategies
   - Implemented risk-based position sizing (max 2% risk per trade)
   - Added trend strength calculation for dynamic position sizing

3. **Service Monitoring Integration**
   - Added service monitoring to critical external API calls
   - Implemented proper error handling and reporting for Steampunk Holdings integration
   - Added service recovery reporting for successful API calls

4. **Dashboard & Deployment**
   - Updated system service files for proper dashboard deployment
   - Fixed dashboard server to use the full database-backed implementation
   - Updated Nginx configuration for proper proxying and static file handling
   - Added database initialization script with sample data

## Code Review Checklist

### Exchange Implementations

- [ ] Ensure all exchange classes implement the base interface methods
- [ ] Verify paper trading mode works correctly
- [ ] Check proper error handling and logging
- [ ] Verify proper handling of exchange-specific symbol formats

### Trading Strategies

- [ ] Ensure strategies include stop-loss and take-profit calculations
- [ ] Verify risk-based position sizing is implemented
- [ ] Check for proper signal confidence calculation
- [ ] Ensure strategies have a `run()` method for standalone execution

### External Integrations

- [ ] Verify service monitoring is implemented for API calls
- [ ] Check for proper error handling and retry logic
- [ ] Ensure failed operations are stored locally for later retry
- [ ] Verify authentication is properly implemented

### Database Models

- [ ] Ensure models have proper relationships
- [ ] Check for appropriate indexes on commonly queried fields
- [ ] Verify models include helper methods for common operations
- [ ] Ensure proper type annotations and validation

### Web Dashboard

- [ ] Check for proper authentication and authorization
- [ ] Verify API endpoints return appropriate data
- [ ] Ensure templates are properly rendered
- [ ] Check for responsive design for mobile compatibility

## Common Issues to Watch For

1. **API Inconsistency**: Different exchange implementations should follow the same interface pattern.
2. **Inadequate Error Handling**: External API calls should include proper error handling, logging, and recovery mechanisms.
3. **Risk Management**: Trading strategies must include stop-loss, take-profit, and position sizing calculations.
4. **Service Dependencies**: Ensure proper handling of service dependencies with fallbacks for failures.

## Testing Requirements

New code should include appropriate tests for:

1. Exchange API functionality (unit tests with API call mocking)
2. Trading strategy signal generation and execution
3. Integration points between components
4. Error handling scenarios

## Deployment Process

Deployment of the system follows these steps:

1. Run the database initialization script: `python scripts/init_database.py`
2. Install the dashboard service: `sudo ./install_dashboard_service.sh`
3. Configure Nginx: `sudo cp nginx/dashboard.conf /etc/nginx/sites-available/dashboard && sudo ln -sf /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/`
4. Restart Nginx: `sudo systemctl restart nginx`

For SSL setup:
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d steampunk.holdings
```

## Contributing Guidelines

1. Follow the existing code style and naming conventions
2. Ensure compatibility with the existing architecture
3. Document all public methods and classes
4. Add appropriate logging for error conditions and important events
5. Implement proper error handling for external dependencies
6. Ensure all exchange-specific implementations follow the same interface pattern
7. Include appropriate tests for new functionality
