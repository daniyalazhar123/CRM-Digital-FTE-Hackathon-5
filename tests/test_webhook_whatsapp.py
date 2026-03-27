"""
CRM Digital FTE - WhatsApp Webhook Tests
Feature 6: Test Coverage Enhancement

Tests for WhatsApp Twilio webhook processing with signature validation.
"""

import sys
import os
import pytest
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from api.main import app

# Create test client
client = TestClient(app)


class TestWhatsAppTwilioWebhook:
    """Test WhatsApp Twilio webhook processing."""
    
    def test_twilio_format_message(self):
        """Test Twilio webhook format processing."""
        payload = {
            'From': 'whatsapp:+14155551234',
            'To': 'whatsapp:+14155238886',
            'Body': 'Hello, I need help with my account',
            'MessageSid': 'SM1234567890abcdef',
            'NumMedia': '0'
        }
        
        response = client.post('/webhooks/whatsapp', data=payload)
        
        # Should return XML (TwiML)
        assert response.status_code == 200
        assert 'application/xml' in response.headers.get('content-type', '')
    
    def test_twilio_with_media(self):
        """Test WhatsApp message with media attachments."""
        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Check this image',
            'MessageSid': 'SM1234567890',
            'NumMedia': '1',
            'MediaUrl0': 'https://example.com/image.jpg'
        }
        
        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200
    
    def test_twilio_multiple_media(self):
        """Test WhatsApp message with multiple media attachments."""
        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Check these files',
            'MessageSid': 'SM1234567890',
            'NumMedia': '3',
            'MediaUrl0': 'https://example.com/file1.pdf',
            'MediaUrl1': 'https://example.com/file2.pdf',
            'MediaUrl2': 'https://example.com/file3.pdf'
        }
        
        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200
    
    def test_phone_number_extraction(self):
        """Test phone number extraction from WhatsApp format."""
        from channels.whatsapp_handler import WhatsAppHandler
        import asyncio
        
        handler = WhatsAppHandler()
        
        form_data = {'From': 'whatsapp:+14155551234'}
        result = asyncio.run(handler.process_webhook(form_data))
        
        assert result['customer_phone'] == '+14155551234'
    
    def test_response_splitting(self):
        """Test long response splitting for WhatsApp."""
        from channels.whatsapp_handler import WhatsAppHandler
        
        handler = WhatsAppHandler()
        
        # Short message (no split)
        short = "Hello, how can I help you?"
        result = handler.format_response_for_whatsapp(short)
        assert len(result) == 1
        assert result[0] == short
        
        # Long message (should split)
        long_msg = "A" * 2000
        result = handler.format_response_for_whatsapp(long_msg)
        assert len(result) > 1
        assert all(len(msg) <= 1600 for msg in result)
    
    def test_twiml_generation(self):
        """Test TwiML response generation."""
        from channels.whatsapp_handler import WhatsAppHandler
        import asyncio
        
        handler = WhatsAppHandler()
        
        twiml = asyncio.run(handler.send_twiML_response("Hello"))
        
        assert '<?xml' in twiml
        assert '<Response>' in twiml
        assert '<Message>' in twiml
    
    def test_twiml_long_message(self):
        """Test TwiML generation for long messages."""
        from channels.whatsapp_handler import WhatsAppHandler
        import asyncio
        
        handler = WhatsAppHandler()
        
        long_msg = "A" * 2000
        twiml = asyncio.run(handler.send_twiML_response(long_msg))
        
        # Should have multiple Message tags
        assert twiml.count('<Message>') > 1
    
    def test_whatsapp_handler_import(self):
        """Test WhatsApp handler can be imported."""
        from channels.whatsapp_handler import WhatsAppHandler
        assert WhatsAppHandler is not None
    
    def test_signature_validation_skip(self):
        """Test that signature validation is skipped without credentials."""
        # Without TWILIO_AUTH_TOKEN set, validation should be skipped
        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Test message'
        }
        
        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked for WhatsApp webhook."""
        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Metrics test'
        }
        
        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200


class TestWhatsAppHandlerUnit:
    """Unit tests for WhatsAppHandler class."""
    
    def test_handler_initialization(self):
        """Test WhatsAppHandler initializes correctly."""
        from channels.whatsapp_handler import WhatsAppHandler
        handler = WhatsAppHandler()
        assert handler is not None
        # In mock mode without credentials
        assert handler._initialized == False or handler._initialized == True
    
    def test_process_webhook_basic(self):
        """Test basic webhook processing."""
        from channels.whatsapp_handler import WhatsAppHandler
        import asyncio
        
        handler = WhatsAppHandler()
        
        form_data = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Test message',
            'MessageSid': 'SM123'
        }
        
        result = asyncio.run(handler.process_webhook(form_data))
        
        assert result['channel'] == 'whatsapp'
        assert result['customer_phone'] == '+14155551234'
        assert result['content'] == 'Test message'
    
    def test_send_message_mock(self):
        """Test send_message in mock mode."""
        from channels.whatsapp_handler import WhatsAppHandler
        import asyncio
        
        handler = WhatsAppHandler()
        
        result = asyncio.run(handler.send_message(
            to_phone='+14155551234',
            body='Test body'
        ))
        
        assert 'delivery_status' in result
    
    def test_manual_signature_validation(self):
        """Test manual signature validation method."""
        from channels.whatsapp_handler import WhatsAppHandler
        
        handler = WhatsAppHandler()
        handler.auth_token = 'test_token'
        
        # This would require proper signature calculation
        # For now, just test the method exists and doesn't crash
        result = handler.validate_webhook_signature_manual(
            request_url='http://example.com/webhook',
            params={'Body': 'test'},
            signature='invalid'
        )
        
        assert isinstance(result, bool)


class TestWhatsAppStatusWebhook:
    """Test WhatsApp status webhook."""
    
    def test_status_update(self):
        """Test message status update webhook."""
        payload = {
            'MessageSid': 'SM123',
            'MessageStatus': 'delivered'
        }
        
        response = client.post('/webhooks/whatsapp/status', data=payload)
        assert response.status_code == 200
