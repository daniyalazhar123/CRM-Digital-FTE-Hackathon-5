"""
Gmail Handler - Fixed Version
Uses Gmail API via service account OR OAuth credentials.
Replace dummy auth with real implementation.
"""

import os
import json
import base64
import logging
from email.mime.text import MIMEText
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gmail"])

# ── Auth ────────────────────────────────────────────────────────────────────────
def _get_gmail_service():
    """
    Returns authenticated Gmail API service.
    Priority:
      1. GMAIL_SERVICE_ACCOUNT_JSON env var (JSON string of service account key)
      2. GMAIL_SERVICE_ACCOUNT_FILE env var (path to JSON file)
      3. OAuth credentials (GMAIL_CREDENTIALS_FILE)
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GRequest
        import google.oauth2.credentials

        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        DELEGATED_EMAIL = os.getenv("GMAIL_DELEGATED_EMAIL", "")

        # Option 1: Service account JSON as env variable
        sa_json_str = os.getenv("GMAIL_SERVICE_ACCOUNT_JSON", "")
        if sa_json_str:
            sa_info = json.loads(sa_json_str)
            credentials = service_account.Credentials.from_service_account_info(
                sa_info, scopes=SCOPES
            )
            if DELEGATED_EMAIL:
                credentials = credentials.with_subject(DELEGATED_EMAIL)
            return build('gmail', 'v1', credentials=credentials)

        # Option 2: Service account file path
        sa_file = os.getenv("GMAIL_SERVICE_ACCOUNT_FILE", "")
        if sa_file and os.path.exists(sa_file):
            credentials = service_account.Credentials.from_service_account_file(
                sa_file, scopes=SCOPES
            )
            if DELEGATED_EMAIL:
                credentials = credentials.with_subject(DELEGATED_EMAIL)
            return build('gmail', 'v1', credentials=credentials)

        # Option 3: OAuth token file
        token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")
        creds_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        if os.path.exists(token_file):
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                token_file, SCOPES
            )
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GRequest())
            return build('gmail', 'v1', credentials=creds)

        logger.error("No Gmail credentials configured. Set GMAIL_SERVICE_ACCOUNT_JSON or GMAIL_SERVICE_ACCOUNT_FILE in .env")
        return None

    except ImportError:
        logger.error("google-api-python-client not installed. Run: pip install google-api-python-client google-auth")
        return None
    except Exception as e:
        logger.error(f"Gmail auth error: {e}")
        return None


# ── Webhook ─────────────────────────────────────────────────────────────────────
@router.post("/webhooks/gmail")
async def gmail_webhook(request: Request):
    """
    Receives Gmail push notifications via Google Pub/Sub.
    Setup: https://developers.google.com/gmail/api/guides/push
    """
    try:
        body = await request.json()
        # Pub/Sub message is base64-encoded
        pubsub_message = body.get("message", {})
        if not pubsub_message:
            return JSONResponse({"status": "no message"})

        data_b64 = pubsub_message.get("data", "")
        if data_b64:
            data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
            email_address = data.get("emailAddress", "")
            history_id    = data.get("historyId", "")
            logger.info(f"Gmail push: email={email_address}, historyId={history_id}")

            # Process new emails
            await _process_new_emails(email_address, history_id)

        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)


async def _process_new_emails(email_address: str, history_id: str):
    """Fetch and process new emails from Gmail."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_process_emails, email_address, history_id)


def _sync_process_emails(email_address: str, history_id: str):
    service = _get_gmail_service()
    if not service:
        logger.error("Gmail service not available — check credentials")
        return

    try:
        # List unread messages
        results = service.users().messages().list(
            userId='me',
            q='is:unread label:inbox',
            maxResults=10
        ).execute()

        messages = results.get('messages', [])
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId='me',
                id=msg_ref['id'],
                format='full'
            ).execute()
            _handle_email(service, msg)

    except Exception as e:
        logger.error(f"Email processing error: {e}")


def _handle_email(service, msg: dict):
    """Extract email data and route through CRM agent."""
    try:
        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
        sender   = headers.get('From', '')
        subject  = headers.get('Subject', '')
        msg_id   = msg.get('id', '')

        # Extract body
        body_text = _extract_body(msg['payload'])
        if not body_text:
            return

        logger.info(f"Processing email from {sender}: {subject}")

        # Route through CRM agent
        import sys, os as _os
        sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
        from agent.crm_agent import process_message

        # Extract email address from "Name <email>" format
        import re
        email_match = re.search(r'<(.+?)>', sender)
        customer_email = email_match.group(1) if email_match else sender

        result = process_message(
            customer_email=customer_email,
            message=body_text,
            channel="email",
            customer_name=sender.split('<')[0].strip() if '<' in sender else None
        )

        # Send reply
        reply_text = result.get("response", "")
        if reply_text:
            _send_reply(service, msg_id, sender, subject, reply_text)

        # Mark as read
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

    except Exception as e:
        logger.error(f"Email handling error: {e}")


def _extract_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    for part in payload.get('parts', []):
        text = _extract_body(part)
        if text:
            return text
    return ""


def _send_reply(service, original_msg_id: str, to: str, subject: str, body: str):
    """Send email reply via Gmail API."""
    try:
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"

        mime_msg = MIMEText(body)
        mime_msg['to']      = to
        mime_msg['subject'] = subject

        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
        service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': original_msg_id}
        ).execute()
        logger.info(f"Email reply sent to {to}")
    except Exception as e:
        logger.error(f"Email send error: {e}")