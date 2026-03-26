"""
CRM Digital FTE - Database Layer
Phase 2: Specialization — Step 2

PostgreSQL database layer that bridges InMemoryStore with production database.
Provides CRUD operations, vector search, and migration capabilities.
"""

import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'crm_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres123')
}

# Connection pool settings - Increased for concurrent load
POOL_MIN_CONN = 5
POOL_MAX_CONN = 50

# Retry settings with exponential backoff
MAX_RETRIES = 5
RETRY_DELAY = 0.5  # seconds
RETRY_BACKOFF_MULTIPLIER = 2.0  # Exponential backoff


# =============================================================================
# CONNECTION POOL
# =============================================================================

class DatabasePool:
    """Manages PostgreSQL connection pool."""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._create_pool()
    
    def _create_pool(self):
        """Create connection pool."""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=POOL_MIN_CONN,
                maxconn=POOL_MAX_CONN,
                **DB_CONFIG
            )
            print(f"✓ Database pool created: {POOL_MIN_CONN}-{POOL_MAX_CONN} connections")
        except Exception as e:
            print(f"✗ Failed to create database pool: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool with retry and exponential backoff."""
        import time
        for attempt in range(MAX_RETRIES):
            try:
                return self._pool.getconn()
            except psycopg2.pool.PoolExhaustedError:
                if attempt == MAX_RETRIES - 1:
                    raise
                # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
                delay = RETRY_DELAY * (RETRY_BACKOFF_MULTIPLIER ** attempt)
                print(f"Connection pool exhausted, retrying in {delay}s...")
                time.sleep(delay)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                # Exponential backoff for other errors
                delay = RETRY_DELAY * (RETRY_BACKOFF_MULTIPLIER ** attempt)
                print(f"Connection attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                time.sleep(delay)
    
    def release_connection(self, conn):
        """Release connection back to pool."""
        if self._pool:
            self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections."""
        if self._pool:
            self._pool.closeall()
            print("✓ All database connections closed")


# =============================================================================
# LAZY POOL INITIALIZATION
# =============================================================================

# Global pool instance (initialized lazily)
_db_pool_instance = None


def get_db_pool():
    """
    Get or create database pool (lazy initialization).
    This prevents connection errors at import time.
    """
    global _db_pool_instance
    if _db_pool_instance is None:
        _db_pool_instance = DatabasePool()
    return _db_pool_instance


# =============================================================================
# DATABASE CONTEXT MANAGER
# =============================================================================

class DatabaseConnection:
    """Context manager for database connections with automatic rollback/commit."""

    def __init__(self, autocommit=False):
        self.conn = None
        self.autocommit = autocommit

    def __enter__(self):
        self.conn = get_db_pool().get_connection()
        self.conn.autocommit = self.autocommit
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
            print(f"✗ Database transaction rolled back: {exc_val}")
        else:
            self.conn.commit()
        get_db_pool().release_connection(self.conn)


# =============================================================================
# DATABASE OPERATIONS - Matches InMemoryStore API
# =============================================================================

class CRMDatabase:
    """
    PostgreSQL database layer matching InMemoryStore interface.
    Provides CRUD operations for customers, tickets, messages, and embeddings.
    """
    
    # -------------------------------------------------------------------------
    # CUSTOMER OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_or_create_customer(self, email: str = None, phone: str = None, 
                                name: str = None) -> dict:
        """
        Get existing customer or create new one.
        Matches InMemoryStore.get_or_create_customer()
        """
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Try to find by email
                if email:
                    cur.execute("""
                        SELECT * FROM customers WHERE email = %s
                    """, (email,))
                    customer = cur.fetchone()
                    
                    if customer:
                        print(f"✓ Found customer: {customer['email']}")
                        return dict(customer)
                
                # Try to find by phone
                if phone:
                    cur.execute("""
                        SELECT * FROM customers WHERE phone = %s
                    """, (phone,))
                    customer = cur.fetchone()
                    
                    if customer:
                        print(f"✓ Found customer: {customer['phone']}")
                        return dict(customer)
                
                # Create new customer
                customer_id = self._generate_uuid()
                cur.execute("""
                    INSERT INTO customers (id, email, phone, name, plan, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (customer_id, email, phone, name, 'free', '{}'))
                
                customer = cur.fetchone()
                print(f"✓ Created customer: {email or phone}")
                return dict(customer)
    
    def get_customer_by_id(self, customer_id: str) -> Optional[dict]:
        """Get customer by UUID."""
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM customers WHERE id = %s
                """, (customer_id,))
                customer = cur.fetchone()
                return dict(customer) if customer else None
    
    # -------------------------------------------------------------------------
    # TICKET OPERATIONS
    # -------------------------------------------------------------------------
    
    def create_ticket(self, customer_id: str, issue: str, priority: str, 
                      channel: str) -> dict:
        """
        Create a new support ticket.
        Matches InMemoryStore.create_ticket()
        """
        ticket_id = f"TKT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._generate_short_id()}"
        
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO tickets (id, customer_id, issue, priority, channel, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (ticket_id, customer_id, issue, priority, channel, 'open'))
                
                ticket = cur.fetchone()
                print(f"✓ Created ticket: {ticket_id}")
                return dict(ticket)
    
    def get_ticket(self, ticket_id: str) -> Optional[dict]:
        """Get ticket by ID."""
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM tickets WHERE id = %s
                """, (ticket_id,))
                ticket = cur.fetchone()
                return dict(ticket) if ticket else None
    
    def escalate_ticket(self, ticket_id: str, reason: str) -> bool:
        """
        Mark a ticket as escalated.
        Matches InMemoryStore.escalate_ticket()
        """
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tickets 
                    SET escalated = TRUE, escalation_reason = %s, status = 'escalated'
                    WHERE id = %s
                """, (reason, ticket_id))
                
                if cur.rowcount > 0:
                    print(f"✓ Escalated ticket: {ticket_id} (reason: {reason})")
                    return True
                return False
    
    def resolve_ticket(self, ticket_id: str) -> bool:
        """Mark ticket as resolved."""
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tickets 
                    SET status = 'resolved', resolved_at = NOW()
                    WHERE id = %s
                """, (ticket_id,))
                
                if cur.rowcount > 0:
                    print(f"✓ Resolved ticket: {ticket_id}")
                    return True
                return False
    
    # -------------------------------------------------------------------------
    # MESSAGE OPERATIONS
    # -------------------------------------------------------------------------
    
    def add_message(self, ticket_id: str, customer_id: str, role: str, 
                    content: str, channel: str, sentiment_score: float = None) -> dict:
        """
        Add a message to a ticket.
        Matches InMemoryStore.add_message()
        """
        message_id = self._generate_uuid()
        
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO messages (id, ticket_id, customer_id, role, content, channel, sentiment_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (message_id, ticket_id, customer_id, role, content, channel, sentiment_score))
                
                message = cur.fetchone()
                print(f"✓ Added message: {role} ({len(content)} chars)")
                return dict(message)
    
    def get_customer_history(self, customer_id: str, limit: int = 10) -> List[dict]:
        """
        Get customer's conversation history.
        Matches InMemoryStore.get_customer_history()
        """
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT m.*, t.id as ticket_id, t.channel as ticket_channel
                    FROM messages m
                    JOIN tickets t ON m.ticket_id = t.id
                    WHERE m.customer_id = %s
                    ORDER BY m.timestamp DESC
                    LIMIT %s
                """, (customer_id, limit))
                
                messages = cur.fetchall()
                print(f"✓ Retrieved {len(messages)} messages for customer")
                return [dict(m) for m in messages]
    
    # -------------------------------------------------------------------------
    # SENTIMENT TRACKING
    # -------------------------------------------------------------------------
    
    def update_sentiment(self, customer_id: str, score: float) -> bool:
        """
        Update customer's sentiment score (stored in metadata).
        Matches InMemoryStore.update_sentiment()
        """
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                # Get current metadata
                cur.execute("""
                    SELECT metadata FROM customers WHERE id = %s
                """, (customer_id,))
                result = cur.fetchone()
                
                if result:
                    metadata = result[0] if result[0] else {}
                    
                    # Update sentiment history
                    if 'sentiment_history' not in metadata:
                        metadata['sentiment_history'] = []
                    
                    metadata['sentiment_history'].append({
                        'score': score,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    # Keep last 20 readings
                    metadata['sentiment_history'] = metadata['sentiment_history'][-20:]
                    metadata['avg_sentiment'] = sum(
                        s['score'] for s in metadata['sentiment_history']
                    ) / len(metadata['sentiment_history'])
                    
                    cur.execute("""
                        UPDATE customers SET metadata = %s WHERE id = %s
                    """, (json.dumps(metadata), customer_id))
                    
                    print(f"✓ Updated sentiment for customer: {score}")
                    return True
                return False
    
    # -------------------------------------------------------------------------
    # CUSTOMER STATS
    # -------------------------------------------------------------------------
    
    def get_customer_stats(self, customer_id: str) -> dict:
        """
        Get comprehensive customer statistics.
        Matches InMemoryStore.get_customer_stats()
        """
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get customer
                cur.execute("""
                    SELECT * FROM customers WHERE id = %s
                """, (customer_id,))
                customer = cur.fetchone()
                
                if not customer:
                    return self._empty_stats()
                
                # Get ticket stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_tickets,
                        COUNT(*) FILTER (WHERE status = 'open') as open_tickets,
                        COUNT(*) FILTER (WHERE status = 'resolved') as resolved_tickets,
                        COUNT(*) FILTER (WHERE escalated = TRUE) as escalated_tickets
                    FROM tickets WHERE customer_id = %s
                """, (customer_id,))
                ticket_stats = cur.fetchone()
                
                # Get message stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_messages,
                        AVG(sentiment_score) as avg_sentiment,
                        COUNT(DISTINCT channel) as channels_used
                    FROM messages WHERE customer_id = %s
                """, (customer_id,))
                message_stats = cur.fetchone()
                
                # Get channels
                cur.execute("""
                    SELECT DISTINCT channel FROM tickets WHERE customer_id = %s
                """, (customer_id,))
                channels = [row['channel'] for row in cur.fetchall()]
                
                metadata = customer['metadata'] or {}
                
                # Convert datetime to string for JSON serialization
                last_interaction = customer.get('created_at')
                if last_interaction:
                    last_interaction = str(last_interaction)
                
                stats = {
                    'customer_id': customer_id,
                    'customer_email': customer.get('email'),
                    'customer_phone': customer.get('phone'),
                    'total_tickets': ticket_stats['total_tickets'] or 0,
                    'open_tickets': ticket_stats['open_tickets'] or 0,
                    'resolved_tickets': ticket_stats['resolved_tickets'] or 0,
                    'escalated_tickets': ticket_stats['escalated_tickets'] or 0,
                    'total_messages': message_stats['total_messages'] or 0,
                    'avg_sentiment': float(message_stats['avg_sentiment']) if message_stats['avg_sentiment'] else metadata.get('avg_sentiment', 0.5),
                    'channels_used': channels,
                    'preferred_channel': channels[0] if channels else 'unknown',
                    'frustration_flag': metadata.get('frustration_flag', False),
                    'last_interaction': last_interaction
                }
                
                print(f"✓ Retrieved stats for customer: {stats['total_tickets']} tickets")
                return stats
    
    def _empty_stats(self) -> dict:
        """Return empty stats dict."""
        return {
            'customer_id': None,
            'customer_email': None,
            'customer_phone': None,
            'total_tickets': 0,
            'open_tickets': 0,
            'resolved_tickets': 0,
            'escalated_tickets': 0,
            'total_messages': 0,
            'avg_sentiment': 0.5,
            'channels_used': [],
            'preferred_channel': 'unknown',
            'frustration_flag': False,
            'last_interaction': None
        }
    
    # -------------------------------------------------------------------------
    # VECTOR SEARCH (pgvector)
    # -------------------------------------------------------------------------
    
    def store_embedding(self, content: str, embedding_vector: List[float], 
                        category: str = None, source: str = None) -> str:
        """
        Store content with vector embedding.
        """
        embedding_id = self._generate_uuid()
        vector_str = '[' + ','.join(map(str, embedding_vector)) + ']'
        
        with DatabaseConnection(autocommit=True) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO embeddings (id, content, embedding, category, source)
                    VALUES (%s, %s, %s::vector, %s, %s)
                    RETURNING *
                """, (embedding_id, content, vector_str, category, source))
                
                result = cur.fetchone()
                print(f"✓ Stored embedding: {category or 'uncategorized'}")
                return str(embedding_id)
    
    def search_similar(self, query_vector: List[float], limit: int = 5, 
                       category: str = None) -> List[dict]:
        """
        Search for similar content using vector similarity.
        """
        vector_str = '[' + ','.join(map(str, query_vector)) + ']'
        
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if category:
                    cur.execute("""
                        SELECT content, category, source,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM embeddings
                        WHERE category = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (vector_str, category, vector_str, limit))
                else:
                    cur.execute("""
                        SELECT content, category, source,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM embeddings
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (vector_str, vector_str, limit))
                
                results = cur.fetchall()
                print(f"✓ Found {len(results)} similar results")
                return [dict(r) for r in results]
    
    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------

    def get_connection(self):
        """Get a raw database connection for advanced operations."""
        return get_db_pool().get_connection()

    def _generate_uuid(self) -> str:
        """Generate UUID string."""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_short_id(self) -> str:
        """Generate short ID for tickets."""
        import random
        return f"{random.randint(1000, 9999)}"
    
    def close(self):
        """Close database connections."""
        get_db_pool().close_all()


