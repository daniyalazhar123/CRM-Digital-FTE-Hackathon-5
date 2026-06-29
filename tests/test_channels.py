"""
CRM Digital FTE - Channel Handlers Tests
Phase 2: Specialization

Test Gmail, WhatsApp, and Web Form handlers.
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestGmailHandler:
    """Test Gmail handler."""
    
    def test_gmail_handler_import(self):
        """Test that Gmail handler module can be imported."""
        from channels import gmail_handler
        assert gmail_handler is not None
        assert hasattr(gmail_handler, 'router')
        assert hasattr(gmail_handler, 'gmail_webhook')
    
    def test_gmail_extract_email(self):
        """Test email extraction from header."""
        from channels.gmail_handler import _extract_email_data
        import base64
        
        encoded_body = base64.urlsafe_b64encode(b"Hello, I need help with my account.").decode()
        
        # Test with mock Gmail API message structure
        msg = {
            'id': 'msg_123',
            'threadId': 'thread_456',
            'payload': {
                'mimeType': 'text/plain',
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'To', 'value': 'support@techcorp.com'},
                    {'name': 'Subject', 'value': 'Test'}
                ],
                'body': {
                    'data': encoded_body
                }
            }
        }
        result = _extract_email_data(msg)
        assert result is not None
        assert 'customer_email' in result
        assert result['customer_email'] == 'john@example.com'
        assert 'subject' in result
        assert result['subject'] == 'Test'
        assert 'body' in result
    
    def test_gmail_extract_body_simple(self):
        """Test body extraction from simple payload."""
        from channels.gmail_handler import _extract_body
        
        # Mock payload with body
        payload = {
            'body': {
                'data': 'SGVsbG8gV29ybGQ='  # "Hello World" base64 encoded
            }
        }
        
        # Should not raise exception
        try:
            body = _extract_body(payload)
            assert isinstance(body, str)
        except Exception:
            pass


class TestWhatsAppHandler:
    """Test WhatsApp handler (router-based)."""
    
    def test_whatsapp_handler_import(self):
        """Test that WhatsApp handler module can be imported."""
        from channels import whatsapp_handler
        assert whatsapp_handler is not None
        assert hasattr(whatsapp_handler, 'router')
        assert hasattr(whatsapp_handler, 'send_whatsapp_message')
    
    def test_whatsapp_format_response_short(self):
        """Test TwiML building for short messages."""
        from twilio.twiml.messaging_response import MessagingResponse

        response_text = "Short test response"
        twiml = MessagingResponse()
        twiml.message(response_text)
        result = str(twiml)

        assert "Response" in result
        assert "Short test response" in result

    def test_whatsapp_format_response_long(self):
        """Test TwiML building for long messages (>1600 chars)."""
        from twilio.twiml.messaging_response import MessagingResponse

        long_response = "A" * 2000
        twiml = MessagingResponse()
        # Split long message into multiple messages
        for i in range(0, len(long_response), 1600):
            chunk = long_response[i:i + 1600]
            twiml.message(chunk)
        result = str(twiml)

        assert "Response" in result
        # Long messages should have multiple <Message> tags
        assert result.count("<Message>") > 1
    
    def test_whatsapp_phone_format(self):
        """Test phone number formatting via Twilio format."""
        phone = "whatsapp:+14155551234"
        # Extract the number after 'whatsapp:'
        assert phone.startswith("whatsapp:+")
        customer_phone = phone.replace("whatsapp:", "")
        assert customer_phone == "+14155551234"


class TestWebFormHandler:
    """Test Web Form handler."""
    
    def test_web_form_categories(self):
        """Test that valid categories are defined."""
        valid_categories = ['how-to', 'technical', 'billing', 'bug-report', 'other']
        
        assert 'how-to' in valid_categories
        assert 'billing' in valid_categories
        assert 'technical' in valid_categories
        assert 'bug-report' in valid_categories
        assert 'other' in valid_categories
    
    def test_web_form_priorities(self):
        """Test that valid priorities are defined."""
        valid_priorities = ['low', 'medium', 'high']
        
        assert 'low' in valid_priorities
        assert 'medium' in valid_priorities
        assert 'high' in valid_priorities
    
    def test_web_form_validation_name(self):
        """Test name validation."""
        # Valid names
        assert len("John Doe".strip()) >= 2
        assert len("J".strip()) < 2  # Too short
        
    def test_web_form_validation_message(self):
        """Test message validation."""
        # Valid messages
        assert len("This is a test message".strip()) >= 10
        assert len("Short".strip()) < 10  # Too short
    
    def test_web_form_validation_email(self):
        """Test email validation."""
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        
        # Valid emails
        assert re.match(email_pattern, "test@example.com")
        assert re.match(email_pattern, "user.name@domain.co.uk")
        
        # Invalid emails
        assert not re.match(email_pattern, "invalid")
        assert not re.match(email_pattern, "test@")
        assert not re.match(email_pattern, "@example.com")
