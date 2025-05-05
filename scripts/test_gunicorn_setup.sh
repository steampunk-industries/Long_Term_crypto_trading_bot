#!/bin/bash

# Script to test Gunicorn setup without affecting the running service
# ===================================================================

echo "===== Testing Gunicorn Configuration ====="
echo "$(date)"

# Ensure we're in the correct directory
cd /home/ubuntu/Long_Term_crypto_trading_bot

# Check if virtual environment exists
if [ ! -d "crypto_venv" ]; then
    echo "ERROR: Virtual environment not found at crypto_venv"
    echo "Please run deploy_production_dashboard.sh first to set up the environment"
    exit 1
fi

# Check if WSGI file exists
if [ ! -f "wsgi.py" ]; then
    echo "ERROR: WSGI file not found at wsgi.py"
    exit 1
fi

# Check if the WSGI file is executable
if [ ! -x "wsgi.py" ]; then
    echo "Making WSGI file executable..."
    chmod +x wsgi.py
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if Gunicorn is installed
if ! crypto_venv/bin/pip list | grep -q gunicorn; then
    echo "Installing Gunicorn..."
    crypto_venv/bin/pip install gunicorn
fi

echo
echo "Running Gunicorn on a test port (5004)..."
echo "This will not affect the production service on port 5003"
echo

# Test with Gunicorn on a different port with timeout to prevent hanging
echo "Starting Gunicorn test server with 30 second timeout..."
timeout 30s crypto_venv/bin/gunicorn --bind 0.0.0.0:5004 --workers 1 --timeout 30 wsgi:app > logs/test_gunicorn.log 2>&1 &
GUNICORN_PID=$!

echo "Gunicorn started with PID: $GUNICORN_PID"
echo "Waiting for Gunicorn to initialize..."
sleep 3

# Check if Gunicorn is running
if ! ps -p $GUNICORN_PID > /dev/null; then
    echo "ERROR: Gunicorn failed to start"
    echo "Check logs/test_gunicorn.log for details"
    exit 1
fi

echo "Gunicorn is running successfully"

# Test multiple endpoints
echo
echo "Testing multiple endpoints..."
endpoints=("/health" "/login" "/")
for endpoint in "${endpoints[@]}"; do
    echo -n "Testing $endpoint... "
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5004$endpoint)
    
    if [[ "$STATUS_CODE" =~ ^(200|302) ]]; then
        echo "✅ Success (HTTP $STATUS_CODE)"
    else
        echo "❌ Failed (HTTP $STATUS_CODE)"
    fi
done

# Display full response for health endpoint
echo
echo "Health endpoint full response:"
curl -s http://localhost:5004/health

# Cleanup
echo
echo "Stopping test Gunicorn server..."
kill $GUNICORN_PID
wait $GUNICORN_PID 2>/dev/null || true

echo
echo "===== Test Complete ====="
echo "If the test was successful, you can apply the changes to production with:"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl restart crypto-dashboard.service"
echo "sudo systemctl status crypto-dashboard.service"
