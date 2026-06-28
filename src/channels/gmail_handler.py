"""
Gmail Handler — Production Pipeline
Step 2 Final Implementation

OAuth → Read Unread → Skip Duplicates → process_message() → Send Reply → Mark Read
"""

import os
import json
import base64
import logging
import time
import re
import asyncio
from email.mime.text import MIMEText
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gmail"])

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from db.database import CRMDatabase
from agent.crm_agent import process_message

from cache.redis_client import get_cache
from workers.kafka_producer import publish_to_kafka, KafkaTopics
from workers.metrics_collector import get_metrics_store

db = CRMDatabase()

# ── Retry Logic ─────────────────────────────────────────────────────────────────

def _execute_with_retry(request, max_retries=3, base_delay=1.0, backoff=2.0):
    """Execute a Google API request with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return request.execute()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (backoff ** attempt)
                logger.warning(
                    "[GMAIL] API retry %d/%d after %.1fs: %s",
                    attempt + 1, max_retries, delay, e
                )
                time.sleep(delay)
            else:
                logger.error(
                    "[GMAIL] API failed after %d retries: %s", max_retries, e
                )
                raise


# ── Auth ────────────────────────────────────────────────────────────────────────

def _get_gmail_service():
    """
    Returns authenticated Gmail API service.
    Priority:
      1. GMAIL_SERVICE_ACCOUNT_JSON (JSON string)
      2. GMAIL_SERVICE_ACCOUNT_FILE (path to JSON)
      3. OAuth token.json + credentials.json
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
        if os.path.exists(token_file):
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                token_file, SCOPES
            )
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GRequest())
            return build('gmail', 'v1', credentials=creds)

        logger.error(
            "No Gmail credentials configured. "
            "Set GMAIL_SERVICE_ACCOUNT_JSON, GMAIL_SERVICE_ACCOUNT_FILE, "
            "or ensure token.json and credentials.json exist."
        )
        return None

    except ImportError:
        logger.error(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client google-auth"
        )
        return None
    except Exception as e:
        logger.error(f"Gmail auth error: {e}")
        return None


# ── Webhook Endpoint ────────────────────────────────────────────────────────────

@router.post("/webhooks/gmail")
async def gmail_webhook(request: Request):
    """Receives Gmail push notifications via Google Pub/Sub."""
    try:
        body = await request.json()
        pubsub_message = body.get("message", {})
        if not pubsub_message:
            return JSONResponse({"status": "no message"})

        data_b64 = pubsub_message.get("data", "")
        if data_b64:
            data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
            email_address = data.get("emailAddress", "")
            history_id    = data.get("historyId", "")
            logger.info(f"Gmail push: email={email_address}, historyId={history_id}")
            await _process_new_emails(email_address, history_id)

        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)


