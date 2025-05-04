"""
API Gateway microservice for the crypto trading bot.
Provides RESTful API endpoints for interacting with the system.
"""

import os
import json
import time
import logging
import threading
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import jwt
from jwt.exceptions import InvalidTokenError
import hashlib
import secrets

from microservices.base_service import BaseService, HealthCheck


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api_gateway")

# Create FastAPI app
app = FastAPI(
    title="Crypto Trading Bot API",
    description="API for interacting with the crypto trading bot",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key security scheme
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60


# ----- Models -----

class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Health status")
    timestamp: float = Field(..., description="Timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, Any] = Field(..., description="Service statuses")


class LoginRequest(BaseModel):
    """Login request model."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response model."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")
    expires_at: float = Field(..., description="Token expiration timestamp")
    user_id: str = Field(..., description="User ID")


class ApiKeyResponse(BaseModel):
    """API key response model."""
    
    api_key: str = Field(..., description="API key")
    name: str = Field(..., description="API key name")
    created_at: float = Field(..., description="Creation timestamp")
    expires_at: Optional[float] = Field(None, description="Expiration timestamp")


class ApiKeyRequest(BaseModel):
    """API key request model."""
    
    name: str = Field(..., description="API key name")
    expires_in_days: Optional[int] = Field(None, description="Days until expiration")


class TradingCommandRequest(BaseModel):
    """Trading command request model."""
    
    strategy: str = Field(..., description="Strategy type (low_risk, medium_risk, high_risk)")
    command: str = Field(..., description="Command (start, stop, status, reset)")


class StrategyParametersRequest(BaseModel):
    """Strategy parameters request model."""
    
    strategy: str = Field(..., description="Strategy type (low_risk, medium_risk, high_risk)")
    parameters: Dict[str, Any] = Field(..., description="Strategy parameters")


class SymbolRequest(BaseModel):
    """Symbol request model."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., BTC/USDT)")


# ----- Helper functions and dependencies -----

# Mock user database (in-memory for simplicity)
USERS = {
    "admin": {
        "user_id": "user_1",
        "username": "admin",
        "hashed_password": hashlib.sha256("admin_password".encode()).hexdigest(),
        "is_active": True,
        "is_admin": True,
    }
}

# Mock API key database (in-memory for simplicity)
API_KEYS = {
    # Format: "api_key": {"user_id": "user_id", "name": "key_name", "created_at": timestamp, "expires_at": timestamp}
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get a user from the database."""
    return USERS.get(username)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user["is_active"]:
        return None
    return user


def create_jwt_token(user_id: str) -> str:
    """Create a JWT token."""
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode = {
        "sub": user_id,
        "exp": expiration,
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_api_key(user_id: str, name: str, expires_in_days: Optional[int] = None) -> str:
    """Create a new API key."""
    api_key = secrets.token_hex(32)
    created_at = time.time()
    expires_at = None
    if expires_in_days:
        expires_at = created_at + (expires_in_days * 24 * 60 * 60)
    
    API_KEYS[api_key] = {
        "user_id": user_id,
        "name": name,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    
    return api_key


async def get_current_user_from_api_key(api_key: str = Depends(api_key_header)) -> Dict[str, Any]:
    """Get the current user from an API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    api_key_data = API_KEYS.get(api_key)
    if not api_key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if the API key has expired
    if api_key_data["expires_at"] and api_key_data["expires_at"] < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    user_id = api_key_data["user_id"]
    user = None
    for u in USERS.values():
        if u["user_id"] == user_id:
            user = u
            break
    
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or not found",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return user


# ----- API Gateway Service -----

class ApiGatewayService(BaseService):
    """API Gateway Service for handling API requests."""

    def __init__(
        self,
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        api_port: int = 8000,
        enable_swagger: bool = True,
    ):
        """
        Initialize the API gateway service.
        
        Args:
            rabbitmq_url: The URL of the RabbitMQ server.
            api_port: The port to run the API on.
            enable_swagger: Whether to enable Swagger UI.
        """
        super().__init__(
            service_name="api_gateway",
            rabbitmq_url=rabbitmq_url,
            exchange_name="crypto_trading",
            exchange_type="topic",
            queue_name="api_gateway_queue",
        )
        
        self.api_port = api_port
        self.enable_swagger = enable_swagger
        
        # Store pending RPC requests
        self.pending_requests = {}
        
        # WebSocket connections
        self.active_websockets = {}
        
        # Health check
        self.health_check = HealthCheck(self)
        
        # Set API instance
        self.app = app

    def run(self):
        """Run the API gateway service."""
        # Subscribe to response topics
        self.subscribe("trading.status.*", self._handle_status_update)
        self.subscribe("market.data.*", self._handle_market_data)
        
        # Start API server
        self.api_thread = threading.Thread(target=self._start_api_server)
        self.api_thread.daemon = True
        self.api_thread.start()
        
        # Start websocket broadcast thread
        self.websocket_thread = threading.Thread(target=self._websocket_broadcast_loop)
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        
        self.logger.info(f"API Gateway service started on port {self.api_port}")

    def _start_api_server(self):
        """Start the FastAPI server."""
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=self.api_port,
            log_level="info",
        )

    def _handle_status_update(self, topic: str, message: Dict[str, Any], properties):
        """
        Handle status update messages.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Extract strategy type from topic
        strategy_type = topic.split(".")[-1]
        
        # Forward status update to websocket clients
        self._broadcast_to_websockets("status_update", {
            "strategy": strategy_type,
            "status": message,
        })
        
        # If this is a response to an RPC call, forward it to the pending request
        if properties.correlation_id and properties.correlation_id in self.pending_requests:
            request_id = properties.correlation_id
            request_data = self.pending_requests[request_id]
            
            # Pass the message to the response object
            request_data["response"] = message
            request_data["completed"] = True
            
            self.logger.debug(f"Received response for request {request_id}")

    def _handle_market_data(self, topic: str, message: Dict[str, Any], properties):
        """
        Handle market data messages.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Extract data type from topic
        data_type = topic.split(".")[-1]
        
        # Forward market data to websocket clients
        self._broadcast_to_websockets("market_data", {
            "type": data_type,
            "data": message,
        })

    def _websocket_broadcast_loop(self):
        """Thread for broadcasting updates to WebSocket clients."""
        while not self.should_stop:
            try:
                # Sleep briefly
                time.sleep(0.1)
                
                # Check and clean up expired pending requests
                current_time = time.time()
                expired_requests = []
                
                for request_id, request_data in self.pending_requests.items():
                    if current_time - request_data["timestamp"] > 30.0:  # 30 seconds timeout
                        expired_requests.append(request_id)
                
                for request_id in expired_requests:
                    if not self.pending_requests[request_id]["completed"]:
                        self.logger.warning(f"Request {request_id} timed out")
                    del self.pending_requests[request_id]
            except Exception as e:
                self.logger.error(f"Error in websocket broadcast loop: {e}")

    def _broadcast_to_websockets(self, event_type: str, data: Dict[str, Any]):
        """
        Broadcast a message to all connected WebSockets.
        
        Args:
            event_type: The type of event.
            data: The event data.
        """
        message = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        
        # Convert message to JSON
        json_message = json.dumps(message)
        
        # Send to all active websockets
        for ws_id, ws in list(self.active_websockets.items()):
            try:
                # Use _background to avoid blocking
                ws._background.send_text(json_message)
            except Exception as e:
                self.logger.error(f"Error sending to websocket {ws_id}: {e}")
                # Clean up failed connection
                self.active_websockets.pop(ws_id, None)

    def send_trading_command(self, strategy: str, command: str) -> Dict[str, Any]:
        """
        Send a trading command to a strategy.
        
        Args:
            strategy: The strategy type.
            command: The command.
            
        Returns:
            The command response.
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending request
        self.pending_requests[request_id] = {
            "timestamp": time.time(),
            "response": None,
            "completed": False,
        }
        
        # Send the command
        self.publish(
            f"trading.command.{command}",
            {
                "strategy": strategy,
                "timestamp": time.time(),
            },
            correlation_id=request_id,
            reply_to=self.queue_name,
        )
        
        # Wait for the response
        start_time = time.time()
        while time.time() - start_time < 5.0:  # 5 seconds timeout
            if self.pending_requests[request_id]["completed"]:
                response = self.pending_requests[request_id]["response"]
                del self.pending_requests[request_id]
                return response
            
            # Sleep briefly
            time.sleep(0.1)
        
        # Timeout
        del self.pending_requests[request_id]
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Command timed out",
        )

    def update_strategy_parameters(self, strategy: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update strategy parameters.
        
        Args:
            strategy: The strategy type.
            parameters: The parameters.
            
        Returns:
            The response.
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending request
        self.pending_requests[request_id] = {
            "timestamp": time.time(),
            "response": None,
            "completed": False,
        }
        
        # Send the command
        self.publish(
            f"trading.params.strategy_params",
            {
                "strategy": strategy,
                "params": parameters,
                "timestamp": time.time(),
            },
            correlation_id=request_id,
            reply_to=self.queue_name,
        )
        
        # Wait for the response
        start_time = time.time()
        while time.time() - start_time < 5.0:  # 5 seconds timeout
            if self.pending_requests[request_id]["completed"]:
                response = self.pending_requests[request_id]["response"]
                del self.pending_requests[request_id]
                return response
            
            # Sleep briefly
            time.sleep(0.1)
        
        # Timeout
        del self.pending_requests[request_id]
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Command timed out",
        )

    def add_trading_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Add a new trading symbol.
        
        Args:
            symbol: The symbol to add.
            
        Returns:
            The response.
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending request
        self.pending_requests[request_id] = {
            "timestamp": time.time(),
            "response": None,
            "completed": False,
        }
        
        # Send the command
        self.publish(
            f"market.command.add_symbol",
            {
                "symbol": symbol,
                "timestamp": time.time(),
            },
            correlation_id=request_id,
            reply_to=self.queue_name,
        )
        
        # Wait for the response
        start_time = time.time()
        while time.time() - start_time < 5.0:  # 5 seconds timeout
            if self.pending_requests[request_id]["completed"]:
                response = self.pending_requests[request_id]["response"]
                del self.pending_requests[request_id]
                return response
            
            # Sleep briefly
            time.sleep(0.1)
        
        # Timeout
        del self.pending_requests[request_id]
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Command timed out",
        )

    def remove_trading_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Remove a trading symbol.
        
        Args:
            symbol: The symbol to remove.
            
        Returns:
            The response.
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending request
        self.pending_requests[request_id] = {
            "timestamp": time.time(),
            "response": None,
            "completed": False,
        }
        
        # Send the command
        self.publish(
            f"market.command.remove_symbol",
            {
                "symbol": symbol,
                "timestamp": time.time(),
            },
            correlation_id=request_id,
            reply_to=self.queue_name,
        )
        
        # Wait for the response
        start_time = time.time()
        while time.time() - start_time < 5.0:  # 5 seconds timeout
            if self.pending_requests[request_id]["completed"]:
                response = self.pending_requests[request_id]["response"]
                del self.pending_requests[request_id]
                return response
            
            # Sleep briefly
            time.sleep(0.1)
        
        # Timeout
        del self.pending_requests[request_id]
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Command timed out",
        )

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of all services.
        
        Returns:
            The health status of all services.
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending request
        self.pending_requests[request_id] = {
            "timestamp": time.time(),
            "responses": {},
            "completed": False,
        }
        
        # Send health check request to all services
        self.publish(
            "health.check",
            {
                "timestamp": time.time(),
            },
            correlation_id=request_id,
            reply_to=self.queue_name,
        )
        
        # Wait for responses (with timeout)
        start_time = time.time()
        while time.time() - start_time < 3.0:  # 3 seconds timeout
            # Sleep briefly
            time.sleep(0.1)
        
        # Get collected responses
        responses = self.pending_requests[request_id].get("responses", {})
        del self.pending_requests[request_id]
        
        # Add our own health status
        responses["api_gateway"] = {
            "healthy": True,
            "timestamp": time.time(),
        }
        
        # Get health check of RabbitMQ connection
        rabbit_health = self.health_check.check()
        responses["rabbitmq"] = {
            "healthy": rabbit_health,
            "timestamp": time.time(),
        }
        
        return {
            "status": "ok" if all(s.get("healthy", False) for s in responses.values()) else "degraded",
            "timestamp": time.time(),
            "version": "1.0.0",
            "services": responses,
        }


# Create API Gateway service instance
service = None


# ----- API Routes -----

@app.on_event("startup")
async def startup_event():
    """Startup event to initialize the API Gateway service."""
    global service
    
    # Get configuration from environment variables
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    api_port = int(os.getenv("API_PORT", "8000"))
    enable_swagger = os.getenv("ENABLE_SWAGGER", "true").lower() == "true"
    
    # Create API Gateway service
    service = ApiGatewayService(
        rabbitmq_url=rabbitmq_url,
        api_port=api_port,
        enable_swagger=enable_swagger,
    )
    
    # Start service
    service_thread = threading.Thread(target=service.run)
    service_thread.daemon = True
    service_thread.start()
    
    # Create default API key for admin
    if len(API_KEYS) == 0:
        admin_user = USERS.get("admin")
        if admin_user:
            create_api_key(admin_user["user_id"], "Admin Key", None)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event to stop the API Gateway service."""
    global service
    if service:
        service.stop()


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Check the health of all services."""
    global service
    if not service:
        return {
            "status": "starting",
            "timestamp": time.time(),
            "version": "1.0.0",
            "services": {},
        }
    
    return service.check_health()


@app.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(request: LoginRequest):
    """Login and get a JWT token."""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_jwt_token(user["user_id"])
    expires_at = (datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)).timestamp()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user_id": user["user_id"],
    }


@app.post("/api-keys", response_model=ApiKeyResponse, tags=["auth"])
async def create_api_key_endpoint(request: ApiKeyRequest, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Create a new API key."""
    api_key = create_api_key(user["user_id"], request.name, request.expires_in_days)
    api_key_data = API_KEYS[api_key]
    
    return {
        "api_key": api_key,
        "name": api_key_data["name"],
        "created_at": api_key_data["created_at"],
        "expires_at": api_key_data["expires_at"],
    }


@app.get("/api-keys", response_model=List[ApiKeyResponse], tags=["auth"])
async def get_api_keys(user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Get all API keys for the current user."""
    user_api_keys = []
    
    for api_key, api_key_data in API_KEYS.items():
        if api_key_data["user_id"] == user["user_id"]:
            user_api_keys.append({
                "api_key": api_key,
                "name": api_key_data["name"],
                "created_at": api_key_data["created_at"],
                "expires_at": api_key_data["expires_at"],
            })
    
    return user_api_keys


@app.delete("/api-keys/{api_key}", tags=["auth"])
async def delete_api_key(api_key: str, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Delete an API key."""
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    if API_KEYS[api_key]["user_id"] != user["user_id"] and not user["is_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this API key",
        )
    
    del API_KEYS[api_key]
    
    return {"status": "success"}


@app.post("/trading/command", tags=["trading"])
async def send_trading_command(request: TradingCommandRequest, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Send a command to a trading strategy."""
    global service
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not available",
        )
    
    try:
        response = service.send_trading_command(request.strategy, request.command)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/trading/parameters", tags=["trading"])
async def update_strategy_parameters(request: StrategyParametersRequest, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Update strategy parameters."""
    global service
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not available",
        )
    
    try:
        response = service.update_strategy_parameters(request.strategy, request.parameters)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/market/symbols", tags=["market"])
async def add_trading_symbol(request: SymbolRequest, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Add a new trading symbol."""
    global service
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not available",
        )
    
    try:
        response = service.add_trading_symbol(request.symbol)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.delete("/market/symbols/{symbol}", tags=["market"])
async def remove_trading_symbol(symbol: str, user: Dict[str, Any] = Depends(get_current_user_from_api_key)):
    """Remove a trading symbol."""
    global service
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not available",
        )
    
    try:
        response = service.remove_trading_symbol(symbol)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    global service
    if not service:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    
    # Accept the connection
    await websocket.accept()
    
    # Generate a WebSocket ID
    ws_id = str(uuid.uuid4())
    
    # Add to active websockets
    service.active_websockets[ws_id] = websocket
    
    try:
        # Send initial status message
        await websocket.send_json({
            "type": "connected",
            "timestamp": time.time(),
            "data": {
                "message": "Connected to WebSocket",
                "client_id": ws_id,
            },
        })
        
        # Wait for messages
        while True:
            # Receive message
            try:
                message = await websocket.receive_text()
                
                # Parse message
                try:
                    data = json.loads(message)
                    
                    # Handle message
                    if "type" in data:
                        if data["type"] == "ping":
                            # Send pong
                            await websocket.send_json({
                                "type": "pong",
                                "timestamp": time.time(),
                                "data": {
                                    "message": "Pong",
                                },
                            })
                        elif data["type"] == "subscribe":
                            # Nothing to do, all clients get all messages
                            await websocket.send_json({
                                "type": "subscribed",
                                "timestamp": time.time(),
                                "data": {
                                    "message": "Subscribed",
                                    "topics": ["*"],
                                },
                            })
                except json.JSONDecodeError:
                    # Ignore invalid JSON
                    pass
            except WebSocketDisconnect:
                # Client disconnected
                break
    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        # Log error
        logger.error(f"WebSocket error: {e}")
        
        # Send error message
        try:
            await websocket.send_json({
                "type": "error",
                "timestamp": time.time(),
                "data": {
                    "message": str(e),
                },
            })
        except Exception:
            pass
    finally:
        # Remove from active websockets
        service.active_websockets.pop(ws_id, None)


if __name__ == "__main__":
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="API Gateway service")
    parser.add_argument("--rabbitmq", type=str, default="amqp://guest:guest@localhost:5672/", help="RabbitMQ URL")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--swagger", action="store_true", help="Enable Swagger UI")
    
    args = parser.parse_args()
    
    # Create and start API Gateway service
    service = ApiGatewayService(
        rabbitmq_url=args.rabbitmq,
        api_port=args.port,
        enable_swagger=args.swagger,
    )
    
    # Start service
    service.start()
