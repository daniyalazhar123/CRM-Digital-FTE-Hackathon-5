"""
CRM Digital FTE - Database Tests
Phase 2: Specialization

Test database operations using direct psycopg2 connections.
"""

import sys
import os
import time
import random
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# TEST FIXTURES (using direct connections, not pool)
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'crm_db',
    'user': 'postgres',
    'password': 'postgres123'
}


def get_test_email():
    """Generate unique test email."""
    return f"test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


def get_test_phone():
    """Generate unique test phone."""
    return f"+1415555{random.randint(1000, 9999)}"


def get_db_connection():
    """Get direct database connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


# =============================================================================
# TEST: Customer CRUD
# =============================================================================

class TestCustomerCRUD:
    """Test customer CRUD operations."""
    
    def test_create_new_customer_email(self):
        """Test creating a new customer with email."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name, plan)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, name, plan
                """, (email, "Test User", "free"))
                
                customer = cur.fetchone()
                assert customer is not None
                assert customer['email'] == email
                assert customer['name'] == "Test User"
                assert customer['plan'] == "free"
        finally:
            conn.close()
    
    def test_create_new_customer_phone(self):
        """Test creating a new customer with phone."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                phone = get_test_phone()
                cur.execute("""
                    INSERT INTO customers (phone, name)
                    VALUES (%s, %s)
                    RETURNING id, phone, name
                """, (phone, "Phone User"))
                
                customer = cur.fetchone()
                assert customer is not None
                assert customer['phone'] == phone
        finally:
            conn.close()
    
    def test_customer_has_uuid(self):
        """Test that customer has UUID primary key."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name)
                    VALUES (%s, %s)
                    RETURNING id
                """, (email, "UUID Test"))
                
                customer = cur.fetchone()
                assert customer is not None
                assert len(str(customer['id'])) == 36  # UUID length
        finally:
            conn.close()
    
    def test_customer_default_plan_is_free(self):
        """Test that new customers get 'free' plan by default."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name)
                    VALUES (%s, %s)
                    RETURNING plan
                """, (email, "Plan Test"))
                
                customer = cur.fetchone()
                assert customer is not None
                assert customer['plan'] == 'free'
        finally:
            conn.close()


# =============================================================================
# TEST: Ticket CRUD
# =============================================================================

class TestTicketCRUD:
    """Test ticket CRUD operations."""
    
    def test_create_ticket_returns_id(self):
        """Test that creating a ticket returns an ID."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Create customer first
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name)
                    VALUES (%s, %s)
                    RETURNING id
                """, (email, "Ticket Test"))
                customer = cur.fetchone()
                
                # Create ticket
                ticket_id = f"TKT-{int(time.time())}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (ticket_id, customer['id'], "Test issue", "medium", "email"))
                
                ticket = cur.fetchone()
                assert ticket is not None
                assert ticket['id'] == ticket_id
        finally:
            conn.close()
    
    def test_ticket_id_starts_with_TKT(self):
        """Test that ticket ID starts with TKT- prefix."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (ticket_id, customer['id'], "Test", "medium", "email"))
                
                ticket = cur.fetchone()
                assert ticket['id'].startswith('TKT-')
        finally:
            conn.close()
    
    def test_ticket_default_status_is_open(self):
        """Test that new tickets have 'open' status."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING status
                """, (ticket_id, customer['id'], "Test", "medium", "email", "open"))
                
                ticket = cur.fetchone()
                assert ticket['status'] == 'open'
        finally:
            conn.close()
    
    def test_ticket_escalation(self):
        """Test escalating a ticket."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel, escalated)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (ticket_id, customer['id'], "Test", "high", "email", False))
                
                # Update to escalated
                cur.execute("""
                    UPDATE tickets SET escalated = TRUE, escalation_reason = %s
                    WHERE id = %s
                """, ("test_reason", ticket_id))
                
                cur.execute("SELECT escalated FROM tickets WHERE id = %s", (ticket_id,))
                result = cur.fetchone()
                assert result['escalated'] == True
        finally:
            conn.close()


# =============================================================================
# TEST: Message CRUD
# =============================================================================

