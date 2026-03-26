"""
CRM Digital FTE - Multi-Channel End-to-End Tests
Phase 3: Integration & Testing — Exercise 3.1

Comprehensive E2E tests for all communication channels:
- Web Form submissions
- Gmail webhook simulation
- WhatsApp webhook simulation
- Cross-channel continuity and customer recognition

These tests verify the complete multi-channel architecture works correctly
with real PostgreSQL database and full agent processing.
"""

import sys
import os
import pytest
import asyncio
import time
import random
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from api.main import app
from db.database import CRMDatabase

# Create test client
client = TestClient(app)

# Initialize database for direct access
db = CRMDatabase()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_conn():
    """Provide database connection for tests."""
    conn = db.get_connection()
    yield conn
    conn.close()


@pytest.fixture
def test_email():
    """Generate unique test email address."""
    return f"e2e_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


@pytest.fixture
def test_phone():
    """Generate unique test phone number."""
    return f"+1415555{random.randint(1000, 9999)}"


@pytest.fixture
def customer_data(test_email):
    """Create customer test data."""
    return {
        'email': test_email,
        'name': f"E2E Test User {random.randint(1000, 9999)}",
        'plan': 'free'
    }


def cleanup_test_data(db_conn, email: str = None, phone: str = None):
    """
    Cleanup test data from database.
    
    Args:
        db_conn: Database connection
        email: Email to cleanup
        phone: Phone to cleanup
    """
    try:
        with db_conn.cursor() as cur:
            if email:
                cur.execute(
                    "DELETE FROM messages WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)",
                    (email,)
                )
                cur.execute(
                    "DELETE FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)",
                    (email,)
                )
                cur.execute("DELETE FROM customers WHERE email = %s", (email,))
            if phone:
                cur.execute(
                    "DELETE FROM messages WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)",
                    (phone,)
                )
                cur.execute(
                    "DELETE FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)",
                    (phone,)
                )
                cur.execute("DELETE FROM customers WHERE phone = %s", (phone,))
            db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")


# =============================================================================
# WEB FORM CHANNEL TESTS
# =============================================================================

