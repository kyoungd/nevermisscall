"""
Unit tests for Pydantic models.

Tests model validation, serialization, and business logic following
the unittest patterns and real business rule validation.
"""

import unittest
from datetime import datetime
from decimal import Decimal

from shared.models.api import (
    ApiResponse,
    success_response,
    error_response,
    HealthStatus,
    PaginatedResponse
)
from shared.models.auth import (
    User,
    UserProfile,
    Tenant,
    JwtPayload,
    BusinessSettings
)
from shared.models.core import (
    Call,
    Conversation,
    Message,
    Lead,
    PhoneNumber,
    Appointment
)
from shared.models.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError
)


class TestApiResponseModels(unittest.TestCase):
    """Test API response models validate real API communication patterns."""
    
    def test_success_response_creates_valid_structure(self):
        """Test success_response creates valid response structure for API clients."""
        data = {"user_id": "123", "name": "Test User"}
        response = success_response(data, "User retrieved successfully")
        
        self.assertIsInstance(response, ApiResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.data, data)
        self.assertEqual(response.message, "User retrieved successfully")
        self.assertIsNone(response.error)
        self.assertIsNotNone(response.timestamp)
    
    def test_error_response_creates_valid_error_structure(self):
        """Test error_response creates valid error structure for API error handling."""
        response = error_response("User not found", details={
            'code': 'NOT_FOUND',
            'field': 'user_id'
        })
        
        self.assertIsInstance(response, ApiResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.error, "User not found")
        self.assertIsNotNone(response.data)  # Should contain error details
        self.assertIsNotNone(response.timestamp)
    
    def test_health_status_model_validation(self):
        """Test HealthStatus model validates real service monitoring data."""
        # Valid health status
        health = HealthStatus(
            status='healthy',
            service='auth-service',
            version='1.0.0',
            uptime=3600,
            database_status='healthy'
        )
        
        self.assertEqual(health.status, 'healthy')
        self.assertEqual(health.service, 'auth-service')
        self.assertEqual(health.database_status, 'healthy')
        self.assertIsNotNone(health.timestamp)
    
    def test_health_status_rejects_invalid_status(self):
        """Test HealthStatus rejects invalid status values (business rule validation)."""
        with self.assertRaises(ValueError):
            HealthStatus(
                status='invalid_status',  # Should only allow healthy/unhealthy/degraded
                service='test-service'
            )
    
    def test_paginated_response_calculates_navigation_flags(self):
        """Test PaginatedResponse calculates navigation flags for UI pagination."""
        # First page with more data
        response = PaginatedResponse(
            data=[1, 2, 3],
            total=25,
            page=1,
            limit=10
        )
        
        self.assertFalse(response.has_previous)
        self.assertTrue(response.has_next)
        
        # Middle page
        response = PaginatedResponse(
            data=[11, 12, 13],
            total=25,
            page=2,
            limit=10
        )
        
        self.assertTrue(response.has_previous)
        self.assertTrue(response.has_next)
        
        # Last page
        response = PaginatedResponse(
            data=[21, 22, 23, 24, 25],
            total=25,
            page=3,
            limit=10
        )
        
        self.assertTrue(response.has_previous)
        self.assertFalse(response.has_next)


