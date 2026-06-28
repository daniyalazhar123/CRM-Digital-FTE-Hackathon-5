"""
CRM Digital FTE — Knowledge Base Live Search Test (pytest)

Verifies:
  Query → embed_text() → pgvector search_document_chunks() → Top 5 chunks

Run:
    pytest tests/test_knowledge_search.py -v

Requires: NeonDB accessible (USE_FALLBACK not set in .env) and chunks ingested.
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "agent"))

from db.database import CRMDatabase
from agent.embeddings import embed_text
from agent.tools import search_knowledge_base

db = CRMDatabase()


def test_db_has_chunks():
    """Verify document chunks exist in the database."""
    count = db.get_document_chunk_count()
    print(f"\n  Chunks in DB: {count}")
    assert count > 0, (
        "No document chunks found. Run: python ingest_documents.py context/"
    )


def test_embedding_dimensions():
    """Verify embed_text returns 1536-dim vector."""
    vec = embed_text("What is your refund policy?")
    assert vec is not None, "embed_text returned None"
    assert len(vec) == 1536, f"Expected 1536 dims, got {len(vec)}"
    # Verify it's a unit vector (norm ≈ 1.0)
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 0.01, f"Expected unit vector, norm={norm}"


def test_pgvector_search_returns_results():
    """Verify pgvector cosine similarity returns top K chunks."""
    vec = embed_text("How do I add team members?")
    assert vec is not None
    results = db.search_document_chunks(query_embedding=vec, limit=5)
    assert len(results) > 0, "search_document_chunks returned empty"
    assert len(results) <= 5, f"Expected ≤5 results, got {len(results)}"
    for r in results:
        assert "document_title" in r
        assert "content" in r
        assert "similarity" in r
    print(f"\n  Retrieved {len(results)} chunk(s)")
    for r in results:
        print(f"    sim={r['similarity']:.4f}  title=\"{r['document_title']}\"")


def test_search_results_have_metadata():
    """Verify each result has required fields."""
    vec = embed_text("API documentation")
    assert vec is not None
    results = db.search_document_chunks(query_embedding=vec, limit=3)
    assert len(results) > 0
    r = results[0]
    assert "document_title" in r
    assert "chunk_index" in r
    assert "content" in r
    assert "metadata" in r
    assert "similarity" in r


def test_search_knowledge_base_tool_returns_pgvector():
    """Verify the Agent SDK tool returns real pgvector results."""
    result_json = search_knowledge_base(query="pricing plans", max_results=3)
    parsed = json.loads(result_json)
    assert parsed.get("success") is True, f"search_knowledge_base failed: {parsed.get('error')}"
    assert parsed.get("source") in ("pgvector", "redis_cache"), (
        f"Expected pgvector or redis_cache source, got {parsed.get('source')}"
    )
    results = parsed.get("results", [])
    assert len(results) > 0, "No results from search_knowledge_base"
    print(f"\n  Tool returned {len(results)} chunk(s) from pgvector")


def test_semantic_relevance_refund():
    """Verify 'refund policy' query returns pricing-related content."""
    vec = embed_text("What is your refund policy?")
    assert vec is not None
    results = db.search_document_chunks(query_embedding=vec, limit=5)
    # At least one result should mention billing/refund/pricing
    refund_keywords = ["refund", "billing", "pricing", "plan", "free", "pro",
                        "business", "enterprise"]
    found = False
    for r in results:
        content = (r.get("content", "") + r.get("document_title", "")).lower()
        if any(kw in content for kw in refund_keywords):
            found = True
            break
    assert found, "No semantically relevant chunk found for 'refund policy' query"
