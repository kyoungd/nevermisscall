"""Simple validation tests to verify core functionality works."""

import pytest
from datetime import datetime
from uuid import uuid4

def test_phone_validation():
    """Test basic phone number validation."""
    from src.as_call_service.services.validation_service import ValidationService
    
    validation_service = ValidationService()
    
    # Valid phone numbers
    assert validation_service.validate_phone_number("+12125551234") is True
    assert validation_service.validate_phone_number("+447700900000") is True
    
    # Invalid phone numbers
    assert validation_service.validate_phone_number("12125551234") is False  # Missing +
    assert validation_service.validate_phone_number("") is False  # Empty

def test_message_validation():
    """Test basic message content validation."""
    from src.as_call_service.services.validation_service import ValidationService
    
    validation_service = ValidationService()
    
    # Valid messages
    assert validation_service.validate_message_content("Hello, I need help") is True
    
    # Invalid messages
    assert validation_service.validate_message_content("") is False  # Empty
    assert validation_service.validate_message_content("A" * 1601) is False  # Too long

def test_call_model_creation():
    """Test basic Call model creation."""
    from src.as_call_service.models import CallCreate
    
    # Should create without error
    call_data = CallCreate(
        call_sid="CA123",
        tenant_id=uuid4(),
        customer_phone="+12125551234",
        business_phone="+13105551234",
        direction="inbound",
        status="ringing",
        start_time=datetime.utcnow(),
    )
    
    assert call_data.call_sid == "CA123"
    assert call_data.direction == "inbound"

def test_conversation_model_creation():
    """Test basic Conversation model creation."""
    from src.as_call_service.models import ConversationCreate
    
    # Should create without error
    conversation_data = ConversationCreate(
        tenant_id=uuid4(),
        call_id=uuid4(),
        customer_phone="+12125551234",
        business_phone="+13105551234",
    )
    
    assert conversation_data.status == "active"

def test_business_hours_validation():
    """Test business hours validation logic."""
    from src.as_call_service.services.validation_service import ValidationService
    
    validation_service = ValidationService()
    
    business_hours = {
        'monday': {'start': '08:00', 'end': '17:00'},
        'sunday': None,  # Closed
    }
    
    # During business hours (Monday 10 AM)
    monday_10am = datetime(2024, 1, 1, 10, 0, 0)  # Monday
    result = validation_service.validate_business_hours(business_hours, monday_10am)
    assert result['withinHours'] is True
    
    # Closed day (Sunday)
    sunday_10am = datetime(2024, 1, 7, 10, 0, 0)  # Sunday  
    result = validation_service.validate_business_hours(business_hours, sunday_10am)
    assert result['withinHours'] is False

def test_address_extraction():
    """Test address extraction from messages."""
    from src.as_call_service.services.validation_service import ValidationService
    
    validation_service = ValidationService()
    
    # Should extract address
    message_with_address = "I live at 123 Main Street"
    result = validation_service.extract_address_from_message(message_with_address)
    assert result is not None
    assert "123 Main Street" in result
    
    # Should return None for no address
    message_no_address = "I need help with plumbing"
    result = validation_service.extract_address_from_message(message_no_address)
    assert result is None

@pytest.mark.asyncio
async def test_service_area_validation_disabled():
    """Test service area validation when disabled."""
    from src.as_call_service.services.validation_service import ValidationService
    from unittest.mock import patch
    
    validation_service = ValidationService()
    tenant_id = uuid4()
    address = "123 Main St"
    
    # Test that the method exists and can be called
    # For now, just test that the service can be instantiated
    result = await validation_service.validate_service_area(tenant_id, address)
    
    # Should return some result structure
    assert isinstance(result, dict)
    assert 'valid' in result