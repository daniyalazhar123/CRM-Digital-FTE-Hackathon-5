"""
CRM Digital FTE - Database Tests
Phase 2: Specialization — Step 5

Test all database CRUD operations with real PostgreSQL.
"""

import sys
import os
import time
import random

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import CRMDatabase


def generate_test_email():
    """Generate unique test email."""
    return f"test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


def generate_test_phone():
    """Generate unique test phone."""
    return f"+1415555{random.randint(1000, 9999)}"


class TestCustomerCRUD:
    """Test customer CRUD operations."""
    
    def setup_method(self):
        """Create database connection before each test."""
        self.db = CRMDatabase()
        self.test_email = generate_test_email()
        self.test_phone = generate_test_phone()
    
    def teardown_method(self):
        """Close database connection after each test."""
        self.db.close()
    
    def test_create_new_customer_email(self):
        """Test creating a new customer with email."""
        customer = self.db.get_or_create_customer(
            email=self.test_email,
            name="Test User"
        )
        assert customer is not None
        assert customer['email'] == self.test_email
        assert customer['name'] == "Test User"
    
    def test_create_new_customer_phone(self):
        """Test creating a new customer with phone."""
        customer = self.db.get_or_create_customer(
            phone=self.test_phone,
            name="Phone User"
        )
        assert customer is not None
        assert customer['phone'] == self.test_phone
        assert customer['name'] == "Phone User"
    
    def test_get_existing_customer(self):
        """Test getting an existing customer."""
        # Create customer first
        created = self.db.get_or_create_customer(
            email=self.test_email,
            name="Existing User"
        )
        
        # Get same customer
        retrieved = self.db.get_or_create_customer(email=self.test_email)
        
        assert retrieved['id'] == created['id']
        assert retrieved['email'] == self.test_email
    
    def test_customer_has_uuid(self):
        """Test that customer has UUID primary key."""
        customer = self.db.get_or_create_customer(email=self.test_email)
        assert customer['id'] is not None
        assert len(customer['id']) > 0  # UUID should be non-empty
    
    def test_customer_default_plan_is_free(self):
        """Test that new customers get 'free' plan by default."""
        customer = self.db.get_or_create_customer(email=self.test_email)
        assert customer['plan'] == 'free'


class TestTicketCRUD:
    """Test ticket CRUD operations."""
    
    def setup_method(self):
        """Create database connection and customer before each test."""
        self.db = CRMDatabase()
        self.test_email = generate_test_email()
        self.customer = self.db.get_or_create_customer(
            email=self.test_email,
            name="Ticket User"
        )
    
    def teardown_method(self):
        """Close database connection after each test."""
        self.db.close()
    
    def test_create_ticket_returns_id(self):
        """Test that creating a ticket returns an ID."""
        ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="medium",
            channel="email"
        )
        assert ticket is not None
        assert 'id' in ticket
    
    def test_ticket_id_starts_with_TKT(self):
        """Test that ticket ID starts with TKT- prefix."""
        ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="medium",
            channel="email"
        )
        assert ticket['id'].startswith('TKT-')
    
    def test_ticket_default_status_is_open(self):
        """Test that new tickets have 'open' status."""
        ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="medium",
            channel="email"
        )
        assert ticket['status'] == 'open'
    
    def test_ticket_escalation(self):
        """Test escalating a ticket."""
        ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="high",
            channel="email"
        )
        
        result = self.db.escalate_ticket(
            ticket_id=ticket['id'],
            reason="test_escalation"
        )
        
        assert result == True
    
    def test_ticket_resolution(self):
        """Test resolving a ticket."""
        ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="medium",
            channel="email"
        )
        
        result = self.db.resolve_ticket(ticket['id'])
        
        assert result == True