class TestAuthModels(unittest.TestCase):
    """Test authentication models enforce real business authentication rules."""
    
    def test_user_model_creates_valid_user_data(self):
        """Test User model creates valid user data for authentication system."""
        user_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "user@example.com"
        }
        
        user = User(**user_data)
        
        self.assertEqual(user.id, user_data["id"])
        self.assertEqual(user.email, user_data["email"])
        self.assertIsNone(user.password_hash)  # Should not be included in API responses
        self.assertIsNotNone(user.created_at)
    
    def test_user_model_validates_email_format(self):
        """Test User model validates email format (real business rule)."""
        with self.assertRaises(ValueError):
            User(
                id="123e4567-e89b-12d3-a456-426614174000",
                email="invalid-email"  # Should require valid email format
            )
    
    def test_tenant_model_validates_business_data(self):
        """Test Tenant model validates business data for multi-tenant system."""
        tenant_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "business_name": "Test Plumbing Co",
            "business_address": "123 Main St, City, ST 12345",
            "trade_type": "plumbing",
            "service_area_radius": 25
        }
        
        tenant = Tenant(**tenant_data)
        
        self.assertEqual(tenant.business_name, "Test Plumbing Co")
        self.assertEqual(tenant.trade_type, "plumbing")
        self.assertEqual(tenant.service_area_radius, 25)
        self.assertFalse(tenant.onboarding_completed)  # Default value
        self.assertEqual(tenant.onboarding_step, 1)  # Default value
    
    def test_business_settings_model_validates_hours(self):
        """Test BusinessSettings model validates business hours structure."""
        settings_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "timezone": "America/New_York"
        }
        
        settings = BusinessSettings(**settings_data)
        
        # Should have default business hours
        self.assertIn("monday", settings.business_hours)
        self.assertIn("open", settings.business_hours["monday"])
        self.assertIn("close", settings.business_hours["monday"])
        self.assertIn("enabled", settings.business_hours["monday"])
        
        # Should have default auto-response settings
        self.assertTrue(settings.auto_response_enabled)
        self.assertIsNotNone(settings.auto_response_message)
    
    def test_jwt_payload_validates_authentication_claims(self):
        """Test JwtPayload validates authentication claims for JWT tokens."""
        payload_data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "role": "admin",
            "email": "admin@example.com",
            "exp": 1640995200  # Unix timestamp
        }
        
        payload = JwtPayload(**payload_data)
        
        self.assertEqual(payload.user_id, payload_data["user_id"])
        self.assertEqual(payload.tenant_id, payload_data["tenant_id"])
        self.assertEqual(payload.role, "admin")
        self.assertEqual(payload.exp, 1640995200)


