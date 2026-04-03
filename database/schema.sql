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
-- TABLE: customer_identifiers
-- Purpose: Cross-channel customer identification (email, phone, WhatsApp)
-- =============================================================================
CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type VARCHAR(50), -- 'email', 'phone', 'whatsapp'
    identifier_value VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(customer_id, identifier_type, identifier_value)
);

-- Indexes for customer_identifiers
CREATE INDEX idx_customer_identifiers_customer_id ON customer_identifiers(customer_id);
CREATE INDEX idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX idx_customer_identifiers_type ON customer_identifiers(identifier_type);

-- =============================================================================
-- TABLE: conversations
-- Purpose: Conversation threads with channel tracking
-- =============================================================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    ticket_id VARCHAR(50) REFERENCES tickets(id) ON DELETE CASCADE,
    channel VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'resolved', 'escalated'
    sentiment_score FLOAT,
    sentiment_trend VARCHAR(50) DEFAULT 'stable', -- 'improving', 'stable', 'declining'
    frustration_flag BOOLEAN DEFAULT FALSE,
    resolution_type VARCHAR(100), -- 'ai_resolved', 'escalated', 'pending'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for conversations
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_ticket_id ON conversations(ticket_id);
CREATE INDEX idx_conversations_channel ON conversations(channel);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_last_activity ON conversations(last_activity);

-- =============================================================================
-- TABLE: knowledge_base
-- Purpose: Product documentation with vector embeddings
-- =============================================================================
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    embedding VECTOR(1536),
    source_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for knowledge_base
CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_base_is_active ON knowledge_base(is_active);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);

-- =============================================================================
-- TABLE: channel_configs
-- Purpose: Channel-specific configurations
-- =============================================================================
CREATE TABLE channel_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(50) UNIQUE NOT NULL, -- 'email', 'whatsapp', 'web_form'
    is_active BOOLEAN DEFAULT TRUE,
    max_response_chars INTEGER,
    max_response_words INTEGER,
    response_style VARCHAR(50), -- 'formal', 'conversational', 'semi-formal'
    webhook_url VARCHAR(500),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default channel configs
INSERT INTO channel_configs (channel, max_response_chars, max_response_words, response_style) VALUES
    ('email', 3000, 500, 'formal'),
    ('whatsapp', 300, 50, 'conversational'),
    ('web_form', 1800, 300, 'semi-formal');

-- =============================================================================
-- TABLE: agent_metrics
-- Purpose: Performance tracking and monitoring
-- =============================================================================
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(100) NOT NULL, -- 'response_time', 'escalation', 'error', 'sentiment'
    channel VARCHAR(50),
    value FLOAT,
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agent_metrics
CREATE INDEX idx_agent_metrics_type ON agent_metrics(metric_type);
CREATE INDEX idx_agent_metrics_channel ON agent_metrics(channel);
CREATE INDEX idx_agent_metrics_recorded_at ON agent_metrics(recorded_at);

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