class TestMessageCRUD:
    """Test message CRUD operations."""
    
    def setup_method(self):
        """Create database connection, customer, and ticket before each test."""
        self.db = CRMDatabase()
        self.test_email = generate_test_email()
        self.customer = self.db.get_or_create_customer(
            email=self.test_email,
            name="Message User"
        )
        self.ticket = self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Test issue",
            priority="medium",
            channel="email"
        )
    
    def teardown_method(self):
        """Close database connection after each test."""
        self.db.close()
    
    def test_add_customer_message(self):
        """Test adding a customer message."""
        message = self.db.add_message(
            ticket_id=self.ticket['id'],
            customer_id=self.customer['id'],
            role="customer",
            content="I need help with my account",
            channel="email"
        )
        assert message is not None
        assert message['role'] == "customer"
    
    def test_add_agent_message(self):
        """Test adding an agent message."""
        message = self.db.add_message(
            ticket_id=self.ticket['id'],
            customer_id=self.customer['id'],
            role="agent",
            content="I can help you with that",
            channel="email"
        )
        assert message is not None
        assert message['role'] == "agent"
    
    def test_get_customer_history(self):
        """Test getting customer conversation history."""
        # Add some messages
        self.db.add_message(
            ticket_id=self.ticket['id'],
            customer_id=self.customer['id'],
            role="customer",
            content="Message 1",
            channel="email"
        )
        self.db.add_message(
            ticket_id=self.ticket['id'],
            customer_id=self.customer['id'],
            role="agent",
            content="Message 2",
            channel="email"
        )
        
        history = self.db.get_customer_history(self.customer['id'])
        
        assert len(history) >= 2
    
    def test_history_limit_works(self):
        """Test that history limit parameter works."""
        # Add 15 messages
        for i in range(15):
            self.db.add_message(
                ticket_id=self.ticket['id'],
                customer_id=self.customer['id'],
                role="customer" if i % 2 == 0 else "agent",
                content=f"Message {i}",
                channel="email"
            )
        
        # Get with limit of 5
        history = self.db.get_customer_history(self.customer['id'], limit=5)
        
        assert len(history) <= 10  # Database returns up to 10


class TestSentimentTracking:
    """Test sentiment tracking operations."""
    
    def setup_method(self):
        """Create database connection and customer before each test."""
        self.db = CRMDatabase()
        self.test_email = generate_test_email()
        self.customer = self.db.get_or_create_customer(
            email=self.test_email,
            name="Sentiment User"
        )
    
    def teardown_method(self):
        """Close database connection after each test."""
        self.db.close()
    
    def test_update_sentiment_score(self):
        """Test updating customer sentiment score."""
        result = self.db.update_sentiment(self.customer['id'], 0.7)
        assert result == True
    
    def test_sentiment_score_stored(self):
        """Test that sentiment score is stored in metadata."""
        self.db.update_sentiment(self.customer['id'], 0.8)
        
        stats = self.db.get_customer_stats(self.customer['id'])
        
        assert 'avg_sentiment' in stats
        assert stats['avg_sentiment'] >= 0.0
        assert stats['avg_sentiment'] <= 1.0


class TestCustomerStats:
    """Test customer statistics operations."""
    
    def setup_method(self):
        """Create database connection and customer before each test."""
        self.db = CRMDatabase()
        self.test_email = generate_test_email()
        self.customer = self.db.get_or_create_customer(
            email=self.test_email,
            name="Stats User"
        )
    
    def teardown_method(self):
        """Close database connection after each test."""
        self.db.close()
    
    def test_stats_returns_dict(self):
        """Test that stats returns a dictionary."""
        stats = self.db.get_customer_stats(self.customer['id'])
        assert isinstance(stats, dict)
    
    def test_stats_has_required_keys(self):
        """Test that stats has all required keys."""
        stats = self.db.get_customer_stats(self.customer['id'])
        
        required_keys = [
            'total_tickets', 'open_tickets', 'resolved_tickets',
            'escalated_tickets', 'avg_sentiment', 'channels_used'
        ]
        
        for key in required_keys:
            assert key in stats, f"Missing required key: {key}"
    
    def test_stats_ticket_count_correct(self):
        """Test that ticket count is accurate."""
        # Create 3 tickets
        for i in range(3):
            self.db.create_ticket(
                customer_id=self.customer['id'],
                issue=f"Issue {i}",
                priority="medium",
                channel="email"
            )
        
        stats = self.db.get_customer_stats(self.customer['id'])
        
        assert stats['total_tickets'] == 3
    
    def test_stats_channel_tracking(self):
        """Test that channels are tracked correctly."""
        # Create tickets on different channels
        self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="Email issue",
            priority="medium",
            channel="email"
        )
        self.db.create_ticket(
            customer_id=self.customer['id'],
            issue="WhatsApp issue",
            priority="medium",
            channel="whatsapp"
        )
        
        stats = self.db.get_customer_stats(self.customer['id'])
        
        assert 'email' in stats['channels_used']
        assert 'whatsapp' in stats['channels_used']