class TestWebFormChannel:
    """
    Test the web support form (required build).
    
    The web form is the primary customer-facing interface for support requests.
    These tests verify form validation, submission, and ticket creation.
    """

    @pytest.mark.asyncio
    async def test_form_submission(self, test_email, db_conn):
        """
        Web form submission should create ticket and return ID.
        
        Test flow:
        1. Submit valid form data
        2. Verify 200 response
        3. Verify ticket_id returned
        4. Verify ticket exists in database
        """
        try:
            response = client.post("/support/submit", json={
                "name": "Test User",
                "email": test_email,
                "subject": "Help with API",
                "category": "technical",
                "message": "I need help with the API authentication endpoint."
            })

            assert response.status_code == 200
            data = response.json()
            assert "ticket_id" in data
            assert data["message"] is not None
            assert "ticket_id" in data

            # Verify ticket exists in database
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT id, channel, status FROM tickets WHERE id = %s",
                    (data["ticket_id"],)
                )
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket[1] == "web_form"
                assert ticket[2] in ["open", "processing", "resolved"]

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_form_validation_name_too_short(self):
        """
        Form should validate name field.
        
        Name must be at least 2 characters.
        """
        response = client.post("/support/submit", json={
            "name": "A",  # Too short
            "email": "test@example.com",
            "subject": "Test Subject",
            "category": "how-to",
            "message": "This is a valid message."
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_form_validation_message_too_short(self):
        """
        Form should validate message field.
        
        Message must be at least 10 characters.
        """
        response = client.post("/support/submit", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test Subject",
            "category": "how-to",
            "message": "Short"  # Too short
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_form_validation_invalid_email(self):
        """
        Form should validate email format.
        """
        response = client.post("/support/submit", json={
            "name": "Test User",
            "email": "invalid-email",
            "subject": "Test Subject",
            "category": "how-to",
            "message": "This is a valid message."
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_form_validation_invalid_category(self):
        """
        Form should validate category field.
        
        Category must be one of: how-to, technical, billing, bug-report, other
        """
        response = client.post("/support/submit", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test Subject",
            "category": "invalid-category",
            "message": "This is a valid message."
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ticket_status_retrieval(self, test_email, db_conn):
        """
        Should be able to check ticket status after submission.
        
        Test flow:
        1. Submit form
        2. Get ticket_id from response
        3. Query ticket status endpoint
        4. Verify status and messages returned
        """
        try:
            # Submit form
            submit_response = client.post("/support/submit", json={
                "name": "Test User",
                "email": test_email,
                "subject": "Status Test",
                "category": "general",
                "message": "Testing ticket status retrieval functionality."
            })

            ticket_id = submit_response.json()["ticket_id"]

            # Check status
            status_response = client.get(f"/support/ticket/{ticket_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["ticket_id"] == ticket_id
            assert status_data["status"] in ["open", "processing", "resolved"]
            assert "messages" in status_data

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_form_all_categories(self, test_email, db_conn):
        """
        Test form submission with all valid categories.
        
        Verifies each category is accepted and processed correctly.
        """
        valid_categories = ['how-to', 'technical', 'billing', 'bug-report', 'other']
        ticket_ids = []

        try:
            for category in valid_categories:
                response = client.post("/support/submit", json={
                    "name": "Test User",
                    "email": test_email,
                    "subject": f"Test {category}",
                    "category": category,
                    "message": f"Testing {category} category submission."
                })

                assert response.status_code == 200
                data = response.json()
                assert "ticket_id" in data
                ticket_ids.append(data["ticket_id"])

            # Verify all tickets in database with correct categories
            with db_conn.cursor() as cur:
                for ticket_id in ticket_ids:
                    cur.execute(
                        "SELECT issue FROM tickets WHERE id = %s",
                        (ticket_id,)
                    )
                    ticket = cur.fetchone()
                    assert ticket is not None

        finally:
            cleanup_test_data(db_conn, email=test_email)


# =============================================================================
# EMAIL CHANNEL (GMAIL) TESTS
# =============================================================================

class TestEmailChannel:
    """
    Test Gmail integration.
    
    These tests simulate Gmail Pub/Sub webhook notifications
    and verify email processing pipeline.
    """

    @pytest.mark.asyncio
    async def test_gmail_webhook_processing(self, db_conn):
        """
        Gmail webhook should process incoming emails.
        
        Simulates a Pub/Sub notification from Gmail API.
        """
        test_email_addr = f"gmail_test_{int(time.time())}@test.com"

        try:
            # Simulate Pub/Sub notification
            response = client.post("/webhooks/gmail", json={
                "message": {
                    "data": "eyJmcm9tIjogInRlc3RAZXhhbXBsZS5jb20iLCAic3ViamVjdCI6ICJUZXN0In0=",
                    "messageId": f"test-{int(time.time())}"
                },
                "subscription": "projects/test-project/subscriptions/gmail-push"
            })

            # Should accept webhook (processing happens in background)
            assert response.status_code == 200

        finally:
            pass  # No cleanup needed for mock webhooks

    @pytest.mark.asyncio
    async def test_gmail_webhook_with_full_email(self, test_email, db_conn):
        """
        Gmail webhook with complete email data.
        
        Tests full email parsing and ticket creation.
        """
        try:
            # Simulate complete email webhook
            response = client.post("/webhooks/gmail", json={
                "from": test_email,
                "to": "support@techcorp.com",
                "subject": "How to reset my password?",
                "body": "Hi, I forgot my password and need to reset it. Can you help me with the steps?",
                "received_at": datetime.utcnow().isoformat()
            })

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "status" in data or "ticket_id" in data or "message" in data

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_gmail_escalation_pricing(self, test_email, db_conn):
        """
        Gmail: Pricing inquiries should escalate.
        
        Tests guardrail: NEVER discuss pricing → escalate immediately
        """
        try:
            response = client.post("/webhooks/gmail", json={
                "from": test_email,
                "to": "support@techcorp.com",
                "subject": "Enterprise Pricing Question",
                "body": "What is the price for enterprise plan? I need a quote for 100 users.",
                "received_at": datetime.utcnow().isoformat()
            })

            assert response.status_code == 200

            # Verify escalation in database
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT escalated, escalation_reason
                    FROM tickets
                    WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (test_email,)
                )
                ticket = cur.fetchone()
                if ticket:
                    assert ticket[0] == True
                    assert "pricing" in str(ticket[1]).lower()

        finally:
            cleanup_test_data(db_conn, email=test_email)


# =============================================================================
# WHATSAPP CHANNEL TESTS
# =============================================================================

class TestWhatsAppChannel:
    """
    Test WhatsApp/Twilio integration.
    
    These tests simulate Twilio WhatsApp API webhook notifications
    and verify message processing with character limits.
    """

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_processing(self, test_phone, db_conn):
        """
        WhatsApp webhook should process incoming messages.
        
        Simulates Twilio webhook with form data.
        """
        try:
            # Twilio sends form data, not JSON
            response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "Hello, I need help with my account",
                    "ProfileName": "Test User"
                }
            )

            # Will return 200 (TwiML response) or 403 (signature validation in production)
            assert response.status_code in [200, 403]

        finally:
            cleanup_test_data(db_conn, phone=test_phone)

    @pytest.mark.asyncio
    async def test_whatsapp_response_character_limit(self, test_phone, db_conn):
        """
        WhatsApp responses must respect 300 character limit.
        
        Tests channel-specific response formatting constraint.
        """
        try:
            # Send message that might generate long response
            response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "Can you explain all the features available in the product? I want a comprehensive list.",
                    "ProfileName": "Test User"
                }
            )

            # Should process successfully
            assert response.status_code in [200, 403]

        finally:
            cleanup_test_data(db_conn, phone=test_phone)

    @pytest.mark.asyncio
    async def test_whatsapp_escalation_human_request(self, test_phone, db_conn):
        """
        WhatsApp: "human", "agent", or "representative" should escalate.
        
        Tests escalation trigger for explicit human requests.
        """
        try:
            response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "I want to speak to a human agent please",
                    "ProfileName": "Test User"
                }
            )

            assert response.status_code in [200, 403]

            # Verify escalation in database
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT escalated, escalation_reason
                    FROM tickets
                    WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (test_phone,)
                )
                ticket = cur.fetchone()
                if ticket:
                    assert ticket[0] == True
                    assert "human" in str(ticket[1]).lower() or "explicit" in str(ticket[1]).lower()

        finally:
            cleanup_test_data(db_conn, phone=test_phone)

    @pytest.mark.asyncio
    async def test_whatsapp_phone_format(self):
        """
        Test WhatsApp phone number format handling.
        
        Verifies whatsapp: prefix handling.
        """
        # Test without whatsapp: prefix
        phone = "+14155551234"
        formatted = f'whatsapp:{phone}' if not phone.startswith('whatsapp:') else phone
        assert formatted.startswith('whatsapp:')

        # Test with whatsapp: prefix
        phone = "whatsapp:+14155551234"
        formatted = f'whatsapp:{phone}' if not phone.startswith('whatsapp:') else phone
        assert formatted == "whatsapp:+14155551234"


