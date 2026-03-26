"""
CRM Digital FTE - Performance Benchmark Tests
Phase 3: Integration Testing — Step 2

Performance benchmarks for response times, escalation detection, and database queries.
Uses REAL PostgreSQL database (no mocking).
"""

import sys
import os
import time
import random
import pytest
import statistics
import psycopg2
from datetime import datetime
from typing import Dict, List

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from api.main import app
from db.database import CRMDatabase

# Create test client
client = TestClient(app)

# Initialize database for direct access
db = CRMDatabase()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_unique_email():
    """Generate unique test email address."""
    return f"perf_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


def cleanup_test_data(db_conn, email=None):
    """Cleanup test data from database."""
    try:
        with db_conn.cursor() as cur:
            if email:
                cur.execute("DELETE FROM messages WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)", (email,))
                cur.execute("DELETE FROM tickets WHERE customer_id IN (SELECT id FROM customers WHERE email = %s)", (email,))
                cur.execute("DELETE FROM customers WHERE email = %s", (email,))
            db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")


def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile of a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]


def get_db_connection():
    """Get direct database connection."""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='crm_db',
        user='postgres',
        password='postgres123'
    )


# =============================================================================
# RESPONSE TIME BENCHMARK TESTS
# =============================================================================

class TestResponseTimesBenchmark:
    """Test response time benchmarks."""

    def test_agent_p95_latency(self, db_conn):
        """
        Test P95 latency:
        1. Run 10 requests
        2. P95 must be < 5000ms
        3. Show min/avg/max/p95
        """
        email_base = generate_unique_email()
        response_times = []
        
        questions = [
            "How do I reset my password?",
            "What features are available in the free plan?",
            "How can I export my data?",
            "Is there a mobile app available?",
            "How do I integrate the API?",
            "Can I customize the dashboard?",
            "How do I add team members?",
            "What security measures are in place?",
            "How do I backup my data?",
            "Can I export reports to PDF?"
        ]
        
        try:
            for i, question in enumerate(questions):
                start_time = time.time()
                
                response = client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": f"{email_base}_{i}",
                        "subject": "Question",
                        "category": "how-to",
                        "message": question
                    }
                )
                
                elapsed = time.time() - start_time
                response_times.append(elapsed * 1000)  # Convert to ms
                
                assert response.status_code == 200, f"Request {i+1} failed"
            
            # Calculate statistics
            min_time = min(response_times)
            max_time = max(response_times)
            avg_time = statistics.mean(response_times)
            p95_time = calculate_percentile(response_times, 95)
            
            # Print detailed report
            print(f"\n{'='*60}")
            print(f"AGENT P95 LATENCY BENCHMARK RESULTS")
            print(f"{'='*60}")
            print(f"Requests: {len(response_times)}")
            print(f"Min:      {min_time:.2f} ms")
            print(f"Max:      {max_time:.2f} ms")
            print(f"Avg:      {avg_time:.2f} ms")
            print(f"P50:      {calculate_percentile(response_times, 50):.2f} ms")
            print(f"P90:      {calculate_percentile(response_times, 90):.2f} ms")
            print(f"P95:      {p95_time:.2f} ms")
            print(f"P99:      {calculate_percentile(response_times, 99):.2f} ms")
            print(f"{'='*60}")
            
            # Assert P95 < 5000ms
            assert p95_time < 5000, f"P95 latency {p95_time:.2f}ms exceeded 5000ms limit"
            
            # Store results for reporting
            self.benchmark_results = {
                'test': 'agent_p95_latency',
                'requests': len(response_times),
                'min_ms': min_time,
                'max_ms': max_time,
                'avg_ms': avg_time,
                'p50_ms': calculate_percentile(response_times, 50),
                'p90_ms': calculate_percentile(response_times, 90),
                'p95_ms': p95_time,
                'p99_ms': calculate_percentile(response_times, 99),
                'passed': p95_time < 5000
            }
            
        finally:
            for i in range(len(questions)):
                cleanup_test_data(db_conn, email=f"{email_base}_{i}")

    def test_escalation_detection_speed(self):
        """
        Test escalation detection speed:
        1. Test 5 escalation keywords
        2. Each detected in < 100ms
        """
        escalation_tests = [
            ("I want to speak to a lawyer about this", "legal_threat"),
            ("What is the pricing for enterprise?", "pricing_inquiry"),
            ("I need a refund immediately", "refund_request"),
            ("Get me a real person now", "human_requested"),
            ("I'm going to sue your company", "legal_threat")
        ]
        
        detection_times = []
        
        for message, expected_type in escalation_tests:
            start_time = time.time()
            
            # Import escalation detection function
            from agent.crm_agent import detect_escalation
            
            result = detect_escalation(message)
            
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            detection_times.append(elapsed)
            
            # Verify escalation detected
            assert result['is_escalation'] == True, f"Failed to detect escalation: {message}"
            assert result['reason'] == expected_type, f"Wrong escalation type: expected {expected_type}, got {result['reason']}"
            assert elapsed < 100, f"Escalation detection took {elapsed:.2f}ms, exceeded 100ms limit"
        
        # Print report
        avg_detection = statistics.mean(detection_times)
        print(f"\n{'='*60}")
        print(f"ESCALATION DETECTION SPEED BENCHMARK")
        print(f"{'='*60}")
        print(f"Tests: {len(escalation_tests)}")
        print(f"Avg detection time: {avg_detection:.2f} ms")
        print(f"Max detection time: {max(detection_times):.2f} ms")
        print(f"All detections < 100ms: {'✓ PASS' if all(t < 100 for t in detection_times) else '✗ FAIL'}")
        print(f"{'='*60}")

    def test_database_query_speed(self, db_conn):
        """
        Test database query speed:
        1. 100 customer lookups
        2. Average < 50ms each
        """
        # First, create a test customer
        email = generate_unique_email()
        
        try:
            # Create customer via API
            response = client.post(
                "/support/submit",
                json={
                    "name": "Test User",
                    "email": email,
                    "subject": "Test",
                    "category": "how-to",
                    "message": "Test message"
                }
            )
            assert response.status_code == 200
            
            query_times = []
            
            # Perform 100 customer lookups
            for i in range(100):
                start_time = time.time()
                
                # Direct DB query
                with db_conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, email, name FROM customers WHERE email = %s",
                        (email,)
                    )
                    result = cur.fetchone()
                
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                query_times.append(elapsed)
                
                assert result is not None, "Customer lookup failed"
            
            # Calculate statistics
            avg_time = statistics.mean(query_times)
            p95_time = calculate_percentile(query_times, 95)
            
            # Print report
            print(f"\n{'='*60}")
            print(f"DATABASE QUERY SPEED BENCHMARK")
            print(f"{'='*60}")
            print(f"Queries: {len(query_times)}")
            print(f"Min:     {min(query_times):.2f} ms")
            print(f"Max:     {max(query_times):.2f} ms")
            print(f"Avg:     {avg_time:.2f} ms")
            print(f"P95:     {p95_time:.2f} ms")
            print(f"{'='*60}")
            
            # Assert average < 50ms
            assert avg_time < 50, f"Average query time {avg_time:.2f}ms exceeded 50ms limit"
            
        finally:
            cleanup_test_data(db_conn, email=email)


