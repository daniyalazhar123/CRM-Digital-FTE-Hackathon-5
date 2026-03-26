"""
CRM Digital FTE - Load Test Script
Phase 3: Integration & Testing — Exercise 3.2

Locust-based load testing for multi-channel CRM Digital FTE.

This script simulates realistic user behavior across all channels:
- Web form submissions (primary load)
- Health check monitoring
- Metrics queries

Usage:
    # Run with web UI (recommended for visualization)
    locust -f tests/load_test.py --host=http://localhost:8000

    # Run headless (for automated testing)
    locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s

    # Run with custom user count and spawn rate
    locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 200 -r 20 -t 600s

Parameters:
    -u: Number of users to simulate
    -r: Spawn rate (users per second)
    -t: Test duration (e.g., 300s, 5m, 1h)

Validation Metrics:
    - Response time P95 < 3 seconds
    - Error rate < 1%
    - System remains stable under load
"""

from locust import HttpUser, task, between, events
import random
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# LOAD TEST USERS
# =============================================================================

class WebFormUser(HttpUser):
    """
    Simulate users submitting support forms.
    
    This is the primary user type for load testing.
    Web form submissions are the most common interaction channel.
    
    Behavior:
    - Submits support form with random data
    - Waits 2-10 seconds between submissions
    - Weight: 3 (most common channel)
    """
    
    wait_time = between(2, 10)
    weight = 3  # Web form is most common
    
    # Valid categories for support form
    categories = ['how-to', 'technical', 'billing', 'bug-report', 'other']
    
    # Sample subjects for realistic load testing
    subjects = [
        "How to reset my password?",
        "API integration question",
        "Feature request for dashboard",
        "Bug report: Login issue",
        "Billing inquiry",
        "How to export data?",
        "Account settings help",
        "Mobile app question",
        "Integration with third-party tools",
        "Performance issue"
    ]
    
    # Sample messages for realistic load testing
    messages = [
        "Hi, I need help with understanding how to use the API. Can you provide some guidance on authentication?",
        "I'm experiencing issues with the dashboard. It's not loading properly in my browser.",
        "Could you explain the difference between the free and premium plans? What features are included?",
        "I found a bug in the system. When I click the save button, nothing happens.",
        "How can I integrate your service with my existing application? Do you have documentation?",
        "I'm trying to export my data but the export feature doesn't seem to work.",
        "The system is running very slow today. Is there a known issue?",
        "I need help setting up my account. Can you walk me through the initial configuration?",
        "Is there a mobile app available? I couldn't find it in the app store.",
        "I'm interested in the enterprise plan. What additional features does it offer?"
    ]
    
    @task
    def submit_support_form(self):
        """
        Submit a support form with realistic random data.
        
        This task simulates a real user filling out and submitting
        the web support form.
        """
        # Generate unique email for each submission
        timestamp = int(time.time() * 1000)
        random_id = random.randint(1, 10000)
        
        email = f"loadtest_{timestamp}_{random_id}@example.com"
        
        # Select random subject and message
        subject = random.choice(self.subjects)
        message = random.choice(self.messages)
        category = random.choice(self.categories)
        
        # Track start time for performance measurement
        start_time = time.time()
        
        with self.client.post(
            "/support/submit",
            json={
                "name": f"Load Test User {random_id}",
                "email": email,
                "subject": subject,
                "category": category,
                "message": message
            },
            catch_response=True
        ) as response:
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                # Verify response contains ticket_id
                try:
                    data = response.json()
                    if "ticket_id" in data:
                        response.success()
                        logger.debug(f"Form submitted successfully: {data['ticket_id']} ({elapsed:.2f}s)")
                    else:
                        response.failure("Missing ticket_id in response")
                except Exception as e:
                    response.failure(f"Invalid response format: {e}")
            elif response.status_code == 422:
                # Validation error - might be expected with random data
                response.failure(f"Validation error: {response.text}")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class HealthCheckUser(HttpUser):
    """
    Monitor system health during load test.
    
    This user type continuously checks system health and metrics
    to verify the system remains responsive under load.
    
    Behavior:
    - Checks /health endpoint
    - Queries /metrics/channels
    - Waits 5-15 seconds between checks
    - Weight: 1 (monitoring traffic)
    """
    
    wait_time = between(5, 15)
    weight = 1  # Lower weight than form submissions
    
    @task(3)
    def check_health(self):
        """
        Check system health endpoint.
        
        Verifies the system reports healthy status.
        """
        start_time = time.time()
        
        with self.client.get("/health", catch_response=True) as response:
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure(f"Unhealthy status: {data.get('status')}")
                except Exception as e:
                    response.failure(f"Invalid health response: {e}")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def check_metrics(self):
        """
        Check channel metrics endpoint.
        
        Verifies metrics are being collected and reported.
        """
        start_time = time.time()
        
        with self.client.get("/metrics/channels", catch_response=True) as response:
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Verify at least one channel has metrics
                    if len(data) > 0:
                        response.success()
                    else:
                        response.failure("Empty metrics response")
                except Exception as e:
                    response.failure(f"Invalid metrics response: {e}")
            else:
                response.failure(f"Metrics check failed: {response.status_code}")