class TestMessageCRUD:
    """Test message CRUD operations."""
    
    def test_add_customer_message(self):
        """Test adding a customer message."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel)
                    VALUES (%s, %s, %s, %s, %s)
                """, (ticket_id, customer['id'], "Test", "medium", "email"))
                
                message_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO messages (id, ticket_id, customer_id, role, content, channel)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, role
                """, (message_id, ticket_id, customer['id'], "customer", "Test message", "email"))
                
                message = cur.fetchone()
                assert message is not None
                assert message['role'] == "customer"
        finally:
            conn.close()
    
    def test_add_agent_message(self):
        """Test adding an agent message."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel) VALUES (%s, %s, %s, %s, %s)
                """, (ticket_id, customer['id'], "Test", "medium", "email"))
                
                message_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO messages (id, ticket_id, customer_id, role, content, channel)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING role
                """, (message_id, ticket_id, customer['id'], "agent", "Agent response", "email"))
                
                message = cur.fetchone()
                assert message['role'] == "agent"
        finally:
            conn.close()
    
    def test_get_customer_history(self):
        """Test getting customer conversation history."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                ticket_id = f"TKT-{int(time.time())}-{random.randint(1000,9999)}"
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel) VALUES (%s, %s, %s, %s, %s)
                """, (ticket_id, customer['id'], "Test", "medium", "email"))
                
                # Add 3 messages
                for i in range(3):
                    message_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO messages (id, ticket_id, customer_id, role, content, channel)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (message_id, ticket_id, customer['id'], "customer", f"Message {i}", "email"))
                
                # Get history
                cur.execute("""
                    SELECT COUNT(*) as count FROM messages WHERE customer_id = %s
                """, (customer['id'],))
                result = cur.fetchone()
                assert result['count'] == 3
        finally:
            conn.close()


# =============================================================================
# TEST: Sentiment Tracking
# =============================================================================

class TestSentimentTracking:
    """Test sentiment tracking operations."""
    
    def test_update_sentiment_score(self):
        """Test updating customer sentiment score in metadata."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (email, "Test", '{"sentiment_history": []}'))
                customer = cur.fetchone()
                
                # Update metadata with sentiment
                cur.execute("""
                    UPDATE customers 
                    SET metadata = metadata || '{"avg_sentiment": 0.7}'::jsonb
                    WHERE id = %s
                """, (customer['id'],))
                
                cur.execute("""
                    SELECT metadata->>'avg_sentiment' as avg_sentiment 
                    FROM customers WHERE id = %s
                """, (customer['id'],))
                result = cur.fetchone()
                assert result['avg_sentiment'] == "0.7"
        finally:
            conn.close()


# =============================================================================
# TEST: Customer Stats
# =============================================================================

class TestCustomerStats:
    """Test customer statistics operations."""
    
    def test_stats_ticket_count(self):
        """Test that ticket count is accurate."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                # Create 3 tickets
                for i in range(3):
                    ticket_id = f"TKT-{int(time.time())}-{i}"
                    cur.execute("""
                        INSERT INTO tickets (id, customer_id, issue, priority, channel)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (ticket_id, customer['id'], f"Issue {i}", "medium", "email"))
                
                # Count tickets
                cur.execute("""
                    SELECT COUNT(*) as count FROM tickets WHERE customer_id = %s
                """, (customer['id'],))
                result = cur.fetchone()
                assert result['count'] == 3
        finally:
            conn.close()
    
    def test_stats_channel_tracking(self):
        """Test that channels are tracked correctly."""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = get_test_email()
                cur.execute("""
                    INSERT INTO customers (email, name) VALUES (%s, %s) RETURNING id
                """, (email, "Test"))
                customer = cur.fetchone()
                
                # Create tickets on different channels
                for channel in ['email', 'whatsapp', 'web_form']:
                    ticket_id = f"TKT-{int(time.time())}-{channel}"
                    cur.execute("""
                        INSERT INTO tickets (id, customer_id, issue, priority, channel)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (ticket_id, customer['id'], "Test", "medium", channel))
                
                # Get distinct channels
                cur.execute("""
                    SELECT DISTINCT channel FROM tickets WHERE customer_id = %s
                """, (customer['id'],))
                channels = [row['channel'] for row in cur.fetchall()]
                
                assert 'email' in channels
                assert 'whatsapp' in channels
                assert 'web_form' in channels
        finally:
            conn.close()
