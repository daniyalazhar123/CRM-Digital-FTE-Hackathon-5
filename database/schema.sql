-- =============================================================================
-- CRM Digital FTE - PostgreSQL Schema with pgvector
-- =============================================================================
-- Database: crm_db
-- Extension: vector (pgvector 0.8.2)
-- Purpose: Customer Success FTE CRM/Ticket Management System
-- =============================================================================

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- TABLE: customers
-- Purpose: Unified customer records across all channels (email, WhatsApp, web)
-- =============================================================================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    name VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Indexes for customers
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_created_at ON customers(created_at);

-- =============================================================================
-- TABLE: tickets
-- Purpose: Support ticket tracking with channel metadata
-- =============================================================================
CREATE TABLE tickets (
    id VARCHAR(50) PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    issue TEXT,
    priority VARCHAR(20),
    channel VARCHAR(50),
    status VARCHAR(50) DEFAULT 'open',
    escalated BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for tickets
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_channel ON tickets(channel);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_escalated ON tickets(escalated);

-- =============================================================================
-- TABLE: messages
-- Purpose: All conversation messages with sentiment tracking
-- =============================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id VARCHAR(50) REFERENCES tickets(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    role VARCHAR(20),
    content TEXT,
    channel VARCHAR(50),
    sentiment_score FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for messages
CREATE INDEX idx_messages_ticket_id ON messages(ticket_id);
CREATE INDEX idx_messages_customer_id ON messages(customer_id);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);

-- =============================================================================
-- TABLE: embeddings
-- Purpose: Vector embeddings for semantic knowledge base search
-- =============================================================================
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT,
    embedding VECTOR(1536),
    category VARCHAR(100),
    source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search (ivfflat)
CREATE INDEX idx_embeddings_embedding ON embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_category ON embeddings(category);

-- =============================================================================
-- SAMPLE DATA (Optional - for testing)
-- =============================================================================

-- Sample customer
INSERT INTO customers (email, phone, name, plan) VALUES 
    ('test@example.com', '+14155551234', 'Test User', 'pro');

-- =============================================================================
-- USEFUL QUERIES
-- =============================================================================

-- Get customer with ticket count
-- SELECT c.*, COUNT(t.id) as ticket_count 
-- FROM customers c LEFT JOIN tickets t ON c.id = t.customer_id 
-- GROUP BY c.id;

-- Get recent messages for a ticket
-- SELECT * FROM messages WHERE ticket_id = 'TKT-00001' ORDER BY timestamp DESC;

-- Semantic search example (find similar content)
-- SELECT content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
-- FROM embeddings ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector LIMIT 5;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
