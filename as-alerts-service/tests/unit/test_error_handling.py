"""
Unit tests for AS Alerts Service error handling.

Tests error scenarios and exception handling following unittest patterns
and real error conditions that occur in production.
"""

import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from main import app


class TestAPIErrorHandling(unittest.TestCase):
    """Test API error handling provides proper HTTP responses for client errors."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    def test_invalid_json_request_body(self):
        """Test API handles malformed JSON request bodies properly."""
        # Send malformed JSON
        response = self.client.post(
            "/alerts",
            data="{ invalid json }",  # Not proper JSON
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 422)
    
    def test_missing_content_type_header(self):
        """Test API handles missing Content-Type header properly."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        # Send without Content-Type header
        response = self.client.post("/alerts", json=request_data)
        # FastAPI should still handle this, but test the behavior
        
        # Should either work (FastAPI is forgiving) or return proper error
        self.assertIn(response.status_code, [200, 201, 422])
    
    def test_oversized_request_payload(self):
        """Test API handles oversized request payloads appropriately."""
        # Create request with very large message
        large_message = "x" * 100000  # 100KB message
        
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": large_message
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        # Should handle gracefully (either accept or reject with proper code)
        self.assertIn(response.status_code, [201, 413, 422])
    
    def test_unsupported_http_methods(self):
        """Test API returns proper errors for unsupported HTTP methods."""
        # Test unsupported methods on various endpoints
        unsupported_methods = [
            ("PATCH", "/alerts"),
            ("DELETE", "/alerts"),
            ("PUT", "/alerts"),  # Only POST is supported
            ("PATCH", "/health"),
            ("POST", "/health"),  # Only GET is supported
        ]
        
        for method, endpoint in unsupported_methods:
            with self.subTest(method=method, endpoint=endpoint):
                response = self.client.request(method, endpoint)
                self.assertEqual(response.status_code, 405)  # Method Not Allowed
    
    def test_nonexistent_endpoints(self):
        """Test API returns 404 for nonexistent endpoints."""
        nonexistent_endpoints = [
            "/nonexistent",
            "/alerts/invalid/endpoint",
            "/api/v1/alerts",  # Wrong API version
            "/alert",  # Singular instead of plural
            "/healthcheck",  # Different spelling
        ]
        
        for endpoint in nonexistent_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 404)


