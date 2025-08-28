import pytest
from pydantic import ValidationError
from dispatch_bot.models.basic_schemas import BasicDispatchRequest, BasicDispatchResponse
from dispatch_bot.models.basic_schemas import TradeType, UrgencyLevel, ConversationStage


class TestPhoneNumberValidation:
    """Test phone number validation in BasicDispatchRequest"""
    
    def test_valid_phone_number_formats(self):
        """Test various valid phone number formats"""
        valid_phones = [
            "+12125551234",  # US format with country code
            "+442071234567", # UK format with country code
            "+33123456789",  # French format
            "+14155551234",  # Another US number
        ]
        
        for phone in valid_phones:
            request_data = {
                "conversation_sid": "test_sid_123",
                "caller_phone": phone,
                "current_message": "Test message",
                "business_name": "Test Plumbing",
                "business_address": "123 Main St, Test City, CA 90210"
            }
            request = BasicDispatchRequest(**request_data)
            assert request.caller_phone == phone
    
    def test_invalid_phone_number_formats(self):
        """Test invalid phone number formats should raise ValidationError"""
        invalid_phones = [
            "1234567890",     # Missing + prefix
            "+1234",          # Too short
            "+123456789012345678", # Too long
            "not-a-phone",    # Invalid format
            "",               # Empty string
            "+1-212-555-1234" # Hyphens not allowed
        ]
        
        for phone in invalid_phones:
            request_data = {
                "conversation_sid": "test_sid_123", 
                "caller_phone": phone,
                "current_message": "Test message",
                "business_name": "Test Plumbing",
                "business_address": "123 Main St, Test City, CA 90210"
            }
            with pytest.raises(ValidationError):
                BasicDispatchRequest(**request_data)


class TestBusinessHoursValidation:
    """Test business hours validation"""
    
    def test_valid_business_hours_formats(self):
        """Test valid business hours time formats"""
        valid_hours = [
            ("07:00", "18:00"),
            ("06:30", "17:30"), 
            ("08:15", "19:45"),
            ("00:00", "23:59")
        ]
        
        for start, end in valid_hours:
            request_data = {
                "conversation_sid": "test_sid_123",
                "caller_phone": "+12125551234",
                "current_message": "Test message",
                "business_name": "Test Plumbing",
                "business_address": "123 Main St, Test City, CA 90210",
                "business_hours_start": start,
                "business_hours_end": end
            }
            request = BasicDispatchRequest(**request_data)
            assert request.business_hours_start == start
            assert request.business_hours_end == end
    
    def test_invalid_business_hours_formats(self):
        """Test invalid business hours formats should raise ValidationError"""
        invalid_hours = [
            ("25:00", "18:00"),  # Invalid hour
            ("07:60", "18:00"),  # Invalid minute  
            ("7:00", "18:00"),   # Missing leading zero
            ("07", "18:00"),     # Missing minutes
            ("07:00:00", "18:00"), # Seconds not allowed
            ("invalid", "18:00")   # Non-numeric
        ]
        
        for start, end in invalid_hours:
            request_data = {
                "conversation_sid": "test_sid_123",
                "caller_phone": "+12125551234", 
                "current_message": "Test message",
                "business_name": "Test Plumbing",
                "business_address": "123 Main St, Test City, CA 90210",
                "business_hours_start": start,
                "business_hours_end": end
            }
            with pytest.raises(ValidationError):
                BasicDispatchRequest(**request_data)


class TestAddressParsing:
    """Test address extraction and validation"""
    
    def test_basic_address_extraction(self):
        """Test basic address parsing from customer messages"""
        test_cases = [
            ("My faucet is leaking at 123 Main St", "123 Main St"),
            ("Need help with toilet at 456 Oak Avenue", "456 Oak Avenue"), 
            ("Drain clog at 789 First Street, Apt 2B", "789 First Street, Apt 2B"),
            ("Emergency at 1001 Broadway Suite 100", "1001 Broadway Suite 100")
        ]
        
        # We'll test this with a utility function later
        from dispatch_bot.utils.address_parser import extract_address_from_message
        
        for message, expected_address in test_cases:
            extracted = extract_address_from_message(message)
            assert expected_address.lower() in extracted.lower()
    
    def test_address_confidence_scoring(self):
        """Test confidence scoring for address extraction"""
        from dispatch_bot.utils.address_parser import extract_address_with_confidence
        
        high_confidence_messages = [
            "Leaking pipe at 123 Main Street, Los Angeles, CA 90210",
            "Need plumber at 456 Oak Ave, Suite 200, Beverly Hills 90210"
        ]
        
        low_confidence_messages = [
            "My sink is broken",  # No address
            "Help me please"      # No address
        ]
        
        for message in high_confidence_messages:
            result = extract_address_with_confidence(message)
            assert result["confidence"] > 0.8
        
        for message in low_confidence_messages:
            result = extract_address_with_confidence(message)
            assert result["confidence"] < 0.3