class TestCoreBusinessModels(unittest.TestCase):
    """Test core business models enforce real business logic and data integrity."""
    
    def test_call_model_validates_call_tracking_data(self):
        """Test Call model validates real call tracking business data."""
        call_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # Twilio format
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "customer_phone": "+15551234567",
            "business_phone": "+15559876543",
            "direction": "inbound",
            "status": "completed",
            "start_time": "2024-01-01T12:00:00Z",
            "duration": 180  # 3 minutes
        }
        
        call = Call(**call_data)
        
        self.assertEqual(call.call_sid, "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.assertEqual(call.customer_phone, "+15551234567")
        self.assertEqual(call.duration, 180)
        self.assertEqual(call.direction, "inbound")
        self.assertFalse(call.processed)  # Default value
        self.assertFalse(call.sms_triggered)  # Default value
    
    def test_conversation_model_tracks_ai_human_interaction(self):
        """Test Conversation model tracks AI-to-human handoff business logic."""
        conversation_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "call_id": "789e0123-e89b-12d3-a456-426614174000",
            "customer_phone": "+15551234567",
            "business_phone": "+15559876543",
            "ai_active": True,
            "message_count": 5,
            "ai_message_count": 3,
            "human_message_count": 2
        }
        
        conversation = Conversation(**conversation_data)
        
        self.assertTrue(conversation.ai_active)
        self.assertFalse(conversation.human_active)  # Default
        self.assertEqual(conversation.message_count, 5)
        self.assertEqual(conversation.ai_message_count, 3)
        self.assertEqual(conversation.human_message_count, 2)
        self.assertFalse(conversation.appointment_scheduled)  # Default
    
    def test_lead_model_validates_business_lead_data(self):
        """Test Lead model validates real business lead tracking data."""
        lead_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "conversation_id": "789e0123-e89b-12d3-a456-426614174000",
            "call_id": "abc1234e-e89b-12d3-a456-426614174000",
            "customer_phone": "+15551234567",
            "customer_name": "John Smith",
            "problem_description": "Kitchen sink is clogged and overflowing",
            "job_type": "emergency_plumbing",
            "urgency_level": "high",
            "estimated_value": Decimal("250.00")
        }
        
        lead = Lead(**lead_data)
        
        self.assertEqual(lead.customer_name, "John Smith")
        self.assertEqual(lead.problem_description, "Kitchen sink is clogged and overflowing")
        self.assertEqual(lead.urgency_level, "high")
        self.assertEqual(lead.estimated_value, Decimal("250.00"))
        self.assertEqual(lead.status, "new")  # Default value
    
    def test_phone_number_model_validates_twilio_integration(self):
        """Test PhoneNumber model validates Twilio phone number business data."""
        phone_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "phone_number": "+15551234567",
            "phone_number_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "area_code": "555",
            "region": "California",
            "voice_webhook_url": "https://api.nevermisscall.com/twilio/voice",
            "sms_webhook_url": "https://api.nevermisscall.com/twilio/sms",
            "monthly_price_cents": 100,
            "status": "active"
        }
        
        phone = PhoneNumber(**phone_data)
        
        self.assertEqual(phone.phone_number, "+15551234567")
        self.assertEqual(phone.area_code, "555")
        self.assertEqual(phone.monthly_price_cents, 100)
        self.assertEqual(phone.currency, "USD")  # Default value
        self.assertEqual(phone.capabilities, ['voice', 'sms'])  # Default value
    
    def test_appointment_model_validates_scheduling_business_logic(self):
        """Test Appointment model validates real appointment scheduling business logic."""
        appointment_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "tenant_id": "456e7890-e89b-12d3-a456-426614174000",
            "lead_id": "789e0123-e89b-12d3-a456-426614174000",
            "conversation_id": "abc1234e-e89b-12d3-a456-426614174000",
            "customer_phone": "+15551234567",
            "customer_name": "John Smith",
            "customer_address": "123 Main St, City, ST 12345",
            "scheduled_date": "2024-01-15",
            "scheduled_time": "14:00",
            "duration_minutes": 120,
            "service_type": "emergency_plumbing",
            "estimated_value": Decimal("350.00")
        }
        
        appointment = Appointment(**appointment_data)
        
        self.assertEqual(appointment.customer_name, "John Smith")
        self.assertEqual(appointment.scheduled_date, "2024-01-15")
        self.assertEqual(appointment.scheduled_time, "14:00")
        self.assertEqual(appointment.duration_minutes, 120)
        self.assertEqual(appointment.status, "scheduled")  # Default value
        self.assertFalse(appointment.confirmation_sent)  # Default value


class TestExceptionModels(unittest.TestCase):
    """Test exception models provide actionable error information."""
    
    def test_validation_error_provides_field_context(self):
        """Test ValidationError provides field context for API error responses."""
        error = ValidationError("Email format is invalid", field="customer_email")
        
        self.assertEqual(error.field, "customer_email")
        self.assertEqual(error.code, "VALIDATION_ERROR")
        self.assertEqual(str(error), "Email format is invalid")
    
    def test_not_found_error_provides_resource_context(self):
        """Test NotFoundError provides resource context for debugging."""
        error = NotFoundError(resource="user", identifier="123")
        
        self.assertEqual(error.resource, "user")
        self.assertEqual(error.identifier, "123")
        self.assertEqual(error.code, "NOT_FOUND")
        self.assertIn("User not found: 123", str(error))
    
    def test_unauthorized_error_provides_auth_context(self):
        """Test UnauthorizedError provides authentication context."""
        error = UnauthorizedError(reason="Invalid JWT token")
        
        self.assertEqual(error.reason, "Invalid JWT token")
        self.assertEqual(error.code, "UNAUTHORIZED")
        self.assertIn("Invalid JWT token", str(error))


if __name__ == '__main__':
    unittest.main()