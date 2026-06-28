"""
CRM Digital FTE - Agent Tools
Phase 2: Specialization

All function tools for the Customer Success FTE agent.
These tools provide the agent's capabilities for handling customer support.
Both plain functions (callable directly) and @function_tool wrappers (for Agent SDK).
"""

import os
import json
import logging
from typing import Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from db.database import CRMDatabase

logger = logging.getLogger(__name__)

db = CRMDatabase()

try:
    from agents import function_tool as _agents_function_tool
    def function_tool(func):
        _agents_function_tool(func)
        return func
except ImportError:
    def function_tool(func):
        return func


@function_tool
def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search product documentation for relevant information."""
    try:
        logger.info(f"Searching KB for: {query}")
        dummy_vector = [0.1] * 1536
        results = db.search_similar(
            query_vector=dummy_vector,
            limit=max_results
        )
        if results:
            return json.dumps({"success": True, "source": "embeddings", "results": results})
        fallback_results = _search_product_docs(query, max_results)
        return json.dumps({"success": True, "source": "product_docs", "results": fallback_results})
    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return json.dumps({"success": False, "error": str(e)})


@function_tool
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
        return json.dumps({"success": True, "ticket_id": ticket['id'], "customer_id": customer['id'], "status": "open"})
    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        return json.dumps({"success": False, "error": str(e)})


@function_tool
def get_customer_context(customer_email: str) -> str:
    """Get customer's complete context including history and stats."""
    try:
        logger.info(f"Getting context for {customer_email}")
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
        return json.dumps({
            "success": True,
            "customer": {"id": customer['id'], "email": customer.get('email'), "name": customer.get('name')},
            "history": serializable_history,
            "stats": serializable_stats,
            "is_returning_customer": serializable_stats.get('total_tickets', 0) > 0
        })
    except Exception as e:
        logger.error(f"Get customer context error: {e}")
        return json.dumps({"success": False, "error": str(e)})


@function_tool
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


@function_tool
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


@function_tool
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


def _search_product_docs(query: str, max_results: int = 5) -> list:
    """Fallback search in product-docs.md file."""
    try:
        docs_path = os.path.join(os.path.dirname(__file__), '..', '..', 'context', 'product-docs.md')
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        sections = content.split('## ')
        query_lower = query.lower()
        results = []
        for section in sections[1:]:
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



