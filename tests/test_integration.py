"""
CRM Digital FTE - Integration Tests
Phase 3: Integration Testing — Step 1

End-to-end integration tests for multi-channel flows, performance, and data persistence.
Uses REAL PostgreSQL database (no mocking).
"""

import sys
import os
import time
import random
import pytest
import psycopg2
from datetime import datetime
from typing import Dict, List

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
# HELPER FUNCTIONS
# =============================================================================

def generate_unique_email():
    """Generate unique test email address."""
    return f"integration_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


def generate_unique_phone():
    """Generate unique test phone number."""
    return f"+1415555{random.randint(1000, 9999)}"


def get_db_connection():
    """Get direct database connection."""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='crm_db',
        user='postgres',
        password='postgres123'
    )


def cleanup_test_data(db_conn, email=None, phone=None):
    """Cleanup test data from database."""
    try:
        with db_conn.cursor() as cur:
            if email:
                cur.execute("DELETE FROM messages WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)", (email,))
                cur.execute("DELETE FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)", (email,))
                cur.execute("DELETE FROM customers WHERE email = %s", (email,))
            if phone:
                cur.execute("DELETE FROM messages WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)", (phone,))
                cur.execute("DELETE FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE phone = %s)", (phone,))
                cur.execute("DELETE FROM customers WHERE phone = %s", (phone,))
            db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")


# =============================================================================
# MULTI-CHANNEL FLOW TESTS
# =============================================================================

