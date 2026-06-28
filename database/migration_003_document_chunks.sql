-- =============================================================================
-- Migration 003: Unified Document Chunks with pgvector
-- =============================================================================
-- Purpose: Consolidate embeddings + knowledge_base into a single table.
-- Provides: document, chunk, embedding, metadata in one place.
-- =============================================================================
-- Run: psql -h <host> -U <user> -d neondb -f database/migration_003_document_chunks.sql
-- =============================================================================

BEGIN;

-- ── Create the unified document_chunks table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL DEFAULT gen_random_uuid(),
    document_title  VARCHAR(500) NOT NULL,
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    content         TEXT NOT NULL,
    embedding       VECTOR(1536),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── pgvector index: IVFFlat with cosine distance ─────────────────────────────
-- 100 lists is a good default for small-to-medium knowledge bases (<100K docs)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── Supporting B-tree indexes ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata
    ON document_chunks USING gin (metadata);

-- ── Note: The old embeddings and knowledge_base tables are intentionally kept ─
-- ── for backward compatibility. New code should only use document_chunks.    ─
-- ── Drop old tables when fully migrated:                                    ─
-- ──   DROP TABLE IF EXISTS knowledge_base;                                  ─
-- ──   DROP TABLE IF EXISTS embeddings;                                      ─

COMMIT;
