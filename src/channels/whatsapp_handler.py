"""
WhatsApp Channel Handler - Real Twilio Integration
CRM Digital FTE - Hackathon 5
"""

import os
import logging
from typing import Optional
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

# Twilio config from environment
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

router = APIRouter(tags=["whatsapp"])


def get_twilio_client() -> Optional[Client]:
    """Get real Twilio client."""
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return None


def validate_twilio_signature(request_url: str, post_params: dict, signature: str) -> bool:
    """Validate that request is from Twilio."""
    if not TWILIO_AUTH_TOKEN:
        logger.warning("No auth token - skipping validation in dev mode")
        return True
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    return validator.validate(request_url, post_params, signature)


def parse_whatsapp_message(form_data: dict) -> dict:
    """
    Parse incoming WhatsApp webhook from Twilio.
    Returns normalized message dict.
    """
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    body = form_data.get("Body", "").strip()
    message_sid = form_data.get("MessageSid", "")

    # Clean phone number for customer identifier
    # whatsapp:+923001234567 -> +923001234567
    customer_phone = from_number.replace("whatsapp:", "").strip()

    logger.info(f"WhatsApp message from {customer_phone}: {body[:50]}...")

    return {
        "customer_phone": customer_phone,
        "from_number": from_number,
        "to_number": to_number,
        "message": body,
        "message_sid": message_sid,
        "channel": "whatsapp",
        "raw": form_data
    }


def build_twiml_response(response_text: str) -> str:
    """Build TwiML response for Twilio."""
    resp = MessagingResponse()

    # WhatsApp limit is 1600 chars per message
    if len(response_text) > 1600:
        # Split into multiple messages
        chunks = [response_text[i:i + 1600] for i in range(0, len(response_text), 1600)]
        for chunk in chunks[:3]:  # Max 3 messages
            resp.message(chunk)
    else:
        resp.message(response_text)

    return str(resp)


@router.post("/webhooks/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    From: str = Form(default=""),
    To: str = Form(default=""),
    Body: str = Form(default=""),
    MessageSid: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    ProfileName: str = Form(default=""),
):
    """
    Real Twilio WhatsApp webhook endpoint.
    Receives messages from WhatsApp Sandbox and processes with CRM Agent.
    """
    try:
        # Get form data for signature validation
        form_data = await request.form()
        form_dict = dict(form_data)

        # Validate Twilio signature (skip in dev)
        twilio_signature = request.headers.get("X-Twilio-Signature", "")
        request_url = str(request.url)

        # In production, uncomment this:
        # if not validate_twilio_signature(request_url, form_dict, twilio_signature):
        #     logger.warning("Invalid Twilio signature")
        #     return PlainTextResponse("Invalid signature", status_code=403)

        # Parse message
        message_data = parse_whatsapp_message(form_dict)
        customer_phone = message_data["customer_phone"]
        message_body = message_data["message"]

        if not message_body:
            logger.warning(f"Empty message from {customer_phone}")
            resp = MessagingResponse()
            resp.message("I received your message but it appears to be empty. How can I help you?")
            return PlainTextResponse(str(resp), media_type="application/xml")

        # Log the incoming message
        logger.info(f"Processing WhatsApp from {customer_phone}: {message_body}")

        # Import and call agent
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from agent.crm_agent import process_message

        # Process with real CRM Agent
        result = process_message(
            customer_email=customer_phone,  # Use phone as identifier
            message=message_body,
            channel="whatsapp",
            customer_name=ProfileName or None
        )

        agent_response = result.get("response", "Our team will assist you shortly.")
        ticket_id = result.get("ticket_id", "")
        escalated = result.get("escalated", False)

        logger.info(f"Agent response for {customer_phone}: ticket={ticket_id}, escalated={escalated}")

        # Build TwiML response
        twiml = build_twiml_response(agent_response)

        return PlainTextResponse(twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)

        # Always return valid TwiML even on error
        resp = MessagingResponse()
        resp.message("We received your message and will respond shortly.")
        return PlainTextResponse(str(resp), media_type="application/xml")


def send_whatsapp_message(to_number: str, body: str) -> dict:
    """
    Send WhatsApp message proactively via Twilio.
    Used for follow-ups or notifications.
    """
    try:
        client = get_twilio_client()
        if not client:
            logger.warning("Twilio client not available")
            return {"success": False, "error": "Twilio not configured"}

        # Ensure WhatsApp format
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        from_number = TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )

        logger.info(f"WhatsApp sent to {to_number}: SID={message.sid}")
        return {
            "success": True,
            "message_sid": message.sid,
            "status": message.status
        }

    except Exception as e:
        logger.error(f"Send WhatsApp error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Quick test
    result = send_whatsapp_message("+923001234567", "Test from CRM FTE!")
    print(result)
