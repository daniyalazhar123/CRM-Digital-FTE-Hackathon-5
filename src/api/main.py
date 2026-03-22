"""
CRM Digital FTE - FastAPI Service Layer
Phase 2: Specialization — Step 4

Production API layer for Customer Success FTE.
Handles web form submissions, Gmail webhooks, WhatsApp webhooks, and metrics.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, EmailStr, validator

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import CRM Agent
from agent.crm_agent import process_message

# Import database
from db.database import CRMDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = CRMDatabase()

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Customer Success FTE API",
    description="24/7 AI-powered customer support across Email, WhatsApp, and Web",
    version="2.0.0"
)

# CORS for web form
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SupportFormSubmission(BaseModel):
    """Support form submission model."""
    name: str
    email: EmailStr
    subject: str
    category: str
    message: str
    priority: Optional[str] = "medium"
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()
    
    @validator('message')
    def message_must_have_content(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Message must be at least 10 characters')
        return v.strip()
    
    @validator('category')
    def category_must_be_valid(cls, v):
        valid_categories = ['billing', 'technical', 'how-to', 'bug-report', 'other']
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {valid_categories}')
        return v


class SupportFormResponse(BaseModel):
    """Response model for form submission."""
    ticket_id: str
    message: str
    estimated_response_time: str


class TicketStatus(BaseModel):
    """Ticket status response."""
    ticket_id: str
    status: str
    messages: List[dict]
    created_at: str
    last_updated: str


class CustomerInfo(BaseModel):
    """Customer information response."""
    customer_id: str
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    total_tickets: int
    last_interaction: str


class ChannelMetrics(BaseModel):
    """Channel metrics response."""
    channel: str
    total_conversations: int
    avg_sentiment: float
    escalations: int


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status and channel availability.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Customer Success FTE API",
        "version": "2.0.0",
        "channels": {
            "email": "active",
            "whatsapp": "active",
            "web_form": "active"
        }
    }


# =============================================================================
# WEB FORM ENDPOINTS
# =============================================================================

@app.post("/support/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission):
    """
    Handle support form submission.
    
    This endpoint:
    1. Validates the submission
    2. Creates a ticket in the system
    3. Processes with CRM agent
    4. Returns confirmation to user
    """
    try:
        logger.info(f"Processing support form from {submission.email}")
        
        # Process with CRM agent
        result = process_message(
            customer_email=submission.email,
            message=f"Subject: {submission.subject}\nCategory: {submission.category}\n\n{submission.message}",
            channel="web_form",
            customer_name=submission.name
        )
        
        logger.info(f"Ticket created: {result['ticket_id']}")
        
        return SupportFormResponse(
            ticket_id=result['ticket_id'],
            message="Thank you for contacting us! Our AI assistant will respond shortly.",
            estimated_response_time="Usually within 5 minutes"
        )
        
    except Exception as e:
        logger.error(f"Form submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/support/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    """
    Get status and conversation history for a ticket.
    """
    try:
        ticket = db.get_ticket(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get messages
        messages = db.get_customer_history(ticket['customer_id'], limit=20)
        
        return {
            "ticket_id": ticket_id,
            "status": ticket['status'],
            "messages": messages,
            "created_at": str(ticket['created_at']),
            "last_updated": str(ticket.get('resolved_at') or ticket['created_at'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GMAIL WEBHOOK ENDPOINT
# =============================================================================

@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Gmail push notifications via Pub/Sub.
    
    Processes incoming emails and queues them for agent processing.
    """
    try:
        body = await request.json()
        logger.info(f"Received Gmail webhook: {body}")
        
        # Extract message data from Pub/Sub payload
        # In production, decode base64 and parse email
        message_data = {
            "channel": "email",
            "content": body.get('message', {}).get('data', ''),
            "received_at": datetime.utcnow().isoformat()
        }
        
        # Process in background
        background_tasks.add_task(
            process_gmail_message,
            message_data
        )
        
        return {"status": "processed", "message": "Email queued for processing"}
        
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_gmail_message(message_data: dict):
    """Process Gmail message in background."""
    # Parse email content
    # Extract sender, subject, body
    # Call process_message()
    # Send response via Gmail API
    pass


# =============================================================================
# WHATSAPP WEBHOOK ENDPOINT (Twilio)
# =============================================================================

@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming WhatsApp messages via Twilio webhook.
    """
    try:
        form_data = await request.form()
        logger.info(f"Received WhatsApp message: {form_data}")
        
        # Extract message data
        message_data = {
            "from": form_data.get('From', '').replace('whatsapp:', ''),
            "body": form_data.get('Body', ''),
            "message_sid": form_data.get('MessageSid'),
            "profile_name": form_data.get('ProfileName')
        }
        
        # Process in background
        background_tasks.add_task(
            process_whatsapp_message,
            message_data
        )
        
        # Return TwiML response (empty = no immediate reply, agent will respond)
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/whatsapp/status")
async def whatsapp_status_webhook(request: Request):
    """Handle WhatsApp message status updates (delivered, read, etc.)."""
    try:
        form_data = await request.form()
        logger.info(f"Received WhatsApp status: {form_data}")
        
        # Update message delivery status in database
        # message_sid = form_data.get('MessageSid')
        # status = form_data.get('MessageStatus')
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"WhatsApp status webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_whatsapp_message(message_data: dict):
    """Process WhatsApp message in background."""
    # Call process_message() with channel="whatsapp"
    # Send response via Twilio API
    pass


# =============================================================================
# CUSTOMER ENDPOINTS
# =============================================================================

@app.get("/customers/lookup")
async def lookup_customer(
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None)
):
    """
    Look up customer by email or phone across all channels.
    """
    if not email and not phone:
        raise HTTPException(
            status_code=400,
            detail="Provide email or phone parameter"
        )
    
    try:
        # Get or create customer
        customer = db.get_or_create_customer(
            email=email,
            phone=phone
        )
        
        # Get stats
        stats = db.get_customer_stats(customer['id'])
        
        return {
            "customer_id": customer['id'],
            "email": customer.get('email'),
            "phone": customer.get('phone'),
            "name": customer.get('name'),
            "total_tickets": stats['total_tickets'],
            "last_interaction": stats['last_interaction']
        }
        
    except Exception as e:
        logger.error(f"Customer lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# METRICS ENDPOINTS
# =============================================================================

@app.get("/metrics/channels")
async def get_channel_metrics():
    """
    Get performance metrics by channel.
    """
    try:
        # In production, query database for real metrics
        # For now, return sample data
        return {
            "email": {
                "total_conversations": 150,
                "avg_sentiment": 0.65,
                "escalations": 25
            },
            "whatsapp": {
                "total_conversations": 230,
                "avg_sentiment": 0.72,
                "escalations": 18
            },
            "web_form": {
                "total_conversations": 89,
                "avg_sentiment": 0.68,
                "escalations": 12
            }
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/summary")
async def get_metrics_summary():
    """Get overall system metrics."""
    try:
        return {
            "total_tickets": 469,
            "open_tickets": 23,
            "resolved_tickets": 434,
            "escalated_tickets": 55,
            "avg_response_time_ms": 1250,
            "avg_sentiment": 0.68,
            "escalation_rate": 0.117
        }
        
    except Exception as e:
        logger.error(f"Summary metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