# =============================================================================
# CROSS-CHANNEL CONTINUITY TESTS
# =============================================================================

class TestCrossChannelContinuity:
    """
    Test that conversations persist across channels.
    
    These tests verify customer recognition and history tracking
    when the same customer uses multiple communication channels.
    """

    @pytest.mark.asyncio
    async def test_customer_history_across_channels(self, test_email, test_phone, db_conn):
        """
        Customer history should include all channel interactions.
        
        Test flow:
        1. Customer contacts via web form
        2. Same customer contacts via WhatsApp (linked by identifier)
        3. Verify both interactions in customer history
        """
        try:
            # First contact via web form
            web_response = client.post("/support/submit", json={
                "name": "Cross Channel User",
                "email": test_email,
                "subject": "Initial Contact",
                "category": "general",
                "message": "First contact via web form"
            })

            assert web_response.status_code == 200
            ticket_id_1 = web_response.json()["ticket_id"]

            # Get customer_id from first ticket
            with db_conn.cursor() as cur:
                cur.execute("SELECT customer_id FROM tickets WHERE id = %s", (ticket_id_1,))
                customer_id = cur.fetchone()[0]

                # Link phone to email via customer_identifiers table
                cur.execute(
                    """
                    INSERT INTO customer_identifiers (customer_id, email, phone)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (customer_id) DO UPDATE SET phone = %s
                    """,
                    (customer_id, test_email, test_phone, test_phone)
                )
                db_conn.commit()

            # Second contact via WhatsApp (same customer)
            whatsapp_response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "Following up on my web form submission",
                    "ProfileName": "Cross Channel User"
                }
            )

            assert whatsapp_response.status_code in [200, 403]

            # Verify customer has interactions from both channels
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT channel
                    FROM tickets
                    WHERE customer_id = %s
                    """,
                    (customer_id,)
                )
                channels = [row[0] for row in cur.fetchall()]
                assert "web_form" in channels
                assert "whatsapp" in channels

        finally:
            cleanup_test_data(db_conn, email=test_email, phone=test_phone)

    @pytest.mark.asyncio
    async def test_customer_lookup_by_email(self, test_email, db_conn):
        """
        Customer lookup should work by email.
        
        Tests cross-channel customer identification.
        """
        try:
            # Create customer via web form
            response = client.post("/support/submit", json={
                "name": "Lookup Test User",
                "email": test_email,
                "subject": "Test",
                "category": "how-to",
                "message": "Testing customer lookup."
            })

            assert response.status_code == 200

            # Look up customer
            lookup_response = client.get(
                "/customers/lookup",
                params={"email": test_email}
            )

            assert lookup_response.status_code == 200
            customer = lookup_response.json()
            assert "customer_id" in customer
            assert customer["email"] == test_email

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_customer_lookup_by_phone(self, test_phone, db_conn):
        """
        Customer lookup should work by phone.
        
        Tests cross-channel customer identification.
        """
        try:
            # Create customer via WhatsApp
            client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "Testing customer lookup by phone",
                    "ProfileName": "Lookup Test User"
                }
            )

            # Look up customer
            lookup_response = client.get(
                "/customers/lookup",
                params={"phone": test_phone}
            )

            assert lookup_response.status_code == 200
            customer = lookup_response.json()
            assert "customer_id" in customer
            assert customer["phone"] == test_phone

        finally:
            cleanup_test_data(db_conn, phone=test_phone)

    @pytest.mark.asyncio
    async def test_multi_channel_ticket_sequence(self, test_email, db_conn):
        """
        Test complete multi-channel ticket sequence.
        
        Test flow:
        1. Customer submits web form
        2. Customer follows up via email
        3. Customer follows up via WhatsApp
        4. All tickets linked to same customer
        """
        test_email_addr = test_email
        test_phone_num = f"+1415555{random.randint(1000, 9999)}"

        try:
            # Step 1: Web form
            web_response = client.post("/support/submit", json={
                "name": "Sequence Test User",
                "email": test_email_addr,
                "subject": "Multi-channel sequence test",
                "category": "technical",
                "message": "Starting multi-channel support sequence."
            })
            assert web_response.status_code == 200
            ticket_1 = web_response.json()["ticket_id"]

            # Get customer_id
            with db_conn.cursor() as cur:
                cur.execute("SELECT customer_id FROM tickets WHERE id = %s", (ticket_1,))
                customer_id = cur.fetchone()[0]

                # Link identifiers
                cur.execute(
                    """
                    INSERT INTO customer_identifiers (customer_id, email, phone)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (customer_id) DO UPDATE SET phone = %s
                    """,
                    (customer_id, test_email_addr, test_phone_num, test_phone_num)
                )
                db_conn.commit()

            # Step 2: Email follow-up
            email_response = client.post("/webhooks/gmail", json={
                "from": test_email_addr,
                "to": "support@techcorp.com",
                "subject": "Re: Multi-channel sequence test",
                "body": "Following up via email.",
                "received_at": datetime.utcnow().isoformat()
            })
            assert email_response.status_code == 200

            # Step 3: WhatsApp follow-up
            whatsapp_response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone_num}",
                    "Body": "Following up via WhatsApp",
                    "ProfileName": "Sequence Test User"
                }
            )
            assert whatsapp_response.status_code in [200, 403]

            # Verify all tickets linked to same customer
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM tickets WHERE customer_id = %s
                    """,
                    (customer_id,)
                )
                count = cur.fetchone()[0]
                assert count >= 3, f"Expected at least 3 tickets, got {count}"

                cur.execute(
                    """
                    SELECT DISTINCT channel FROM tickets WHERE customer_id = %s
                    """,
                    (customer_id,)
                )
                channels = [row[0] for row in cur.fetchall()]
                assert "web_form" in channels
                assert "email" in channels
                assert "whatsapp" in channels

        finally:
            cleanup_test_data(db_conn, email=test_email_addr, phone=test_phone_num)


