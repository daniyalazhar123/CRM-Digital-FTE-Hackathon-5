"""
CRM Digital FTE - WhatsApp Handler (Production)
Feature 3: Real WhatsApp Webhook with Twilio Signature Validation

Handles WhatsApp webhook notifications via Twilio API.
Supports signature validation, media messages, and response splitting.
"""

import os
import hashlib
import hmac
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, parse_qs
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

    async def validate_webhook_signature(self, request_url: str, request_body: dict, 
                                          signature: str) -> bool:
        """
        Validate Twilio webhook signature.

        Twilio signs requests with X-Twilio-Signature header.
        Algorithm: HMAC-SHA1 of URL + sorted params, using auth token.

        Args:
            request_url: Full URL of the webhook (including query params)
            request_body: Form data from request
            signature: X-Twilio-Signature header value

        Returns:
            bool: True if signature is valid
        """
        if not self.auth_token:
            logger.warning("No auth token for signature validation")
            return True  # Skip validation in mock mode

        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(self.auth_token)
            
            # Convert body dict to format Twilio expects
            params = {k: v for k, v in request_body.items()}
            
            is_valid = validator.validate(request_url, params, signature)
            
            if not is_valid:
                logger.warning(f"Invalid Twilio signature for {request_url}")
            
            return is_valid
            
        except ImportError:
            logger.warning("Twilio library not installed, skipping validation")
            return True
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False

    def validate_webhook_signature_manual(self, request_url: str, params: dict, 
                                           signature: str) -> bool:
        """
        Manual signature validation (fallback if Twilio lib not available).

        Args:
            request_url: Full webhook URL
            params: Request parameters
            signature: Expected signature

        Returns:
            bool: True if valid
        """
        try:
            # Parse URL to get base URL without query string
            parsed = urlparse(request_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Sort parameters by key
            sorted_params = sorted(params.items())
            
            # Build signature string: URL + sorted params
            sig_string = base_url
            for key, value in sorted_params:
                sig_string += key + value
            
            # Calculate HMAC-SHA1
            expected_sig = hmac.new(
                self.auth_token.encode('utf-8'),
                sig_string.encode('utf-8'),
                hashlib.sha1
            ).digest()
            
            # Base64 encode
            import base64
            expected_sig_b64 = base64.b64encode(expected_sig).decode('utf-8')
            
            # Compare
            return hmac.compare_digest(signature, expected_sig_b64)
            
        except Exception as e:
            logger.error(f"Manual signature validation error: {e}")
            return False

    async def process_webhook(self, form_data: dict) -> dict:
        """
        Process incoming WhatsApp message from Twilio webhook.

        Twilio webhook format:
        - From: whatsapp:+1234567890
        - To: whatsapp:+14155238886
        - Body: Message text
        - MessageSid: Unique message ID
        - NumMedia: Number of attached media
        - ProfileName: Sender's WhatsApp name

        Args:
            form_data: Twilio form data

        Returns:
            dict with message details
        """
        try:
            # Extract phone number (remove 'whatsapp:' prefix)
            from_number = form_data.get('From', '')
            customer_phone = from_number.replace('whatsapp:', '')
            
            # Extract message content
            message_body = form_data.get('Body', '')
            
            # Check for media attachments
            num_media = int(form_data.get('NumMedia', '0'))
            media_urls = []
            
            if num_media > 0:
                # Twilio provides MediaUrl0, MediaUrl1, etc.
                for i in range(num_media):
                    media_key = f'MediaUrl{i}'
                    if media_key in form_data:
                        media_urls.append(form_data[media_key])
                
                logger.info(f"Message has {num_media} media attachments")
            
            # Build message data
            message_data = {
                'channel': 'whatsapp',
                'channel_message_id': form_data.get('MessageSid'),
                'customer_phone': customer_phone,
                'content': message_body,
                'received_at': datetime.utcnow().isoformat(),
                'metadata': {
                    'num_media': num_media,
                    'media_urls': media_urls,
                    'profile_name': form_data.get('ProfileName'),
                    'wa_id': form_data.get('WaId'),
                    'to': form_data.get('To'),
                    'from': from_number
                }
            }

            logger.info(f"Received WhatsApp message from {customer_phone}")
            logger.info(f"Content: {message_body[:100]}...")
            
            if media_urls:
                logger.info(f"Media URLs: {media_urls}")

            return message_data

        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {e}")
            return {}

    async def send_message(self, to_phone: str, body: str, 
                           media_url: str = None) -> dict:
        """
        Send WhatsApp message via Twilio.

        Args:
            to_phone: Recipient phone number (with country code)
            body: Message text
            media_url: Optional media URL (image, video, etc.)

        Returns:
            dict with delivery status
        """
        try:
            # Ensure phone number is in WhatsApp format
            if not to_phone.startswith('whatsapp:'):
                to_phone = f'whatsapp:{to_phone}'

            if self._initialized and self.client:
                # Build message parameters
                message_params = {
                    'body': body,
                    'from_': self.whatsapp_number,
                    'to': to_phone
                }
                
                # Add media if provided
                if media_url:
                    message_params['media_url'] = media_url
                
                # Send via Twilio API
                message = self.client.messages.create(**message_params)

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
                if media_url:
                    logger.info(f"Media: {media_url}")

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

    def format_response_for_whatsapp(self, response: str,
                                      max_length: int = 1600) -> List[str]:
        """
        Format and split response for WhatsApp (max 1600 chars per message).

        WhatsApp limits:
        - Text messages: 1600 characters
        - If longer, split into multiple messages at sentence boundaries

        Args:
            response: Response text
            max_length: Maximum characters per message (default 1600)

        Returns:
            list of message strings
        """
        if len(response) <= max_length:
            return [response]

        messages = []
        remaining = response

        while remaining:
            if len(remaining) <= max_length:
                messages.append(remaining)
                break

            # Find a good break point (sentence boundary)
            break_point = remaining.rfind('. ', 0, max_length)

            if break_point == -1:
                # Try space
                break_point = remaining.rfind(' ', 0, max_length)

            if break_point == -1:
                # No good break point, hard cut
                break_point = max_length - 1

            # Ensure we don't exceed max_length
            messages.append(remaining[:break_point].strip())
            remaining = remaining[break_point:].strip()

        logger.info(f"Split response into {len(messages)} messages")
        return messages

    async def send_twiML_response(self, message: str) -> str:
        """
        Generate TwiML response for WhatsApp.

        TwiML format:
        <?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Message>message text</Message>
        </Response>

        Args:
            message: Message text to send

        Returns:
            str: TwiML XML response
        """
        # Split long messages
        message_parts = self.format_response_for_whatsapp(message)
        
        # Build TwiML
        twiml = '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n'
        
        for part in message_parts:
            # Escape XML special characters
            escaped = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            twiml += f'  <Message>{escaped}</Message>\n'
        
        twiml += '</Response>'
        
        return twiml

    async def update_delivery_status(self, message_sid: str, status: str) -> bool:
        """
        Update message delivery status.

        Status values:
        - queued: Message received by Twilio
        - sent: Message sent to carrier
        - delivered: Message delivered to recipient
        - read: Message read by recipient (if enabled)
        - failed: Message failed to send

        Args:
            message_sid: Twilio message SID
            status: Delivery status

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

    async def get_message_status(self, message_sid: str) -> Optional[str]:
        """
        Get message delivery status from Twilio.

        Args:
            message_sid: Twilio message SID

        Returns:
            str: Status or None if not found
        """
        try:
            if self._initialized and self.client:
                message = self.client.messages(message_sid).fetch()
                return message.status
            return None
        except Exception as e:
            logger.error(f"Error getting message status: {e}")
            return None
