"""
CRM Digital FTE - FastAPI Service Layer
"""

import os
import sys
import logging
import time
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

# Prometheus (Safe)
PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    pass

# Dummy metrics if prometheus not available
if not PROMETHEUS_AVAILABLE:
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
    REQUEST_COUNT = REQUEST_LATENCY = ERROR_COUNT = CHANNEL_MESSAGES = ESCALATION_COUNT = DummyMetric()
else:
    REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'API request latency', ['method', 'endpoint'])
    ERROR_COUNT = Counter('api_errors_total', 'Total API errors', ['type', 'endpoint'])
    CHANNEL_MESSAGES = Counter('channel_messages_total', 'Messages by channel', ['channel'])
    ESCALATION_COUNT = Counter('escalations_total', 'Total escalations', ['reason'])

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent.crm_agent import process_message
from db.database import CRMDatabase

# Import routers
from channels.web_form_handler import router as web_form_router
from channels.whatsapp_handler import router as whatsapp_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = CRMDatabase()

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Customer Success FTE API",
    description="24/7 AI-powered customer support across Email, WhatsApp, and Web",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_form_router)
app.include_router(whatsapp_router)

# =============================================================================
# HEALTH & METRICS
# =============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Customer Success FTE API",
        "version": "2.1.0",
        "channels": {"email": "active", "whatsapp": "active", "web_form": "active"}
    }

@app.get("/metrics")
async def metrics_endpoint():
    return {
        "status": "ok",
        "service": "Customer Success FTE API",
        "version": "2.1.0",
        "message": "Metrics endpoint working",
        "channels": ["whatsapp", "email", "web_form"]
    }

# =============================================================================
# REQUEST MIDDLEWARE
# =============================================================================

@app.middleware("http")
async def track_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    if PROMETHEUS_AVAILABLE:
        endpoint = request.url.path
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        if response.status_code >= 500:
            ERROR_COUNT.labels(type="server_error", endpoint=endpoint).inc()
        elif response.status_code >= 400:
            ERROR_COUNT.labels(type="client_error", endpoint=endpoint).inc()

    return response

# (Baqi Gmail, Customer Lookup, etc. endpoints agar chahiye toh baad mein add kar sakte hain)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)