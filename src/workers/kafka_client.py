"""
CRM Digital FTE - Kafka Client
Phase 2: Specialization — Step 1

Kafka producer and consumer for real event streaming.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
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


class FTEKafkaProducer:
    """
    Kafka producer for real event publishing.
    Requires a running Kafka instance (localhost:9092).
    """
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self._running = False
    
    async def start(self):
        """Start the Kafka producer."""
        from aiokafka import AIOKafkaProducer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info(f"Kafka Producer connected to {self.bootstrap_servers}")
        self._running = True
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
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
        event['timestamp'] = datetime.now(timezone.utc).isoformat()
        event['source'] = 'crm-fte'
        
        if not self.producer or not self._running:
            raise RuntimeError("Kafka producer not started. Call start() first.")
        
        await self.producer.send_and_wait(topic, event)
        logger.debug(f"Published to {topic}: {event.get('event_type', 'unknown')}")
    
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
    Kafka consumer for real event consumption.
    Requires a running Kafka instance (localhost:9092).
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
        self._running = False
    
    async def start(self):
        """Start the Kafka consumer."""
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
    
    async def stop(self):
        """Stop the Kafka consumer."""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka Consumer stopped")
        self._running = False
    
    async def consume(self, handler: Callable[[str, Dict[str, Any]], None]):
        """
        Consume messages from topics and call handler.
        
        Args:
            handler: Async function to call with (topic, message)
        """
        if not self.consumer or not self._running:
            raise RuntimeError("Kafka consumer not started. Call start() first.")
        
        async for msg in self.consumer:
            try:
                await handler(msg.topic, msg.value)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def consume_one(self, timeout: float = 5.0) -> Optional[tuple]:
        """
        Consume one message with timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (topic, message) or None
        """
        if not self.consumer or not self._running:
            raise RuntimeError("Kafka consumer not started. Call start() first.")
        
        try:
            msg = await asyncio.wait_for(
                self.consumer.getone(),
                timeout=timeout
            )
            return (msg.topic, msg.value)
        except asyncio.TimeoutError:
            return None
