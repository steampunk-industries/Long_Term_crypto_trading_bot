# Crypto Trading Dashboard Access Guide

## Accessing the Dashboard with HTTPS

The dashboard is now running securely with HTTPS. To access it:

1. Open your browser and navigate to:
   ```
   https://localhost:5003/
   ```

2. Since we're using self-signed certificates, your browser will likely show a security warning.
   - In Chrome: Click "Advanced" and then "Proceed to localhost (unsafe)"
   - In Firefox: Click "Advanced", then "Accept the Risk and Continue"
   - In Safari: Click "Show Details" and then "visit this website"

3. Log in with your credentials on the login page

## Viewing Multi-Currency Trading Interface

After logging in, you can access the multi-currency trading features:

1. From the dashboard home page, click on the "Multi-Currency" link in the navigation menu
2. The multi-currency page shows:
   - Trading opportunities ranked by confidence score
   - Current portfolio allocation across multiple currencies
   - Performance metrics for multi-currency strategies

## Troubleshooting

If you encounter issues accessing the dashboard:

1. Verify the dashboard service is running:
   ```bash
   sudo systemctl status crypto-dashboard.service
   ```

2. Check for errors in the logs:
   ```bash
   sudo journalctl -u crypto-dashboard.service -n 50
   ```
   
3. Ensure your browser is allowing self-signed certificates:
   - Try using Chrome with the `--ignore-certificate-errors` flag
   - Or use `curl -k https://localhost:5003/` to test the connection

4. If you need to restart the service:
   ```bash
   sudo systemctl restart crypto-dashboard.service
   ```

## Note on Certificate Security

The current implementation uses self-signed certificates, which are appropriate for development but not for production. For production deployment, consider:

1. Obtaining properly signed certificates from a Certificate Authority like Let's Encrypt
2. Setting up a reverse proxy like Nginx for SSL termination
3. Implementing proper certificate renewal processes
