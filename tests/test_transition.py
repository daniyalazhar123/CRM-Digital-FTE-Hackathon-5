"""
Transition Tests: Verify agent behavior matches incident phase discoveries.
Run these BEFORE deploying to production.
"""

import sys
import os
import time
import random
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.crm_agent import process_message
from agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_context,
    escalate_ticket,
    send_response,
    track_sentiment,
)


def _test_email():
    return f"transition_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


class TestEdgeCases:
    """Tests based on edge cases discovered during incubation."""

    def test_edge_case_empty_message(self):
        """Edge case #1: Empty messages should not crash."""
        email = _test_email()
        result = process_message(
            customer_email=email,
            message="",
            channel="web_form",
            customer_name="Test"
        )
        assert result is not None
        assert 'response' in result
        assert len(result['response']) > 0

    def test_edge_case_pricing_escalation(self):
        """Edge case #2: Pricing questions must escalate."""
        email = _test_email()
        result = process_message(
            customer_email=email,
            message="How much does the enterprise plan cost?",
            channel="email"
        )
        assert result['escalated'] is True
        assert result['escalation_reason'] in ('pricing_inquiry', 'pricing_inquiry')

    def test_channel_response_length_whatsapp(self):
        """Verify WhatsApp responses are not excessively long."""
        email = _test_email()
        result = process_message(
            customer_email=email,
            message="How do I reset my password?",
            channel="whatsapp"
        )
        assert len(result['response']) <= 1600

    def test_channel_response_length_email(self):
        """Verify email responses are within reasonable limits."""
        email = _test_email()
        result = process_message(
            customer_email=email,
            message="How do I add team members to my workspace?",
            channel="email"
        )
        assert len(result['response']) <= 5000

    def test_tool_execution_returns_required_fields(self):
        """Verify that process_message returns all required fields."""
        email = _test_email()
        result = process_message(
            customer_email=email,
            message="I need help with the API",
            channel="web_form",
            customer_name="Test User"
        )
        required_fields = ['response', 'ticket_id', 'escalated', 'tool_calls_count', 'response_time_ms']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        assert result['ticket_id'] is not None
        assert result['ticket_id'].startswith('TKT-')


class TestToolFunctions:
    """Verify tool functions are callable and return expected structure."""

    def test_search_knowledge_base_tool(self):
        result = search_knowledge_base(query="password reset", max_results=3)
        assert result is not None
        assert isinstance(result, str)
        parsed = __import__('json').loads(result)
        assert 'success' in parsed

    def test_create_ticket_tool(self):
        email = _test_email()
        result = create_ticket(
            customer_email=email,
            message="Test issue",
            channel="email",
            priority="low",
            customer_name="Tester"
        )
        assert result is not None
        parsed = __import__('json').loads(result)
        assert parsed.get('success') is True
        assert 'ticket_id' in parsed

    def test_get_customer_context_tool(self):
        email = _test_email()
        result = get_customer_context(customer_email=email)
        assert result is not None
        parsed = __import__('json').loads(result)
        assert 'customer' in parsed

    def test_escalate_ticket_tool(self):
        email = _test_email()
        ticket = __import__('json').loads(create_ticket(
            customer_email=email, message="Escalate test", channel="email"
        ))
        ticket_id = ticket['ticket_id']
        result = escalate_ticket(ticket_id=ticket_id, reason="test_escalation")
        assert result is not None
        parsed = __import__('json').loads(result)
        assert 'escalated' in parsed

    def test_send_response_tool(self):
        email = _test_email()
        ticket = __import__('json').loads(create_ticket(
            customer_email=email, message="Response test", channel="email"
        ))
        ticket_id = ticket['ticket_id']
        result = send_response(
            ticket_id=ticket_id,
            response="Test response",
            channel="email"
        )
        assert result is not None
        parsed = __import__('json').loads(result)
        assert 'delivery_status' in parsed or 'success' in parsed

    def test_track_sentiment_tool(self):
        email = _test_email()
        customer = __import__('json').loads(get_customer_context(customer_email=email))
        customer_id = customer['customer']['id']
        result = track_sentiment(customer_id=customer_id, sentiment_score=0.75)
        assert result is not None
        parsed = __import__('json').loads(result)
        assert 'sentiment_score' in parsed
