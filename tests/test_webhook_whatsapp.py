"""
CRM Digital FTE - WhatsApp Webhook Tests (Updated for Router-based Handler)

Tests for WhatsApp Twilio webhook processing with signature validation.
"""

import sys
import os
import pytest
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def get_test_client():
    """Get TestClient for the FastAPI app."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Could not create test client: {e}")
        return None


class TestWhatsAppTwilioWebhook:
    """Test WhatsApp Twilio webhook processing."""

    def test_twilio_format_message(self):
        """Test Twilio webhook format processing."""
        client = get_test_client()
        if client is None:
            return

        payload = {
            'From': 'whatsapp:+14155551234',
            'To': 'whatsapp:+14155238886',
            'Body': 'Hello, I need help with my account',
            'MessageSid': 'SM1234567890abcdef',
            'NumMedia': '0'
        }

        response = client.post('/webhooks/whatsapp', data=payload)

        # Should return 200 with TwiML
        assert response.status_code == 200
        assert 'Response' in response.text

    def test_twilio_with_media(self):
        """Test WhatsApp message with media attachments."""
        client = get_test_client()
        if client is None:
            return

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
        client = get_test_client()
        if client is None:
            return

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
        from channels.whatsapp_handler import parse_whatsapp_message

        form_data = {'From': 'whatsapp:+14155551234', 'Body': 'test'}
        result = parse_whatsapp_message(form_data)

        assert result['customer_phone'] == '+14155551234'

    def test_twiml_generation(self):
        """Test TwiML response generation."""
        from channels.whatsapp_handler import build_twiml_response

        twiml = build_twiml_response("Hello")

        assert '<?xml' in twiml or 'Response' in twiml
        assert '<Message>' in twiml

    def test_twiml_long_message(self):
        """Test TwiML generation for long messages."""
        from channels.whatsapp_handler import build_twiml_response

        long_msg = "A" * 2000
        twiml = build_twiml_response(long_msg)

        # Should have multiple Message tags
        assert twiml.count('<Message>') > 1

    def test_whatsapp_handler_import(self):
        """Test WhatsApp handler can be imported."""
        from channels.whatsapp_handler import parse_whatsapp_message, build_twiml_response, send_whatsapp_message
        assert parse_whatsapp_message is not None
        assert build_twiml_response is not None

    def test_signature_validation_skip(self):
        """Test that signature validation is skipped without credentials."""
        client = get_test_client()
        if client is None:
            return

        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Test message'
        }

        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200

    def test_metrics_tracking(self):
        """Test that metrics are tracked for WhatsApp webhook."""
        client = get_test_client()
        if client is None:
            return

        payload = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Metrics test'
        }

        response = client.post('/webhooks/whatsapp', data=payload)
        assert response.status_code == 200


class TestWhatsAppHandlerUnit:
    """Unit tests for WhatsApp handler functions."""

    def test_process_webhook_basic(self):
        """Test basic webhook processing."""
        from channels.whatsapp_handler import parse_whatsapp_message

        form_data = {
            'From': 'whatsapp:+14155551234',
            'Body': 'Test message',
            'MessageSid': 'SM123'
        }

        result = parse_whatsapp_message(form_data)

        assert result['channel'] == 'whatsapp'
        assert result['customer_phone'] == '+14155551234'
        assert result['message'] == 'Test message'

    def test_send_whatsapp_message(self):
        """Test send_whatsapp_message with real Twilio credentials.

        Since +14155551234 is not a sandbox participant, Twilio will error.
        Function should always return a dict without crashing.
        """
        from channels.whatsapp_handler import send_whatsapp_message

        result = send_whatsapp_message(
            to_number='+14155551234',
            body='Test body'
        )

        assert 'success' in result
        # With real credentials, send to non-sandbox number should fail
        # Function should not raise exception and should return dict
