"""
Base microservice module for the crypto trading bot.
Provides a framework for creating microservices.
"""

import os
import json
import signal
import sys
import time
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
import threading
import queue

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker
from pika.spec import Basic, BasicProperties

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class BaseService(ABC):
    """Base class for all microservices."""

    def __init__(
        self,
        service_name: str,
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "crypto_trading",
        exchange_type: str = "topic",
        queue_name: Optional[str] = None,
    ):
        """
        Initialize the microservice.

        Args:
            service_name: The name of the service.
            rabbitmq_url: The URL of the RabbitMQ server.
            exchange_name: The name of the exchange.
            exchange_type: The type of the exchange.
            queue_name: The name of the queue. If None, a unique queue name will be generated.
        """
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)

        self.service_name = service_name
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.queue_name = queue_name or f"{service_name}-{uuid.uuid4().hex[:8]}"

        self.connection = None
        self.channel = None
        self.consuming_channel = None
        
        # Dictionary of topic patterns and their handlers
        self.handlers = {}
        
        # Set to True when stop() is called
        self.should_stop = False

        # Thread-safe queue for async message processing
        self.message_queue = queue.Queue()
        
        # Thread for processing messages
        self.processing_thread = None
        
        # RPC responses
        self.rpc_responses = {}
        self.rpc_correlation_ids = {}

        # Signal handler
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle signals."""
        self.logger.info(f"Received signal {sig}. Shutting down...")
        self.stop()
        sys.exit(0)

    def _connect(self):
        """Connect to RabbitMQ."""
        try:
            # Create a connection
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )

            # Create a channel
            self.channel = self.connection.channel()
            
            # Declare an exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type=self.exchange_type,
                durable=True,
            )
            
            # Declare a queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                exclusive=False,
                auto_delete=False,
            )
            
            # Create a separate channel for consuming
            self.consuming_channel = self.connection.channel()
            
            self.logger.info(f"Connected to RabbitMQ: {self.rabbitmq_url}")
            
            return True
        except AMQPConnectionError as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            self.consuming_channel = None
            return False

    def _reconnect(self, max_retries: int = 5, retry_delay: float = 2.0):
        """
        Reconnect to RabbitMQ with retries.
        
        Args:
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.
            
        Returns:
            True if reconnected successfully, False otherwise.
        """
        retries = 0
        while retries < max_retries and not self.should_stop:
            self.logger.info(f"Attempting to reconnect to RabbitMQ (attempt {retries + 1}/{max_retries})...")
            if self._connect():
                # Re-subscribe to all topics
                for topic_pattern in self.handlers.keys():
                    self._subscribe(topic_pattern)
                return True
            
            # Increment retry counter
            retries += 1
            
            # Wait before retrying
            if retries < max_retries:
                time.sleep(retry_delay)
        
        return False

    def _process_messages(self):
        """Process messages from the queue in a separate thread."""
        while not self.should_stop:
            try:
                # Get message from queue with timeout
                try:
                    topic, method, properties, body = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the message
                self._process_message(topic, method, properties, body)
                
                # Mark the message as processed
                self.message_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    def _process_message(self, topic: str, method: Basic.Deliver, properties: BasicProperties, body: bytes):
        """
        Process a message.
        
        Args:
            topic: The topic of the message.
            method: The delivery method.
            properties: The message properties.
            body: The message body.
        """
        try:
            # Decode the message body
            message = json.loads(body.decode())
            
            # Check if this is an RPC response
            if properties.correlation_id and properties.correlation_id in self.rpc_responses:
                self.rpc_responses[properties.correlation_id] = message
                return
            
            # Find matching handlers
            for pattern, handler in self.handlers.items():
                if self._match_topic(topic, pattern):
                    # Call the handler
                    handler(topic, message, properties)
        except json.JSONDecodeError:
            self.logger.error(f"Error decoding message: {body}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _callback(self, ch: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes):
        """
        Callback for message processing.
        
        Args:
            ch: The channel.
            method: The delivery method.
            properties: The message properties.
            body: The message body.
        """
        # Get the topic from the routing key
        topic = method.routing_key
        
        # Add message to queue for async processing
        self.message_queue.put((topic, method, properties, body))
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """
        Check if a topic matches a pattern.
        
        Args:
            topic: The topic to check.
            pattern: The pattern to check against.
            
        Returns:
            True if the topic matches the pattern, False otherwise.
        """
        # Split topic and pattern into parts
        topic_parts = topic.split(".")
        pattern_parts = pattern.split(".")
        
        # Check if the parts match
        if len(topic_parts) != len(pattern_parts):
            return False
        
        # Check each part
        for t, p in zip(topic_parts, pattern_parts):
            if p == "*":
                continue
            if t != p:
                return False
        
        return True

    def _subscribe(self, topic_pattern: str):
        """
        Subscribe to a topic pattern.
        
        Args:
            topic_pattern: The topic pattern to subscribe to.
        """
        if not self.consuming_channel:
            self.logger.error("Cannot subscribe: no consuming channel")
            return
        
        # Bind the queue to the exchange with the topic pattern
        self.consuming_channel.queue_bind(
            exchange=self.exchange_name,
            queue=self.queue_name,
            routing_key=topic_pattern,
        )
        
        self.logger.info(f"Subscribed to topic pattern: {topic_pattern}")

    def _unsubscribe(self, topic_pattern: str):
        """
        Unsubscribe from a topic pattern.
        
        Args:
            topic_pattern: The topic pattern to unsubscribe from.
        """
        if not self.consuming_channel:
            self.logger.error("Cannot unsubscribe: no consuming channel")
            return
        
        # Unbind the queue from the exchange with the topic pattern
        self.consuming_channel.queue_unbind(
            exchange=self.exchange_name,
            queue=self.queue_name,
            routing_key=topic_pattern,
        )
        
        self.logger.info(f"Unsubscribed from topic pattern: {topic_pattern}")

    def start(self):
        """Start the microservice."""
        if not self._connect():
            self.logger.error("Failed to connect to RabbitMQ. Exiting...")
            return
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Basic QoS settings
        self.consuming_channel.basic_qos(prefetch_count=1)
        
        # Start consuming
        self.consuming_channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._callback,
        )
        
        self.logger.info(f"Service {self.service_name} started")
        
        try:
            # Call the run method
            self.run()
            
            # Start consuming messages
            self.logger.info("Waiting for messages...")
            self.consuming_channel.start_consuming()
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except ChannelClosedByBroker as e:
            self.logger.error(f"Channel closed by broker: {e}")
        except Exception as e:
            self.logger.error(f"Error: {e}")
        finally:
            self.stop()

    def publish(self, topic: str, message: Dict[str, Any], correlation_id: Optional[str] = None, reply_to: Optional[str] = None):
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to.
            message: The message to publish.
            correlation_id: Optional correlation ID for RPC.
            reply_to: Optional reply queue for RPC.
        """
        if not self.channel:
            self.logger.error("Cannot publish: no channel")
            return
        
        try:
            # Encode the message
            body = json.dumps(message).encode()
            
            # Create properties
            properties = pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # Persistent
                correlation_id=correlation_id,
                reply_to=reply_to,
            )
            
            # Publish the message
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=topic,
                body=body,
                properties=properties,
            )
            
            self.logger.debug(f"Published message to topic {topic}: {message}")
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")

    def subscribe(self, topic_pattern: str, handler: Callable[[str, Dict[str, Any], BasicProperties], None]):
        """
        Subscribe to a topic pattern with a handler.
        
        Args:
            topic_pattern: The topic pattern to subscribe to.
            handler: The handler to call when a message is received.
        """
        # Store the handler
        self.handlers[topic_pattern] = handler
        
        # Subscribe to the topic pattern
        self._subscribe(topic_pattern)

    def unsubscribe(self, topic_pattern: str):
        """
        Unsubscribe from a topic pattern.
        
        Args:
            topic_pattern: The topic pattern to unsubscribe from.
        """
        # Remove the handler
        if topic_pattern in self.handlers:
            del self.handlers[topic_pattern]
        
        # Unsubscribe from the topic pattern
        self._unsubscribe(topic_pattern)

    def call(self, topic: str, message: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Call a remote procedure and wait for a response.
        
        Args:
            topic: The topic to publish to.
            message: The message to publish.
            timeout: Timeout in seconds.
            
        Returns:
            The response message, or None if the call times out.
        """
        if not self.channel:
            self.logger.error("Cannot call: no channel")
            return None
        
        # Generate a correlation ID
        correlation_id = uuid.uuid4().hex
        
        # Create a promise for the response
        self.rpc_responses[correlation_id] = None
        
        # Publish the message
        self.publish(topic, message, correlation_id=correlation_id, reply_to=self.queue_name)
        
        # Wait for the response
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if response has arrived
            if self.rpc_responses[correlation_id] is not None:
                response = self.rpc_responses[correlation_id]
                del self.rpc_responses[correlation_id]
                return response
            
            # Sleep briefly
            time.sleep(0.1)
        
        # Timed out
        del self.rpc_responses[correlation_id]
        self.logger.warning(f"Call to {topic} timed out after {timeout} seconds")
        return None

    def stop(self):
        """Stop the microservice."""
        self.should_stop = True
        
        if self.consuming_channel:
            try:
                self.consuming_channel.stop_consuming()
            except Exception:
                pass
        
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
        
        self.connection = None
        self.channel = None
        self.consuming_channel = None
        
        self.logger.info(f"Service {self.service_name} stopped")

    @abstractmethod
    def run(self):
        """Run the microservice. This method must be implemented by subclasses."""
        pass


class HealthCheck:
    """Health check utility for microservices."""

    def __init__(self, service: BaseService):
        """
        Initialize the health check.
        
        Args:
            service: The service to check.
        """
        self.service = service
        self.logger = service.logger
        self.healthy = True
        self.last_check = time.time()
        self.check_interval = 60.0  # seconds
        
        # Register health check handler
        self.service.subscribe("health.check", self._health_check_handler)
        
        # Start periodic health check
        self._start_periodic_health_check()

    def _health_check_handler(self, topic: str, message: Dict[str, Any], properties: BasicProperties):
        """
        Handle health check requests.
        
        Args:
            topic: The topic of the message.
            message: The message.
            properties: The message properties.
        """
        # Perform health check
        health_status = self.check()
        
        # Send response
        if properties.reply_to and properties.correlation_id:
            self.service.publish(
                properties.reply_to,
                {
                    "service": self.service.service_name,
                    "healthy": health_status,
                    "timestamp": time.time(),
                },
                correlation_id=properties.correlation_id,
            )

    def _start_periodic_health_check(self):
        """Start periodic health check."""
        def periodic_check():
            while not self.service.should_stop:
                # Check if it's time to perform a health check
                if time.time() - self.last_check >= self.check_interval:
                    self.check()
                    self.last_check = time.time()
                
                # Sleep
                time.sleep(1.0)
        
        # Start thread
        thread = threading.Thread(target=periodic_check)
        thread.daemon = True
        thread.start()

    def check(self) -> bool:
        """
        Check the health of the service.
        
        Returns:
            True if the service is healthy, False otherwise.
        """
        # Check RabbitMQ connection
        if not self.service.connection or not self.service.connection.is_open:
            self.healthy = False
            self.logger.warning("Health check failed: RabbitMQ connection is closed")
            
            # Try to reconnect
            if self.service._reconnect():
                self.healthy = True
                self.logger.info("Health check: reconnected to RabbitMQ")
        else:
            self.healthy = True
            self.logger.debug("Health check passed")
        
        return self.healthy
