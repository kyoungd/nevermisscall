"""Test just the models without service dependencies."""

import pytest
from datetime import datetime
from uuid import uuid4


def test_call_model_creation():
    """Test basic Call model creation."""
    from src.as_call_service.models.call import CallCreate
    
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
    assert call_data.customer_phone == "+12125551234"


def test_conversation_model_creation():
    """Test basic Conversation model creation."""
    from src.as_call_service.models.conversation import ConversationCreate
    
    # Should create without error
    conversation_data = ConversationCreate(
        tenant_id=uuid4(),
        call_id=uuid4(),
        customer_phone="+12125551234",
        business_phone="+13105551234",
    )
    
    assert conversation_data.status == "active"
    assert conversation_data.customer_phone == "+12125551234"


def test_message_model_creation():
    """Test basic Message model creation."""
    from src.as_call_service.models.message import MessageCreate
    
    # Should create without error
    message_data = MessageCreate(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        direction="inbound",
        sender="customer",
        body="Hello, I need help with my sink",
    )
    
    assert message_data.direction == "inbound"
    assert message_data.sender == "customer"
    assert message_data.body == "Hello, I need help with my sink"


def test_lead_model_creation():
    """Test basic Lead model creation."""
    from src.as_call_service.models.lead import LeadCreate
    
    # Should create without error
    lead_data = LeadCreate(
        tenant_id=uuid4(),
        conversation_id=uuid4(),
        call_id=uuid4(),
        customer_phone="+12125551234",
        problem_description="Leaky faucet in kitchen",
    )
    
    assert lead_data.urgency_level == "normal"  # Default value
    assert lead_data.status == "new"  # Default value
    assert lead_data.problem_description == "Leaky faucet in kitchen"


def test_phone_number_validation_in_model():
    """Test phone number validation in models."""
    from src.as_call_service.models.call import CallCreate
    from pydantic import ValidationError
    
    # Valid phone number should work
    call_data = CallCreate(
        call_sid="CA123",
        tenant_id=uuid4(),
        customer_phone="+12125551234",
        business_phone="+13105551234",
        direction="inbound",
        status="ringing",
        start_time=datetime.utcnow(),
    )
    assert call_data.customer_phone == "+12125551234"

    # Invalid phone number should fail
    with pytest.raises(ValidationError):
        CallCreate(
            call_sid="CA123",
            tenant_id=uuid4(),
            customer_phone="invalid-phone",  # Invalid format
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )


def test_message_length_validation():
    """Test message length validation in models."""
    from src.as_call_service.models.message import MessageCreate
    from pydantic import ValidationError
    
    # Valid message should work
    message_data = MessageCreate(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        direction="inbound",
        sender="customer",
        body="Hello, I need help",
    )
    assert message_data.body == "Hello, I need help"

    # Too long message should fail
    with pytest.raises(ValidationError):
        MessageCreate(
            conversation_id=uuid4(),
            tenant_id=uuid4(),
            direction="inbound",
            sender="customer",
            body="A" * 1601,  # Too long
        )


def test_call_webhook_model():
    """Test CallWebhook model with alias fields."""
    from src.as_call_service.models.call import CallWebhook
    
    webhook_data = CallWebhook(
        callSid="CA123456789",
        from_="+12125551234",
        to="+13105551234",
        call_status="ringing",
        direction="inbound",
    )
    
    assert webhook_data.callSid == "CA123456789"
    assert webhook_data.from_ == "+12125551234"
    assert webhook_data.call_status == "ringing"


def test_lead_status_validation():
    """Test lead status validation in models."""
    from src.as_call_service.models.lead import LeadStatusUpdate
    from pydantic import ValidationError
    
    # Valid status should work
    status_update = LeadStatusUpdate(
        status="qualified",
        notes="Customer confirmed interest",
    )
    assert status_update.status == "qualified"

    # Invalid status should fail validation
    with pytest.raises(ValidationError):
        LeadStatusUpdate(
            status="invalid_status",  # Not in allowed enum
        )


def test_ai_analysis_model():
    """Test AI analysis model."""
    from src.as_call_service.models.lead import AIAnalysis
    
    ai_analysis = AIAnalysis(
        confidence=0.85,
        job_classification="faucet_repair",
        urgency_score=0.3,
        service_area_valid=True,
        address_validated=True,
    )
    
    assert ai_analysis.confidence == 0.85
    assert ai_analysis.job_classification == "faucet_repair"
    assert ai_analysis.service_area_valid is True