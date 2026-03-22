"""
CRM Digital FTE - Message Processor
Phase 2: Specialization — Step 1

Unified message processor that consumes from Kafka and processes with CRM agent.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .kafka_client import FTEKafkaProducer, FTEKafkaConsumer, TOPICS, MOCK_MODE

logger = logging.getLogger(__name__)


class UnifiedMessageProcessor:
    """
    Processes incoming messages from all channels through the CRM agent.
    
    In MOCK_MODE, processes messages but doesn't require Kafka.
    """
    
    def __init__(self):
        """Initialize the message processor."""
        self.producer = FTEKafkaProducer()
        self.consumer = None
        self._running = False
        
        # Import CRM agent
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))
        from crm_agent import process_message
        self.process_message = process_message
    
    async def start(self):
        """Start the message processor."""
        logger.info("Starting Unified Message Processor...")
        
        # Start producer
        await self.producer.start()
        
        # Start consumer (if not in mock mode)
        if not MOCK_MODE:
            self.consumer = FTEKafkaConsumer(
                topics=[TOPICS['tickets_incoming']],
                group_id='fte-message-processor'
            )
            await self.consumer.start()
            logger.info("Message processor started, listening for tickets...")
        else:
            logger.info("Message processor started in MOCK MODE")
        
        self._running = True
    
    async def stop(self):
        """Stop the message processor."""
        self._running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        await self.producer.stop()
        logger.info("Message processor stopped")
    
    async def process_message_from_kafka(self, topic: str, message: Dict[str, Any]):
        """
        Process a message received from Kafka.
        
        Args:
            topic: Kafka topic
            message: Message dictionary
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract channel and customer info
            channel = message.get('channel', 'email')
            customer_identifier = message.get('customer_email') or message.get('customer_phone')
            content = message.get('content', '')
            customer_name = message.get('customer_name')
            
            logger.info(f"Processing {channel} message from {customer_identifier}")
            
            # Process with CRM agent
            result = self.process_message(
                customer_email=customer_identifier,
                message=content,
                channel=channel,
                customer_name=customer_name
            )
            
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Publish metrics
            await self.producer.publish(TOPICS['metrics'], {
                'event_type': 'message_processed',
                'channel': channel,
                'processing_time_ms': processing_time,
                'escalated': result.get('escalated', False),
                'ticket_id': result.get('ticket_id')
            })
            
            logger.info(f"Processed {channel} message in {processing_time:.0f}ms")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.handle_error(message, e)
    
    async def handle_error(self, message: Dict[str, Any], error: Exception):
        """
        Handle processing errors gracefully.
        
        Args:
            message: Original message that failed
            error: Exception that occurred
        """
        logger.error(f"Message processing error: {error}")
        
        # Publish to dead letter queue
        await self.producer.publish(TOPICS['dlq'], {
            'event_type': 'processing_error',
            'original_message': message,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send apologetic response via appropriate channel
        channel = message.get('channel', 'email')
        customer_identifier = message.get('customer_email') or message.get('customer_phone')
        
        apology = "I'm sorry, I'm having trouble processing your request right now. A human agent will follow up shortly."
        
        # In production, send via channel handler
        logger.info(f"Sending apology to {customer_identifier} via {channel}: {apology}")
    
    async def run_demo(self):
        """
        Run a demo processing cycle (for testing without Kafka).
        
        Processes sample messages to demonstrate functionality.
        """
        logger.info("Running demo processing cycle...")
        
        # Sample messages
        demo_messages = [
            {
                'channel': 'email',
                'customer_email': 'demo@example.com',
                'content': 'How do I reset my password?',
                'customer_name': 'Demo User'
            },
            {
                'channel': 'whatsapp',
                'customer_phone': '+14155551234',
                'content': 'I need help with my account',
                'customer_name': 'WhatsApp User'
            },
            {
                'channel': 'web_form',
                'customer_email': 'web@test.com',
                'content': 'What is the price for enterprise?',
                'customer_name': 'Web User'
            }
        ]
        
        for msg in demo_messages:
            await self.process_message_from_kafka('demo', msg)
            await asyncio.sleep(1)
        
        logger.info("Demo processing cycle complete")


async def main():
    """Main entry point for message processor."""
    processor = UnifiedMessageProcessor()
    
    try:
        await processor.start()
        
        if MOCK_MODE:
            # Run demo in mock mode
            await processor.run_demo()
        else:
            # Consume from Kafka
            await processor.consumer.consume(
                processor.process_message_from_kafka
            )
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await processor.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