class TestTwilioSidDeduplication:
    """Test Twilio SID deduplication logic"""
    
    def test_conversation_sid_required(self):
        """Test that conversation_sid is required"""
        request_data = {
            # Missing conversation_sid
            "caller_phone": "+12125551234",
            "current_message": "Test message", 
            "business_name": "Test Plumbing",
            "business_address": "123 Main St, Test City, CA 90210"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            BasicDispatchRequest(**request_data)
        
        assert "conversation_sid" in str(exc_info.value)
    
    def test_conversation_sid_minimum_length(self):
        """Test conversation_sid has minimum length requirement"""
        short_sids = ["", "123", "short"]
        
        for sid in short_sids:
            request_data = {
                "conversation_sid": sid,
                "caller_phone": "+12125551234",
                "current_message": "Test message",
                "business_name": "Test Plumbing", 
                "business_address": "123 Main St, Test City, CA 90210"
            }
            with pytest.raises(ValidationError):
                BasicDispatchRequest(**request_data)
    
    def test_valid_conversation_sid(self):
        """Test valid conversation SID formats"""
        valid_sids = [
            "SM1234567890abcdef1234567890abcdef12",  # Typical Twilio format
            "test_conversation_123456789",           # Test format
            "long_unique_identifier_12345"           # Custom format
        ]
        
        for sid in valid_sids:
            request_data = {
                "conversation_sid": sid,
                "caller_phone": "+12125551234",
                "current_message": "Test message",
                "business_name": "Test Plumbing",
                "business_address": "123 Main St, Test City, CA 90210"
            }
            request = BasicDispatchRequest(**request_data)
            assert request.conversation_sid == sid


class TestRequestModelValidation:
    """Test complete BasicDispatchRequest model validation"""
    
    def test_minimal_valid_request(self):
        """Test minimal valid request with all required fields"""
        request_data = {
            "conversation_sid": "test_sid_123456",
            "caller_phone": "+12125551234",
            "current_message": "My faucet is leaking",
            "business_name": "Joe's Plumbing",
            "business_address": "123 Business Ave, City, CA 90210"
        }
        
        request = BasicDispatchRequest(**request_data)
        
        # Test defaults are applied
        assert request.trade_type == TradeType.PLUMBING
        assert request.business_hours_start == "07:00"
        assert request.business_hours_end == "18:00"
        assert request.service_radius_miles == 25
        assert request.basic_job_estimate_min == 100.0
        assert request.basic_job_estimate_max == 300.0
        assert request.conversation_history == []
    
    def test_business_name_validation(self):
        """Test business name length validation"""
        # Too short
        with pytest.raises(ValidationError):
            BasicDispatchRequest(
                conversation_sid="test_sid_123456",
                caller_phone="+12125551234", 
                current_message="Test message",
                business_name="AB",  # Too short
                business_address="123 Business Ave, City, CA 90210"
            )
        
        # Too long  
        long_name = "A" * 101  # 101 characters
        with pytest.raises(ValidationError):
            BasicDispatchRequest(
                conversation_sid="test_sid_123456",
                caller_phone="+12125551234",
                current_message="Test message", 
                business_name=long_name,
                business_address="123 Business Ave, City, CA 90210"
            )
    
    def test_service_radius_validation(self):
        """Test service radius mile validation"""
        # Too small
        with pytest.raises(ValidationError):
            BasicDispatchRequest(
                conversation_sid="test_sid_123456",
                caller_phone="+12125551234",
                current_message="Test message",
                business_name="Test Plumbing",
                business_address="123 Business Ave, City, CA 90210",
                service_radius_miles=0  # Too small
            )
        
        # Too large
        with pytest.raises(ValidationError):
            BasicDispatchRequest(
                conversation_sid="test_sid_123456", 
                caller_phone="+12125551234",
                current_message="Test message",
                business_name="Test Plumbing",
                business_address="123 Business Ave, City, CA 90210",
                service_radius_miles=101  # Too large
            )


class TestResponseModelValidation:
    """Test BasicDispatchResponse model validation"""
    
    def test_minimal_valid_response(self):
        """Test minimal valid response"""
        response = BasicDispatchResponse(
            next_message="Thank you for contacting Test Plumbing.",
            conversation_stage=ConversationStage.INITIAL
        )
        
        # Test defaults
        assert response.urgency_level == UrgencyLevel.NORMAL
        assert response.address_valid == False
        assert response.in_service_area == False 
        assert response.within_business_hours == True
        assert response.appointment_offered == False
        assert response.requires_followup == False
        assert response.conversation_timeout_minutes == 5
    
    def test_complete_response_with_appointment(self):
        """Test complete response with appointment details"""
        from datetime import datetime
        
        start_time = datetime(2024, 1, 15, 10, 0)
        end_time = datetime(2024, 1, 15, 12, 0)
        
        response = BasicDispatchResponse(
            customer_address="123 Main St, City, CA 90210",
            job_type="faucet_repair",
            urgency_level=UrgencyLevel.NORMAL,
            address_valid=True,
            in_service_area=True,
            within_business_hours=True,
            next_message="I can fix your faucet tomorrow 10-12 PM for $150-$200. YES to confirm?",
            conversation_stage=ConversationStage.CONFIRMING,
            appointment_offered=True,
            proposed_start_time=start_time,
            proposed_end_time=end_time,
            estimated_price_min=150.0,
            estimated_price_max=200.0
        )
        
        assert response.customer_address == "123 Main St, City, CA 90210"
        assert response.job_type == "faucet_repair"
        assert response.appointment_offered == True
        assert response.proposed_start_time == start_time
        assert response.proposed_end_time == end_time
        assert response.estimated_price_min == 150.0
        assert response.estimated_price_max == 200.0