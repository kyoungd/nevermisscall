"""
Unit tests for AS Alerts Service API endpoints.

Tests FastAPI endpoints with heavy mocking following unittest patterns
and real API usage scenarios.
"""

import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app, AlertSeverity, AlertStatus


class TestHealthEndpoint(unittest.TestCase):
    """Test health endpoint provides accurate service status for monitoring."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('shared.health_check')
    def test_health_check_healthy_service(self, mock_health_check):
        """Test health endpoint returns healthy status when database is accessible."""
        # Mock successful health check from shared library
        mock_health_check.return_value = True
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertEqual(response_data["status"], "healthy")
        self.assertEqual(response_data["service"], "as-alerts-service")
        self.assertTrue(response_data["database_connected"])
    
    @patch('shared.health_check')
    def test_health_check_database_unavailable(self, mock_health_check):
        """Test health endpoint returns 503 when database is unavailable."""
        # Mock database health check failure
        mock_health_check.return_value = False
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 503)
    
    @patch('shared.health_check')
    def test_health_check_database_error(self, mock_health_check):
        """Test health endpoint handles database query errors properly."""
        # Mock database health check exception
        mock_health_check.side_effect = Exception("Query timeout")
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 503)


class TestCreateAlertEndpoint(unittest.TestCase):
    """Test alert creation endpoint validates input and creates alerts properly."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.create_alert_in_db')
    def test_create_alert_with_valid_data(self, mock_create_alert):
        """Test creating alert with valid request data."""
        tenant_id = str(uuid4())
        alert_id = str(uuid4())
        created_time = datetime.utcnow()
        
        # Mock successful alert creation - returns dict as in shared library
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": tenant_id,
            "rule_name": "high_cpu_usage",
            "message": "CPU usage exceeded 90%",
            "severity": "high",
            "status": "triggered",
            "created_at": created_time.isoformat(),
            "updated_at": created_time.isoformat(),
            "acknowledged_at": None,
            "acknowledgment_note": None,
            "resolved_at": None,
            "resolution_note": None
        }
        mock_create_alert.return_value = mock_alert_dict
        
        request_data = {
            "tenant_id": tenant_id,
            "rule_name": "high_cpu_usage",
            "message": "CPU usage exceeded 90%",
            "severity": "high"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        self.assertIn("data", response_data)
        alert_data = response_data["data"]
        self.assertEqual(alert_data["id"], alert_id)
        self.assertEqual(alert_data["tenant_id"], tenant_id)
        self.assertEqual(alert_data["severity"], "high")
        self.assertEqual(alert_data["status"], "triggered")
    
    def test_create_alert_with_invalid_tenant_id(self):
        """Test creating alert with invalid tenant_id format."""
        request_data = {
            "tenant_id": "not-a-valid-uuid",
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
        
        response_data = response.json()
        self.assertIn("tenant_id", str(response_data))
    
    def test_create_alert_with_missing_required_fields(self):
        """Test creating alert with missing required fields."""
        required_fields = ["tenant_id", "rule_name", "message"]
        
        for missing_field in required_fields:
            with self.subTest(missing_field=missing_field):
                request_data = {
                    "tenant_id": str(uuid4()),
                    "rule_name": "test_rule",
                    "message": "test message"
                }
                del request_data[missing_field]
                
                response = self.client.post("/alerts", json=request_data)
                
                self.assertEqual(response.status_code, 422)
    
    def test_create_alert_with_invalid_severity(self):
        """Test creating alert with invalid severity value."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule", 
            "message": "test message",
            "severity": "invalid_severity"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 422)
    
    @patch('main.create_alert_in_db')
    def test_create_alert_database_error(self, mock_create_alert):
        """Test creating alert handles database errors properly."""
        mock_create_alert.side_effect = Exception("Database connection failed")
        
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/alerts", json=request_data)
        
        # FastAPI maintains decorator status code but returns error_response structure
        self.assertEqual(response.status_code, 201)  # Decorator status code preserved
        response_data = response.json()
        self.assertFalse(response_data["success"])  # But success=False indicates error
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"], "Failed to create alert")


class TestGetAlertsEndpoint(unittest.TestCase):
    """Test get alerts endpoint enforces tenant isolation and filtering."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.get_alerts_from_db')
    def test_get_alerts_for_tenant(self, mock_get_alerts):
        """Test retrieving alerts for specific tenant."""
        tenant_id = str(uuid4())
        mock_alerts = [{
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "rule_name": "rule1",
            "message": "message1",
            "severity": "medium",
            "status": "triggered",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "acknowledged_at": None,
            "acknowledgment_note": None,
            "resolved_at": None,
            "resolution_note": None
        }]
        mock_get_alerts.return_value = mock_alerts
        
        response = self.client.get(f"/alerts?tenant_id={tenant_id}")
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        self.assertIn("data", response_data)
        alerts_data = response_data["data"]
        self.assertEqual(len(alerts_data), 1)
        self.assertEqual(alerts_data[0]["tenant_id"], tenant_id)
        
        # Verify database function called with correct parameters
        mock_get_alerts.assert_called_once_with(tenant_id, None, None)
    
    @patch('main.get_alerts_from_db')
    def test_get_alerts_with_status_filter(self, mock_get_alerts):
        """Test retrieving alerts with status filter."""
        tenant_id = str(uuid4())
        status_filter = "acknowledged"
        mock_get_alerts.return_value = []
        
        response = self.client.get(f"/alerts?tenant_id={tenant_id}&status={status_filter}")
        
        self.assertEqual(response.status_code, 200)
        
        # Verify database function called with status filter
        mock_get_alerts.assert_called_once_with(tenant_id, status_filter, None)
    
    @patch('main.get_alerts_from_db')
    def test_get_alerts_with_severity_filter(self, mock_get_alerts):
        """Test retrieving alerts with severity filter."""
        tenant_id = str(uuid4())
        severity_filter = "critical"
        mock_get_alerts.return_value = []
        
        response = self.client.get(f"/alerts?tenant_id={tenant_id}&severity={severity_filter}")
        
        self.assertEqual(response.status_code, 200)
        
        # Verify database function called with severity filter
        mock_get_alerts.assert_called_once_with(tenant_id, None, severity_filter)
    
    def test_get_alerts_without_tenant_id(self):
        """Test get alerts endpoint requires tenant_id parameter."""
        response = self.client.get("/alerts")
        
        self.assertEqual(response.status_code, 422)
    
    def test_get_alerts_with_invalid_tenant_id(self):
        """Test get alerts with invalid tenant_id format."""
        response = self.client.get("/alerts?tenant_id=not-a-uuid")
        
        # Shared library error_response returns 200 with error structure
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
    
    def test_get_alerts_with_invalid_status(self):
        """Test get alerts with invalid status filter."""
        tenant_id = str(uuid4())
        response = self.client.get(f"/alerts?tenant_id={tenant_id}&status=invalid_status")
        
        # Shared library error_response returns 200 with error structure
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
    
    def test_get_alerts_with_invalid_severity(self):
        """Test get alerts with invalid severity filter."""
        tenant_id = str(uuid4())
        response = self.client.get(f"/alerts?tenant_id={tenant_id}&severity=invalid_severity")
        
        # Shared library error_response returns 200 with error structure
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)


class TestGetAlertByIdEndpoint(unittest.TestCase):
    """Test get specific alert endpoint validates IDs and returns proper responses."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.get_alert_by_id')
    def test_get_alert_by_id_found(self, mock_get_alert):
        """Test retrieving existing alert by ID."""
        alert_id = str(uuid4())
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message",
            "severity": "medium",
            "status": "triggered",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "acknowledged_at": None,
            "acknowledgment_note": None,
            "resolved_at": None,
            "resolution_note": None
        }
        mock_get_alert.return_value = mock_alert_dict
        
        response = self.client.get(f"/alerts/{alert_id}")
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        alert_data = response_data["data"]
        self.assertEqual(alert_data["id"], alert_id)
    
    @patch('main.get_alert_by_id')
    def test_get_alert_by_id_not_found(self, mock_get_alert):
        """Test retrieving non-existent alert returns 404."""
        alert_id = str(uuid4())
        mock_get_alert.return_value = None
        
        response = self.client.get(f"/alerts/{alert_id}")
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library error_response format
        self.assertFalse(response_data["success"])
        self.assertIn("Alert not found", response_data["error"])


class TestAcknowledgeAlertEndpoint(unittest.TestCase):
    """Test acknowledge alert endpoint updates status correctly."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.update_alert_status')
    def test_acknowledge_alert_with_note(self, mock_update_alert):
        """Test acknowledging alert with acknowledgment note."""
        alert_id = str(uuid4())
        acknowledged_time = datetime.utcnow()
        
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message",
            "severity": "high",
            "status": "acknowledged",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": acknowledged_time.isoformat(),
            "acknowledged_at": acknowledged_time.isoformat(),
            "acknowledgment_note": "Investigating with team",
            "resolved_at": None,
            "resolution_note": None
        }
        mock_update_alert.return_value = mock_alert_dict
        
        request_data = {"note": "Investigating with team"}
        
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        alert_data = response_data["data"]
        self.assertEqual(alert_data["status"], "acknowledged")
        self.assertEqual(alert_data["acknowledgment_note"], "Investigating with team")
        
        # Verify update function called with correct parameters
        mock_update_alert.assert_called_once_with(alert_id, AlertStatus.ACKNOWLEDGED, "Investigating with team")
    
    @patch('main.update_alert_status')
    def test_acknowledge_alert_without_note(self, mock_update_alert):
        """Test acknowledging alert without note."""
        alert_id = str(uuid4())
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message",
            "severity": "medium",
            "status": "acknowledged",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "acknowledged_at": datetime.utcnow().isoformat(),
            "acknowledgment_note": None,
            "resolved_at": None,
            "resolution_note": None
        }
        mock_update_alert.return_value = mock_alert_dict
        
        request_data = {}
        
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify update function called with None note
        mock_update_alert.assert_called_once_with(alert_id, AlertStatus.ACKNOWLEDGED, None)
    
    @patch('main.update_alert_status')
    def test_acknowledge_alert_not_found(self, mock_update_alert):
        """Test acknowledging non-existent alert returns 404."""
        alert_id = str(uuid4())
        mock_update_alert.return_value = None
        
        request_data = {"note": "test note"}
        
        response = self.client.put(f"/alerts/{alert_id}/acknowledge", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("Alert not found", response_data["error"])


class TestResolveAlertEndpoint(unittest.TestCase):
    """Test resolve alert endpoint updates status and workflow correctly."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.update_alert_status')
    def test_resolve_alert_with_note(self, mock_update_alert):
        """Test resolving alert with resolution note."""
        alert_id = str(uuid4())
        resolved_time = datetime.utcnow()
        
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message",
            "severity": "high",
            "status": "resolved",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": resolved_time.isoformat(),
            "acknowledged_at": datetime.utcnow().isoformat(),
            "acknowledgment_note": "Previously acknowledged",
            "resolved_at": resolved_time.isoformat(),
            "resolution_note": "Fixed by restarting service"
        }
        mock_update_alert.return_value = mock_alert_dict
        
        request_data = {"note": "Fixed by restarting service"}
        
        response = self.client.put(f"/alerts/{alert_id}/resolve", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        alert_data = response_data["data"]
        self.assertEqual(alert_data["status"], "resolved")
        self.assertEqual(alert_data["resolution_note"], "Fixed by restarting service")
        
        # Verify update function called with correct parameters
        mock_update_alert.assert_called_once_with(alert_id, AlertStatus.RESOLVED, "Fixed by restarting service")


class TestGetStatisticsEndpoint(unittest.TestCase):
    """Test statistics endpoint provides accurate tenant metrics."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.get_alert_stats_from_db')
    def test_get_statistics_for_tenant(self, mock_get_stats):
        """Test retrieving alert statistics for tenant."""
        from main import AlertStats
        
        tenant_id = str(uuid4())
        mock_stats = AlertStats(
            total=25,
            triggered=8,
            acknowledged=5,
            resolved=12
        )
        mock_get_stats.return_value = mock_stats
        
        response = self.client.get(f"/stats/{tenant_id}")
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        stats_data = response_data["data"]
        self.assertEqual(stats_data["total"], 25)
        self.assertEqual(stats_data["triggered"], 8)
        self.assertEqual(stats_data["acknowledged"], 5)
        self.assertEqual(stats_data["resolved"], 12)
        
        # Verify database function called with correct tenant_id
        mock_get_stats.assert_called_once_with(tenant_id)
    
    def test_get_statistics_with_invalid_tenant_id(self):
        """Test get statistics with invalid tenant_id format."""
        response = self.client.get("/stats/not-a-uuid")
        
        # Shared library error_response returns 200 with error structure
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
    
    @patch('main.get_alert_stats_from_db')
    def test_get_statistics_database_error(self, mock_get_stats):
        """Test get statistics handles database errors properly."""
        tenant_id = str(uuid4())
        mock_get_stats.side_effect = Exception("Database query failed")
        
        response = self.client.get(f"/stats/{tenant_id}")
        
        # Shared library error_response returns 200 with error structure
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)


