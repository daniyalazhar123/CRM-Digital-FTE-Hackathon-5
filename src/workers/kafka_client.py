"""
CRM Digital FTE - Kafka Client
Phase 2: Specialization — Step 1

Kafka producer and consumer with MOCK MODE support.
Works without Kafka by logging messages.
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================================================
# TOPIC DEFINITIONS
# =============================================================================

TOPICS = {
    'tickets_incoming': 'fte.tickets.incoming',
    'tickets_outbound': 'fte.tickets.outbound',
    'escalations': 'fte.escalations',
    'metrics': 'fte.metrics',
    'dlq': 'fte.dlq'  # Dead letter queue
}

# =============================================================================
# MOCK MODE CONFIGURATION
# =============================================================================

MOCK_MODE = True  # Set to False when Kafka is available


class FTEKafkaProducer:
    """
    Kafka producer with mock mode support.
    
    In MOCK_MODE, messages are logged instead of sent to Kafka.
    """
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.mock_mode = MOCK_MODE
        self._running = False
    
    async def start(self):
        """Start the Kafka producer."""
        if self.mock_mode:
            logger.info("Kafka Producer started in MOCK MODE (messages will be logged)")
            return
        
        try:
            from aiokafka import AIOKafkaProducer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self.producer.start()
            logger.info(f"Kafka Producer connected to {self.bootstrap_servers}")
            self._running = True
        except Exception as e:
            logger.warning(f"Kafka connection failed, falling back to MOCK MODE: {e}")
            self.mock_mode = True
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer and not self.mock_mode:
            await self.producer.stop()
            logger.info("Kafka Producer stopped")
        self._running = False
    
    async def publish(self, topic: str, event: Dict[str, Any]):
        """
        Publish event to Kafka topic.
        
        Args:
            topic: Topic name
            event: Event dictionary to publish
        """
        # Add timestamp
        event['timestamp'] = datetime.utcnow().isoformat()
        event['source'] = 'crm-fte'
        
        if self.mock_mode:
            # Mock mode - just log
            logger.info(f"[KAFK MOCK] Publishing to {topic}: {json.dumps(event)[:200]}...")
            return
        
        try:
            if self.producer and self._running:
                await self.producer.send_and_wait(topic, event)
                logger.debug(f"Published to {topic}: {event.get('event_type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            # Fallback to mock mode
            logger.info(f"[KAFKA FALLBACK] {topic}: {event}")
    
    async def publish_batch(self, topic: str, events: List[Dict[str, Any]]):
        """
        Publish multiple events to Kafka topic.
        
        Args:
            topic: Topic name
            events: List of event dictionaries
        """
        for event in events:
            await self.publish(topic, event)


class FTEKafkaConsumer:
    """
    Kafka consumer with mock mode support.
    
    In MOCK_MODE, consumer waits but doesn't receive messages.
    """
    
    def __init__(self, topics: List[str], group_id: str = "crm-fte-consumer",
                 bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka consumer.
        
        Args:
            topics: List of topics to consume
            group_id: Consumer group ID
            bootstrap_servers: Kafka bootstrap servers
        """
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.mock_mode = MOCK_MODE
        self._running = False
    
    async def start(self):
        """Start the Kafka consumer."""
        if self.mock_mode:
            logger.info(f"Kafka Consumer started in MOCK MODE (topics: {self.topics})")
            return
        
        try:
            from aiokafka import AIOKafkaConsumer
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest'
            )
            await self.consumer.start()
            logger.info(f"Kafka Consumer connected to {self.bootstrap_servers}")
            self._running = True
        except Exception as e:
            logger.warning(f"Kafka connection failed, falling back to MOCK MODE: {e}")
            self.mock_mode = True
    
    async def stop(self):
        """Stop the Kafka consumer."""
        if self.consumer and not self.mock_mode:
            await self.consumer.stop()
            logger.info("Kafka Consumer stopped")
        self._running = False
    
    async def consume(self, handler: Callable[[str, Dict[str, Any]], None]):
        """
        Consume messages from topics and call handler.
        
        Args:
            handler: Async function to call with (topic, message)
        """
        if self.mock_mode:
            logger.info("Kafka Consumer in MOCK MODE - waiting for messages (none will arrive)")
            # In mock mode, just wait indefinitely
            while True:
                await asyncio.sleep(60)
            return
        
        try:
            if self.consumer and self._running:
                async for msg in self.consumer:
                    try:
                        await handler(msg.topic, msg.value)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
    
    async def consume_one(self, timeout: float = 5.0) -> Optional[tuple]:
        """
        Consume one message with timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (topic, message) or None
        """
        if self.mock_mode:
            await asyncio.sleep(timeout)
            return None
        
        try:
            if self.consumer and self._running:
                msg = await asyncio.wait_for(
                    self.consumer.getone(),
                    timeout=timeout
                )
                return (msg.topic, msg.value)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
        
        return None
