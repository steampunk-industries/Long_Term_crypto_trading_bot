#!/bin/bash
#
# Deployment script for Crypto Trading Bot microservices
# This script handles setup, building, and deployment of the microservices architecture
#

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to ask for confirmation
confirm() {
    read -r -p "$1 [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Default values for configuration
RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
DOCKER_REGISTRY=""
DEPLOY_ENV="development"
BUILD_DOCKER=true
PUSH_DOCKER=false
DEPLOY_LOCAL=true
DEPLOY_REMOTE=false

# Function to show help message
show_help() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -r, --rabbitmq-url URL    Set RabbitMQ URL (default: $RABBITMQ_URL)"
    echo "  -e, --env ENV             Set deployment environment (development, staging, production)"
    echo "  --docker-registry URL     Set Docker registry URL (for remote deployment)"
    echo "  --no-build                Skip Docker image building"
    echo "  --push                    Push Docker images to registry"
    echo "  --no-local                Skip local deployment"
    echo "  --remote                  Deploy to remote servers (requires additional configuration)"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--rabbitmq-url)
            RABBITMQ_URL="$2"
            shift
            shift
            ;;
        -e|--env)
            DEPLOY_ENV="$2"
            shift
            shift
            ;;
        --docker-registry)
            DOCKER_REGISTRY="$2"
            shift
            shift
            ;;
        --no-build)
            BUILD_DOCKER=false
            shift
            ;;
        --push)
            PUSH_DOCKER=true
            shift
            ;;
        --no-local)
            DEPLOY_LOCAL=false
            shift
            ;;
        --remote)
            DEPLOY_REMOTE=true
            shift
            ;;
        *)
            print_error "Unknown option: $key"
            show_help
            exit 1
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed. Please install Docker to continue."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose to continue."
    exit 1
fi

# Main deployment process
print_header "Crypto Trading Bot Microservices Deployment"
echo "Deployment environment: $DEPLOY_ENV"
echo "RabbitMQ URL: $RABBITMQ_URL"
if [ -n "$DOCKER_REGISTRY" ]; then
    echo "Docker registry: $DOCKER_REGISTRY"
fi

# Preparation
print_header "Preparing Deployment"

# Check for existing .env file
if [ -f .env ]; then
    print_warning "Found existing .env file. Using it for deployment."
else
    print_warning "No .env file found. Creating from .env.example..."
    cp .env.example .env
    print_success "Created .env file from template. Please review and update as needed."
fi

# Create necessary directories
mkdir -p data/mongodb data/postgres data/rabbitmq

# Check and update environment variables based on deployment environment
if [ "$DEPLOY_ENV" == "production" ]; then
    print_warning "Production deployment detected. Updating security settings..."
    
    # Generate secure passwords for production
    if grep -q "DEFAULT_PASSWORD=password" .env; then
        RANDOM_PASSWORD=$(openssl rand -hex 12)
        sed -i.bak "s/DEFAULT_PASSWORD=password/DEFAULT_PASSWORD=$RANDOM_PASSWORD/" .env
        print_success "Generated secure random password for services"
    fi
fi

# Build Docker images
if [ "$BUILD_DOCKER" = true ]; then
    print_header "Building Docker Images"
    
    # Build base image
    echo "Building base image..."
    docker build -t crypto_trading_base -f Dockerfile.microservices .
    print_success "Built base Docker image"
    
    # Build service images
    echo "Building service images..."
    
    # API Gateway
    docker build -t crypto_trading_api_gateway \
        --build-arg BASE_IMAGE=crypto_trading_base \
        --build-arg SERVICE_MODULE=microservices.api_gateway \
        -f Dockerfile.microservices .
    print_success "Built API Gateway image"
    
    # Market Data Service
    docker build -t crypto_trading_market_data \
        --build-arg BASE_IMAGE=crypto_trading_base \
        --build-arg SERVICE_MODULE=microservices.market_data_service \
        -f Dockerfile.microservices .
    print_success "Built Market Data Service image"
    
    # Trading Services
    for strategy in low_risk medium_risk high_risk; do
        docker build -t crypto_trading_${strategy} \
            --build-arg BASE_IMAGE=crypto_trading_base \
            --build-arg SERVICE_MODULE=microservices.trading_service \
            --build-arg SERVICE_ARGS="--strategy ${strategy}" \
            -f Dockerfile.microservices .
        print_success "Built Trading Service (${strategy}) image"
    done
fi

# Push Docker images to registry
if [ "$PUSH_DOCKER" = true ] && [ -n "$DOCKER_REGISTRY" ]; then
    print_header "Pushing Docker Images to Registry"
    
    # Tag and push images
    services=("api_gateway" "market_data" "low_risk" "medium_risk" "high_risk")
    
    for service in "${services[@]}"; do
        echo "Pushing crypto_trading_${service} to registry..."
        docker tag crypto_trading_${service} ${DOCKER_REGISTRY}/crypto_trading_${service}:latest
        docker push ${DOCKER_REGISTRY}/crypto_trading_${service}:latest
        print_success "Pushed ${service} image to registry"
    done
