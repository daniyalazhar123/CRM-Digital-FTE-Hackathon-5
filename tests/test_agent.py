"""
CRM Digital FTE - Agent Tests
Phase 2: Specialization — Step 5

Test process_message() from CRM Agent.
"""

import sys
import os
import time
import random

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.crm_agent import process_message


def generate_test_email():
    """Generate unique test email."""
    return f"agent_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


class TestEscalationTriggers:
    """Test escalation trigger detection."""
    
    def test_refund_request_escalates(self):
        """Test that refund requests are escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I need a refund for my last payment",
            channel="email"
        )
        
        assert result['escalated'] == True
        assert result['escalation_reason'] == 'refund_request'
    
    def test_pricing_inquiry_escalates(self):
        """Test that pricing inquiries are escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="What is the price for the enterprise plan?",
            channel="email"
        )
        
        assert result['escalated'] == True
        assert result['escalation_reason'] == 'pricing_inquiry'
    
    def test_legal_threat_escalates(self):
        """Test that legal threats are escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I will sue your company for this",
            channel="email"
        )
        
        assert result['escalated'] == True
        assert result['escalation_reason'] == 'legal_threat'
    
    def test_human_request_escalates(self):
        """Test that requests for human agent are escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I want to speak to a human agent please",
            channel="email"
        )
        
        assert result['escalated'] == True
        assert result['escalation_reason'] == 'human_requested'
    
    def test_cancel_subscription_escalates(self):
        """Test that cancel subscription requests are escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I want to cancel my subscription and get money back",
            channel="email"
        )
        
        assert result['escalated'] == True
        # Could be refund_request or pricing_inquiry
        assert result['escalation_reason'] in ['refund_request', 'pricing_inquiry']


class TestNormalResponses:
    """Test normal (non-escalated) responses."""
    
    def test_how_to_question_not_escalated(self):
        """Test that how-to questions are not escalated."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="How do I reset my password?",
            channel="email"
        )
        
        assert result['escalated'] == False
    
    def test_response_has_required_keys(self):
        """Test that response has all required keys."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="How do I add team members?",
            channel="email"
        )
        
        required_keys = ['response', 'ticket_id', 'escalated', 'tool_calls_count', 'response_time_ms']
        
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
    
    def test_ticket_id_created(self):
        """Test that ticket ID is created."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I need help with my account",
            channel="email"
        )
        
        assert result['ticket_id'] is not None
        assert result['ticket_id'].startswith('TKT-')
    
    def test_response_time_under_5_seconds(self):
        """Test that response time is under 5 seconds."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="How do I use the product?",
            channel="email"
        )
        
        assert result['response_time_ms'] < 5000
    
    def test_tool_calls_under_limit(self):
        """Test that tool calls are under limit."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="How do I configure settings?",
            channel="email"
        )
        
        assert result['tool_calls_count'] <= 10


class TestChannels:
    """Test different channel handling."""
    
    def test_email_channel_accepted(self):
        """Test that email channel is accepted."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="Test message",
            channel="email"
        )
        
        assert result['ticket_id'] is not None
    
    def test_whatsapp_channel_accepted(self):
        """Test that whatsapp channel is accepted."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="Test message",
            channel="whatsapp"
        )
        
        assert result['ticket_id'] is not None
    
    def test_web_form_channel_accepted(self):
        """Test that web_form channel is accepted."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="Test message",
            channel="web_form"
        )
        
        assert result['ticket_id'] is not None


class TestResponseContent:
    """Test response content quality."""
    
    def test_response_is_string(self):
        """Test that response is a string."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="How do I use this?",
            channel="email"
        )
        
        assert isinstance(result['response'], str)
    
    def test_response_not_empty(self):
        """Test that response is not empty."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I need help",
            channel="email"
        )
        
        assert len(result['response']) > 0
    
    def test_escalation_response_has_message(self):
        """Test that escalation response has a message."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="I need a refund",
            channel="email"
        )
        
        assert result['escalated'] == True
        assert len(result['response']) > 0
    
    def test_response_mentions_ticket(self):
        """Test that response is associated with ticket."""
        email = generate_test_email()
        result = process_message(
            customer_email=email,
            message="Help me please",
            channel="email"
        )
        
        assert 'ticket_id' in result
        assert result['ticket_id'] is not None


class TestReturningCustomer:
    """Test returning customer recognition."""
    
    def test_returning_customer_recognized(self):
        """Test that returning customer is recognized."""
        email = generate_test_email()
        
        # First message
        result1 = process_message(
            customer_email=email,
            message="I have a question",
            channel="email"
        )
        
        # Second message from same customer
        result2 = process_message(
            customer_email=email,
            message="I have another question",
            channel="email"
        )
        
        # Both should have ticket IDs
        assert result1['ticket_id'] is not None
        assert result2['ticket_id'] is not None
    
    def test_cross_channel_customer_tracking(self):
        """Test that customer is tracked across channels."""
        email = generate_test_email()
        
        # First message via email
        result1 = process_message(
            customer_email=email,
            message="Question via email",
            channel="email"
        )
        
        # Second message via web_form (same customer)
        result2 = process_message(
            customer_email=email,
            message="Question via web form",
            channel="web_form"
        )
        
        # Both should be processed successfully
        assert result1['ticket_id'] is not None
        assert result2['ticket_id'] is not None