class TestInternalCreateAlertEndpoint(unittest.TestCase):
    """Test internal alert creation endpoint with service authentication."""
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @patch('main.create_alert_in_db')
    def test_create_internal_alert_with_valid_auth(self, mock_create_alert):
        """Test creating internal alert with valid service authentication."""
        tenant_id = str(uuid4())
        alert_id = str(uuid4())
        
        mock_alert_dict = {
            "id": alert_id,
            "tenant_id": tenant_id,
            "rule_name": "system_alert",
            "message": "System maintenance required",
            "severity": "medium",
            "status": "triggered",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "acknowledged_at": None,
            "acknowledgment_note": None,
            "resolved_at": None,
            "resolution_note": None
        }
        mock_create_alert.return_value = mock_alert_dict
        
        request_data = {
            "tenant_id": tenant_id,
            "rule_name": "system_alert",
            "message": "System maintenance required"
        }
        
        headers = {
            "X-Service-Key": "nmc-internal-services-auth-key-phase1"
        }
        
        response = self.client.post("/internal/alerts", json=request_data, headers=headers)
        
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        # Response uses shared library success_response format
        self.assertTrue(response_data["success"])
        alert_data = response_data["data"]
        self.assertEqual(alert_data["id"], alert_id)
        self.assertEqual(alert_data["rule_name"], "system_alert")
    
    def test_create_internal_alert_without_auth(self):
        """Test creating internal alert without authentication fails."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        response = self.client.post("/internal/alerts", json=request_data)
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_internal_alert_with_invalid_auth(self):
        """Test creating internal alert with invalid service key fails."""
        request_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "test_rule",
            "message": "test message"
        }
        
        headers = {
            "X-Service-Key": "invalid-service-key"
        }
        
        response = self.client.post("/internal/alerts", json=request_data, headers=headers)
        
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()