fi

# Local deployment
if [ "$DEPLOY_LOCAL" = true ]; then
    print_header "Deploying Locally"
    
    # Check if services are already running
    if docker ps | grep -q crypto_trading; then
        if confirm "Crypto Trading Bot services are already running. Do you want to stop and restart them?"; then
            echo "Stopping existing services..."
            docker-compose -f docker-compose-microservices.yml down
            print_success "Stopped existing services"
        else
            print_warning "Deployment aborted. Existing services will continue running."
            exit 0
        fi
    fi
    
    # Start services
    echo "Starting microservices..."
    RABBITMQ_URL=$RABBITMQ_URL docker-compose -f docker-compose-microservices.yml up -d
    print_success "Started microservices"
    
    # Wait for services to be ready
    echo "Waiting for services to start..."
    sleep 10
    
    # Check service health
    echo "Checking service health..."
    if curl -sSf http://localhost:8000/health >/dev/null 2>&1; then
        print_success "API Gateway is healthy"
    else
        print_warning "API Gateway may not be fully initialized yet. Check logs for details."
    fi
    
    # Show endpoints
    print_header "Deployment Complete"
    echo "API Endpoints:"
    echo "  API Gateway:   http://localhost:8000"
    echo "  Dashboard:     http://localhost:5000"
    echo "  Prometheus:    http://localhost:9090"
    echo "  Grafana:       http://localhost:3000"
    echo "  RabbitMQ:      http://localhost:15672"
    
    echo
    echo "To view logs for a specific service:"
    echo "  docker-compose -f docker-compose-microservices.yml logs -f [service_name]"
    echo
    echo "Available services:"
    echo "  api_gateway, trading_low_risk, trading_medium_risk,"
    echo "  trading_high_risk, market_data_service, rabbitmq, postgres,"
    echo "  prometheus, grafana"
fi

# Remote deployment
if [ "$DEPLOY_REMOTE" = true ]; then
    print_header "Remote Deployment"
    
    if [ -z "$DOCKER_REGISTRY" ]; then
        print_error "Docker registry URL is required for remote deployment"
        echo "Please specify a Docker registry using --docker-registry URL"
        exit 1
    fi
    
    if [ ! -f "remote-deployment.conf" ]; then
        print_error "Remote deployment configuration file 'remote-deployment.conf' not found"
        echo "Please create this file with the necessary SSH connection details"
        exit 1
    fi
    
    # Load remote deployment configuration
    source remote-deployment.conf
    
    if [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_USER" ]; then
        print_error "Remote host or user not specified in remote-deployment.conf"
        exit 1
    fi
    
    echo "Deploying to remote server: $REMOTE_USER@$REMOTE_HOST"
    
    # Copy docker-compose file
    echo "Copying configuration files..."
    scp docker-compose-microservices.yml $REMOTE_USER@$REMOTE_HOST:~/crypto_trading/
    scp .env $REMOTE_USER@$REMOTE_HOST:~/crypto_trading/
    
    # Create remote deployment script
    TMP_DEPLOY_SCRIPT=$(mktemp)
    cat > $TMP_DEPLOY_SCRIPT << EOF
#!/bin/bash
set -e

cd ~/crypto_trading

# Update docker-compose file to use registry images
sed -i 's|image: crypto_trading_|image: ${DOCKER_REGISTRY}/crypto_trading_|g' docker-compose-microservices.yml

# Pull latest images
docker-compose -f docker-compose-microservices.yml pull

# Restart services
docker-compose -f docker-compose-microservices.yml down || true
RABBITMQ_URL="${RABBITMQ_URL}" docker-compose -f docker-compose-microservices.yml up -d

echo "Deployment completed successfully"
EOF
    
    # Copy and execute remote deployment script
    scp $TMP_DEPLOY_SCRIPT $REMOTE_USER@$REMOTE_HOST:~/crypto_trading/deploy.sh
    ssh $REMOTE_USER@$REMOTE_HOST "chmod +x ~/crypto_trading/deploy.sh && ~/crypto_trading/deploy.sh"
    
    # Clean up
    rm $TMP_DEPLOY_SCRIPT
    
    print_success "Remote deployment completed successfully"
    echo "Remote endpoints:"
    echo "  API Gateway:   http://$REMOTE_HOST:8000"
    echo "  Dashboard:     http://$REMOTE_HOST:5000"
    echo "  Prometheus:    http://$REMOTE_HOST:9090"
    echo "  Grafana:       http://$REMOTE_HOST:3000"
    echo "  RabbitMQ:      http://$REMOTE_HOST:15672"
fi

print_header "Next Steps"
echo "1. Update your .env file with your exchange API keys and other settings"
echo "2. Access the dashboard at http://localhost:5000 to monitor your trading"
echo "3. Use the API Gateway at http://localhost:8000 to control your trading"
echo "4. Check Grafana dashboards at http://localhost:3000 for detailed metrics"
echo
echo "For more information, refer to the documentation:"
echo "  https://github.com/your-username/crypto_trading_bot#readme"