class EmailChannelUser(HttpUser):
    """
    Simulate Gmail webhook processing load.
    
    This user type simulates incoming email traffic
    through the Gmail webhook endpoint.
    
    Behavior:
    - Sends email webhook notifications
    - Waits 5-20 seconds between submissions
    - Weight: 2 (moderate email volume)
    """
    
    wait_time = between(5, 20)
    weight = 2
    
    @task
    def send_email_webhook(self):
        """
        Simulate Gmail Pub/Sub webhook notification.
        """
        timestamp = int(time.time() * 1000)
        random_id = random.randint(1, 10000)
        
        test_email = f"email_load_{timestamp}_{random_id}@test.com"
        
        self.client.post(
            "/webhooks/gmail",
            json={
                "from": test_email,
                "to": "support@techcorp.com",
                "subject": f"Load Test Email {random_id}",
                "body": "This is a load test email to verify system performance under stress.",
                "received_at": datetime.utcnow().isoformat()
            },
            catch_response=True
        )


class WhatsAppChannelUser(HttpUser):
    """
    Simulate WhatsApp webhook processing load.
    
    This user type simulates incoming WhatsApp messages
    through the Twilio webhook endpoint.
    
    Behavior:
    - Sends WhatsApp webhook notifications
    - Waits 5-20 seconds between submissions
    - Weight: 2 (moderate WhatsApp volume)
    """
    
    wait_time = between(5, 20)
    weight = 2
    
    @task
    def send_whatsapp_webhook(self):
        """
        Simulate Twilio WhatsApp webhook notification.
        """
        timestamp = int(time.time() * 1000)
        random_id = random.randint(1, 10000)
        
        phone = f"+1415555{random.randint(1000, 9999)}"
        
        self.client.post(
            "/webhooks/whatsapp",
            data={
                "MessageSid": f"SM{timestamp}{random_id}",
                "From": f"whatsapp:{phone}",
                "Body": f"Load test message {random_id} - testing WhatsApp channel performance",
                "ProfileName": f"Load User {random_id}"
            },
            catch_response=True
        )


class MixedChannelUser(HttpUser):
    """
    Simulate realistic mixed-channel user behavior.
    
    This user type represents real-world usage where
    customers may use multiple channels over time.
    
    Behavior:
    - Randomly chooses between web form, email, or WhatsApp
    - Waits 10-30 seconds between interactions
    - Weight: 1 (mixed traffic)
    """
    
    wait_time = between(10, 30)
    weight = 1
    
    @task(3)
    def submit_web_form(self):
        """Submit via web form."""
        random_id = random.randint(1, 10000)
        
        self.client.post(
            "/support/submit",
            json={
                "name": f"Mixed User {random_id}",
                "email": f"mixed_{random_id}@example.com",
                "subject": "Mixed Channel Test",
                "category": random.choice(['how-to', 'technical', 'billing']),
                "message": "This is a mixed channel load test submission."
            }
        )
    
    @task(2)
    def send_email(self):
        """Send via email webhook."""
        random_id = random.randint(1, 10000)
        
        self.client.post(
            "/webhooks/gmail",
            json={
                "from": f"mixed_{random_id}@test.com",
                "to": "support@techcorp.com",
                "subject": "Mixed Channel Email",
                "body": "This is a mixed channel load test email.",
                "received_at": datetime.utcnow().isoformat()
            }
        )
    
    @task(1)
    def send_whatsapp(self):
        """Send via WhatsApp webhook."""
        random_id = random.randint(1, 10000)
        phone = f"+1415555{random.randint(1000, 9999)}"
        
        self.client.post(
            "/webhooks/whatsapp",
            data={
                "MessageSid": f"SM{int(time.time() * 1000)}{random_id}",
                "From": f"whatsapp:{phone}",
                "Body": f"Mixed channel test {random_id}",
                "ProfileName": f"Mixed User {random_id}"
            }
        )


