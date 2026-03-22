"""
CRM Digital FTE - Pytest Configuration and Fixtures
"""

import pytest
import psycopg2
import time
import random


@pytest.fixture(scope="session")
def db_config():
    """Database configuration."""
    return {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'crm_db',
        'user': 'postgres',
        'password': 'postgres123'
    }


@pytest.fixture
def db_conn(db_config):
    """
    Create a direct database connection for testing.
    Uses autocommit mode for test isolation.
    """
    conn = psycopg2.connect(**db_config)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def test_email():
    """Generate unique test email address."""
    return f"test_{int(time.time())}_{random.randint(1000, 9999)}@test.com"


@pytest.fixture
def test_phone():
    """Generate unique test phone number."""
    return f"+1415555{random.randint(1000, 9999)}"


@pytest.fixture
def customer_data(test_email):
    """Create customer test data."""
    return {
        'email': test_email,
        'name': f"Test User {random.randint(1000, 9999)}",
        'plan': 'free'
    }


@pytest.fixture
def ticket_data():
    """Create ticket test data."""
    return {
        'issue': f"Test issue {random.randint(1000, 9999)}",
        'priority': 'medium',
        'channel': 'email'
    }
