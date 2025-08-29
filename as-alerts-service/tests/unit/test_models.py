"""
Unit tests for AS Alerts Service Pydantic models.

Tests model validation, serialization, and business logic following
the unittest patterns and real business rule validation.
"""

import unittest
from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from main import (
    AlertSeverity,
    AlertStatus,
    AlertCreate,
    AlertUpdate,
    AlertStats,
    HealthResponse
)


class TestAlertEnums(unittest.TestCase):
    """Test alert severity and status enums enforce real business constraints."""
    
    def test_alert_severity_values(self):
        """Test AlertSeverity contains expected severity levels."""
        expected_severities = ["low", "medium", "high", "critical"]
        actual_severities = [severity.value for severity in AlertSeverity]
        
        self.assertEqual(set(actual_severities), set(expected_severities))
        
        # Test enum access
        self.assertEqual(AlertSeverity.LOW.value, "low")
        self.assertEqual(AlertSeverity.MEDIUM.value, "medium")
        self.assertEqual(AlertSeverity.HIGH.value, "high")
        self.assertEqual(AlertSeverity.CRITICAL.value, "critical")
    
    def test_alert_status_workflow(self):
        """Test AlertStatus follows the documented workflow states."""
        expected_statuses = ["triggered", "acknowledged", "resolved"]
        actual_statuses = [status.value for status in AlertStatus]
        
        self.assertEqual(set(actual_statuses), set(expected_statuses))
        
        # Test workflow order (business logic)
        self.assertEqual(AlertStatus.TRIGGERED.value, "triggered")
        self.assertEqual(AlertStatus.ACKNOWLEDGED.value, "acknowledged")
        self.assertEqual(AlertStatus.RESOLVED.value, "resolved")


