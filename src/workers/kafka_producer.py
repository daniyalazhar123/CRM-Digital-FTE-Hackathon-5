"""
CRM Digital FTE - Kafka Producer
Phase 2: Specialization

Kafka producer utilities for publishing events to topics.
Handles ticket ingestion, escalations, and metrics publishing.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from aiokafka import AIOKafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None

logger = logging.getLogger(__name__)

# =============================================================================
# KAFKA TOPICS
# =============================================================================

class KafkaTopics:
    """Kafka topic definitions for the CRM Digital FTE system."""
    
    # Ticket ingestion
    TICKETS_INCOMING = "fte.tickets.incoming"
    
    # Channel-specific inbound
    CHANNEL_EMAIL_INBOUND = "fte.channels.email.inbound"
    CHANNEL_WHATSAPP_INBOUND = "fte.channels.whatsapp.inbound"
    CHANNEL_WEBFORM_INBOUND = "fte.channels.webform.inbound"
    
    # Channel-specific outbound
    CHANNEL_EMAIL_OUTBOUND = "fte.channels.email.outbound"
    CHANNEL_WHATSAPP_OUTBOUND = "fte.channels.whatsapp.outbound"
    
    # Escalations
    ESCALATIONS = "fte.escalations"
    
    # Metrics
    METRICS = "fte.metrics"
    
    # Dead letter queue
    DLQ = "fte.dlq"
    
    # All topics list
    ALL_TOPICS = [
        TICKETS_INCOMING,
        CHANNEL_EMAIL_INBOUND,
        CHANNEL_WHATSAPP_INBOUND,
        CHANNEL_WEBFORM_INBOUND,
        CHANNEL_EMAIL_OUTBOUND,
        CHANNEL_WHATSAPP_OUTBOUND,
        ESCALATIONS,
        METRICS,
        DLQ
    ]


# =============================================================================
# KAFKA PRODUCER
# =============================================================================

class KafkaProducer:
    """
    Kafka producer for publishing events.
    
    Handles:
    - Ticket ingestion events
    - Channel messages
    - Escalations
    - Metrics
    """
    
    _instance = None
    _producer = None
    _mock_mode = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaProducer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._initialize()
    
    def _initialize(self):
        """Initialize Kafka producer."""
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available, using mock mode")
            self._mock_mode = True
            self.initialized = True
            return
        
        self.bootstrap_servers = "localhost:9092"
        self._producer = None
        self._mock_mode = False
        self.initialized = True
        logger.info("✓ Kafka producer initialized")
    
    async def start(self):
        """Start the Kafka producer."""
        if self._mock_mode:
            logger.info("Kafka producer in mock mode")
            return
        
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            await self._producer.start()
            logger.info("✓ Kafka producer started")
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")
    
    async def publish(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """
        Publish message to Kafka topic.
        
        Args:
            topic: Kafka topic name
            message: Message dict to publish
            key: Optional message key for partitioning
        """
        if self._mock_mode:
            logger.debug(f"[MOCK] Published to {topic}: {message}")
            return
        
        if not self._producer:
            await self.start()
        
        try:
            await self._producer.send_and_wait(
                topic,
                value=message,
                key=key
            )
            logger.debug(f"Published to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            # Send to DLQ
            await self._publish_to_dlq(topic, message, str(e))
    
    async def publish_ticket(self, ticket_data: Dict[str, Any]):
        """Publish ticket ingestion event."""
        message = {
            "event_type": "ticket_created",
            "timestamp": datetime.utcnow().isoformat(),
            **ticket_data
        }
        await self.publish(KafkaTopics.TICKETS_INCOMING, message, key=ticket_data.get('ticket_id'))
    
    async def publish_channel_message(self, channel: str, message_data: Dict[str, Any]):
        """Publish channel-specific inbound message."""
        topic_map = {
            "email": KafkaTopics.CHANNEL_EMAIL_INBOUND,
            "whatsapp": KafkaTopics.CHANNEL_WHATSAPP_INBOUND,
            "web_form": KafkaTopics.CHANNEL_WEBFORM_INBOUND
        }
        
        topic = topic_map.get(channel, KafkaTopics.CHANNEL_WEBFORM_INBOUND)
        message = {
            "event_type": "message_received",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
            **message_data
        }
        await self.publish(topic, message, key=message_data.get('customer_id'))
    
    async def publish_escalation(self, escalation_data: Dict[str, Any]):
        """Publish escalation event."""
        message = {
            "event_type": "escalation",
            "timestamp": datetime.utcnow().isoformat(),
            **escalation_data
        }
        await self.publish(KafkaTopics.ESCALATIONS, message, key=escalation_data.get('ticket_id'))
    
    async def publish_metric(self, metric_data: Dict[str, Any]):
        """Publish metric event."""
        message = {
            "event_type": "metric",
            "timestamp": datetime.utcnow().isoformat(),
            **metric_data
        }
        await self.publish(KafkaTopics.METRICS, message)
    
    async def _publish_to_dlq(self, original_topic: str, message: Dict[str, Any], error: str):
        """Publish failed message to dead letter queue."""
        dlq_message = {
            "original_topic": original_topic,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "message": message
        }
        await self.publish(KafkaTopics.DLQ, dlq_message)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_producer() -> KafkaProducer:
    """Get singleton Kafka producer instance."""
    return KafkaProducer()


async def publish_ticket_event(ticket_data: Dict[str, Any]):
    """Convenience function to publish ticket event."""
    producer = get_producer()
    await producer.publish_ticket(ticket_data)


async def publish_channel_message(channel: str, message_data: Dict[str, Any]):
    """Convenience function to publish channel message."""
    producer = get_producer()
    await producer.publish_channel_message(channel, message_data)


async def publish_escalation_event(escalation_data: Dict[str, Any]):
    """Convenience function to publish escalation event."""
    producer = get_producer()
    await producer.publish_escalation(escalation_data)