# =============================================================================
# LOAD TEST EVENT HOOKS
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called when load test starts.
    
    Logs test configuration and initial system state.
    """
    logger.info("=" * 60)
    logger.info("LOAD TEST STARTING")
    logger.info("=" * 60)
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Start time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)
    
    # Check initial system health
    try:
        response = environment.client.get("/health")
        if response.status_code == 200:
            logger.info(f"Initial health check: PASSED")
        else:
            logger.warning(f"Initial health check: FAILED ({response.status_code})")
    except Exception as e:
        logger.error(f"Initial health check error: {e}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when load test stops.
    
    Logs final statistics and system state.
    """
    logger.info("=" * 60)
    logger.info("LOAD TEST COMPLETED")
    logger.info("=" * 60)
    logger.info(f"End time: {datetime.utcnow().isoformat()}")
    
    # Get statistics
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    avg_response_time = stats.total.avg_response_time
    
    logger.info(f"Total requests: {total_requests}")
    logger.info(f"Total failures: {total_failures}")
    logger.info(f"Failure rate: {(total_failures / max(total_requests, 1)) * 100:.2f}%")
    logger.info(f"Average response time: {avg_response_time:.2f}ms")
    logger.info("=" * 60)
    
    # Final health check
    try:
        response = environment.client.get("/health")
        if response.status_code == 200:
            logger.info(f"Final health check: PASSED")
        else:
            logger.warning(f"Final health check: FAILED ({response.status_code})")
    except Exception as e:
        logger.error(f"Final health check error: {e}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Called on each request.
    
    Can be used for custom logging or metrics collection.
    """
    # Log slow requests
    if response_time > 2000:  # 2 seconds
        logger.warning(f"Slow request: {name} took {response_time:.0f}ms")
    
    # Log exceptions
    if exception:
        logger.error(f"Request failed: {name} - {exception}")


# =============================================================================
# CUSTOM LOAD TEST SCENARIOS
# =============================================================================

class EscalationTestUser(HttpUser):
    """
    Test escalation handling under load.
    
    This user type specifically triggers escalations to verify
    the system handles them correctly under load.
    
    Behavior:
    - Sends pricing questions (trigger pricing escalation)
    - Sends legal mentions (trigger legal escalation)
    - Sends refund requests (trigger billing escalation)
    """
    
    wait_time = between(10, 30)
    weight = 1
    
    @task(2)
    def send_pricing_inquiry(self):
        """Send pricing question (should escalate)."""
        random_id = random.randint(1, 10000)
        
        self.client.post(
            "/support/submit",
            json={
                "name": f"Escalation Test User {random_id}",
                "email": f"escalation_{random_id}@example.com",
                "subject": "Enterprise Pricing Question",
                "category": "billing",
                "message": "What is the price for enterprise plan? I need a quote for 500 users."
            }
        )
    
    @task(1)
    def send_legal_inquiry(self):
        """Send legal mention (should escalate)."""
        random_id = random.randint(1, 10000)
        
        self.client.post(
            "/webhooks/gmail",
            json={
                "from": f"legal_{random_id}@test.com",
                "to": "support@techcorp.com",
                "subject": "Legal Issue",
                "body": "I need to consult with my lawyer about this matter.",
                "received_at": datetime.utcnow().isoformat()
            }
        )
    
    @task(1)
    def send_refund_request(self):
        """Send refund request (should escalate)."""
        random_id = random.randint(1, 10000)
        phone = f"+1415555{random.randint(1000, 9999)}"
        
        self.client.post(
            "/webhooks/whatsapp",
            data={
                "MessageSid": f"SM{int(time.time() * 1000)}{random_id}",
                "From": f"whatsapp:{phone}",
                "Body": "I want a refund for my last payment",
                "ProfileName": f"Refund User {random_id}"
            }
        )


class StressTestUser(HttpUser):
    """
    Extreme load testing for stress scenarios.
    
    This user type generates high volume traffic
    to test system limits.
    
    Behavior:
    - Very short wait times (0.5-2 seconds)
    - High weight for maximum load
    - Simple requests to maximize throughput
    """
    
    wait_time = between(0.5, 2)
    weight = 5
    
    @task
    def rapid_form_submission(self):
        """Rapid fire form submissions."""
        random_id = random.randint(1, 10000)
        
        self.client.post(
            "/support/submit",
            json={
                "name": f"Stress User {random_id}",
                "email": f"stress_{random_id}@example.com",
                "subject": "Stress Test",
                "category": "how-to",
                "message": "This is a stress test message to verify system performance under extreme load."
            }
        )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import os
    
    # Default configuration
    host = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")
    users = int(os.getenv("LOAD_TEST_USERS", "100"))
    spawn_rate = int(os.getenv("LOAD_TEST_SPAWN_RATE", "10"))
    run_time = os.getenv("LOAD_TEST_RUNTIME", "300s")
    
    print("=" * 60)
    print("CRM Digital FTE - Load Test Runner")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Users: {users}")
    print(f"Spawn Rate: {spawn_rate} users/sec")
    print(f"Run Time: {run_time}")
    print("=" * 60)
    print("\nStarting Locust load test...")
    print("\nCommand:")
    print(f"locust -f {__file__} --host={host} --headless -u {users} -r {spawn_rate} -t {run_time}")
    print("\n" + "=" * 60)
    
    # Note: Run with 'locust' command for full functionality
    # This main block is for reference only
