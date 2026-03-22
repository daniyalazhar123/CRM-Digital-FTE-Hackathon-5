"""
CRM Digital FTE - Workers Tests
Phase 2: Specialization

Test Kafka client and message processor with mock mode.
"""

import sys
import os
import asyncio
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from workers.kafka_client import FTEKafkaProducer, FTEKafkaConsumer, TOPICS, MOCK_MODE
from workers.message_processor import UnifiedMessageProcessor


class TestKafkaMockMode:
    """Test Kafka client in mock mode."""
    
    def test_producer_mock_mode(self):
        """Test that producer is in mock mode."""
        producer = FTEKafkaProducer()
        assert producer.mock_mode == True
    
    def test_producer_publish_mock(self):
        """Test producer publish in mock mode."""
        producer = FTEKafkaProducer()
        
        async def run_test():
            await producer.start()
            await producer.publish(
                TOPICS['tickets_incoming'],
                {'test': 'data', 'event_type': 'test_event'}
            )
            await producer.stop()
        
        # Run async test
        asyncio.run(run_test())
        # Test passes if no exception raised
    
    def test_consumer_mock_mode(self):
        """Test that consumer is in mock mode."""
        consumer = FTEKafkaConsumer([TOPICS['tickets_incoming']])
        assert consumer.mock_mode == True
    
    def test_topics_defined(self):
        """Test that all required topics are defined."""
        assert 'tickets_incoming' in TOPICS
        assert 'tickets_outbound' in TOPICS
        assert 'escalations' in TOPICS
        assert 'metrics' in TOPICS
        assert 'dlq' in TOPICS
        
        # Check topic names
        assert TOPICS['tickets_incoming'] == 'fte.tickets.incoming'
        assert TOPICS['escalations'] == 'fte.escalations'
    
    def test_message_processor_import(self):
        """Test that message processor can be imported."""
        from workers.message_processor import UnifiedMessageProcessor
        processor = UnifiedMessageProcessor()
        assert processor is not None
        assert processor.producer is not None


class TestMessageProcessor:
    """Test message processor."""
    
    def test_processor_initialization(self):
        """Test message processor initializes correctly."""
        processor = UnifiedMessageProcessor()
        assert processor.producer is not None
        assert processor.process_message is not None
    
    def test_processor_mock_mode(self):
        """Test processor uses mock mode."""
        processor = UnifiedMessageProcessor()
        assert processor.producer.mock_mode == True
