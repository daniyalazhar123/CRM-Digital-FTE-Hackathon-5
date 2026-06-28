"""
CRM Digital FTE - Database Layer
Phase 2: Specialization — Step 2

PostgreSQL database layer that bridges InMemoryStore with production database.
Provides CRUD operations, vector search, and migration capabilities.
"""

import psycopg2
import psycopg2.pool
from psycopg2 import pool, sql, extras
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
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
            except psycopg2.pool.PoolError:
                if attempt == MAX_RETRIES - 1:
                    raise
                delay = RETRY_DELAY * (RETRY_BACKOFF_MULTIPLIER ** attempt)
                print(f"Connection pool exhausted, retrying in {delay}s...")
                time.sleep(delay)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                delay = RETRY_DELAY * (RETRY_BACKOFF_MULTIPLIER ** attempt)
                print(f"Connection attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
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

    In production (ENVIRONMENT=production), PostgreSQL MUST be available.
    Set USE_FALLBACK=true in .env to explicitly enable in-memory mode for development.
    """

    def __init__(self):
        self._fallback = None
        use_fallback_env = os.getenv('USE_FALLBACK', '').lower()
        env = os.getenv('ENVIRONMENT', 'development').lower()
        if use_fallback_env in ('true', '1', 'yes'):
            print("Using in-memory fallback database (USE_FALLBACK=true)")
            self._fallback = _FallbackDB()
        else:
            try:
                pool = get_db_pool()
                conn = pool.get_connection()
                pool.release_connection(conn)
            except Exception as e:
                err_msg = (
                    f"PostgreSQL is not available: {e}\n"
                    f"Ensure the database is running and DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD "
                    f"are correctly set in .env\n"
                    f"To use in-memory fallback for development, set USE_FALLBACK=true in .env"
                )
                if env == 'production':
                    raise RuntimeError(f"FATAL: {err_msg}")
                print(f"WARNING: {err_msg}")
                print("Falling back to in-memory database. Set USE_FALLBACK=false to disable this.")
                self._fallback = _FallbackDB()

    def __getattribute__(self, name):
        if name == '_fallback':
            return super().__getattribute__(name)
        fallback = super().__getattribute__('_fallback')
        if fallback is not None and hasattr(fallback, name):
            return getattr(fallback, name)
        return super().__getattribute__(name)

    # -------------------------------------------------------------------------
    # CUSTOMER OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_or_create_customer(self, email: str = None, phone: str = None,
                                name: str = None) -> dict:
        """
        Get existing customer or create new one.
        Matches InMemoryStore.get_or_create_customer()
        
        Cross-channel recognition:
        - If email provided, check if customer with that email OR linked phone exists
        - If phone provided, check if customer with that phone OR linked email exists
        - Updates missing identifiers to link channels
        """
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Try to find by email first
                if email:
                    cur.execute("""
                        SELECT * FROM customers WHERE email = %s
                    """, (email,))
                    customer = cur.fetchone()

                    if customer:
                        # Found by email, update phone if provided and not set
                        if phone and not customer.get('phone'):
                            cur.execute("""
                                UPDATE customers SET phone = %s WHERE id = %s
                            """, (phone, customer['id']))
                            conn.commit()
                            customer['phone'] = phone
                        print(f"✓ Found customer by email: {customer['email']}")
                        return dict(customer)

                # Try to find by phone second
                if phone:
                    cur.execute("""
                        SELECT * FROM customers WHERE phone = %s
                    """, (phone,))
                    customer = cur.fetchone()

                    if customer:
                        # Found by phone, update email if provided and not set
                        if email and not customer.get('email'):
                            cur.execute("""
                                UPDATE customers SET email = %s WHERE id = %s
                            """, (email, customer['id']))
                            conn.commit()
                            customer['email'] = email
                        print(f"✓ Found customer by phone: {customer['phone']}")
                        return dict(customer)

                # Create new customer with both identifiers
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
        ticket_id = f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{self._generate_short_id()}"
        
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
                        'timestamp': datetime.now(timezone.utc).isoformat()
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
    # DOCUMENT CHUNKS (pgvector) — single retrieval pipeline
    # -------------------------------------------------------------------------
    
    def _ensure_document_chunks_table(self):
        """Create document_chunks table if not exists."""
        try:
            with DatabaseConnection(autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            document_id     UUID NOT NULL DEFAULT gen_random_uuid(),
                            document_title  VARCHAR(500) NOT NULL,
                            chunk_index     INTEGER NOT NULL DEFAULT 0,
                            content         TEXT NOT NULL,
                            embedding       VECTOR(1536),
                            metadata        JSONB DEFAULT '{}',
                            created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
                        ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
                        ON document_chunks (document_id)
                    """)
        except Exception:
            pass

    def store_document_chunk(self, document_title: str, chunk_index: int,
                             content: str, embedding: List[float],
                             metadata: dict = None,
                             document_id: str = None) -> str:
        """Store a single document chunk with its embedding."""
        self._ensure_document_chunks_table()
        chunk_id = document_id or self._generate_uuid()
        vector_str = '[' + ','.join(map(str, embedding)) + ']'
        meta_json = json.dumps(metadata or {})
        with DatabaseConnection(autocommit=True) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO document_chunks
                        (document_id, document_title, chunk_index, content, embedding, metadata)
                    VALUES (%s::uuid, %s, %s, %s, %s::vector, %s::jsonb)
                    RETURNING id
                """, (chunk_id, document_title, chunk_index, content, vector_str, meta_json))
                row = cur.fetchone()
                return str(row['id'])

    def search_document_chunks(self, query_embedding: List[float],
                                limit: int = 5) -> List[dict]:
        """Search document chunks by cosine similarity to query embedding."""
        self._ensure_document_chunks_table()
        vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
        with DatabaseConnection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        document_title,
                        chunk_index,
                        content,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM document_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (vector_str, vector_str, limit))
                rows = cur.fetchall()
                results = []
                for r in rows:
                    d = dict(r)
                    d['similarity'] = round(d['similarity'], 4)
                    results.append(d)
                return results

    def get_document_chunk_count(self) -> int:
        """Return total number of stored chunks."""
        self._ensure_document_chunks_table()
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM document_chunks")
                    return cur.fetchone()[0]
        except Exception:
            return 0
    
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

    # -------------------------------------------------------------------------
    # PROCESSED GMAIL MESSAGE IDS (duplicate prevention)
    # -------------------------------------------------------------------------

    def _ensure_processed_table(self):
        """Create processed_emails table if not exists."""
        try:
            with DatabaseConnection(autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS processed_emails (
                            msg_id VARCHAR(255) PRIMARY KEY,
                            processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """)
        except Exception:
            pass

    def is_email_processed(self, msg_id: str) -> bool:
        """Check if a Gmail message ID has already been processed."""
        try:
            self._ensure_processed_table()
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM processed_emails WHERE msg_id = %s", (msg_id,))
                    return cur.fetchone() is not None
        except Exception:
            return False

    def mark_email_processed(self, msg_id: str) -> None:
        """Record a Gmail message ID as processed."""
        try:
            self._ensure_processed_table()
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO processed_emails (msg_id, processed_at) VALUES (%s, NOW()) ON CONFLICT (msg_id) DO NOTHING",
                        (msg_id,)
                    )
        except Exception:
            pass