class TestDatabaseErrorHandling(unittest.TestCase):
    """Test database error handling provides proper fallback behavior."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.create_alert_in_db')
    def test_database_connection_failure_on_create(self, mock_create_alert):
        """Test create alert handles database connection failures."""
        # Simulate connection failure
        mock_create_alert.side_effect = Exception("Connection to database failed")
        
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 500)
        
        response_data = response.json()
        self.assertIn("error", response_data)
    
    @patch('main.get_alerts_from_db')
    def test_database_timeout_on_query(self, mock_get_alerts):
        """Test get alerts handles database timeout errors."""
        # Simulate query timeout
        mock_get_alerts.side_effect = Exception("Query timeout after 60 seconds")
        
        tenant_id = str(uuid4())
        response = self.client.get(f"/alerts?tenant_id={tenant_id}")
        
        self.assertEqual(response.status_code, 500)
    
    @patch('main.get_db_connection')
    def test_database_pool_exhaustion(self, mock_get_db):
        """Test API handles database connection pool exhaustion."""
        # Simulate pool exhaustion
        mock_get_db.side_effect = HTTPException(
            status_code=503, 
            detail="Database not available"
        )
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 503)
    
    @patch('main.update_alert_status')
    def test_database_constraint_violation(self, mock_update_alert):
        """Test alert update handles database constraint violations."""
        # Simulate constraint violation (e.g., invalid status transition)
        mock_update_alert.side_effect = Exception("Check constraint violation")
        
        alert_id = str(uuid4())
        request_data = {"note": "test note"}
        
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json=request_data)
        
        self.assertEqual(response.status_code, 500)


class TestValidationErrorHandling(unittest.TestCase):
    """Test validation error handling provides actionable error messages."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    def test_missing_required_fields_error_detail(self):
        """Test validation errors provide specific field information."""
        # Missing tenant_id
        request_data = {
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
        
        response_data = response.json()
        # Should indicate which field is missing
        self.assertIn("tenant_id", str(response_data))
    
    def test_invalid_uuid_format_error_detail(self):
        """Test UUID validation provides specific format error."""
        request_data = {
            "tenant_id": "not-a-valid-uuid-format",
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
        
        response_data = response.json()
        # Should indicate UUID format issue
        self.assertIn("tenant_id", str(response_data))
    
    def test_invalid_enum_value_error_detail(self):
        """Test enum validation provides available options."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message",
            "severity": "invalid_severity_level"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
        
        response_data = response.json()
        # Should indicate valid severity options
        self.assertIn("severity", str(response_data).lower())
    
    def test_empty_string_validation_error(self):
        """Test empty string validation provides meaningful errors."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "",  # Empty rule name
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
    
    def test_query_parameter_validation_errors(self):
        """Test query parameter validation provides helpful error messages."""
        # Invalid tenant_id in query parameter
        response = self.client.get("/alerts?tenant_id=invalid-uuid")
        
        self.assertEqual(response.status_code, 422)
        
        # Invalid status filter
        tenant_id = str(uuid4())
        response = self.client.get(f"/alerts?tenant_id={tenant_id}&status=invalid_status")
        
        self.assertEqual(response.status_code, 422)


class TestBusinessLogicErrorHandling(unittest.TestCase):
    """Test business logic error handling enforces real business constraints."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.get_alert_by_id')
    def test_alert_not_found_for_operations(self, mock_get_alert):
        """Test operations on non-existent alerts return proper 404."""
        mock_get_alert.return_value = None
        
        alert_id = str(uuid4())
        
        # Test acknowledge non-existent alert
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json={})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Alert not found")
        
        # Test resolve non-existent alert
        response = self.client.put(f"/alerts/{alert_id}/resolve", json={})
        self.assertEqual(response.status_code, 404)
        
        # Test get non-existent alert
        response = self.client.get(f"/alerts/{alert_id}")
        self.assertEqual(response.status_code, 404)
    
    def test_malformed_uuid_handling(self):
        """Test malformed UUID handling in path parameters."""
        malformed_uuids = [
            "123",  # Too short
            "not-a-uuid",  # Invalid format
            "123e4567-e89b-12d3-a456",  # Missing segments
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
        ]
        
        for malformed_uuid in malformed_uuids:
            with self.subTest(malformed_uuid=malformed_uuid):
                # Should handle gracefully and return appropriate error
                response = self.client.get(f"/alerts/{malformed_uuid}")
                self.assertIn(response.status_code, [404, 422])  # Either not found or validation error
    
    @patch('main.get_alert_stats_from_db')
    def test_statistics_calculation_errors(self, mock_get_stats):
        """Test statistics endpoint handles calculation errors."""
        # Simulate database returning inconsistent data
        mock_get_stats.side_effect = Exception("Statistics calculation failed")
        
        tenant_id = str(uuid4())
        response = self.client.get(f"/stats/{tenant_id}")
        
        self.assertEqual(response.status_code, 500)


class TestAuthenticationErrorHandling(unittest.TestCase):
    """Test authentication error handling provides security without information leakage."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    def test_missing_authentication_for_internal_endpoints(self):
        """Test internal endpoints require authentication."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "internal_rule",
            "message": "internal message"
        }
        
        # No Authorization header
        response = self.client.post("/internal/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_invalid_authentication_format(self):
        """Test invalid authentication header formats are rejected."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "internal_rule",
            "message": "internal message"
        }
        
        invalid_auth_headers = [
            {"Authorization": "InvalidFormat"},  # No Bearer
            {"Authorization": "Bearer"},  # No token
            {"Authorization": "Basic dGVzdDp0ZXN0"},  # Wrong auth type
            {"x-api-key": "some-key"},  # Wrong header name
        ]
        
        for headers in invalid_auth_headers:
            with self.subTest(headers=headers):
                response = self.client.post("/internal/alerts", json=request_data, headers=headers)
                self.assertEqual(response.status_code, 401)
    
    def test_authentication_error_consistency(self):
        """Test authentication errors don't leak information about valid keys."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        # Different invalid tokens should return same error structure
        invalid_tokens = [
            "wrong-token",
            "nmc-internal-services-auth-key-phase2",  # Similar but wrong
            "",  # Empty
            "admin",  # Common attempt
        ]
        
        error_responses = []
        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.post("/internal/alerts", json=request_data, headers=headers)
            error_responses.append(response.status_code)
        
        # All should return 401
        self.assertTrue(all(code == 401 for code in error_responses))


class TestConcurrencyErrorHandling(unittest.TestCase):
    """Test error handling under concurrent access scenarios."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.update_alert_status')
    def test_concurrent_alert_update_handling(self, mock_update_alert):
        """Test handling of concurrent alert status updates."""
        # Simulate race condition where alert was already updated
        mock_update_alert.return_value = None  # Alert not found after concurrent update
        
        alert_id = str(uuid4())
        request_data = {"note": "concurrent update test"}
        
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json=request_data)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Alert not found")
    
    @patch('main.get_db_connection')
    def test_database_deadlock_handling(self, mock_get_db):
        """Test handling of database deadlock scenarios."""
        # Simulate deadlock detection
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Deadlock detected")
        
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "deadlock_test",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 500)


if __name__ == '__main__':
    unittest.main()