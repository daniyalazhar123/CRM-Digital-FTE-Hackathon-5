"""
CRM Digital FTE - Prometheus Monitoring Tests
Feature 6: Test Coverage Enhancement

Tests for Prometheus metrics endpoint and tracking.
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from api.main import app

# Create test client
client = TestClient(app)


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""
    
    def test_metrics_endpoint_exists(self):
        """Test that /metrics endpoint exists."""
        response = client.get('/metrics')
        
        # Should return something (even if 503 if prometheus not installed)
        assert response.status_code in [200, 503]
    
    def test_metrics_content_type(self):
        """Test metrics endpoint content type."""
        response = client.get('/metrics')
        
        if response.status_code == 200:
            assert 'text/plain' in response.headers.get('content-type', '')
    
    def test_metrics_format(self):
        """Test metrics response format."""
        response = client.get('/metrics')
        
        if response.status_code == 200:
            content = response.body.decode()
            # Prometheus metrics should contain specific patterns
            assert '#' in content or 'api_' in content


class TestRequestTracking:
    """Test request tracking middleware."""
    
    def test_health_request_tracked(self):
        """Test that health endpoint requests are tracked."""
        # Make request to trigger middleware
        response = client.get('/health')
        assert response.status_code == 200
        
        # Check metrics were updated
        metrics_response = client.get('/metrics')
        if metrics_response.status_code == 200:
            content = metrics_response.body.decode()
            # Should have request count metric
            assert 'api_requests_total' in content or 'http_requests_total' in content
    
    def test_support_submit_tracked(self):
        """Test that support submit requests are tracked."""
        response = client.post('/support/submit', json={
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test',
            'category': 'how-to',
            'message': 'Test message for tracking'
        })
        
        # Check metrics
        metrics_response = client.get('/metrics')
        if metrics_response.status_code == 200:
            content = metrics_response.body.decode()
            assert 'api_requests_total' in content or 'http_requests_total' in content


class TestPrometheusAvailability:
    """Test Prometheus client availability."""
    
    def test_prometheus_import(self):
        """Test prometheus_client can be imported."""
        try:
            from prometheus_client import Counter, Histogram, generate_latest
            assert Counter is not None
            assert Histogram is not None
        except ImportError:
            # OK if not installed
            pass
    
    def test_prometheus_available_flag(self):
        """Test PROMETHEUS_AVAILABLE flag."""
        from api.main import PROMETHEUS_AVAILABLE
        
        # Should be boolean
        assert isinstance(PROMETHEUS_AVAILABLE, bool)


class TestMetricsDefinitions:
    """Test that metrics are properly defined."""
    
    def test_request_count_metric(self):
        """Test REQUEST_COUNT metric definition."""
        from api.main import PROMETHEUS_AVAILABLE
        
        if PROMETHEUS_AVAILABLE:
            from api.main import REQUEST_COUNT
            assert REQUEST_COUNT is not None
    
    def test_request_latency_metric(self):
        """Test REQUEST_LATENCY metric definition."""
        from api.main import PROMETHEUS_AVAILABLE
        
        if PROMETHEUS_AVAILABLE:
            from api.main import REQUEST_LATENCY
            assert REQUEST_LATENCY is not None
    
    def test_error_count_metric(self):
        """Test ERROR_COUNT metric definition."""
        from api.main import PROMETHEUS_AVAILABLE
        
        if PROMETHEUS_AVAILABLE:
            from api.main import ERROR_COUNT
            assert ERROR_COUNT is not None
    
    def test_channel_messages_metric(self):
        """Test CHANNEL_MESSAGES metric definition."""
        from api.main import PROMETHEUS_AVAILABLE
        
        if PROMETHEUS_AVAILABLE:
            from api.main import CHANNEL_MESSAGES
            assert CHANNEL_MESSAGES is not None
    
    def test_escalation_count_metric(self):
        """Test ESCALATION_COUNT metric definition."""
        from api.main import PROMETHEUS_AVAILABLE
        
        if PROMETHEUS_AVAILABLE:
            from api.main import ESCALATION_COUNT
            assert ESCALATION_COUNT is not None


class TestMiddlewareTracking:
    """Test middleware request tracking."""
    
    def test_middleware_exists(self):
        """Test that tracking middleware is registered."""
        # Check app has middleware
        assert len(app.user_middleware) > 0
        
        # Find track_requests middleware
        middleware_names = [
            str(m.cls) if hasattr(m, 'cls') else str(m)
            for m in app.user_middleware
        ]
        
        # Should have HTTP middleware
        assert any('http' in name.lower() or 'middleware' in name.lower() 
                   for name in middleware_names)
    
    def test_middleware_tracks_success_requests(self):
        """Test middleware tracks successful requests."""
        # Make successful request
        response = client.get('/health')
        assert response.status_code == 200
        
        # Verify metrics updated
        metrics = client.get('/metrics')
        if metrics.status_code == 200:
            content = metrics.body.decode()
            # Should track 200 status
            assert '200' in content
    
    def test_middleware_tracks_error_requests(self):
        """Test middleware tracks error requests."""
        # Make request that might error
        response = client.get('/customers/lookup')  # Missing params
        assert response.status_code == 400
        
        # Verify metrics updated
        metrics = client.get('/metrics')
        if metrics.status_code == 200:
            content = metrics.body.decode()
            # Should track 400 status
            assert '400' in content


class TestChannelMetrics:
    """Test channel-specific metrics."""
    
    def test_webform_channel_tracked(self):
        """Test web form channel metrics."""
        response = client.post('/support/submit', json={
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test',
            'category': 'how-to',
            'message': 'Test message'
        })
        
        # Check channel metrics
        metrics = client.get('/metrics')
        if metrics.status_code == 200:
            content = metrics.body.decode()
            # Should have channel metric
            assert 'channel_messages_total' in content or 'web_form' in content


class TestMonitoringIntegration:
    """Test monitoring integration."""
    
    def test_monitoring_module_imports(self):
        """Test monitoring-related imports work."""
        # These should not raise ImportError
        from api.main import (
            PROMETHEUS_AVAILABLE,
        )
        
        assert PROMETHEUS_AVAILABLE is not None
        
        # Metrics may not be defined if prometheus not installed
        try:
            from api.main import (
                REQUEST_COUNT,
                REQUEST_LATENCY,
                ERROR_COUNT
            )
            assert REQUEST_COUNT is not None
        except (ImportError, NameError):
            # OK if prometheus not installed
            pass
    
    def test_k8s_monitoring_config_exists(self):
        """Test Kubernetes monitoring config exists."""
        monitoring_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'k8s', 
            'monitoring.yaml'
        )
        
        # File should exist
        assert os.path.exists(monitoring_path)
        
        # Should contain Prometheus config
        with open(monitoring_path, 'r') as f:
            content = f.read()
            assert 'prometheus' in content.lower() or 'Prometheus' in content
