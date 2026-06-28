"""
WhatsApp Channel Handler - Fixed Version
Main fix: process_message sync call in async context using run_in_executor
"""

import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["whatsapp"])

TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

_executor = ThreadPoolExecutor(max_workers=4)


def _run_agent(customer_phone: str, message_body: str, profile_name: str) -> str:
    """Run sync agent in thread pool — avoids blocking async event loop."""
    try:
        import sys, os as _os
        sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
        from agent.crm_agent import process_message

        result = process_message(
            customer_email=customer_phone,
            message=message_body,
            channel="whatsapp",
            customer_name=profile_name or None
        )
        reply = result.get("response", "").strip()
        if not reply:
            reply = "Assalam o alaikum! Aapki request receive ho gayi. Hum jald madad karenge."
        # WhatsApp: 1600 char limit
        if len(reply) > 1600:
            reply = reply[:1597] + "..."
        return reply
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return "Assalam o alaikum! Main Ayesha hoon. Abhi thodi takleef aa rahi hai, thodi der baad dobara try karein."


def _twiml_response(message: str) -> Response:
    """Return properly formatted TwiML XML response."""
    resp = MessagingResponse()
    resp.message(message)
    xml_str = str(resp)
    return Response(content=xml_str, media_type="text/xml; charset=utf-8")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(default=""),
    Body: str = Form(default=""),
    ProfileName: str = Form(default=""),
):
    """
    WhatsApp webhook - Fixed version.
    
    Fix 1: process_message (sync) runs in ThreadPoolExecutor — no more
            'connection already closed' from blocking the async loop.
    Fix 2: Always returns text/xml TwiML so Twilio delivers the reply.
    Fix 3: Empty body handled gracefully.
    """
    customer_phone = From.replace("whatsapp:", "").strip()
    message_body = Body.strip() if Body else ""

    logger.info(f"WhatsApp from {customer_phone}: {message_body[:80]}...")

    if not message_body:
        return _twiml_response(
            "Assalam o alaikum! Main Ayesha hoon. Aapki kya madad kar sakti hoon? 😊"
        )

    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(
        _executor,
        _run_agent,
        customer_phone,
        message_body,
        ProfileName
    )

    logger.info(f"Replied to {customer_phone} ({len(reply)} chars)")
    return _twiml_response(reply)


# ── Proactive send (optional, e.g. for notifications) ──────────────────────────
def send_whatsapp_message(to_number: str, body: str) -> dict:
    """Send a proactive WhatsApp message via Twilio REST API."""
    try:
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            return {"success": False, "error": "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing in .env"}

        client = Client(account_sid, auth_token)

        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        msg = client.messages.create(
            body=body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        logger.info(f"Proactive WhatsApp sent to {to_number}: {msg.sid}")
        return {"success": True, "sid": msg.sid}

    except Exception as e:
        logger.error(f"Proactive send error: {e}")
        return {"success": False, "error": str(e)}