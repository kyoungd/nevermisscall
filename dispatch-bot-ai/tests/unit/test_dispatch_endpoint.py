"""
Unit tests for /dispatch/process endpoint.
Following TDD approach - these tests will fail initially.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from dispatch_bot.main import app
from dispatch_bot.models.schemas import (
    ProcessConversationRequest,
    TradeType,
    BusinessHours,
    PhoneHours,
    BusinessAddress,
    JobEstimate,
    BusinessSettings
)


class TestDispatchProcessEndpoint:
    """Test cases for the /dispatch/process endpoint."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_request_data(self):
        """Sample request data for testing."""
        return {
            "caller_phone": "+12125551234",
            "called_number": "+15555551111",
            "conversation_history": [],
            "current_message": "Water heater burst in basement! 789 Sunset Blvd, 90210",
            "business_name": "Prime Plumbing",
            "trade_type": "plumbing",
            "business_hours": {
                "monday": {"start": "07:00", "end": "18:00"},
                "tuesday": {"start": "07:00", "end": "18:00"},
                "wednesday": {"start": "07:00", "end": "18:00"},
                "thursday": {"start": "07:00", "end": "18:00"},
                "friday": {"start": "07:00", "end": "18:00"},
                "saturday": {"start": "08:00", "end": "17:00"},
                "sunday": None
            },
            "phone_hours": {
                "always_available": True
            },
            "business_address": {
                "street_address": "123 Main St",
                "city": "Los Angeles",
                "state": "CA",
                "postal_code": "90210",
                "latitude": 34.0522,
                "longitude": -118.2437
            },
            "job_estimates": [
                {
                    "job_type": "water_heater_repair",
                    "description": "Water heater repair/replacement",
                    "estimated_hours": 2.0,
                    "estimated_cost_min": 150.0,
                    "estimated_cost_max": 400.0,
                    "requires_parts": True,
                    "urgency_multiplier": 1.5,
                    "buffer_minutes": 30
                }
            ],
            "business_settings": {
                "accept_emergencies": True,
                "out_of_office": False,
                "max_jobs_per_day": 8,
                "min_buffer_between_jobs": 30,
                "service_radius_miles": 25,
                "max_travel_time_minutes": 60,
                "max_travel_distance_miles": 25,
                "emergency_multiplier": 1.5,
                "overtime_allowed": False,
                "emergency_service_enabled": True,
                "emergency_service_radius_miles": 20,
                "max_emergency_jobs_per_night": 3,
                "work_hours_emergency_multiplier": 1.75,
                "evening_emergency_multiplier": 2.25,
                "night_emergency_multiplier": 2.75,
                "early_6am_multiplier": 1.5,
                "early_630am_multiplier": 1.25,
                "emergency_cutoff_time": None
            },
            "existing_calendar": [],
            "customer_history": None,
            "weather_conditions": "clear"
        }
    
    def test_dispatch_process_endpoint_exists(self, client):
        """Test that the /dispatch/process endpoint exists and accepts POST."""
        response = client.post("/dispatch/process", json={})
        # Should not be 404 (endpoint exists), but may be 400 or 422 (validation error)
        assert response.status_code != 404
    
    def test_dispatch_process_requires_post_method(self, client):
        """Test that /dispatch/process only accepts POST method."""
        # GET should not be allowed
        response = client.get("/dispatch/process")
        assert response.status_code == 405  # Method Not Allowed
        
        # PUT should not be allowed
        response = client.put("/dispatch/process", json={})
        assert response.status_code == 405  # Method Not Allowed
    
    def test_dispatch_process_requires_json_content_type(self, client):
        """Test that /dispatch/process requires JSON content type."""
        response = client.post(
            "/dispatch/process",
            data="not json",
            headers={"Content-Type": "text/plain"}
        )
        # Should return 422 for invalid content type or request format
        assert response.status_code in [400, 422]
    
    def test_dispatch_process_validates_required_fields(self, client):
        """Test that missing required fields cause validation errors."""
        # Empty request should fail validation
        response = client.post("/dispatch/process", json={})
        assert response.status_code == 422
        
        # Response should include validation error details
        error_response = response.json()
        assert "error" in error_response  # Our custom error format uses "error"
        assert error_response["error"]["code"] == "VALIDATION_ERROR"
    
    def test_dispatch_process_validates_phone_number_format(self, client, sample_request_data):
        """Test phone number format validation."""
        # Invalid phone number format
        sample_request_data["caller_phone"] = "invalid-phone"
        
        response = client.post("/dispatch/process", json=sample_request_data)
        # Should fail validation due to invalid phone format
        assert response.status_code == 422
    
    def test_dispatch_process_validates_trade_type(self, client, sample_request_data):
        """Test that invalid trade types are rejected."""
        # Invalid trade type
        sample_request_data["trade_type"] = "invalid_trade"
        
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 422
    
    def test_dispatch_process_valid_request_returns_200(self, client, sample_request_data):
        """Test that a valid request returns HTTP 200."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
    
    def test_dispatch_process_response_structure(self, client, sample_request_data):
        """Test that the response has the correct structure."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        
        # Verify top-level response structure
        required_fields = [
            "extracted_info",
            "validation",
            "next_action",
            "conversation_stage",
            "needs_geocoding",
            "confidence_scores",
            "nlp_analysis"
        ]
        
        for field in required_fields:
            assert field in json_response, f"Missing required field: {field}"
    
    def test_dispatch_process_extracted_info_structure(self, client, sample_request_data):
        """Test that extracted_info has the correct structure."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        extracted_info = json_response["extracted_info"]
        
        # Verify extracted_info structure
        expected_fields = [
            "job_type",
            "job_confidence",
            "urgency_level",
            "urgency_confidence",
            "customer_address",
            "address_verified",
            "preferred_date",
            "customer_confirmed"
        ]
        
        for field in expected_fields:
            assert field in extracted_info, f"Missing field in extracted_info: {field}"
    
    def test_dispatch_process_validation_structure(self, client, sample_request_data):
        """Test that validation section has the correct structure."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        validation = json_response["validation"]
        
        # Verify validation structure
        expected_fields = [
            "service_area_valid",
            "trade_supported",
            "job_type_supported",
            "within_business_hours",
            "capacity_available",
            "address_reachable",
            "validation_errors"
        ]
        
        for field in expected_fields:
            assert field in validation, f"Missing field in validation: {field}"
            
        # validation_errors should be a list
        assert isinstance(validation["validation_errors"], list)
    
    def test_dispatch_process_next_action_structure(self, client, sample_request_data):
        """Test that next_action has the correct structure."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        next_action = json_response["next_action"]
        
        # Verify next_action structure
        expected_fields = [
            "action_type",
            "message_to_customer",
            "follow_up_needed",
            "follow_up_delay_minutes"
        ]
        
        for field in expected_fields:
            assert field in next_action, f"Missing field in next_action: {field}"
        
        # Verify action_type is valid enum value
        valid_action_types = [
            "continue_conversation",
            "request_confirmation",
            "request_emergency_choice",
            "book_appointment",
            "schedule_callback",
            "escalate_to_owner",
            "end_conversation"
        ]
        assert next_action["action_type"] in valid_action_types
    
    def test_dispatch_process_confidence_scores_structure(self, client, sample_request_data):
        """Test that confidence_scores has the correct structure."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        confidence_scores = json_response["confidence_scores"]
        
        # Verify confidence_scores structure
        expected_fields = [
            "job_type_confidence",
            "urgency_confidence",
            "address_confidence",
            "overall_confidence"
        ]
        
        for field in expected_fields:
            assert field in confidence_scores, f"Missing field in confidence_scores: {field}"
            # Confidence scores should be between 0 and 1
            score = confidence_scores[field]
            assert 0.0 <= score <= 1.0, f"Confidence score {field} out of range: {score}"
    
    def test_dispatch_process_conversation_stage_valid(self, client, sample_request_data):
        """Test that conversation_stage is a valid enum value."""
        response = client.post("/dispatch/process", json=sample_request_data)
        assert response.status_code == 200
        
        json_response = response.json()
        stage = json_response["conversation_stage"]
        
        valid_stages = [
            "initial",
            "collecting_info",
            "confirming",
            "booking",
            "complete",
            "escalated",
            "rejected"
        ]
        assert stage in valid_stages, f"Invalid conversation stage: {stage}"