"""
CRM Digital FTE - FastAPI Service Layer
Feature 5: Production API with Prometheus Monitoring

Production API layer for Customer Success FTE.
Handles web form submissions, Gmail webhooks, WhatsApp webhooks, and metrics.
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, EmailStr, validator

# Prometheus monitoring
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = None

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import CRM Agent
from agent.crm_agent import process_message

# Import database
from db.database import CRMDatabase

# Import channel handlers
from channels.web_form_handler import router as web_form_router
from channels.whatsapp_handler import router as whatsapp_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = CRMDatabase()

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Request counters
    REQUEST_COUNT = Counter(
        'api_requests_total',
        'Total API requests',
        ['method', 'endpoint', 'status']
    )
    
    # Request latency histogram
    REQUEST_LATENCY = Histogram(
        'api_request_latency_seconds',
        'API request latency in seconds',
        ['method', 'endpoint'],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # Error counter
    ERROR_COUNT = Counter(
        'api_errors_total',
        'Total API errors',
        ['type', 'endpoint']
    )
    
    # Channel-specific counters
    CHANNEL_MESSAGES = Counter(
        'channel_messages_total',
        'Total messages by channel',
        ['channel']
    )
    
    # Escalation counter
    ESCALATION_COUNT = Counter(
        'escalations_total',
        'Total escalations',
        ['reason']
    )

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Customer Success FTE API",
    description="24/7 AI-powered customer support across Email, WhatsApp, and Web",
    version="2.1.0"
)

# CORS for web form
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include web form router
app.include_router(web_form_router)
app.include_router(whatsapp_router)

# =============================================================================
# PROMETHEUS METRICS ENDPOINT
# =============================================================================

@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    Scraped by Prometheus every 15s.
    """
    if not PROMETHEUS_AVAILABLE:
        return PlainTextResponse("Prometheus client not installed", status_code=503)
    
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# REQUEST TIMING MIDDLEWARE
# =============================================================================

@app.middleware("http")
async def track_requests(request: Request, call_next):
    """
    Middleware to track request metrics.
    
    Records:
    - Request count by method/endpoint/status
    - Request latency
    - Error count
    """
    if not PROMETHEUS_AVAILABLE:
        return await call_next(request)
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Extract endpoint path (remove query params)
    endpoint = request.url.path
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)
    
    # Track errors
    if response.status_code >= 500:
        ERROR_COUNT.labels(
            type="server_error",
            endpoint=endpoint
        ).inc()
    elif response.status_code >= 400:
        ERROR_COUNT.labels(
            type="client_error",
            endpoint=endpoint
        ).inc()
    
    return response


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class CustomerInfo(BaseModel):
    """Customer information response."""
    customer_id: str
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    total_tickets: int
    last_interaction: str


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Customer Success FTE API",
        "version": "2.0.0",
        "channels": {
            "email": "active",
            "whatsapp": "active",
            "web_form": "active"
        }
    }


# =============================================================================
# GMAIL WEBHOOK ENDPOINT
# =============================================================================

@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request):
    """
    Handle Gmail push notifications via Google Cloud Pub/Sub.

    Pub/Sub message format:
    {
        "message": {
            "data": "base64-encoded JSON",
            "attributes": {...}
        },
        "subscription": "..."
    }

    Simple format (for testing):
    {
        "from": "email@example.com",
        "subject": "Subject",
        "body": "Message body"
    }

    Returns 200 OK with ticket_id for successful processing.
    """
    try:
        body = await request.json()
        logger.info(f"Received Gmail webhook: {body}")

        # Check if this is simple format (direct email data)
        if 'from' in body or 'From' in body:
            # Simple format - process directly
            from_email = body.get('from', body.get('From', ''))
            subject = body.get('subject', body.get('Subject', ''))
            msg_body = body.get('body', body.get('Body', body.get('text', '')))
            
            if not from_email:
                return {
                    "status": "error",
                    "message": "No from email"
                }
            
            # Process with CRM agent
            result = process_message(
                customer_email=from_email,
                message=f"{subject}: {msg_body}" if subject else msg_body,
                channel="email"
            )
            
            return {
                "status": "processed",
                "ticket_id": result.get('ticket_id'),
                "message": result.get('response', 'Your message has been received'),
                "escalated": result.get('escalated', False)
            }

        # Import Gmail handler for Pub/Sub format
        from channels.gmail_handler import GmailHandler
        handler = GmailHandler()

        # Process Pub/Sub webhook
        messages = await handler.process_pubsub_webhook(body)

        # Process each message
        results = []
        for msg in messages:
            from_email = msg.get('customer_email', '')
            subject = msg.get('subject', '')
            msg_body = msg.get('content', '')

            if not from_email:
                logger.warning(f"No email in message: {msg}")
                continue

            # Process with CRM agent
            result = process_message(
                customer_email=from_email,
                message=f"{subject}: {msg_body}" if subject else msg_body,
                channel="email"
            )

            results.append({
                'ticket_id': result.get('ticket_id'),
                'escalated': result.get('escalated', False)
            })

        # Return 200 OK for Pub/Sub (must respond within 10s)
        return {
            "status": "processed",
            "messages_processed": len(results),
            "results": results
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON in Gmail webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        # Still return 200 to avoid Pub/Sub retries for transient errors
        return {
            "status": "error",
            "error": str(e)
        }


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
