#!/bin/bash
# Consolidated Dashboard Runner Script
# This script replaces multiple dashboard scripts with a single parameterized script

function usage {
  echo "Usage: $0 [command] [options]"
  echo "Commands:"
  echo "  start       - Start the dashboard server"
  echo "  install     - Install dashboard as a service"
  echo "  deploy      - Deploy the dashboard to production"
  echo "  paper       - Start paper trading with dashboard"
  echo "Options:"
  echo "  --port PORT - Specify port (default: 5000)"
  echo "  --prod      - Use production settings"
  echo "  --help      - Show this help message"
  exit 1
}

# Default values
PORT=5000
ENV="development"

# Parse command
if [ $# -eq 0 ]; then
  usage
fi

COMMAND=$1
shift

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT=$2
      shift 2
      ;;
    --prod)
      ENV="production"
      shift
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

case "$COMMAND" in
  start)
    echo "Starting dashboard server on port $PORT ($ENV mode)..."
    if [ "$ENV" == "production" ]; then
      python production_dashboard.py --port $PORT
    else
      python dashboard_server.py --port $PORT
    fi
    ;;
  install)
    echo "Installing dashboard as a service..."
    sudo ./install_dashboard_service.sh
    ;;
  deploy)
    echo "Deploying dashboard to production..."
    ./deploy_production_dashboard.sh
    ;;
  paper)
    echo "Starting paper trading with dashboard..."
    ./run_paper_trading.sh
    ;;
  *)
    echo "Unknown command: $COMMAND"
    usage
    ;;
esac
