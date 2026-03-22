"""
CRM Digital FTE - WhatsApp Handler (Twilio)
Phase 2: Specialization — Step 7

Handles WhatsApp webhook notifications and sends replies via Twilio API.
"""

import os
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """Handler for Twilio WhatsApp API integration."""
    
    def __init__(self):
        """Initialize WhatsApp handler with Twilio credentials."""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        self.client = None
        self._initialized = False
        
        # Try to initialize Twilio client
        try:
            from twilio.rest import Client
            if self.account_sid and self.auth_token:
                self.client = Client(self.account_sid, self.auth_token)
                self._initialized = True
                logger.info("Twilio WhatsApp handler initialized")
            else:
                logger.warning("Twilio credentials not configured, using mock mode")
        except ImportError:
            logger.warning("Twilio library not installed, using mock mode")
    
    async def validate_webhook(self, signature: str, url: str, params: dict) -> bool:
        """
        Validate Twilio webhook signature.
        
        Args:
            signature: X-Twilio-Signature header
            url: Webhook URL
            params: Form parameters
            
        Returns:
            bool: True if signature valid
        """
        if not self._initialized:
            return True  # Skip validation in mock mode
        
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(self.auth_token)
            return validator.validate(url, params, signature)
        except Exception as e:
            logger.error(f"Webhook validation error: {e}")
            return False
    
    async def process_webhook(self, form_data: dict) -> dict:
        """
        Process incoming WhatsApp message from Twilio webhook.
        
        Args:
            form_data: Twilio form data
            
        Returns:
            dict with message details
        """
        try:
            message_data = {
                'channel': 'whatsapp',
                'channel_message_id': form_data.get('MessageSid'),
                'customer_phone': form_data.get('From', '').replace('whatsapp:', ''),
                'content': form_data.get('Body', ''),
                'received_at': datetime.utcnow().isoformat(),
                'metadata': {
                    'num_media': form_data.get('NumMedia', '0'),
                    'profile_name': form_data.get('ProfileName'),
                    'wa_id': form_data.get('WaId')
                }
            }
            
            logger.info(f"Received WhatsApp message from {message_data['customer_phone']}")
            logger.info(f"Content: {message_data['content'][:100]}...")
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {e}")
            return {}
    
    async def send_message(self, to_phone: str, body: str) -> dict:
        """
        Send WhatsApp message via Twilio.
        
        Args:
            to_phone: Recipient phone number (with country code)
            body: Message text
            
        Returns:
            dict with delivery status
        """
        try:
            # Ensure phone number is in WhatsApp format
            if not to_phone.startswith('whatsapp:'):
                to_phone = f'whatsapp:{to_phone}'
            
            if self._initialized and self.client:
                # Send via Twilio API
                message = self.client.messages.create(
                    body=body,
                    from_=self.whatsapp_number,
                    to=to_phone
                )
                
                logger.info(f"Sent WhatsApp message to {to_phone}: {message.sid}")
                
                return {
                    'channel_message_id': message.sid,
                    'delivery_status': message.status,
                    'sent_at': datetime.utcnow().isoformat()
                }
            else:
                # Mock mode - log and return success
                logger.info(f"[MOCK] Sending WhatsApp to {to_phone}")
                logger.info(f"Body: {body[:200]}...")
                
                return {
                    'channel_message_id': f"mock_{datetime.utcnow().timestamp()}",
                    'delivery_status': 'sent',
                    'sent_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return {
                'channel_message_id': None,
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    def format_response(self, response: str, max_length: int = 1600) -> list:
        """
        Format and split response for WhatsApp (max 1600 chars per message).
        
        Args:
            response: Response text
            max_length: Maximum characters per message
            
        Returns:
            list of message strings
        """
        if len(response) <= max_length:
            return [response]
        
        # Split into multiple messages
        messages = []
        while response:
            if len(response) <= max_length:
                messages.append(response)
                break
            
            # Find a good break point
            break_point = response.rfind('. ', 0, max_length)
            if break_point == -1:
                break_point = response.rfind(' ', 0, max_length)
            if break_point == -1:
                break_point = max_length
            
            messages.append(response[:break_point + 1].strip())
            response = response[break_point + 1:].strip()
        
        return messages
    
    async def update_delivery_status(self, message_sid: str, status: str) -> bool:
        """
        Update message delivery status.
        
        Args:
            message_sid: Twilio message SID
            status: Delivery status (sent, delivered, read, failed)
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # In production, update database with status
            logger.info(f"Message {message_sid} status: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating delivery status: {e}")
            return False