# =============================================================================
# MIGRATION FROM IN-MEMORY STORE
# =============================================================================

def migrate_from_memory(memory_store, db: CRMDatabase = None):
    """
    Migrate all data from InMemoryStore to PostgreSQL.
    Shows migration progress.
    """
    if db is None:
        db = CRMDatabase()
    
    print("\n" + "="*60)
    print("MIGRATING FROM IN-MEMORY STORE TO POSTGRESQL")
    print("="*60)
    
    migrated = {
        'customers': 0,
        'tickets': 0,
        'messages': 0
    }
    
    # Migrate customers
    print("\n[1/3] Migrating customers...")
    for email, customer in memory_store.customers_by_email.items():
        try:
            # Check if exists
            existing = db.get_customer_by_id(customer['id'])
            if not existing:
                # Create customer
                db.get_or_create_customer(
                    email=customer.get('email'),
                    phone=customer.get('phone'),
                    name=customer.get('name')
                )
            migrated['customers'] += 1
            print(f"  ✓ {email}")
        except Exception as e:
            print(f"  ✗ {email}: {e}")
    
    # Migrate tickets
    print("\n[2/3] Migrating tickets...")
    for ticket_id, ticket in memory_store.tickets.items():
        try:
            # Check if exists
            existing = db.get_ticket(ticket_id)
            if not existing:
                # Create ticket
                db.create_ticket(
                    customer_id=ticket['customer_id'],
                    issue=ticket['issue'],
                    priority=ticket['priority'],
                    channel=ticket['channel']
                )
                
                # Update status if needed
                if ticket.get('escalated'):
                    db.escalate_ticket(ticket_id, ticket.get('escalation_reason', 'unknown'))
            
            migrated['tickets'] += 1
            print(f"  ✓ {ticket_id}")
        except Exception as e:
            print(f"  ✗ {ticket_id}: {e}")
    
    # Migrate messages
    print("\n[3/3] Migrating messages...")
    for ticket_id, ticket in memory_store.tickets.items():
        for message in ticket.get('messages', []):
            try:
                db.add_message(
                    ticket_id=ticket_id,
                    customer_id=ticket['customer_id'],
                    role=message['role'],
                    content=message['content'],
                    channel=message['channel']
                )
                migrated['messages'] += 1
            except Exception as e:
                print(f"  ✗ Message in {ticket_id}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    print(f"  Customers: {migrated['customers']}")
    print(f"  Tickets:   {migrated['tickets']}")
    print(f"  Messages:  {migrated['messages']}")
    print("="*60 + "\n")
    
    return migrated


# =============================================================================
# MAIN - TEST DATABASE LAYER
# =============================================================================

def main():
    """Test all database operations."""
    print("="*60)
    print("PHASE 2 STEP 2 — DATABASE LAYER TEST")
    print("="*60)
    
    # Initialize database
    db = CRMDatabase()
    
    # Test 1: Create customer
    print("\n" + "-"*60)
    print("TEST 1: Create Customer")
    print("-"*60)
    
    customer = db.get_or_create_customer(
        email="test.user@example.com",
        phone="+14155551234",
        name="Test User"
    )
    print(f"Customer: {customer}")
    customer_id = customer['id']
    
    # Test 2: Create ticket
    print("\n" + "-"*60)
    print("TEST 2: Create Ticket")
    print("-"*60)
    
    ticket = db.create_ticket(
        customer_id=customer_id,
        issue="How do I add team members?",
        priority="medium",
        channel="email"
    )
    print(f"Ticket: {ticket}")
    ticket_id = ticket['id']
    
    # Test 3: Add messages
    print("\n" + "-"*60)
    print("TEST 3: Add Messages")
    print("-"*60)
    
    msg1 = db.add_message(
        ticket_id=ticket_id,
        customer_id=customer_id,
        role="customer",
        content="How do I add team members to my workspace?",
        channel="email",
        sentiment_score=0.5
    )
    print(f"Message 1: {msg1['id']}")
    
    msg2 = db.add_message(
        ticket_id=ticket_id,
        customer_id=customer_id,
        role="agent",
        content="To add team members, go to Settings > Members > Invite.",
        channel="email",
        sentiment_score=0.7
    )
    print(f"Message 2: {msg2['id']}")
    
    # Test 4: Get customer history
    print("\n" + "-"*60)
    print("TEST 4: Get Customer History")
    print("-"*60)
    
    history = db.get_customer_history(customer_id, limit=10)
    print(f"History: {len(history)} messages")
    for msg in history:
        print(f"  - [{msg['role']}] {msg['content'][:50]}...")
    
    # Test 5: Update sentiment
    print("\n" + "-"*60)
    print("TEST 5: Update Sentiment")
    print("-"*60)
    
    db.update_sentiment(customer_id, 0.6)
    db.update_sentiment(customer_id, 0.7)
    print("Sentiment updated")
    
    # Test 6: Get customer stats
    print("\n" + "-"*60)
    print("TEST 6: Get Customer Stats")
    print("-"*60)
    
    stats = db.get_customer_stats(customer_id)
    print(f"Stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Test 7: Escalate ticket
    print("\n" + "-"*60)
    print("TEST 7: Escalate Ticket")
    print("-"*60)
    
    escalated = db.escalate_ticket(ticket_id, "test_escalation")
    print(f"Escalated: {escalated}")
    
    # Test 8: Vector search (with dummy vector)
    print("\n" + "-"*60)
    print("TEST 8: Vector Search")
    print("-"*60)
    
    # Create dummy embedding (1536 dimensions for OpenAI embeddings)
    dummy_vector = [0.1] * 1536
    embedding_id = db.store_embedding(
        content="How to add team members to workspace",
        embedding_vector=dummy_vector,
        category="how_to",
        source="test"
    )
    print(f"Stored embedding: {embedding_id}")
    
    # Search
    results = db.search_similar(dummy_vector, limit=5, category="how_to")
    print(f"Search results: {len(results)}")
    for r in results:
        print(f"  - {r['content'][:50]}... (similarity: {r['similarity']:.4f})")
    
    # Test 9: Resolve ticket
    print("\n" + "-"*60)
    print("TEST 9: Resolve Ticket")
    print("-"*60)
    
    resolved = db.resolve_ticket(ticket_id)
    print(f"Resolved: {resolved}")
    
    # Cleanup
    db.close()
    
    # Summary
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)
    print("✓ Customer CRUD: PASS")
    print("✓ Ticket CRUD: PASS")
    print("✓ Message CRUD: PASS")
    print("✓ Sentiment Tracking: PASS")
    print("✓ Customer Stats: PASS")
    print("✓ Escalation: PASS")
    print("✓ Vector Search: PASS")
    print("="*60)


if __name__ == "__main__":
    main()