async def _process_new_emails(email_address: str, history_id: str):
    """Fetch and process new emails from Gmail (runs sync code in executor)."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_process_emails, email_address, history_id)


# ── Core Email Processing ───────────────────────────────────────────────────────

def _sync_process_emails(email_address: str, history_id: str):
    """Synchronously fetch all unread inbox messages and process each."""
    service = _get_gmail_service()
    if not service:
        logger.error("Gmail service not available — check credentials")
        return

    try:
        results = _execute_with_retry(
            service.users().messages().list(
                userId='me',
                q='is:unread label:inbox',
                maxResults=10
            )
        )
        messages = results.get('messages', [])
        if not messages:
            logger.info("[GMAIL] No unread messages found")
            return

        logger.info("[GMAIL] Reading message" if len(messages) == 1
                    else f"[GMAIL] Found {len(messages)} unread message(s)")

        for msg_ref in messages:
            msg = _execute_with_retry(
                service.users().messages().get(
                    userId='me',
                    id=msg_ref['id'],
                    format='full'
                )
            )
            _handle_email(service, msg)

    except Exception as e:
        logger.error(f"[GMAIL] Sync processing error: {e}")


def _extract_email_data(msg: dict) -> Optional[dict]:
    """Extract required fields from a Gmail message.

    Returns dict with: msg_id, thread_id, sender, customer_email, subject, body
    or None if extraction fails.
    """
    try:
        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
        msg_id = msg.get('id', '')
        thread_id = msg.get('threadId', '')
        sender = headers.get('From', '')
        subject = headers.get('Subject', '(no subject)')

        body = _extract_body(msg['payload'])
        if not body:
            logger.warning(f"[GMAIL] No plain-text body in message {msg_id}")
            return None

        email_match = re.search(r'<(.+?)>', sender)
        customer_email = email_match.group(1) if email_match else sender

        return {
            "msg_id": msg_id,
            "thread_id": thread_id,
            "sender": sender,
            "customer_email": customer_email,
            "subject": subject,
            "body": body,
        }
    except Exception as e:
        logger.error(f"[GMAIL] Extract error: {e}")
        return None


def _handle_email(service, msg: dict):
    """Core per-message pipeline:
       1. Extract fields
       2. Skip if duplicate (processed_emails table)
       3. Call process_message()
       4. Send AI reply via Gmail API
       5. Mark as READ
       6. Mark as processed
    """
    logger.info("[GMAIL] Reading message")

    email_data = _extract_email_data(msg)
    if not email_data:
        return

    # ── Skip duplicates ─────────────────────────────────────────────────────
    if db.is_email_processed(email_data["msg_id"]):
        logger.info(f"[GMAIL] Skipping duplicate {email_data['msg_id']}")
        return

    # ── Process via CRM Agent ───────────────────────────────────────────────
    logger.info(f"[GMAIL] Processing message {email_data['msg_id']} from {email_data['customer_email']}")

    customer_name = None
    if '<' in email_data["sender"]:
        customer_name = email_data["sender"].split('<')[0].strip()
        if not customer_name:
            customer_name = None

    result = process_message(
        customer_email=email_data["customer_email"],
        message=email_data["body"],
        channel="email",
        customer_name=customer_name,
    )

    reply_text = result.get("response", "")
    if not reply_text:
        logger.warning(f"[GMAIL] Empty AI response for {email_data['msg_id']}")
    else:
        # ── Send AI reply ───────────────────────────────────────────────────
        logger.info(f"[GMAIL] Sending reply to {email_data['customer_email']}")
        _send_reply(
            service,
            thread_id=email_data["thread_id"],
            to=email_data["sender"],
            subject=email_data["subject"],
            body=reply_text,
        )

    # ── Mark as READ ────────────────────────────────────────────────────────
    logger.info(f"[GMAIL] Marking read {email_data['msg_id']}")
    _execute_with_retry(
        service.users().messages().modify(
            userId='me',
            id=email_data["msg_id"],
            body={'removeLabelIds': ['UNREAD']},
        )
    )

    # ── Record as processed ─────────────────────────────────────────────────
    db.mark_email_processed(email_data["msg_id"])

    # ── Publish to Kafka ────────────────────────────────────────────────────
    publish_to_kafka(KafkaTopics.EMAIL_RECEIVED, {
        "event_type": "email_received",
        "msg_id": email_data["msg_id"],
        "thread_id": email_data["thread_id"],
        "customer_email": email_data["customer_email"],
        "subject": email_data["subject"],
        "channel": "email",
    })
    if result.get("ticket_id"):
        publish_to_kafka(KafkaTopics.TICKET_CREATED, {
            "event_type": "ticket_created",
            "ticket_id": result["ticket_id"],
            "customer_email": email_data["customer_email"],
            "channel": "email",
        })

    logger.info(f"[GMAIL] Message {email_data['msg_id']} processed successfully")


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text from a Gmail message payload."""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    for part in payload.get('parts', []):
        text = _extract_body(part)
        if text:
            return text
    return ""


def _send_reply(service, thread_id: str, to: str, subject: str, body: str):
    """Send an email reply threaded to the original message via Gmail API."""
    if not subject.lower().startswith('re:'):
        subject = f"Re: {subject}"

    mime_msg = MIMEText(body)
    mime_msg['to'] = to
    mime_msg['subject'] = subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
    _execute_with_retry(
        service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': thread_id},
        )
    )
    logger.info(f"[GMAIL] Reply sent to {to}")
