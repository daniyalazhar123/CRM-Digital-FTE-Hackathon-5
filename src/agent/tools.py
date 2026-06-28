"""
CRM Digital FTE - Agent Tools
Phase 2: Specialization — OpenAI Agents SDK

All function tools for the Customer Success FTE agent.
- Plain functions (callable directly, backward compatible)
- @function_tool wrappers from OpenAI Agents SDK (for Agent(tools=...))
"""

import os
import json
import logging
import asyncio
from typing import Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from db.database import CRMDatabase
from embeddings import embed_text
from cache.redis_client import cached_kb_search, cache_kb_search, cached_customer_lookup, cache_customer_lookup, invalidate_customer_cache

logger = logging.getLogger(__name__)

db = CRMDatabase()

# =============================================================================
# PLAIN FUNCTIONS — callable directly, backward compatible
# =============================================================================


def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search product documentation using pgvector cosine similarity.

    Real production pipeline:
      query → Redis cache check → embed_text() → pgvector similarity search → top K chunks → Redis cache store
    """
    try:
        logger.info(f"Searching KB for: {query[:80]}")

        # ── Check Redis cache first ──
        cached = asyncio.run(cached_kb_search(query, max_results))
        if cached is not None:
            logger.info("[REDIS] KB cache HIT for: %s", query[:80])
            return json.dumps({
                "success": True,
                "source": "redis_cache",
                "results": cached,
            })

        # ── Embed query ──
        query_embedding = embed_text(query)
        if query_embedding is None:
            return json.dumps({
                "success": False,
                "error": "Embedding unavailable — set OPENAI_API_KEY in .env",
                "source": None,
                "results": [],
            })

        # ── pgvector search ──
        results = db.search_document_chunks(
            query_embedding=query_embedding,
            limit=max_results,
        )

        # ── Store in Redis cache ──
        asyncio.run(cache_kb_search(query, results, max_results))

        return json.dumps({
            "success": True,
            "source": "pgvector",
            "results": results,
        })
    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def create_ticket(customer_email: str, message: str, channel: str,
                  priority: str = "medium", customer_name: Optional[str] = None) -> str:
    """Create a support ticket for tracking. ALWAYS call at start of every conversation."""
    try:
        logger.info(f"Creating ticket for {customer_email} via {channel}")
        is_phone = customer_email.startswith('+') or customer_email.replace('-', '').replace(' ', '').isdigit()
        if is_phone or channel == 'whatsapp':
            customer = db.get_or_create_customer(phone=customer_email, name=customer_name)
        else:
            customer = db.get_or_create_customer(email=customer_email, name=customer_name)
        ticket = db.create_ticket(
            customer_id=customer['id'], issue=message, priority=priority, channel=channel
        )

        # ── Invalidate customer cache (stats changed) ──
        identifier = customer.get('email') or customer.get('phone') or customer_email
        asyncio.run(invalidate_customer_cache(identifier))

        return json.dumps({"success": True, "ticket_id": ticket['id'], "customer_id": customer['id'], "status": "open"})
    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def get_customer_context(customer_email: str) -> str:
    """Get customer's complete context including history and stats.

    Production pipeline:
      identifier → Redis cache check → DB lookup → Redis cache store
    """
    try:
        logger.info(f"Getting context for {customer_email}")

        # ── Check Redis cache first ──
        cached = asyncio.run(cached_customer_lookup(customer_email))
        if cached is not None:
            logger.info("[REDIS] Customer cache HIT for: %s", customer_email)
            return json.dumps({
                "success": True,
                "customer": cached.get("customer"),
                "history": cached.get("history", []),
                "stats": cached.get("stats", {}),
                "is_returning_customer": cached.get("stats", {}).get("total_tickets", 0) > 0,
                "source": "redis_cache",
            })

        is_phone = customer_email.startswith('+') or customer_email.replace('-', '').replace(' ', '').isdigit()
        if is_phone:
            customer = db.get_or_create_customer(phone=customer_email)
        else:
            customer = db.get_or_create_customer(email=customer_email)
        history = db.get_customer_history(customer['id'], limit=10)
        stats = db.get_customer_stats(customer['id'])
        serializable_history = []
        for h in history[:5]:
            h_copy = dict(h) if hasattr(h, '__dict__') else h
            for key, value in h_copy.items():
                if hasattr(value, 'isoformat'):
                    h_copy[key] = value.isoformat()
            serializable_history.append(h_copy)
        serializable_stats = {}
        for key, value in stats.items():
            if hasattr(value, 'isoformat'):
                serializable_stats[key] = value.isoformat()
            else:
                serializable_stats[key] = value

        # ── Store in Redis cache ──
        cache_payload = {
            "customer": {"id": customer['id'], "email": customer.get('email'), "name": customer.get('name')},
            "history": serializable_history,
            "stats": serializable_stats,
        }
        asyncio.run(cache_customer_lookup(customer_email, cache_payload))

        return json.dumps({
            "success": True,
            "customer": cache_payload["customer"],
            "history": serializable_history,
            "stats": serializable_stats,
            "is_returning_customer": serializable_stats.get('total_tickets', 0) > 0
        })
    except Exception as e:
        logger.error(f"Get customer context error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def escalate_ticket(ticket_id: str, reason: str, notes: str = "") -> str:
    """Escalate a ticket to human support."""
    try:
        logger.info(f"Escalating ticket {ticket_id} for {reason}")
        success = db.escalate_ticket(ticket_id, reason)
        escalation_messages = {
            "pricing_inquiry": "That's a great question about pricing. Our sales team can provide accurate information tailored to your needs. I'm connecting you with them.",
            "refund_request": "I understand your concern about billing. Let me connect you with our billing team who can assist you.",
            "legal_threat": "I understand this is a serious matter. I'm escalating this to our specialist team who will review your case promptly.",
            "negative_sentiment": "I completely understand your frustration. Let me connect you with a specialist who can give this the attention it deserves.",
            "human_requested": "I understand you'd like to speak with someone directly. I'm arranging for a team member to contact you.",
            "no_relevant_info": "That's a great question, and I want to make sure you get accurate information. Let me connect you with a specialist.",
            "frustrated_customer": "I can see you've had a frustrating experience. Let me connect you with a specialist for personal attention."
        }
        escalation_message = escalation_messages.get(reason,
            "I'm connecting you with a specialist who can better assist you.")
        return json.dumps({"success": success, "escalated": success, "reason": reason, "message": escalation_message})
    except Exception as e:
        logger.error(f"Escalate ticket error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def send_response(ticket_id: str, response: str, channel: str) -> str:
    """Send response to customer via their channel. ALWAYS use this to reply."""
    try:
        logger.info(f"Sending response to ticket {ticket_id} via {channel}")
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            return json.dumps({"success": False, "error": "Ticket not found"})
        from formatters import format_response
        formatted_response = format_response(response, channel, ticket_id=ticket_id)
        db.add_message(
            ticket_id=ticket_id, customer_id=ticket['customer_id'],
            role="agent", content=formatted_response, channel=channel
        )
        db.resolve_ticket(ticket_id)
        return json.dumps({"success": True, "char_count": len(formatted_response), "truncated": False, "delivery_status": "sent"})
    except Exception as e:
        logger.error(f"Send response error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def track_sentiment(customer_id: str, sentiment_score: float) -> str:
    """Track customer sentiment and detect trends."""
    try:
        logger.info(f"Tracking sentiment {sentiment_score} for customer {customer_id}")
        if not (0.0 <= sentiment_score <= 1.0):
            return json.dumps({"success": False, "error": "Sentiment score must be between 0.0 and 1.0"})
        db.update_sentiment(customer_id, sentiment_score)
        stats = db.get_customer_stats(customer_id)
        trend = stats.get('sentiment_trend', 'stable')
        frustration_flag = stats.get('frustration_flag', False)
        return json.dumps({"success": True, "sentiment_score": sentiment_score, "trend": trend, "frustration_flag": frustration_flag})
    except Exception as e:
        logger.error(f"Track sentiment error: {e}")
        return json.dumps({"success": False, "error": str(e)})





# =============================================================================
# FUNCTION TOOL WRAPPERS — for OpenAI Agents SDK Agent(tools=...)
# =============================================================================

from agents import function_tool
from agents.tool import FunctionTool


@function_tool
def _tool_search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search product documentation for relevant information. Call when customer asks a question about product features, usage, or troubleshooting."""
    logger.info("[TOOL] _tool_search_knowledge_base(query=%s, max_results=%s)", query[:50], max_results)
    return search_knowledge_base(query, max_results)


