"""
Tests for the validation service - Phase 1 implementation.
"""

import pytest
from datetime import datetime, time
from dispatch_bot.services.validation_service import ValidationService
from dispatch_bot.models.basic_schemas import BasicDispatchRequest, UrgencyLevel


class TestValidationService:
    """Test validation service functionality"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service instance"""
        return ValidationService()
    
    @pytest.fixture
    def basic_request(self):
        """Create basic valid request for testing"""
        return BasicDispatchRequest(
            conversation_sid="test_sid_123456789",
            caller_phone="+12125551234",
            current_message="My faucet is leaking at 123 Main St",
            business_name="Joe's Plumbing",
            business_address="456 Business Ave, City, CA 90210"
        )


class TestBusinessHoursValidation:
    """Test business hours validation logic"""
    
    @pytest.fixture
    def validation_service(self):
        return ValidationService()
    
    def test_within_business_hours(self, validation_service):
        """Test request during business hours"""
        # 10 AM request, business hours 7 AM - 6 PM
        request_time = datetime(2024, 1, 15, 10, 0)  # 10:00 AM
        
        result = validation_service.validate_business_hours(
            request_time, "07:00", "18:00"
        )
        
        assert result["within_business_hours"] == True
        assert result["current_time"] == "10:00"
        assert result["business_start"] == "07:00"
        assert result["business_end"] == "18:00"
        assert "during business hours" in result["validation_message"]
    
    def test_outside_business_hours_early(self, validation_service):
        """Test request before business hours"""
        # 5 AM request, business hours 7 AM - 6 PM
        request_time = datetime(2024, 1, 15, 5, 30)  # 5:30 AM
        
        result = validation_service.validate_business_hours(
            request_time, "07:00", "18:00"
        )
        
        assert result["within_business_hours"] == False
        assert result["current_time"] == "05:30"
        assert "outside business hours" in result["validation_message"]
    
    def test_outside_business_hours_late(self, validation_service):
        """Test request after business hours"""
        # 8 PM request, business hours 7 AM - 6 PM
        request_time = datetime(2024, 1, 15, 20, 0)  # 8:00 PM
        
        result = validation_service.validate_business_hours(
            request_time, "07:00", "18:00"
        )
        
        assert result["within_business_hours"] == False
        assert result["current_time"] == "20:00"
        assert "outside business hours" in result["validation_message"]
    
    def test_boundary_times(self, validation_service):
        """Test boundary times - start and end of business hours"""
        # Exactly at start time
        start_time = datetime(2024, 1, 15, 7, 0)
        result = validation_service.validate_business_hours(
            start_time, "07:00", "18:00"
        )
        assert result["within_business_hours"] == True
        
        # Exactly at end time
        end_time = datetime(2024, 1, 15, 18, 0)  
        result = validation_service.validate_business_hours(
            end_time, "07:00", "18:00"
        )
        assert result["within_business_hours"] == True
        
        # One minute after end time
        after_end = datetime(2024, 1, 15, 18, 1)
        result = validation_service.validate_business_hours(
            after_end, "07:00", "18:00"
        )
        assert result["within_business_hours"] == False


class TestUrgencyDetection:
    """Test urgency level detection from messages"""
    
    @pytest.fixture
    def validation_service(self):
        return ValidationService()
    
    def test_emergency_keywords_detection(self, validation_service):
        """Test emergency keyword detection"""
        emergency_messages = [
            "EMERGENCY! Pipe burst and flooding my basement",
            "Water everywhere, burst pipe, need help now",
            "Sewage backup flooding house ASAP",
            "Emergency flooding situation"
        ]
        
        for message in emergency_messages:
            urgency, confidence = validation_service.determine_urgency_level(message)
            assert urgency == UrgencyLevel.EMERGENCY
            assert confidence > 0.3
    
    def test_urgent_keywords_detection(self, validation_service):
        """Test urgent keyword detection"""
        urgent_messages = [
            "My faucet is leaking badly",
            "Toilet broken and won't stop running",
            "No water coming from kitchen sink",
            "Drain is clogged and backing up"
        ]
        
        for message in urgent_messages:
            urgency, confidence = validation_service.determine_urgency_level(message)
            assert urgency == UrgencyLevel.URGENT
            assert confidence > 0.2
    
    def test_normal_messages(self, validation_service):
        """Test normal priority messages"""
        normal_messages = [
            "Need to schedule plumbing service",
            "Can someone look at my garbage disposal?",
            "Want to get my water heater checked",
            "Planning bathroom renovation"
        ]
        
        for message in normal_messages:
            urgency, confidence = validation_service.determine_urgency_level(message)
            assert urgency == UrgencyLevel.NORMAL
            assert confidence >= 0.5
    
    def test_empty_message_urgency(self, validation_service):
        """Test urgency detection with empty/invalid messages"""
        empty_messages = ["", None, "   "]
        
        for message in empty_messages:
            urgency, confidence = validation_service.determine_urgency_level(message)
            assert urgency == UrgencyLevel.NORMAL
            assert confidence == 0.0