class TestAlertCreateModel(unittest.TestCase):
    """Test AlertCreate model validates real alert creation scenarios."""
    
    def test_valid_alert_creation(self):
        """Test AlertCreate with valid data creates proper model."""
        valid_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "high_cpu_usage",
            "message": "CPU usage exceeded 90% for 5 minutes",
            "severity": "high"
        }
        
        alert_create = AlertCreate(**valid_data)
        
        self.assertEqual(alert_create.tenant_id, valid_data["tenant_id"])
        self.assertEqual(alert_create.rule_name, valid_data["rule_name"])
        self.assertEqual(alert_create.message, valid_data["message"])
        self.assertEqual(alert_create.severity, AlertSeverity.HIGH)
    
    def test_alert_create_with_default_severity(self):
        """Test AlertCreate defaults to medium severity when not specified."""
        alert_data = {
            "tenant_id": str(uuid4()),
            "rule_name": "disk_space_warning",
            "message": "Disk space is getting low"
        }
        
        alert_create = AlertCreate(**alert_data)
        
        self.assertEqual(alert_create.severity, AlertSeverity.MEDIUM)
    
    def test_tenant_id_validation_with_valid_uuid(self):
        """Test tenant_id validation accepts valid UUIDs."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
            str(uuid4())
        ]
        
        for valid_uuid in valid_uuids:
            with self.subTest(uuid=valid_uuid):
                alert_data = {
                    "tenant_id": valid_uuid,
                    "rule_name": "test_rule",
                    "message": "test message"
                }
                
                alert_create = AlertCreate(**alert_data)
                self.assertEqual(alert_create.tenant_id, valid_uuid)
    
    def test_tenant_id_validation_rejects_invalid_uuids(self):
        """Test tenant_id validation rejects invalid UUID formats."""
        invalid_uuids = [
            "not-a-uuid",
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
            "",
            "123",
            None
        ]
        
        for invalid_uuid in invalid_uuids:
            with self.subTest(uuid=invalid_uuid):
                alert_data = {
                    "tenant_id": invalid_uuid,
                    "rule_name": "test_rule", 
                    "message": "test message"
                }
                
                with self.assertRaises(ValidationError) as context:
                    AlertCreate(**alert_data)
                
                error = context.exception
                self.assertIn("tenant_id", str(error))
    
    def test_required_fields_validation(self):
        """Test AlertCreate requires all mandatory fields."""
        required_fields = ["tenant_id", "rule_name", "message"]
        
        for missing_field in required_fields:
            with self.subTest(missing_field=missing_field):
                alert_data = {
                    "tenant_id": str(uuid4()),
                    "rule_name": "test_rule",
                    "message": "test message"
                }
                
                # Remove the required field
                del alert_data[missing_field]
                
                with self.assertRaises(ValidationError):
                    AlertCreate(**alert_data)
    
    def test_severity_validation_with_valid_values(self):
        """Test severity field accepts valid severity enum values."""
        valid_severities = ["low", "medium", "high", "critical"]
        
        for severity in valid_severities:
            with self.subTest(severity=severity):
                alert_data = {
                    "tenant_id": str(uuid4()),
                    "rule_name": "test_rule",
                    "message": "test message",
                    "severity": severity
                }
                
                alert_create = AlertCreate(**alert_data)
                self.assertEqual(alert_create.severity.value, severity)
    
    def test_severity_validation_rejects_invalid_values(self):
        """Test severity field rejects invalid values."""
        invalid_severities = ["emergency", "urgent", "info", "", "unknown"]
        
        for severity in invalid_severities:
            with self.subTest(severity=severity):
                alert_data = {
                    "tenant_id": str(uuid4()),
                    "rule_name": "test_rule",
                    "message": "test message", 
                    "severity": severity
                }
                
                with self.assertRaises(ValidationError):
                    AlertCreate(**alert_data)


class TestAlertUpdateModel(unittest.TestCase):
    """Test AlertUpdate model validates status change scenarios."""
    
    def test_alert_update_with_note(self):
        """Test AlertUpdate with acknowledgment/resolution note."""
        update_data = {"note": "Investigating the issue with team"}
        
        alert_update = AlertUpdate(**update_data)
        
        self.assertEqual(alert_update.note, "Investigating the issue with team")
    
    def test_alert_update_without_note(self):
        """Test AlertUpdate without note (optional field)."""
        update_data = {}
        
        alert_update = AlertUpdate(**update_data)
        
        self.assertIsNone(alert_update.note)
    
    def test_alert_update_with_empty_note(self):
        """Test AlertUpdate accepts empty string as note."""
        update_data = {"note": ""}
        
        alert_update = AlertUpdate(**update_data)
        
        self.assertEqual(alert_update.note, "")


# Alert model is now handled by shared library database operations
# Tests moved to test_database.py for database-backed alert operations


class TestAlertStatsModel(unittest.TestCase):
    """Test AlertStats model provides accurate statistics for business decisions."""
    
    def test_alert_stats_with_all_counts(self):
        """Test AlertStats with realistic alert distribution."""
        stats_data = {
            "total": 47,
            "triggered": 12,
            "acknowledged": 8,
            "resolved": 27
        }
        
        stats = AlertStats(**stats_data)
        
        self.assertEqual(stats.total, 47)
        self.assertEqual(stats.triggered, 12)
        self.assertEqual(stats.acknowledged, 8)
        self.assertEqual(stats.resolved, 27)
        
        # Business logic validation: total should equal sum of statuses
        calculated_total = stats.triggered + stats.acknowledged + stats.resolved
        self.assertEqual(stats.total, calculated_total)
    
    def test_alert_stats_with_zero_counts(self):
        """Test AlertStats handles zero counts (new tenant scenario)."""
        stats_data = {
            "total": 0,
            "triggered": 0,
            "acknowledged": 0,
            "resolved": 0
        }
        
        stats = AlertStats(**stats_data)
        
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.triggered, 0)
        self.assertEqual(stats.acknowledged, 0)
        self.assertEqual(stats.resolved, 0)


# ErrorResponse is now provided by shared library
# Tests moved to shared library test suite


class TestHealthResponseModel(unittest.TestCase):
    """Test HealthResponse provides accurate service health status."""
    
    def test_healthy_service_response(self):
        """Test HealthResponse for healthy service state."""
        health_data = {
            "status": "healthy",
            "service": "as-alerts-service",
            "database_connected": True
        }
        
        health_response = HealthResponse(**health_data)
        
        self.assertEqual(health_response.status, "healthy")
        self.assertEqual(health_response.service, "as-alerts-service")
        self.assertTrue(health_response.database_connected)
    
    def test_unhealthy_service_response(self):
        """Test HealthResponse for unhealthy service state."""
        health_data = {
            "status": "unhealthy",
            "service": "as-alerts-service",
            "database_connected": False
        }
        
        health_response = HealthResponse(**health_data)
        
        self.assertEqual(health_response.status, "unhealthy")
        self.assertFalse(health_response.database_connected)
    
    def test_health_response_default_database_connected(self):
        """Test HealthResponse defaults database_connected to True."""
        health_data = {
            "status": "healthy",
            "service": "as-alerts-service"
        }
        
        health_response = HealthResponse(**health_data)
        
        self.assertTrue(health_response.database_connected)  # Default value


if __name__ == '__main__':
    unittest.main()