@function_tool
def _tool_create_ticket(customer_email: str, message: str, channel: str,
                        priority: str = "medium", customer_name: Optional[str] = None) -> str:
    """Create a support ticket for tracking. ALWAYS call at the start of every conversation to log the interaction."""
    logger.info("[TOOL] _tool_create_ticket(customer_email=%s, channel=%s)", customer_email, channel)
    return create_ticket(customer_email, message, channel, priority, customer_name)


@function_tool
def _tool_get_customer_context(customer_email: str) -> str:
    """Get customer's complete context including history, total tickets, sentiment trend, and returning status. Call at the start of every conversation."""
    logger.info("[TOOL] _tool_get_customer_context(customer_email=%s)", customer_email)
    return get_customer_context(customer_email)


@function_tool
def _tool_escalate_ticket(ticket_id: str, reason: str, notes: str = "") -> str:
    """Escalate a ticket to human support. Use for pricing inquiries, refund requests, legal threats, negative sentiment, frustrated customers, or when customer asks for a human."""
    logger.info("[TOOL] _tool_escalate_ticket(ticket_id=%s, reason=%s)", ticket_id, reason)
    return escalate_ticket(ticket_id, reason, notes)


@function_tool
def _tool_send_response(ticket_id: str, response: str, channel: str) -> str:
    """Send a formatted response to the customer via their channel. ALWAYS use this to reply — it enforces channel-specific limits (WhatsApp: 300 chars, Email: 3000 chars, Web: 1800 chars)."""
    logger.info("[TOOL] _tool_send_response(ticket_id=%s, channel=%s, response_len=%s)", ticket_id, channel, len(response))
    return send_response(ticket_id, response, channel)


@function_tool
def _tool_track_sentiment(customer_id: str, sentiment_score: float) -> str:
    """Track customer sentiment (0.0-1.0) and detect frustration trends. Call after every customer message."""
    logger.info("[TOOL] _tool_track_sentiment(customer_id=%s, score=%.2f)", customer_id, sentiment_score)
    return track_sentiment(customer_id, sentiment_score)


AGENT_TOOLS: list[FunctionTool] = [
    _tool_search_knowledge_base,
    _tool_create_ticket,
    _tool_get_customer_context,
    _tool_escalate_ticket,
    _tool_send_response,
    _tool_track_sentiment,
]