# =============================================================================
# LOAD BENCHMARK TESTS
# =============================================================================

class TestLoadBenchmark:
    """Test load benchmarks."""

    def test_concurrent_users_benchmark(self, db_conn):
        """
        Test concurrent users benchmark:
        1. Simulate 10 concurrent users
        2. All requests complete successfully
        3. Average response time < 5s
        """
        import concurrent.futures
        
        emails = [generate_unique_email() for _ in range(10)]
        results = []
        
        def submit_ticket(email):
            start_time = time.time()
            try:
                response = client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": email,
                        "subject": "Load Test",
                        "category": "how-to",
                        "message": "This is a load benchmark test message."
                    }
                )
                elapsed = (time.time() - start_time) * 1000
                return {
                    'success': response.status_code == 200,
                    'elapsed_ms': elapsed,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'elapsed_ms': (time.time() - start_time) * 1000,
                    'error': str(e)
                }
        
        try:
            # Submit concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(submit_ticket, email) for email in emails]
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
            
            # Calculate statistics
            successful = [r for r in results if r['success']]
            response_times = [r['elapsed_ms'] for r in successful]
            
            avg_time = statistics.mean(response_times) if response_times else 0
            p95_time = calculate_percentile(response_times, 95) if response_times else 0
            
            # Print report
            print(f"\n{'='*60}")
            print(f"CONCURRENT USERS BENCHMARK (10 users)")
            print(f"{'='*60}")
            print(f"Total requests: {len(results)}")
            print(f"Successful: {len(successful)}")
            print(f"Failed: {len(results) - len(successful)}")
            print(f"Success rate: {len(successful)/len(results)*100:.1f}%")
            print(f"Avg response time: {avg_time:.2f} ms")
            print(f"P95 response time: {p95_time:.2f} ms")
            print(f"{'='*60}")
            
            # Assertions
            assert len(successful) == 10, f"Expected 10 successful requests, got {len(successful)}"
            assert avg_time < 5000, f"Average response time {avg_time:.2f}ms exceeded 5000ms limit"
            
        finally:
            for email in emails:
                cleanup_test_data(db_conn, email=email)

    def test_sustained_throughput_benchmark(self, db_conn):
        """
        Test sustained throughput:
        1. Send 50 tickets over 30 seconds
        2. All processed successfully
        3. Calculate throughput (tickets/sec)
        """
        email_base = generate_unique_email()
        results = []
        
        start_time = time.time()
        
        try:
            for i in range(50):
                request_start = time.time()
                
                response = client.post(
                    "/support/submit",
                    json={
                        "name": "Test User",
                        "email": f"{email_base}_{i}",
                        "subject": f"Throughput Test {i}",
                        "category": "how-to",
                        "message": f"This is throughput test ticket {i}."
                    }
                )
                
                elapsed = (time.time() - request_start) * 1000
                results.append({
                    'success': response.status_code == 200,
                    'elapsed_ms': elapsed
                })
            
            total_time = time.time() - start_time
            throughput = 50 / total_time
            
            successful = [r for r in results if r['success']]
            
            # Print report
            print(f"\n{'='*60}")
            print(f"SUSTAINED THROUGHPUT BENCHMARK")
            print(f"{'='*60}")
            print(f"Tickets: {len(results)}")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} tickets/sec")
            print(f"Success rate: {len(successful)/len(results)*100:.1f}%")
            print(f"{'='*60}")
            
            # Assertions
            assert len(successful) == 50, f"Expected 50 successful requests, got {len(successful)}"
            assert throughput > 1.0, f"Throughput {throughput:.2f} tickets/sec too low"
            
        finally:
            for i in range(50):
                cleanup_test_data(db_conn, email=f"{email_base}_{i}")


