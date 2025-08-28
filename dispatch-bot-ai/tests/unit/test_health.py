"""
Unit tests for health check endpoint.
Following TDD approach - this test will fail initially.
"""

import pytest
from fastapi.testclient import TestClient
from dispatch_bot.main import app


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_endpoint_returns_200(self):
        """Test that the health endpoint returns HTTP 200."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_correct_structure(self):
        """Test that the health endpoint returns the correct JSON structure."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        
        # Verify required fields exist
        assert "status" in json_response
        assert "version" in json_response
        assert "timestamp" in json_response
        assert "services" in json_response
        assert "uptime_seconds" in json_response

    def test_health_endpoint_status_is_healthy(self):
        """Test that the health endpoint returns 'healthy' status."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "healthy"

    def test_health_endpoint_has_services_status(self):
        """Test that the health endpoint includes services status."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        
        # Verify services object structure
        services = json_response["services"]
        assert isinstance(services, dict)
        
        # At minimum, we should have these service checks
        expected_services = ["database", "geocoding", "llm", "traffic"]
        for service in expected_services:
            assert service in services
            # Each service should have a status
            assert services[service] in ["healthy", "degraded", "unhealthy"]

    def test_health_endpoint_version_format(self):
        """Test that version follows semantic versioning format."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        
        version = json_response["version"]
        # Basic semantic version pattern (X.Y.Z)
        import re
        version_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(version_pattern, version), f"Version {version} doesn't match semver pattern"

    def test_health_endpoint_uptime_is_numeric(self):
        """Test that uptime_seconds is a numeric value."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        
        uptime = json_response["uptime_seconds"]
        assert isinstance(uptime, (int, float))
        assert uptime >= 0