"""
CRM Digital FTE - Agent Tools
Phase 2: Specialization

All @function_tool decorated functions for the Customer Success FTE agent.
These tools provide the agent's capabilities for handling customer support.
"""

import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field

# Import database layer
from database import CRMDatabase

logger = logging.getLogger(__name__)

# Initialize database
db = CRMDatabase()

# =============================================================================
# PYDANTIC INPUT SCHEMAS
# =============================================================================

class KnowledgeSearchInput(BaseModel):
    """Input for knowledge base search."""
    query: str = Field(..., description="The search query")
    category: Optional[str] = Field(None, description="Optional category filter")
    max_results: int = Field(5, ge=1, le=10, description="Max results to return")


class CreateTicketInput(BaseModel):
    """Input for creating a ticket."""
    customer_email: str = Field(..., description="Customer email address or phone number")
    message: str = Field(..., description="Customer message/issue")
    channel: str = Field(..., description="Source channel (email, whatsapp, web_form)")
    priority: str = Field("medium", description="Ticket priority")
    customer_name: Optional[str] = Field(None, description="Customer name")


class CustomerContextInput(BaseModel):
    """Input for getting customer context."""
    customer_email: str = Field(..., description="Customer email address or phone number")


class EscalateTicketInput(BaseModel):
    """Input for escalating a ticket."""
    ticket_id: str = Field(..., description="Ticket ID to escalate")
    reason: str = Field(..., description="Escalation reason")
    notes: str = Field("", description="Additional notes")


class SendResponseInput(BaseModel):
    """Input for sending a response."""
    ticket_id: str = Field(..., description="Ticket ID")
    response: str = Field(..., description="Response text")
    channel: str = Field(..., description="Channel to send via (email, whatsapp, web_form)")


class TrackSentimentInput(BaseModel):
    """Input for tracking sentiment."""
    customer_id: str = Field(..., description="Customer ID")
    sentiment_score: float = Field(..., ge=0.0, le=1.0, description="Sentiment score 0-1")


# =============================================================================
# AGENT TOOLS
# =============================================================================