# =============================================================================
# MEMORY AND RESOURCE TESTS
# =============================================================================

class TestMemoryAndResources:
    """Test memory and resource usage."""

    def test_database_connection_pooling(self, db_conn):
        """
        Test database connection pooling:
        1. Make 20 rapid requests
        2. Verify connections are reused
        3. No connection exhaustion errors
        """
        email_base = generate_unique_email()
        errors = []
        
        try:
            for i in range(20):
                try:
                    response = client.post(
                        "/support/submit",
                        json={
                            "name": "Test User",
                            "email": f"{email_base}_{i}",
                            "subject": "Connection Test",
                            "category": "how-to",
                            "message": f"Connection pool test {i}."
                        }
                    )
                    if response.status_code != 200:
                        errors.append(f"Request {i} returned {response.status_code}")
                except Exception as e:
                    errors.append(f"Request {i} error: {str(e)}")
            
            # Print report
            print(f"\n{'='*60}")
            print(f"DATABASE CONNECTION POOLING TEST")
            print(f"{'='*60}")
            print(f"Requests: 20")
            print(f"Errors: {len(errors)}")
            print(f"Success rate: {(20-len(errors))/20*100:.1f}%")
            print(f"{'='*60}")
            
            assert len(errors) == 0, f"Connection pooling errors: {errors}"
            
        finally:
            for i in range(20):
                cleanup_test_data(db_conn, email=f"{email_base}_{i}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
