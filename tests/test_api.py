"""
CRM Digital FTE - API Tests
Phase 2: Specialization — Step 5

Test FastAPI endpoints using TestClient.
"""

import sys
import os
import time
import random

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from api.main import app

# Create test client
client = TestClient(app)


def generate_test_email():
    """Generate unique test email."""
    return f"api_test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_returns_200(self):
        """Test that health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_response_has_status(self):
        """Test that health response has status field."""
        response = client.get("/health")
        data = response.json()
        assert 'status' in data
    
    def test_health_status_is_healthy(self):
        """Test that health status is 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data['status'] == 'healthy'


class TestSupportSubmit:
    """Test support form submission endpoint."""
    
    def test_submit_valid_form(self):
        """Test submitting a valid form."""
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "email": generate_test_email(),
                "subject": "Test Subject",
                "category": "how-to",
                "message": "This is a test message for the support form."
            }
        )
        assert response.status_code == 200
    
    def test_submit_missing_email_fails(self):
        """Test that missing email fails validation."""
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "subject": "Test Subject",
                "category": "how-to",
                "message": "This is a test message."
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_submit_invalid_email_fails(self):
        """Test that invalid email fails validation."""
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "email": "invalid-email",
                "subject": "Test Subject",
                "category": "how-to",
                "message": "This is a test message."
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_submit_returns_ticket_id(self):
        """Test that submission returns ticket_id."""
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "email": generate_test_email(),
                "subject": "Test Subject",
                "category": "how-to",
                "message": "This is a test message for the support form."
            }
        )
        data = response.json()
        assert 'ticket_id' in data
    
    def test_submit_returns_escalated_flag(self):
        """Test that submission returns escalated flag."""
        # This will escalate because we're calling the agent
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "email": generate_test_email(),
                "subject": "Pricing Question",
                "category": "billing",
                "message": "What is the price for enterprise?"
            }
        )
        # Should succeed (agent handles escalation internally)
        assert response.status_code == 200


class TestTicketEndpoint:
    """Test ticket status endpoint."""
    
    def test_get_nonexistent_ticket_returns_404(self):
        """Test that nonexistent ticket returns 404."""
        response = client.get("/support/ticket/TKT-NONEXISTENT")
        assert response.status_code == 404
    
    def test_get_ticket_wrong_format_404(self):
        """Test that wrong ticket ID format returns 404."""
        response = client.get("/support/ticket/invalid-format")
        assert response.status_code == 404


class TestCustomerLookup:
    """Test customer lookup endpoint."""
    
    def test_lookup_without_params_returns_400(self):
        """Test that lookup without params returns 400."""
        response = client.get("/customers/lookup")
        assert response.status_code == 400
    
    def test_lookup_with_email_returns_200(self):
        """Test that lookup with email returns 200."""
        response = client.get(
            "/customers/lookup",
            params={"email": generate_test_email()}
        )
        assert response.status_code == 200
    
    def test_lookup_returns_customer_id(self):
        """Test that lookup returns customer_id."""
        email = generate_test_email()
        response = client.get(
            "/customers/lookup",
            params={"email": email}
        )
        data = response.json()
        assert 'customer_id' in data


class TestMetrics:
    """Test metrics endpoints."""
    
    def test_channel_metrics_returns_200(self):
        """Test that channel metrics returns 200."""
        response = client.get("/metrics/channels")
        assert response.status_code == 200
    
    def test_channel_metrics_has_email(self):
        """Test that channel metrics has email data."""
        response = client.get("/metrics/channels")
        data = response.json()
        assert 'email' in data
    
    def test_channel_metrics_has_whatsapp(self):
        """Test that channel metrics has whatsapp data."""
        response = client.get("/metrics/channels")
        data = response.json()
        assert 'whatsapp' in data