def search_knowledge_base(params: KnowledgeSearchInput) -> str:
    """
    Search product documentation for relevant information.
    
    Use this when the customer asks questions about product features,
    how to use something, or needs technical information.

    Args:
        params: KnowledgeSearchInput with query, category, max_results

    Returns:
        JSON string with search results
    """
    try:
        logger.info(f"Searching KB for: {params.query}")

        # Try database embeddings first
        dummy_vector = [0.1] * 1536  # Placeholder
        
        results = db.search_similar(
            query_vector=dummy_vector,
            limit=params.max_results,
            category=params.category
        )

        if results:
            return json.dumps({
                "success": True,
                "source": "embeddings",
                "results": results
            })

        # Fallback: Search product-docs.md directly
        fallback_results = _search_product_docs(params.query, params.max_results)

        return json.dumps({
            "success": True,
            "source": "product_docs",
            "results": fallback_results
        })

    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def create_ticket(params: CreateTicketInput) -> str:
    """
    Create a support ticket for tracking.
    
    Use this to log EVERY customer interaction before responding.
    Include the channel source for multi-channel tracking.

    Args:
        params: CreateTicketInput with customer_email, message, channel, priority

    Returns:
        JSON string with ticket_id and customer_id
    """
    try:
        logger.info(f"Creating ticket for {params.customer_email} via {params.channel}")

        # Detect if customer_email is actually an email or phone number
        is_phone = params.customer_email.startswith('+') or params.customer_email.replace('-', '').replace(' ', '').isdigit()
        
        # Get or create customer with correct identifier
        if is_phone or params.channel == 'whatsapp':
            customer = db.get_or_create_customer(
                phone=params.customer_email,
                name=params.customer_name
            )
        else:
            customer = db.get_or_create_customer(
                email=params.customer_email,
                name=params.customer_name
            )

        # Create ticket
        ticket = db.create_ticket(
            customer_id=customer['id'],
            issue=params.message,
            priority=params.priority,
            channel=params.channel
        )

        return json.dumps({
            "success": True,
            "ticket_id": ticket['id'],
            "customer_id": customer['id'],
            "status": "open"
        })

    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def get_customer_context(params: CustomerContextInput) -> str:
    """
    Get customer's complete context including history and stats.
    
    Use this to check if customer is returning and their past interactions
    across ALL channels (email, WhatsApp, web form).

    Args:
        params: CustomerContextInput with customer_email

    Returns:
        JSON string with history, stats, and is_returning_customer flag
    """
    try:
        logger.info(f"Getting context for {params.customer_email}")

        # Detect if customer_email is actually an email or phone number
        is_phone = params.customer_email.startswith('+') or params.customer_email.replace('-', '').replace(' ', '').isdigit()
        
        # Get customer with correct identifier
        if is_phone:
            customer = db.get_or_create_customer(phone=params.customer_email)
        else:
            customer = db.get_or_create_customer(email=params.customer_email)

        # Get history
        history = db.get_customer_history(customer['id'], limit=10)

        # Get stats
        stats = db.get_customer_stats(customer['id'])

        # Convert to serializable format
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

        return json.dumps({
            "success": True,
            "customer": {
                "id": customer['id'],
                "email": customer.get('email'),
                "name": customer.get('name')
            },
            "history": serializable_history,
            "stats": serializable_stats,
            "is_returning_customer": serializable_stats.get('total_tickets', 0) > 0
        })

    except Exception as e:
        logger.error(f"Get customer context error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def escalate_ticket(params: EscalateTicketInput) -> str:
    """
    Escalate a ticket to human support.
    
    Use this when:
    - Customer mentions legal keywords (lawyer, attorney, sue)
    - Customer asks about pricing
    - Customer requests refund
    - Customer explicitly requests human
    - Sentiment score < 0.3
    - Cannot find relevant info after 2 searches

    Args:
        params: EscalateTicketInput with ticket_id, reason, notes

    Returns:
        JSON string with success status and escalation message
    """
    try:
        logger.info(f"Escalating ticket {params.ticket_id} for {params.reason}")

        # Mark as escalated
        success = db.escalate_ticket(params.ticket_id, params.reason)

        # Generate customer message
        from prompts import ESCALATION_MESSAGES
        escalation_message = ESCALATION_MESSAGES.get(params.reason,
            "I'm connecting you with a specialist who can better assist you.")

        return json.dumps({
            "success": success,
            "escalated": success,
            "reason": params.reason,
            "message": escalation_message
        })

    except Exception as e:
        logger.error(f"Escalate ticket error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def send_response(params: SendResponseInput) -> str:
    """
    Send response to customer via their channel.
    
    ALWAYS use this tool to reply to customers (never respond directly).
    This ensures proper channel formatting and message tracking.

    Args:
        params: SendResponseInput with ticket_id, response, channel

    Returns:
        JSON string with success status, char_count, and truncated flag
    """
    try:
        logger.info(f"Sending response to ticket {params.ticket_id} via {params.channel}")

        # Get ticket to find customer_id
        ticket = db.get_ticket(params.ticket_id)
        if not ticket:
            return json.dumps({"success": False, "error": "Ticket not found"})

        # Format response for channel
        from formatters import format_response
        formatted_response = format_response(
            params.response,
            params.channel,
            ticket_id=params.ticket_id
        )

        # Save to database
        db.add_message(
            ticket_id=params.ticket_id,
            customer_id=ticket['customer_id'],
            role="agent",
            content=formatted_response,
            channel=params.channel
        )

        # Resolve ticket
        db.resolve_ticket(params.ticket_id)

        return json.dumps({
            "success": True,
            "char_count": len(formatted_response),
            "truncated": len(formatted_response) != len(params.response),
            "delivery_status": "sent"
        })

    except Exception as e:
        logger.error(f"Send response error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def track_sentiment(params: TrackSentimentInput) -> str:
    """
    Track customer sentiment and detect trends.
    
    Use this on EVERY customer message to track satisfaction
    and detect frustration early.

    Args:
        params: TrackSentimentInput with customer_id, sentiment_score

    Returns:
        JSON string with trend and frustration_flag
    """
    try:
        logger.info(f"Tracking sentiment {params.sentiment_score} for customer {params.customer_id}")

        # Validate score
        if not (0.0 <= params.sentiment_score <= 1.0):
            return json.dumps({
                "success": False,
                "error": "Sentiment score must be between 0.0 and 1.0"
            })

        # Update sentiment
        db.update_sentiment(params.customer_id, params.sentiment_score)

        # Get stats to determine trend
        stats = db.get_customer_stats(params.customer_id)

        # Determine trend
        trend = stats.get('sentiment_trend', 'stable')
        frustration_flag = stats.get('frustration_flag', False)

        return json.dumps({
            "success": True,
            "sentiment_score": params.sentiment_score,
            "trend": trend,
            "frustration_flag": frustration_flag
        })

    except Exception as e:
        logger.error(f"Track sentiment error: {e}")
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _search_product_docs(query: str, max_results: int = 5) -> list:
    """Fallback search in product-docs.md file."""
    try:
        docs_path = os.path.join(os.path.dirname(__file__), '..', '..', 'context', 'product-docs.md')
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple keyword search
        sections = content.split('## ')
        query_lower = query.lower()

        results = []
        for section in sections[1:]:  # Skip title
            lines = section.split('\n')
            title = lines[0].strip()

            if query_lower in title.lower() or query_lower in section.lower():
                results.append({
                    "title": title,
                    "content": section[:500] + "..." if len(section) > 500 else section,
                    "score": 10 if query_lower in title.lower() else 5
                })

        return results[:max_results]

    except Exception as e:
        logger.error(f"Fallback search error: {e}")
        return []