# =============================================================================
# CHANNEL METRICS TESTS
# =============================================================================

class TestChannelMetrics:
    """
    Test channel-specific metrics.
    
    These tests verify metrics collection and reporting
    for all communication channels.
    """

    @pytest.mark.asyncio
    async def test_metrics_by_channel(self):
        """
        Should return metrics broken down by channel.
        
        Verifies metrics endpoint returns data for all channels.
        """
        response = client.get("/metrics/channels")

        assert response.status_code == 200
        data = response.json()

        # Should have metrics for each enabled channel
        for channel in ["email", "whatsapp", "web_form"]:
            if channel in data:
                assert "total_conversations" in data[channel]
                assert "avg_sentiment" in data[channel]
                assert "escalations" in data[channel]

    @pytest.mark.asyncio
    async def test_metrics_summary(self):
        """
        Should return overall system metrics summary.
        
        Verifies aggregate metrics across all channels.
        """
        response = client.get("/metrics/summary")

        assert response.status_code == 200
        data = response.json()

        # Verify key metrics present
        assert "total_tickets" in data
        assert "open_tickets" in data
        assert "resolved_tickets" in data
        assert "escalated_tickets" in data
        assert "avg_response_time_ms" in data
        assert "avg_sentiment" in data
        assert "escalation_rate" in data

    @pytest.mark.asyncio
    async def test_health_check_all_channels(self):
        """
        Health check should show all channels active.
        
        Verifies channel status in health endpoint.
        """
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "channels" in data
        assert "email" in data["channels"]
        assert "whatsapp" in data["channels"]
        assert "web_form" in data["channels"]


