"""
CRM Digital FTE - Database Queries
Phase 2: Specialization

Prepared database queries for efficient access patterns.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Any
from datetime import datetime


# =============================================================================
# CUSTOMER QUERIES
# =============================================================================

def get_customer_by_email(conn, email: str) -> Optional[Dict]:
    """Get customer by email address."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM customers WHERE email = %s", (email,))
        return cur.fetchone()


def get_customer_by_phone(conn, phone: str) -> Optional[Dict]:
    """Get customer by phone number."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM customers WHERE phone = %s", (phone,))
        return cur.fetchone()


def get_customer_with_stats(conn, customer_id: str) -> Optional[Dict]:
    """Get customer with ticket count and last interaction."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                c.*,
                COUNT(t.id) as total_tickets,
                MAX(t.created_at) as last_interaction,
                AVG(m.sentiment_score) as avg_sentiment
            FROM customers c
            LEFT JOIN tickets t ON c.id = t.customer_id
            LEFT JOIN messages m ON c.id = m.customer_id
            WHERE c.id = %s
            GROUP BY c.id
        """, (customer_id,))
        return cur.fetchone()


def link_customer_identifier(conn, customer_id: str, identifier_type: str, identifier_value: str):
    """Link additional identifier to customer (for cross-channel tracking)."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (customer_id, identifier_type, identifier_value))
        conn.commit()


# =============================================================================
# TICKET QUERIES
# =============================================================================

def get_tickets_by_customer(conn, customer_id: str, limit: int = 20) -> List[Dict]:
    """Get all tickets for a customer."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM tickets 
            WHERE customer_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (customer_id, limit))
        return cur.fetchall()


def get_active_conversation(conn, customer_id: str, channel: str = None) -> Optional[Dict]:
    """Get active conversation (within 24 hours) for customer."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if channel:
            cur.execute("""
                SELECT * FROM conversations 
                WHERE customer_id = %s 
                  AND channel = %s 
                  AND status = 'active'
                  AND last_activity > NOW() - INTERVAL '24 hours'
                ORDER BY last_activity DESC 
                LIMIT 1
            """, (customer_id, channel))
        else:
            cur.execute("""
                SELECT * FROM conversations 
                WHERE customer_id = %s 
                  AND status = 'active'
                  AND last_activity > NOW() - INTERVAL '24 hours'
                ORDER BY last_activity DESC 
                LIMIT 1
            """, (customer_id,))
        return cur.fetchone()


def get_ticket_with_messages(conn, ticket_id: str) -> Optional[Dict]:
    """Get ticket with all messages."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                t.*,
                json_agg(
                    json_build_object(
                        'id', m.id,
                        'role', m.role,
                        'content', m.content,
                        'channel', m.channel,
                        'timestamp', m.timestamp,
                        'sentiment_score', m.sentiment_score
                    ) ORDER BY m.timestamp
                ) as messages
            FROM tickets t
            LEFT JOIN messages m ON t.id = m.ticket_id
            WHERE t.id = %s
            GROUP BY t.id
        """, (ticket_id,))
        return cur.fetchone()


# =============================================================================
# CONVERSATION QUERIES
# =============================================================================

def create_conversation(conn, customer_id: str, ticket_id: str, channel: str) -> str:
    """Create new conversation thread."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO conversations (customer_id, ticket_id, channel, status)
            VALUES (%s, %s, %s, 'active')
            RETURNING id
        """, (customer_id, ticket_id, channel))
        conn.commit()
        return cur.fetchone()['id']


def update_conversation_sentiment(conn, conversation_id: str, sentiment_score: float):
    """Update conversation sentiment score and trend."""
    with conn.cursor() as cur:
        # Get previous sentiments to calculate trend
        cur.execute("""
            SELECT sentiment_score FROM conversations 
            WHERE id = %s
        """, (conversation_id,))
        result = cur.fetchone()
        
        if result:
            old_score = result[0]
            trend = 'stable'
            if old_score and sentiment_score < old_score - 0.1:
                trend = 'declining'
            elif old_score and sentiment_score > old_score + 0.1:
                trend = 'improving'
            
            frustration_flag = sentiment_score < 0.3
            
            cur.execute("""
                UPDATE conversations 
                SET sentiment_score = %s, 
                    sentiment_trend = %s,
                    frustration_flag = %s,
                    last_activity = NOW()
                WHERE id = %s
            """, (sentiment_score, trend, frustration_flag, conversation_id))
            conn.commit()


def get_customer_conversations(conn, customer_id: str, limit: int = 10) -> List[Dict]:
    """Get customer's conversation history."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM conversations 
            WHERE customer_id = %s 
            ORDER BY last_activity DESC 
            LIMIT %s
        """, (customer_id, limit))
        return cur.fetchall()


# =============================================================================
# METRICS QUERIES
# =============================================================================

def record_metric(conn, metric_type: str, channel: str, value: float, metadata: Dict = None):
    """Record a metric event."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO agent_metrics (metric_type, channel, value, metadata)
            VALUES (%s, %s, %s, %s)
        """, (metric_type, channel, value, metadata or '{}'))
        conn.commit()


def get_metrics_summary(conn, hours: int = 1) -> Dict[str, Any]:
    """Get metrics summary for time period."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_metrics,
                AVG(CASE WHEN metric_type = 'response_time' THEN value END) as avg_response_time,
                COUNT(CASE WHEN metric_type = 'escalation' THEN 1 END) as total_escalations,
                COUNT(CASE WHEN metric_type = 'error' THEN 1 END) as total_errors,
                AVG(CASE WHEN metric_type = 'sentiment' THEN value END) as avg_sentiment
            FROM agent_metrics
            WHERE recorded_at > NOW() - (%s || ' hours')::INTERVAL
        """, (hours,))
        return cur.fetchone()


def get_channel_metrics(conn, hours: int = 1) -> Dict[str, Dict]:
    """Get metrics broken down by channel."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                channel,
                COUNT(*) as total_messages,
                AVG(CASE WHEN metric_type = 'response_time' THEN value END) as avg_response_time,
                COUNT(CASE WHEN metric_type = 'escalation' THEN 1 END) as escalations,
                AVG(CASE WHEN metric_type = 'sentiment' THEN value END) as avg_sentiment
            FROM agent_metrics
            WHERE recorded_at > NOW() - (%s || ' hours')::INTERVAL
            GROUP BY channel
        """, (hours,))
        
        return {row['channel']: dict(row) for row in cur.fetchall()}


# =============================================================================
# KNOWLEDGE BASE QUERIES
# =============================================================================

def search_knowledge_base(conn, query_embedding: List[float], limit: int = 5, category: str = None) -> List[Dict]:
    """Search knowledge base using vector similarity."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if category:
            cur.execute("""
                SELECT title, content, category,
                       1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_base
                WHERE category = %s AND is_active = TRUE
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, category, query_embedding, limit))
        else:
            cur.execute("""
                SELECT title, content, category,
                       1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_base
                WHERE is_active = TRUE
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
        return cur.fetchall()


def add_knowledge_article(conn, title: str, content: str, category: str = None, 
                         embedding: List[float] = None, source_url: str = None):
    """Add article to knowledge base."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO knowledge_base (title, content, category, embedding, source_url)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, content, category, embedding, source_url))
        conn.commit()