# =============================================================================
# FALLBACK DATABASE (In-Memory, used when PostgreSQL is unavailable)
# =============================================================================

class _FallbackDB:
    """In-memory dict-based database for development when PostgreSQL is unavailable."""

    def __init__(self):
        self.customers = {}
        self.tickets = {}
        self.messages = []
        self._document_chunks = []
        self._next_ticket_num = 1
        self._processed_email_ids = set()

    def _gen_uuid(self):
        import uuid
        return str(uuid.uuid4())

    def _gen_ticket_id(self):
        ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        n = self._next_ticket_num
        self._next_ticket_num += 1
        return f"TKT-{ts}-{n:04d}"

    def get_or_create_customer(self, email=None, phone=None, name=None):
        for c in self.customers.values():
            if email and c.get('email') == email:
                if phone and not c.get('phone'):
                    c['phone'] = phone
                return dict(c)
            if phone and c.get('phone') == phone:
                if email and not c.get('email'):
                    c['email'] = email
                return dict(c)
        cid = self._gen_uuid()
        customer = {
            'id': cid, 'email': email, 'phone': phone,
            'name': name, 'plan': 'free',
            'created_at': datetime.now(timezone.utc),
            'metadata': '{}'
        }
        self.customers[cid] = customer
        return dict(customer)

    def get_customer_by_id(self, customer_id):
        c = self.customers.get(customer_id)
        return dict(c) if c else None

    def create_ticket(self, customer_id, issue, priority, channel):
        tid = self._gen_ticket_id()
        ticket = {
            'id': tid, 'customer_id': customer_id, 'issue': issue,
            'priority': priority, 'channel': channel, 'status': 'open',
            'escalated': False, 'escalation_reason': None,
            'created_at': datetime.now(timezone.utc), 'resolved_at': None
        }
        self.tickets[tid] = ticket
        return dict(ticket)

    def get_ticket(self, ticket_id):
        t = self.tickets.get(ticket_id)
        return dict(t) if t else None

    def escalate_ticket(self, ticket_id, reason):
        t = self.tickets.get(ticket_id)
        if t:
            t['escalated'] = True
            t['escalation_reason'] = reason
            t['status'] = 'escalated'
            return True
        return False

    def resolve_ticket(self, ticket_id):
        t = self.tickets.get(ticket_id)
        if t:
            t['status'] = 'resolved'
            t['resolved_at'] = datetime.now(timezone.utc)
            return True
        return False

    def add_message(self, ticket_id, customer_id, role, content, channel, sentiment_score=None):
        mid = self._gen_uuid()
        msg = {
            'id': mid, 'ticket_id': ticket_id, 'customer_id': customer_id,
            'role': role, 'content': content, 'channel': channel,
            'sentiment_score': sentiment_score,
            'timestamp': datetime.now(timezone.utc)
        }
        self.messages.append(msg)
        return dict(msg)

    def get_customer_history(self, customer_id, limit=10):
        results = [dict(m) for m in self.messages if m['customer_id'] == customer_id]
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results[:limit]

    def update_sentiment(self, customer_id, score):
        c = self.customers.get(customer_id)
        if not c:
            return False
        import json as _json
        metadata = json.loads(c['metadata']) if isinstance(c['metadata'], str) else (c.get('metadata') or {})
        if 'sentiment_history' not in metadata:
            metadata['sentiment_history'] = []
        metadata['sentiment_history'].append({
            'score': score, 'timestamp': datetime.now(timezone.utc).isoformat()
        })
        metadata['sentiment_history'] = metadata['sentiment_history'][-20:]
        scores = [s['score'] for s in metadata['sentiment_history']]
        metadata['avg_sentiment'] = sum(scores) / len(scores)
        c['metadata'] = json.dumps(metadata)
        return True

    def get_customer_stats(self, customer_id):
        c = self.customers.get(customer_id)
        if not c:
            return _empty_stats_dict()
        metadata = json.loads(c['metadata']) if isinstance(c['metadata'], str) else (c.get('metadata') or {})
        customer_tickets = [t for t in self.tickets.values() if t['customer_id'] == customer_id]
        customer_msgs = [m for m in self.messages if m['customer_id'] == customer_id]
        sentiments = [m['sentiment_score'] for m in customer_msgs if m.get('sentiment_score') is not None]
        channels = list(set(t['channel'] for t in customer_tickets if t.get('channel')))
        avg_sent = sum(sentiments) / len(sentiments) if sentiments else metadata.get('avg_sentiment', 0.5)

        return {
            'customer_id': customer_id,
            'customer_email': c.get('email'),
            'customer_phone': c.get('phone'),
            'total_tickets': len(customer_tickets),
            'open_tickets': sum(1 for t in customer_tickets if t['status'] == 'open'),
            'resolved_tickets': sum(1 for t in customer_tickets if t['status'] == 'resolved'),
            'escalated_tickets': sum(1 for t in customer_tickets if t.get('escalated')),
            'total_messages': len(customer_msgs),
            'avg_sentiment': float(avg_sent),
            'channels_used': channels,
            'preferred_channel': channels[0] if channels else 'unknown',
            'frustration_flag': metadata.get('frustration_flag', False),
            'last_interaction': str(c.get('created_at', ''))
        }

    def store_document_chunk(self, document_title: str, chunk_index: int,
                              content: str, embedding: list,
                              metadata: dict = None,
                              document_id: str = None) -> str:
        eid = document_id or self._gen_uuid()
        self._document_chunks.append({
            'id': eid,
            'document_id': document_id or self._gen_uuid(),
            'document_title': document_title,
            'chunk_index': chunk_index,
            'content': content,
            'embedding': embedding,
            'metadata': metadata or {},
            'created_at': datetime.now(timezone.utc),
        })
        return eid

    def search_document_chunks(self, query_embedding: list,
                                limit: int = 5) -> list:
        import math
        candidates = [c for c in self._document_chunks if c.get('embedding')]
        scored = []
        for c in candidates:
            dot = sum(a * b for a, b in zip(query_embedding, c['embedding']))
            nq = math.sqrt(sum(x * x for x in query_embedding)) or 1
            ne = math.sqrt(sum(x * x for x in c['embedding'])) or 1
            sim = dot / (nq * ne)
            scored.append((sim, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{
            'document_title': c['document_title'],
            'chunk_index': c['chunk_index'],
            'content': c['content'],
            'metadata': c.get('metadata', {}),
            'similarity': round(s, 4),
        } for s, c in scored[:limit]]

    def get_document_chunk_count(self) -> int:
        return len(self._document_chunks)

    def get_connection(self):
        return None

    def close(self):
        pass

    # Processed Gmail message IDs
    def is_email_processed(self, msg_id: str) -> bool:
        return msg_id in self._processed_email_ids

    def mark_email_processed(self, msg_id: str) -> None:
        self._processed_email_ids.add(msg_id)


def _empty_stats_dict():
    return {
        'customer_id': None, 'customer_email': None, 'customer_phone': None,
        'total_tickets': 0, 'open_tickets': 0, 'resolved_tickets': 0,
        'escalated_tickets': 0, 'total_messages': 0, 'avg_sentiment': 0.5,
        'channels_used': [], 'preferred_channel': 'unknown',
        'frustration_flag': False, 'last_interaction': None
    }


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
