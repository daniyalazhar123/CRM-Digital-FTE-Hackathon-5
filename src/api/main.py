"""
CRM Digital FTE — FastAPI Service Layer
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

# Prometheus — safe import
PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    pass

# Dummy metrics when prometheus_client not installed
if not PROMETHEUS_AVAILABLE:
    class _Dummy:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return _Dummy()
        def set(self, *args, **kwargs): pass
    REQUEST_COUNT = REQUEST_LATENCY = ERROR_COUNT = CHANNEL_MESSAGES = _Dummy()
    ESCALATION_COUNT = CACHE_HITS = CACHE_MISSES = KB_SEARCH_DURATION = _Dummy()
    TICKETS_CREATED = TICKETS_RESOLVED = ERROR_RATE = ESCALATION_RATE = _Dummy()
else:
    # ── API-level counters ──
    REQUEST_COUNT = Counter("api_requests_total", "Total API requests", ["method", "endpoint", "status"])
    REQUEST_LATENCY = Histogram("api_request_latency_seconds", "API request latency", ["method", "endpoint"],
                                 buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0))
    ERROR_COUNT = Counter("api_errors_total", "Total API errors", ["type", "endpoint"])
    ERROR_RATE = Gauge("error_rate_ratio", "Error rate over 1h window")

    # ── Channel counters ──
    CHANNEL_MESSAGES = Counter("channel_messages_total", "Messages by channel", ["channel"])

    # ── Escalation counters ──
    ESCALATION_COUNT = Counter("escalations_total", "Total escalations", ["reason"])
    ESCALATION_RATE = Gauge("escalation_rate_ratio", "Escalation rate over 1h window")

    # ── Cache counters ──
    CACHE_HITS = Counter("cache_hits_total", "Redis cache hits", ["cache_type"])
    CACHE_MISSES = Counter("cache_misses_total", "Redis cache misses", ["cache_type"])

    # ── KB search latency ──
    KB_SEARCH_DURATION = Histogram("kb_search_duration_seconds", "KB pgvector search latency",
                                   buckets=(.01, .025, .05, .1, .25, .5, .75, 1.0, 2.5, 5.0))

    # ── Ticket counters ──
    TICKETS_CREATED = Counter("tickets_created_total", "Total tickets created")
    TICKETS_RESOLVED = Counter("tickets_resolved_total", "Total tickets resolved")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent.crm_agent import process_message
from db.database import CRMDatabase

# Import routers
from channels.web_form_handler import router as web_form_router
from channels.whatsapp_handler import router as whatsapp_router
from channels.gmail_handler import router as gmail_router

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
app.include_router(gmail_router)

# =============================================================================
# HEALTH & METRICS
# =============================================================================

@app.get("/health")
async def health_check():
    redis_ok = False
    kafka_ok = False
    try:
        from cache.redis_client import get_cache
        cache = get_cache()
        redis_ok = await cache.health_check()
    except Exception:
        pass
    try:
        from workers.kafka_producer import get_producer
        producer = get_producer()
        kafka_ok = True
    except Exception:
        pass
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "Customer Success FTE API",
        "version": "2.1.0",
        "channels": {"email": "active", "whatsapp": "active", "web_form": "active"},
        "redis": "connected" if redis_ok else "disconnected",
        "kafka": "available" if kafka_ok else "unavailable"
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus /metrics endpoint — returns exposition format."""
    if PROMETHEUS_AVAILABLE:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    return JSONResponse({
        "status": "warning",
        "message": "prometheus_client not installed — install with: pip install prometheus-client",
        "service": "Customer Success FTE API",
        "version": "2.1.0"
    })


@app.get("/metrics/summary")
async def metrics_summary():
    """Human-readable metrics summary."""
    from workers.metrics_collector import get_metrics_store
    store = get_metrics_store()
    return store.get_summary()


@app.get("/metrics/channels")
async def metrics_channels():
    """Per-channel metrics."""
    from workers.metrics_collector import get_metrics_store
    store = get_metrics_store()
    return store.get_channel_metrics()


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


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
