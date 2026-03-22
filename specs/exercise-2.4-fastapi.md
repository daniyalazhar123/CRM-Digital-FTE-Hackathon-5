# Exercise 2.4 - FastAPI Service Layer

**Status:** ✅ COMPLETE  
**Date:** March 22, 2026  
**File:** `src/api/main.py`

---

## Overview

Built a production-ready FastAPI service layer for the Customer Success FTE. The API handles web form submissions, Gmail webhooks, WhatsApp webhooks, customer lookups, and metrics endpoints.

---

## Installation

### Dependencies Installed
```bash
pip install fastapi uvicorn[standard] python-multipart email-validator
```

**Versions:**
- fastapi: 0.115.0
- uvicorn: 0.32.0
- python-multipart: 0.0.20
- email-validator: 2.3.0

---

## API Endpoints

### Health Check

**GET /health**

Returns service status and channel availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-22T08:00:00Z",
  "service": "Customer Success FTE API",
  "version": "2.0.0",
  "channels": {
    "email": "active",
    "whatsapp": "active",
    "web_form": "active"
  }
}
```

---

### Web Form Submission

**POST /support/submit**

Handles support form submissions.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "How to add team members",
  "category": "how-to",
  "message": "I need help adding team members to my workspace.",
  "priority": "medium"
}
```

**Response:**
```json
{
  "ticket_id": "TKT-20260322032812-1855",
  "message": "Thank you for contacting us! Our AI assistant will respond shortly.",
  "estimated_response_time": "Usually within 5 minutes"
}
```

**Validation:**
- Name: min 2 characters
- Email: valid email format
- Message: min 10 characters
- Category: billing, technical, how-to, bug-report, other

---

### Ticket Status

**GET /support/ticket/{ticket_id}**

Get status and conversation history for a ticket.

**Response:**
```json
{
  "ticket_id": "TKT-20260322032812-1855",
  "status": "resolved",
  "messages": [...],
  "created_at": "2026-03-22T08:28:12Z",
  "last_updated": "2026-03-22T08:28:13Z"
}
```

---

### Gmail Webhook

**POST /webhooks/gmail**

Handles Gmail push notifications via Pub/Sub.

**Request:** Pub/Sub message payload

**Response:**
```json
{
  "status": "processed",
  "message": "Email queued for processing"
}
```

---

### WhatsApp Webhook

**POST /webhooks/whatsapp**

Handles incoming WhatsApp messages via Twilio.

**Request:** Twilio form data (From, Body, MessageSid, ProfileName)

**Response:** TwiML XML (empty response, agent responds asynchronously)

---

### WhatsApp Status

**POST /webhooks/whatsapp/status**

Handles WhatsApp message status updates (delivered, read, etc.).

---

### Customer Lookup

**GET /customers/lookup?email=john@example.com**

Look up customer by email or phone.

**Query Parameters:**
- `email` (optional): Customer email
- `phone` (optional): Customer phone

**Response:**
```json
{
  "customer_id": "uuid-here",
  "email": "john@example.com",
  "phone": "+14155551234",
  "name": "John Doe",
  "total_tickets": 5,
  "last_interaction": "2026-03-22T08:28:12Z"
}
```

---

### Channel Metrics

**GET /metrics/channels**

Get performance metrics by channel.

**Response:**
```json
{
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
```

---

### Summary Metrics

**GET /metrics/summary**

Get overall system metrics.

**Response:**
```json
{
  "total_tickets": 469,
  "open_tickets": 23,
  "resolved_tickets": 434,
  "escalated_tickets": 55,
  "avg_response_time_ms": 1250,
  "avg_sentiment": 0.68,
  "escalation_rate": 0.117
}
```

---

## Running the Server

### Development Mode
```bash
cd src/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker (Phase 2 Step 8)
```bash
docker-compose up -d
```

---

## CORS Configuration

CORS is enabled for all origins (configure appropriately for production):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Integration with CRM Agent

The API imports and uses `process_message` from `crm_agent.py`:

```python
from agent.crm_agent import process_message

# Process form submission
result = process_message(
    customer_email=submission.email,
    message=f"Subject: {submission.subject}\n{submission.message}",
    channel="web_form",
    customer_name=submission.name
)
```

---

## File Structure

```
src/api/
├── __init__.py              # Package marker
└── main.py                  # FastAPI application (500+ lines)
```

---

## Testing

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Form Submission
```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Subject",
    "category": "how-to",
    "message": "This is a test message for the support form."
  }'
```

### Test Customer Lookup
```bash
curl "http://localhost:8000/customers/lookup?email=test@example.com"
```

### Test Metrics
```bash
curl http://localhost:8000/metrics/channels
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 404 | Not Found (ticket/customer not found) |
| 500 | Internal Server Error |

Error responses include detail message:
```json
{
  "detail": "Error description"
}
```

---

## Next Steps

1. **Channel Handlers** - Create Gmail, WhatsApp, and web form handlers (Step 5)
2. **Web Support Form** - Build React component (Step 6)
3. **Kafka Integration** - Add event streaming (Step 7)
4. **Kubernetes Deployment** - Create K8s manifests (Step 8)

---

*Phase 2 Step 4 Complete — FastAPI Service Layer Ready!*
