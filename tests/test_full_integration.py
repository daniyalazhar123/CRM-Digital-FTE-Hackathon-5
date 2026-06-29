"""CRM Digital FTE — Full Integration Test (Step 9)

Tests all 10 required production features against real services:
1. Redis connectivity + SET/GET/TTL
2. pgvector KB search (NeonDB)
3. Cache integration (Redis + KB)
4. Kafka producer (5 topics)
5. Prometheus metrics (12 counters + generate_latest)
6. Customer CRUD (NeonDB)
7. Ticket CRUD (NeonDB)
8. Duplicate email detection (NeonDB)
9. Sentiment tracking (NeonDB)
10. Escalation pipeline (non-LLM)

No mocks, no monkeypatch, no fake services.
"""

import sys
import os
import json
import time
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_1_redis_connectivity():
    """Test Redis connection, SET, GET, TTL, DELETE."""
    from cache.redis_client import RedisCache, get_cache

    # Create a fresh instance (singleton may have been closed by prior tests)
    cache = RedisCache()

    async def _test():
        # Force fresh connection
        cache._redis = None
        cache._pool = None
        ok = await cache.health_check()
        assert ok, "Redis health check failed"
        print("  [PASS] Redis health check")

        await cache.set("test:integration", {"hello": "world"}, ttl=60)
        val = await cache.get("test:integration")
        assert val is not None and val.get("hello") == "world", "SET/GET failed"
        print("  [PASS] Redis SET/GET")

        ttl = await cache.ttl("test:integration")
        assert 0 < ttl <= 60, f"TTL out of range: {ttl}"
        print(f"  [PASS] Redis TTL ({ttl}s)")

        await cache.delete("test:integration")
        gone = await cache.get("test:integration")
        assert gone is None, "DELETE failed"
        print("  [PASS] Redis DELETE")

    asyncio.run(_test())


def test_2_pgvector_kb_search():
    """Test pgvector similarity search against real database."""
    from agent.tools import search_knowledge_base
    from agent.embeddings import embed_text

    # Verify embedding dimensions
    vec = embed_text("test query")
    assert vec is not None, "embed_text returned None"
    assert len(vec) == 1536, f"Expected 1536-dim, got {len(vec)}"
    print("  [PASS] Embedding dimensions (1536)")

    # Search with real query
    result = search_knowledge_base("What is the refund policy?", max_results=3)
    data = json.loads(result)
    assert data.get("success"), f"Search failed: {data.get('error')}"
    source = data.get("source")
    assert source in ("pgvector", "redis_cache"), f"Unexpected source: {source}"
    results = data.get("results", [])
    assert len(results) > 0, "No search results returned"
    print(f"  [PASS] KB search ({source}) — {len(results)} results")


def test_3_cache_integration():
    """Test that Redis caching works for KB search."""
    from agent.tools import search_knowledge_base
    from cache.redis_client import cached_kb_search

    async def _test():
        query = "How do I reset my password?"
        # Ensure cache is populated (search already cached from test_2)
        cached = await cached_kb_search(query, max_results=3)
        if cached is None:
            # First call — will populate cache via tools.py
            import asyncio
            from cache.redis_client import cache_kb_search
            result = search_knowledge_base(query, max_results=3)
            data = json.loads(result)
            await cache_kb_search(query, data.get("results", []), max_results=3)

        cached2 = await cached_kb_search(query, max_results=3)
        assert cached2 is not None, "Cache should return results"
        print("  [PASS] KB search cached in Redis")

        # Verify cache set TTL
        from cache.redis_client import get_cache
        c = get_cache()
        key = f"kb:{query[:100].strip().lower()}:3"
        ttl = await c.ttl(key)
        assert ttl > 0, f"Cache TTL should be positive, got {ttl}"
        print(f"  [PASS] Cache TTL ({ttl}s remaining)")

    asyncio.run(_test())


def test_4_kafka_topics():
    """Test all 5 required Kafka topics can receive messages."""
    from workers.kafka_producer import get_producer, KafkaTopics

    async def _test():
        p = get_producer()
        try:
            await p.start()
        except Exception as e:
            import pytest
            pytest.skip(f"Kafka unavailable: {e}")
            return
        topics = [
            KafkaTopics.EMAIL_RECEIVED,
            KafkaTopics.WHATSAPP_RECEIVED,
            KafkaTopics.TICKET_CREATED,
            KafkaTopics.TICKET_UPDATED,
            KafkaTopics.METRICS_EVENTS,
        ]
        for topic in topics:
            await p.publish(topic, {
                "event_type": "integration_test",
                "test": True,
                "timestamp": time.time(),
            })
            print(f"  [PASS] Published to {topic}")
        await p.stop()

    asyncio.run(_test())


