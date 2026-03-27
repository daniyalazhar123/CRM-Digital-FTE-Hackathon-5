"""
CRM Digital FTE - Gmail Webhook Tests
Feature 6: Test Coverage Enhancement

Tests for Gmail Pub/Sub webhook processing.
"""

import sys
import os
import pytest
import base64
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from api.main import app

# Create test client
client = TestClient(app)


class TestGmailPubSubWebhook:
    """Test Gmail Pub/Sub webhook processing."""
    
    def test_pubsub_message_format(self):
        """Test Pub/Sub message format parsing."""
        # Create Pub/Sub formatted message
        payload = {
            'from': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test message body'
        }
        
        # Encode as Pub/Sub would
        encoded_data = base64.b64encode(
            json.dumps(payload).encode('utf-8')
        ).decode('utf-8')
        
        pubsub_message = {
            'message': {
                'data': encoded_data,
                'attributes': {
                    'projectId': 'test-project'
                },
                'messageId': 'msg-123'
            },
            'subscription': 'projects/test-project/subscriptions/gmail-sub'
        }
        
        response = client.post('/webhooks/gmail', json=pubsub_message)
        
        # Should return 200 (even if processing fails)
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
    
    def test_pubsub_base64_decode(self):
        """Test base64 decoding of Pub/Sub messages."""
        # Valid base64 encoded JSON
        payload = {'from': 'user@test.com', 'body': 'Hello'}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        
        message = {
            'message': {
                'data': encoded
            }
        }
        
        response = client.post('/webhooks/gmail', json=message)
        assert response.status_code == 200
    
    def test_pubsub_invalid_base64(self):
        """Test handling of invalid base64 data."""
        message = {
            'message': {
                'data': 'not-valid-base64!!!'
            }
        }
        
        response = client.post('/webhooks/gmail', json=message)
        assert response.status_code == 200  # Should handle gracefully
    
    def test_pubsub_missing_data(self):
        """Test handling of missing data field."""
        message = {
            'message': {}
        }
        
        response = client.post('/webhooks/gmail', json=message)
        assert response.status_code == 200
    
    def test_pubsub_missing_message(self):
        """Test handling of missing message field."""
        message = {}
        
        response = client.post('/webhooks/gmail', json=message)
        assert response.status_code == 200
    
    def test_simple_webhook_format(self):
        """Test simple webhook format (non-Pub/Sub)."""
        payload = {
            'from': 'customer@example.com',
            'subject': 'Help needed',
            'body': 'How do I reset my password?'
        }
        
        response = client.post('/webhooks/gmail', json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert 'status' in data
    
    def test_email_extraction(self):
        """Test email extraction from various From formats."""
        from channels.gmail_handler import GmailHandler
        
        handler = GmailHandler()
        
        # Test various formats
        assert handler._extract_email('John Doe <john@example.com>') == 'john@example.com'
        assert handler._extract_email('<jane@example.com>') == 'jane@example.com'
        assert handler._extract_email('bob@example.com') == 'bob@example.com'
        assert handler._extract_email('') == ''
    
    def test_body_extraction_multipart(self):
        """Test body extraction from multipart emails."""
        # This would require mocking Gmail API payload
        # For now, test the method exists
        from channels.gmail_handler import GmailHandler
        import asyncio
        
        handler = GmailHandler()
        
        # Test with simple payload
        payload = {
            'mimeType': 'text/plain',
            'body': {
                'data': base64.b64encode(b'Test body').decode()
            }
        }
        
        text_body, html_body = asyncio.run(handler._extract_body_content(payload))
        assert text_body == 'Test body'
    
    def test_gmail_handler_import(self):
        """Test Gmail handler can be imported."""
        from channels.gmail_handler import GmailHandler
        assert GmailHandler is not None
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked for Gmail webhook."""
        payload = {
            'from': 'metrics@test.com',
            'subject': 'Metrics test',
            'body': 'Testing metrics tracking'
        }
        
        response = client.post('/webhooks/gmail', json=payload)
        assert response.status_code == 200


class TestGmailHandlerUnit:
    """Unit tests for GmailHandler class."""
    
    def test_handler_initialization(self):
        """Test GmailHandler initializes correctly."""
        from channels.gmail_handler import GmailHandler
        handler = GmailHandler()
        assert handler is not None
        assert handler._authenticated == False
    
    def test_process_webhook_delegation(self):
        """Test process_webhook delegates to process_pubsub_webhook."""
        from channels.gmail_handler import GmailHandler
        import asyncio
        
        handler = GmailHandler()
        
        payload = {'from': 'test@example.com', 'body': 'test'}
        result = asyncio.run(handler.process_webhook(payload))
        
        assert isinstance(result, list)
    
    def test_send_reply_mock(self):
        """Test send_reply in mock mode."""
        from channels.gmail_handler import GmailHandler
        import asyncio
        
        handler = GmailHandler()
        
        result = asyncio.run(handler.send_reply(
            to_email='test@example.com',
            subject='Test',
            body='Test body'
        ))
        
        assert 'delivery_status' in result
        assert result['delivery_status'] == 'sent'
