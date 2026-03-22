"""
CRM Digital FTE - Gmail Handler
Phase 2: Specialization — Step 7

Handles Gmail webhook notifications and sends replies via Gmail API.
"""

import base64
import email
from email.mime.text import MIMEText
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GmailHandler:
    """Handler for Gmail API integration."""
    
    def __init__(self, credentials_path: str = None):
        """
        Initialize Gmail handler.
        
        Args:
            credentials_path: Path to Gmail API credentials JSON
        """
        self.credentials_path = credentials_path
        self.service = None
        self._authenticated = False
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            bool: True if authentication successful
        """
        try:
            # In production, implement OAuth2 flow here
            # For now, return True for testing
            logger.info("Gmail authentication configured")
            self._authenticated = True
            return True
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    async def process_webhook(self, payload: dict) -> List[dict]:
        """
        Process Gmail Pub/Sub webhook notification.
        
        Args:
            payload: Pub/Sub message payload
            
        Returns:
            List of message dictionaries
        """
        try:
            # Decode Pub/Sub message
            if 'message' in payload:
                data = payload['message'].get('data', '')
                if data:
                    decoded = base64.b64decode(data).decode('utf-8')
                    logger.info(f"Received Gmail notification: {decoded}")
            
            # In production, fetch actual messages from Gmail API
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error processing Gmail webhook: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Optional[dict]:
        """
        Fetch a Gmail message by ID.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            dict with email details or None
        """
        try:
            if not self._authenticated:
                await self.authenticate()
            
            # In production, call Gmail API:
            # message = self.service.users().messages().get(
            #     userId='me', id=message_id, format='full'
            # ).execute()
            
            # For testing, return mock data
            return {
                'channel': 'email',
                'channel_message_id': message_id,
                'customer_email': 'test@example.com',
                'subject': 'Test Subject',
                'content': 'Test message content',
                'received_at': datetime.utcnow().isoformat(),
                'thread_id': None
            }
            
        except Exception as e:
            logger.error(f"Error fetching Gmail message: {e}")
            return None
    
    async def send_reply(self, to_email: str, subject: str, body: str, 
                         thread_id: str = None) -> dict:
        """
        Send email reply via Gmail API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Optional Gmail thread ID for threading
            
        Returns:
            dict with delivery status
        """
        try:
            if not self._authenticated:
                await self.authenticate()
            
            # Create MIME message
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
            
            # In production, encode and send via Gmail API:
            # raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            # result = self.service.users().messages().send(
            #     userId='me', body={'raw': raw, 'threadId': thread_id}
            # ).execute()
            
            # For testing, log and return success
            logger.info(f"Sending Gmail reply to {to_email}: {subject}")
            logger.info(f"Body: {body[:200]}...")
            
            return {
                'channel_message_id': f"mock_{datetime.utcnow().timestamp()}",
                'delivery_status': 'sent',
                'thread_id': thread_id
            }
            
        except Exception as e:
            logger.error(f"Error sending Gmail reply: {e}")
            return {
                'channel_message_id': None,
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    def _extract_body(self, payload: dict) -> str:
        """
        Extract text body from Gmail message payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            str: Message body text
        """
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        return ''
    
    def _extract_email(self, from_header: str) -> str:
        """
        Extract email address from From header.
        
        Args:
            from_header: From header string
            
        Returns:
            str: Email address
        """
        import re
        match = re.search(r'<(.+?)>', from_header)
        return match.group(1) if match else from_header