class TestRequestValidation:
    """Test comprehensive request validation"""
    
    @pytest.fixture
    def validation_service(self):
        return ValidationService()
    
    @pytest.fixture
    def valid_request(self):
        return BasicDispatchRequest(
            conversation_sid="test_sid_123456789",
            caller_phone="+12125551234",
            current_message="My kitchen faucet is leaking at 123 Main Street, Los Angeles, CA 90210",
            business_name="Joe's Plumbing Service",
            business_address="456 Business Ave, Los Angeles, CA 90210",
            business_hours_start="07:00",
            business_hours_end="18:00",
            service_radius_miles=25
        )
    
    def test_valid_request_validation(self, validation_service, valid_request):
        """Test validation of completely valid request"""
        result = validation_service.validate_request_data(valid_request)
        
        assert result["valid"] == True
        assert len(result["errors"]) == 0
        
        # Check that address was extracted
        assert result["extracted_info"]["address"]["address"] is not None
        assert result["extracted_info"]["address"]["confidence"] > 0.5
        
        # Check business hours validation
        assert "hours_validation" in result
    
    def test_invalid_conversation_sid(self, validation_service, valid_request):
        """Test validation with invalid conversation SID"""
        valid_request.conversation_sid = "short"  # Too short
        
        result = validation_service.validate_request_data(valid_request)
        
        assert result["valid"] == False
        assert any("SID too short" in error for error in result["errors"])
    
    def test_empty_message_validation(self, validation_service, valid_request):
        """Test validation with empty message"""
        valid_request.current_message = ""
        
        result = validation_service.validate_request_data(valid_request)
        
        assert result["valid"] == False
        assert any("empty" in error.lower() for error in result["errors"])
    
    def test_invalid_job_estimates(self, validation_service, valid_request):
        """Test validation with invalid job estimates"""
        valid_request.basic_job_estimate_min = 300.0
        valid_request.basic_job_estimate_max = 200.0  # Max < Min
        
        result = validation_service.validate_request_data(valid_request)
        
        assert result["valid"] == False
        assert any("estimate" in error.lower() for error in result["errors"])
    
    def test_message_with_address_extraction(self, validation_service, valid_request):
        """Test that address is properly extracted from message"""
        valid_request.current_message = "Emergency leak at 789 Oak Avenue, Suite 101, Beverly Hills, CA 90210"
        
        result = validation_service.validate_request_data(valid_request)
        
        # Should extract address successfully
        address_info = result["extracted_info"]["address"]
        assert address_info["address"] is not None
        assert "789 Oak Avenue" in address_info["address"]
        assert address_info["confidence"] > 0.7  # High confidence due to complete address
    
    def test_message_without_clear_address(self, validation_service, valid_request):
        """Test message without clear address"""
        valid_request.current_message = "My sink is making weird noises"
        
        result = validation_service.validate_request_data(valid_request)
        
        # Should have low or no address confidence
        address_info = result["extracted_info"]["address"] 
        assert address_info["confidence"] < 0.3


class TestValidationServiceEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def validation_service(self):
        return ValidationService()
    
    def test_malformed_business_hours(self, validation_service):
        """Test handling of malformed business hours"""
        request_time = datetime(2024, 1, 15, 10, 0)
        
        # This should be caught by Pydantic validation before reaching the service
        # But test the service handles exceptions gracefully
        result = validation_service.validate_business_hours(
            request_time, "invalid", "also_invalid"
        )
        
        assert result["within_business_hours"] == False
        assert "error" in result
    
    def test_very_long_message(self, validation_service):
        """Test handling of very long messages"""
        long_message = "A" * 1500  # Longer than max allowed
        
        urgency, confidence = validation_service.determine_urgency_level(long_message)
        
        # Should still return valid response
        assert urgency in [UrgencyLevel.NORMAL, UrgencyLevel.URGENT, UrgencyLevel.EMERGENCY]
        assert 0.0 <= confidence <= 1.0
    
    def test_special_characters_in_message(self, validation_service):
        """Test handling of special characters and emojis"""
        special_message = "My faucet is leaking 💧🚿 at 123 Main St! Help ASAP!!! 😭"
        
        urgency, confidence = validation_service.determine_urgency_level(special_message)
        
        # Should detect urgency despite special characters
        assert urgency in [UrgencyLevel.URGENT, UrgencyLevel.EMERGENCY]
        assert confidence > 0.0