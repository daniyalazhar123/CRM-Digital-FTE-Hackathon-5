-- Migration: 001_initial_schema
-- Date: 2026-04-03
-- Description: Initial database schema for CRM Digital FTE

-- This migration creates the complete schema including:
-- - customers
-- - customer_identifiers (for cross-channel tracking)
-- - tickets
-- - messages
-- - conversations
-- - embeddings
-- - knowledge_base
-- - channel_configs
-- - agent_metrics

-- Run this migration to set up the database from scratch
\i database/schema.sql
