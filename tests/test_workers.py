"""
CRM Digital FTE - Workers Tests
Phase 2: Specialization

Test Kafka client and message processor.
"""

import sys
import os
import asyncio
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from workers.kafka_client import FTEKafkaProducer, FTEKafkaConsumer, TOPICS
from workers.message_processor import UnifiedMessageProcessor


class TestKafkaTopics:
    """Test Kafka topic definitions."""
    
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