def test_5_prometheus_metrics():
    """Test all 12 Prometheus counters generate proper exposition format."""
    from api.main import (
        REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT, CHANNEL_MESSAGES,
        ESCALATION_COUNT, CACHE_HITS, CACHE_MISSES, KB_SEARCH_DURATION,
        TICKETS_CREATED, TICKETS_RESOLVED, ERROR_RATE, ESCALATION_RATE,
        PROMETHEUS_AVAILABLE,
    )
    assert PROMETHEUS_AVAILABLE, "prometheus_client not installed"

    from prometheus_client import generate_latest, REGISTRY

    # Increment each counter type
    REQUEST_COUNT.labels(method="GET", endpoint="/test", status=200).inc()
    ERROR_COUNT.labels(type="test", endpoint="/test").inc()
    CHANNEL_MESSAGES.labels(channel="email").inc()
    ESCALATION_COUNT.labels(reason="refund").inc()
    CACHE_HITS.labels(cache_type="kb").inc()
    CACHE_MISSES.labels(cache_type="customer").inc()
    KB_SEARCH_DURATION.observe(0.5)
    TICKETS_CREATED.inc()
    TICKETS_RESOLVED.inc()
    ERROR_RATE.set(0.05)
    ESCALATION_RATE.set(0.1)

    data = generate_latest(REGISTRY).decode("utf-8")
    required = [
        "api_requests_total", "api_request_latency_seconds",
        "api_errors_total", "error_rate_ratio",
        "channel_messages_total", "escalations_total",
        "escalation_rate_ratio", "cache_hits_total",
        "cache_misses_total", "kb_search_duration_seconds",
        "tickets_created_total", "tickets_resolved_total",
    ]
    for name in required:
        assert name in data, f"Metric {name} missing from generate_latest()"
    print(f"  [PASS] All 12 metrics in generate_latest() output")


def test_6_customer_crud():
    """Test customer CRUD against real database."""
    from db.database import CRMDatabase
    db = CRMDatabase()

    email = f"integration_{int(time.time())}@example.com"
    customer = db.get_or_create_customer(email=email, name="Integration Test")
    assert customer is not None, "Customer creation failed"
    assert customer.get("email") == email, f"Email mismatch: {customer}"
    assert customer.get("name") == "Integration Test", f"Name mismatch: {customer}"
    print(f"  [PASS] Customer CRUD — {customer['id']}")


def test_7_ticket_crud():
    """Test ticket CRUD against real database."""
    from db.database import CRMDatabase
    db = CRMDatabase()

    email = f"ticket_{int(time.time())}@example.com"
    customer = db.get_or_create_customer(email=email)
    ticket = db.create_ticket(
        customer_id=customer["id"],
        issue="Integration test ticket",
        priority="high",
        channel="email",
    )
    assert ticket is not None, "Ticket creation failed"
    assert ticket["id"].startswith("TKT-"), f"Unexpected ticket ID: {ticket['id']}"
    assert ticket["status"] == "open", f"Expected open, got {ticket['status']}"
    print(f"  [PASS] Ticket CRUD — {ticket['id']}")

    # Escalation
    escalated = db.escalate_ticket(ticket["id"], "refund_request")
    assert escalated, f"Escalation failed for {ticket['id']}"
    print(f"  [PASS] Ticket escalation — {ticket['id']}")


def test_8_duplicate_email_detection():
    """Test duplicate email detection against real database."""
    from db.database import CRMDatabase
    db = CRMDatabase()

    msg_id = f"integration_test_msg_{int(time.time())}"
    assert not db.is_email_processed(msg_id), "New msg_id should not be processed"
    db.mark_email_processed(msg_id)
    assert db.is_email_processed(msg_id), "Marked msg_id should be processed"
    print("  [PASS] Duplicate email detection")


def test_9_sentiment_tracking():
    """Test sentiment tracking against real database."""
    from db.database import CRMDatabase
    from agent.crm_agent import analyze_sentiment_simple
    db = CRMDatabase()

    email = f"sentiment_{int(time.time())}@example.com"
    customer = db.get_or_create_customer(email=email)

    score = analyze_sentiment_simple("I love this product! Great work!")
    assert score > 0.7, f"Positive sentiment too low: {score}"
    db.update_sentiment(customer["id"], score)
    print(f"  [PASS] Sentiment tracking — score={score:.2f}")


def test_10_escalation_pipeline():
    """Test escalation pipeline (rule-based, no LLM)."""
    from agent.crm_agent import check_escalation_triggers

    test_cases = [
        ("I want a refund now", True, "refund_request"),
        ("I need to sue your company", True, "legal_threat"),
    ]
    for message, expected_escalation, expected_reason in test_cases:
        should, reason = check_escalation_triggers(message)
        assert should == expected_escalation, f"Message '{message}': expected escalation={expected_escalation}, got {should}"
        if expected_escalation:
            assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"
    print("  [PASS] Escalation pipeline")


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("FULL INTEGRATION TEST — All Real Services")
    print("=" * 60)
    tests = [
        ("Redis Connectivity", test_1_redis_connectivity),
        ("pgvector KB Search", test_2_pgvector_kb_search),
        ("Cache Integration", test_3_cache_integration),
        ("Kafka Topics (5)", test_4_kafka_topics),
        ("Prometheus Metrics (12)", test_5_prometheus_metrics),
        ("Customer CRUD", test_6_customer_crud),
        ("Ticket CRUD", test_7_ticket_crud),
        ("Duplicate Detection", test_8_duplicate_email_detection),
        ("Sentiment Tracking", test_9_sentiment_tracking),
        ("Escalation Pipeline", test_10_escalation_pipeline),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
    total = len(tests)
    print()
    print("=" * 60)
    print(f"INTEGRATION TEST: {passed}/{total} PASSED")
    print("=" * 60)