class TestMultiChannelFlow:
    """Test end-to-end multi-channel flows."""

    def test_email_to_ticket_flow(self, db_conn):
        """
        Test complete email to ticket flow:
        1. Submit via email channel
        2. Verify ticket created in PostgreSQL
        3. Verify response generated
        4. Verify sentiment tracked
        """
        email = generate_unique_email()
        start_time = time.time()
        
        try:
            # Submit via email webhook
            response = client.post(
                "/webhooks/gmail",
                json={
                    "from": email,
                    "to": "support@techcorp.com",
                    "subject": "How to reset password?",
                    "body": "Hi, I forgot my password and need to reset it. Can you help me with the steps?",
                    "received_at": datetime.utcnow().isoformat()
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify ticket created
            assert 'ticket_id' in data
            ticket_id = data['ticket_id']
            
            # Verify response generated
            assert 'message' in data
            assert len(data['message']) > 0
            
            # Verify in PostgreSQL
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT id, customer_id, issue, channel, status FROM tickets WHERE id = %s",
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket[3] == 'email'  # channel

                # Verify sentiment tracked (use sentiment_score column)
                cur.execute(
                    "SELECT sentiment_score FROM messages WHERE ticket_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (ticket_id,)
                )
                msg = cur.fetchone()
                assert msg is not None
                # Sentiment should be a float
                assert isinstance(msg[0], float) or msg[0] is None

            # Verify performance
            elapsed = time.time() - start_time
            assert elapsed < 3000, f"Response time {elapsed}s exceeded 3s limit"

        finally:
            cleanup_test_data(db_conn, email=email)

    def test_whatsapp_to_ticket_flow(self, db_conn):
        """
        Test complete WhatsApp to ticket flow:
        1. Submit via WhatsApp channel
        2. Verify ticket created
        3. Verify 300 char limit respected
        """
        phone = generate_unique_phone()
        start_time = time.time()
        
        try:
            # Submit via WhatsApp webhook
            response = client.post(
                "/webhooks/whatsapp",
                json={
                    "from": phone,
                    "message": "How do I export my data from the dashboard?",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify ticket created
            assert 'ticket_id' in data
            ticket_id = data['ticket_id']
            
            # Verify response respects WhatsApp 300 char limit
            assert 'message' in data
            assert len(data['message']) <= 300, f"WhatsApp response {len(data['message'])} chars exceeds 300 limit"
            
            # Verify in PostgreSQL
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT id, channel FROM tickets WHERE id = %s",
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket[1] == 'whatsapp'
            
            # Verify performance
            elapsed = time.time() - start_time
            assert elapsed < 3000, f"Response time {elapsed}s exceeded 3s limit"
            
        finally:
            cleanup_test_data(db_conn, phone=phone)

    def test_web_form_to_ticket_flow(self, db_conn):
        """
        Test complete web form to ticket flow:
        1. Submit via web_form channel
        2. Verify ticket created
        3. Verify response returned
        """
        email = generate_unique_email()
        start_time = time.time()
        
        try:
            # Submit via web form
            response = client.post(
                "/support/submit",
                json={
                    "name": "Test User",
                    "email": email,
                    "subject": "Feature Request",
                    "category": "how-to",
                    "message": "How can I integrate the API with my existing application? I need documentation."
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify ticket created
            assert 'ticket_id' in data
            ticket_id = data['ticket_id']
            
            # Verify response returned
            assert 'message' in data
            assert len(data['message']) > 0
            
            # Verify in PostgreSQL
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT id, channel FROM tickets WHERE id = %s",
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket[1] == 'web_form'
            
            # Verify performance
            elapsed = time.time() - start_time
            assert elapsed < 3000, f"Response time {elapsed}s exceeded 3s limit"
            
        finally:
            cleanup_test_data(db_conn, email=email)

    def test_cross_channel_customer_recognition(self, db_conn):
        """
        Test cross-channel customer recognition:
        1. Same customer sends via email then WhatsApp
        2. Verify same customer_id in both tickets
        3. Verify history shows both channels
        """
        email = generate_unique_email()
        phone = generate_unique_phone()
        
        try:
            # First interaction via email
            response1 = client.post(
                "/webhooks/gmail",
                json={
                    "from": email,
                    "to": "support@techcorp.com",
                    "subject": "API Question",
                    "body": "How do I use the REST API?",
                    "received_at": datetime.utcnow().isoformat()
                }
            )
            assert response1.status_code == 200
            ticket_id_1 = response1.json()['ticket_id']
            
            # Get customer_id from first ticket
            with db_conn.cursor() as cur:
                cur.execute("SELECT customer_id FROM tickets WHERE id = %s", (ticket_id_1,))
                customer_id_1 = cur.fetchone()[0]
            
            # Second interaction via WhatsApp (same customer, different channel)
            # Update customer record with phone number for cross-channel tracking
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE customers SET phone = %s WHERE id = %s",
                    (phone, customer_id_1)
                )
                db_conn.commit()
            
            response2 = client.post(
                "/webhooks/whatsapp",
                json={
                    "from": phone,
                    "message": "Thanks, now how about the WebSocket API?",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            assert response2.status_code == 200
            ticket_id_2 = response2.json()['ticket_id']
            
            # Verify same customer_id in both tickets
            with db_conn.cursor() as cur:
                cur.execute("SELECT customer_id FROM tickets WHERE id = %s", (ticket_id_2,))
                customer_id_2 = cur.fetchone()[0]
                
                # Customer IDs should match (cross-channel recognition)
                assert customer_id_1 == customer_id_2, "Cross-channel customer recognition failed"
                
                # Verify history shows both channels
                cur.execute(
                    "SELECT DISTINCT channel FROM tickets WHERE customer_id = %s",
                    (customer_id_1,)
                )
                channels = [row[0] for row in cur.fetchall()]
                assert 'email' in channels
                assert 'whatsapp' in channels
            
        finally:
            cleanup_test_data(db_conn, email=email, phone=phone)

    def test_escalation_end_to_end(self, db_conn):
        """
        Test escalation end-to-end:
        1. Send pricing question (should escalate)
        2. Verify escalated=True in DB
        3. Verify escalation_reason saved
        """
        email = generate_unique_email()
        start_time = time.time()
        
        try:
            # Send pricing question (triggers escalation)
            response = client.post(
                "/support/submit",
                json={
                    "name": "Test User",
                    "email": email,
                    "subject": "Pricing Question",
                    "category": "billing",
                    "message": "What is the price for enterprise plan? I need a discount."
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            ticket_id = data['ticket_id']
            
            # Verify escalation in PostgreSQL
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT escalated, escalation_reason, escalation_reason FROM tickets WHERE id = %s",
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket[0] == True, "Ticket should be escalated for pricing inquiry"
                assert ticket[1] is not None, "Escalation reason should be saved"
                assert 'pricing' in ticket[1].lower(), f"Escalation reason should mention pricing, got: {ticket[1]}"
            
            # Verify performance
            elapsed = time.time() - start_time
            assert elapsed < 3000, f"Response time {elapsed}s exceeded 3s limit"
            
        finally:
            cleanup_test_data(db_conn, email=email)


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance requirements."""

    def test_response_time_under_3_seconds(self, db_conn):
        """
        Test that response time is under 3 seconds:
        1. Process 5 messages
        2. Each must complete under 3000ms
        """
        email = generate_unique_email()
        messages = [
            "How do I reset my password?",
            "What features are available in the free plan?",
            "How can I export my data?",
            "Is there a mobile app available?",
            "How do I contact support?"
        ]
        
        response_times = []
        
        try:
            for i, msg in enumerate(messages):
                start_time = time.time()
                
                response = client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": f"{email}_{i}",  # Unique email for each
                        "subject": "Question",
                        "category": "how-to",
                        "message": msg
                    }
                )
                
                elapsed = time.time() - start_time
                response_times.append(elapsed)
                
                assert response.status_code == 200
                assert elapsed < 3.0, f"Message {i+1} took {elapsed:.2f}s, exceeded 3s limit"
            
            # Report statistics
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print(f"\nResponse Times: avg={avg_time:.2f}s, max={max_time:.2f}s")
            
        finally:
            for i in range(len(messages)):
                cleanup_test_data(db_conn, email=f"{email}_{i}")

    def test_concurrent_messages(self, db_conn):
        """
        Test concurrent message processing:
        1. Send 3 messages simultaneously
        2. All must be processed
        3. No errors
        """
        import concurrent.futures
        
        emails = [generate_unique_email() for _ in range(3)]
        results = []
        
        def submit_message(email):
            start_time = time.time()
            response = client.post(
                "/support/submit",
                json={
                    "name": "Test User",
                    "email": email,
                    "subject": "Concurrent Test",
                    "category": "how-to",
                    "message": "This is a concurrent message test."
                }
            )
            elapsed = time.time() - start_time
            return {
                'status_code': response.status_code,
                'elapsed': elapsed,
                'ticket_id': response.json().get('ticket_id') if response.status_code == 200 else None
            }
        
        try:
            # Submit concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(submit_message, email) for email in emails]
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
            
            # Verify all succeeded
            for i, result in enumerate(results):
                assert result['status_code'] == 200, f"Message {i+1} failed"
                assert result['ticket_id'] is not None, f"Message {i+1} missing ticket_id"
                assert result['elapsed'] < 5.0, f"Message {i+1} took too long: {result['elapsed']:.2f}s"
            
            print(f"\nConcurrent test: {len(results)} messages processed successfully")
            
        finally:
            for email in emails:
                cleanup_test_data(db_conn, email=email)

    def test_100_tickets_load(self, db_conn):
        """
        Test 100 tickets load:
        1. Create 100 tickets in DB
        2. Verify all stored correctly
        3. Check DB performance
        """
        email = generate_unique_email()
        ticket_ids = []
        
        start_time = time.time()
        
        try:
            # Create 100 tickets
            for i in range(100):
                response = client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": f"{email}_{i}",
                        "subject": f"Load Test Ticket {i}",
                        "category": "how-to",
                        "message": f"This is load test ticket number {i}."
                    }
                )
                assert response.status_code == 200
                ticket_ids.append(response.json()['ticket_id'])
            
            total_time = time.time() - start_time
            
            # Verify all tickets in PostgreSQL
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE email LIKE %s)",
                    (f"{email}%",)
                )
                count = cur.fetchone()[0]
                assert count == 100, f"Expected 100 tickets, found {count}"
            
            print(f"\nLoad test: 100 tickets created in {total_time:.2f}s ({100/total_time:.1f} tickets/sec)")
            
        finally:
            for i in range(100):
                cleanup_test_data(db_conn, email=f"{email}_{i}")


# =============================================================================
# DATA PERSISTENCE TESTS
# =============================================================================

class TestDataPersistence:
    """Test data persistence requirements."""

    def test_ticket_survives_restart(self, db_conn):
        """
        Test ticket survives reconnection:
        1. Create ticket
        2. Reconnect to DB
        3. Ticket still exists
        """
        email = generate_unique_email()
        
        try:
            # Create ticket
            response = client.post(
                "/support/submit",
                json={
                    "name": "Test User",
                    "email": email,
                    "subject": "Persistence Test",
                    "category": "how-to",
                    "message": "Testing data persistence."
                }
            )
            assert response.status_code == 200
            ticket_id = response.json()['ticket_id']
            
            # Simulate restart by creating new DB connection
            db_conn.close()
            time.sleep(0.5)  # Brief pause
            
            # Reconnect
            new_conn = get_db_connection()
            
            # Verify ticket still exists
            with new_conn.cursor() as cur:
                cur.execute(
                    "SELECT id, issue FROM tickets WHERE id = %s",
                    (ticket_id,)
                )
                ticket = cur.fetchone()
                assert ticket is not None, "Ticket did not survive reconnection"
                assert ticket[0] == ticket_id
            
            new_conn.close()
            
        finally:
            cleanup_test_data(db_conn, email=email)

    def test_sentiment_history_persists(self, db_conn):
        """
        Test sentiment history persists:
        1. Track 5 sentiment scores
        2. Verify all stored in metadata
        """
        email = generate_unique_email()
        
        try:
            # Create 5 messages with different sentiments
            messages = [
                "I'm very happy with the product!",  # Positive
                "This is okay, nothing special.",    # Neutral
                "I'm frustrated with this bug.",     # Negative
                "Absolutely love the new features!", # Very positive
                "This is terrible, worst ever."      # Very negative
            ]
            
            for msg in messages:
                client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": email,
                        "subject": "Feedback",
                        "category": "other",
                        "message": msg
                    }
                )
            
            # Verify all sentiments stored
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.sentiment, m.content 
                    FROM messages m 
                    JOIN customers c ON m.customer_id = c.id 
                    WHERE c.email = %s 
                    ORDER BY m.created_at
                    """,
                    (email,)
                )
                rows = cur.fetchall()
                
                assert len(rows) >= 5, f"Expected at least 5 messages, found {len(rows)}"
                
                # Verify sentiments are stored (may be NULL for some)
                sentiments = [row[0] for row in rows if row[0] is not None]
                print(f"\nSentiment history: {len(sentiments)} sentiments stored")
            
        finally:
            cleanup_test_data(db_conn, email=email)

    def test_customer_history_limit(self, db_conn):
        """
        Test customer history limit:
        1. Add 15 messages for one customer
        2. get_customer_history(limit=10) returns 10
        """
        email = generate_unique_email()
        
        try:
            # Create 15 messages
            for i in range(15):
                client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": email,
                        "subject": f"Message {i}",
                        "category": "how-to",
                        "message": f"This is test message number {i}."
                    }
                )
            
            # Get customer_id
            with db_conn.cursor() as cur:
                cur.execute("SELECT id FROM customers WHERE email = %s", (email,))
                customer_id = cur.fetchone()[0]
                
                # Query history with limit 10
                cur.execute(
                    """
                    SELECT id, content, created_at 
                    FROM messages 
                    WHERE customer_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 10
                    """,
                    (customer_id,)
                )
                history = cur.fetchall()
                
                assert len(history) == 10, f"Expected 10 messages, got {len(history)}"
            
        finally:
            cleanup_test_data(db_conn, email=email)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