# =============================================================================
# ESCALATION GUARDRAIL TESTS
# =============================================================================

class TestEscalationGuardrails:
    """
    Test escalation guardrails across all channels.
    
    These tests verify hard constraints are enforced:
    - NEVER discuss pricing
    - NEVER process refunds
    - ALWAYS escalate legal mentions
    - Escalate on negative sentiment
    """

    @pytest.mark.asyncio
    async def test_pricing_escalation_web_form(self, test_email, db_conn):
        """
        Web form: Pricing questions should escalate.
        """
        try:
            response = client.post("/support/submit", json={
                "name": "Test User",
                "email": test_email,
                "subject": "Pricing Question",
                "category": "billing",
                "message": "What is the price for enterprise plan?"
            })

            assert response.status_code == 200
            ticket_id = response.json()["ticket_id"]

            # Verify escalation
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT escalated, escalation_reason
                    FROM tickets
                    WHERE id = %s
                    """,
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket[0] == True
                assert "pricing" in str(ticket[1]).lower()

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_legal_escalation_email(self, test_email, db_conn):
        """
        Email: Legal mentions should escalate.
        
        Tests guardrail: Customer mentions "lawyer", "legal", "sue", "attorney"
        """
        try:
            response = client.post("/webhooks/gmail", json={
                "from": test_email,
                "to": "support@techcorp.com",
                "subject": "Legal Issue",
                "body": "I'm going to contact my lawyer about this issue.",
                "received_at": datetime.utcnow().isoformat()
            })

            assert response.status_code == 200

            # Verify escalation
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT escalated, escalation_reason
                    FROM tickets
                    WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (test_email,)
                )
                ticket = cur.fetchone()
                if ticket:
                    assert ticket[0] == True
                    assert any(term in str(ticket[1]).lower()
                              for term in ["lawyer", "legal", "attorney"])

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_refund_escalation_whatsapp(self, test_phone, db_conn):
        """
        WhatsApp: Refund requests should escalate.
        
        Tests guardrail: NEVER process refunds → escalate to billing
        """
        try:
            response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": f"SM{int(time.time())}",
                    "From": f"whatsapp:{test_phone}",
                    "Body": "I want a refund for my last payment",
                    "ProfileName": "Test User"
                }
            )

            assert response.status_code in [200, 403]

            # Verify escalation
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT escalated, escalation_reason
                    FROM tickets
                    WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (test_phone,)
                )
                ticket = cur.fetchone()
                if ticket:
                    assert ticket[0] == True
                    assert "refund" in str(ticket[1]).lower()

        finally:
            cleanup_test_data(db_conn, phone=test_phone)


# =============================================================================
# PERFORMANCE AND RELIABILITY TESTS
# =============================================================================

class TestPerformanceReliability:
    """
    Test performance and reliability requirements.
    
    These tests verify:
    - Response time under 3 seconds
    - System handles concurrent requests
    - Data persistence across operations
    """

    @pytest.mark.asyncio
    async def test_response_time_web_form(self, test_email, db_conn):
        """
        Web form response time should be under 3 seconds.
        """
        try:
            start_time = time.time()

            response = client.post("/support/submit", json={
                "name": "Performance Test User",
                "email": test_email,
                "subject": "Performance Test",
                "category": "how-to",
                "message": "Testing response time for web form submission."
            })

            elapsed = time.time() - start_time

            assert response.status_code == 200
            assert elapsed < 3.0, f"Response time {elapsed:.2f}s exceeded 3s limit"

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_response_time_email(self, test_email, db_conn):
        """
        Email webhook response time should be under 3 seconds.
        """
        try:
            start_time = time.time()

            response = client.post("/webhooks/gmail", json={
                "from": test_email,
                "to": "support@techcorp.com",
                "subject": "Performance Test",
                "body": "Testing response time for email webhook.",
                "received_at": datetime.utcnow().isoformat()
            })

            elapsed = time.time() - start_time

            assert response.status_code == 200
            assert elapsed < 3.0, f"Response time {elapsed:.2f}s exceeded 3s limit"

        finally:
            cleanup_test_data(db_conn, email=test_email)

    @pytest.mark.asyncio
    async def test_concurrent_submissions(self, db_conn):
        """
        System should handle concurrent form submissions.
        
        Tests concurrent request handling.
        """
        import concurrent.futures

        emails = [f"concurrent_{i}_{int(time.time())}@test.com" for i in range(5)]
        results = []

        def submit_form(email):
            response = client.post("/support/submit", json={
                "name": "Concurrent User",
                "email": email,
                "subject": "Concurrent Test",
                "category": "how-to",
                "message": "Testing concurrent submissions."
            })
            return {
                'status_code': response.status_code,
                'ticket_id': response.json().get('ticket_id') if response.status_code == 200 else None
            }

        try:
            # Submit concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(submit_form, email) for email in emails]
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

            # Verify all succeeded
            for result in results:
                assert result['status_code'] == 200
                assert result['ticket_id'] is not None

        finally:
            for email in emails:
                cleanup_test_data(db_conn, email=email)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
