"""Unit tests for phone number models."""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from pydantic import ValidationError

from pns_provisioning_service.models.phone_number import (
    PhoneNumber, PhoneNumberBase, MessagingService,
    ProvisionPhoneNumberRequest, ProvisionPhoneNumberResponse,
    ReleasePhoneNumberRequest, ReleasePhoneNumberResponse,
    PhoneNumberConfiguration, PhoneNumberStatusUpdate
)
from pns_provisioning_service.models.api import (
    ApiResponse, ErrorCodes, success_response, error_response
)


class TestPhoneNumberModels:
    """Test phone number data models."""
    
    def test_phone_number_base_creation(self):
        """Test PhoneNumberBase creation with required fields."""
        tenant_id = uuid4()
        phone_base = PhoneNumberBase(
            tenant_id=tenant_id,
            phone_number="+15551234567",
            friendly_name="Test Business"
        )
        
        assert phone_base.tenant_id == tenant_id
        assert phone_base.phone_number == "+15551234567"
        assert phone_base.friendly_name == "Test Business"
        assert phone_base.status == "provisioning"  # default value
        
    def test_phone_number_creation(self):
        """Test full PhoneNumber model creation."""
        phone_id = uuid4()
        tenant_id = uuid4()
        now = datetime.now()
        
        phone = PhoneNumber(
            id=phone_id,
            tenant_id=tenant_id,
            phone_number="+15551234567",
            phone_number_sid="PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            messaging_service_sid="MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            friendly_name="Test Business",
            status="active",
            capabilities=["voice", "sms"],
            voice_webhook_url="https://example.com/voice",
            sms_webhook_url="https://example.com/sms",
            date_provisioned=now,
            created_at=now,
            updated_at=now
        )
        
        assert phone.id == phone_id
        assert phone.phone_number_sid == "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert phone.status == "active"
        assert "voice" in phone.capabilities
        assert "sms" in phone.capabilities
        
    def test_phone_number_invalid_status(self):
        """Test PhoneNumber with invalid status."""
        with pytest.raises(ValidationError):
            PhoneNumber(
                id=uuid4(),
                tenant_id=uuid4(),
                phone_number="+15551234567",
                phone_number_sid="PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                friendly_name="Test",
                status="invalid_status"  # Not in allowed values
            )
    
    def test_messaging_service_creation(self):
        """Test MessagingService model creation."""
        phone_id = uuid4()
        now = datetime.now()
        
        messaging_service = MessagingService(
            id=uuid4(),
            phone_number_id=phone_id,
            messaging_service_sid="MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            friendly_name="Test Messaging Service",
            inbound_request_url="https://example.com/inbound",
            status_callback_url="https://example.com/status",
            created_at=now
        )
        
        assert messaging_service.phone_number_id == phone_id
        assert messaging_service.messaging_service_sid == "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert messaging_service.friendly_name == "Test Messaging Service"


class TestRequestResponseModels:
    """Test API request and response models."""
    
    def test_provision_request_creation(self):
        """Test ProvisionPhoneNumberRequest creation."""
        tenant_id = uuid4()
        request = ProvisionPhoneNumberRequest(
            tenant_id=tenant_id,
            area_code="555",
            friendly_name="Test Business"
        )
        
        assert request.tenant_id == tenant_id
        assert request.area_code == "555"
        assert request.friendly_name == "Test Business"
        assert request.voice_webhook_url is None  # Optional field
        
    def test_provision_request_with_webhooks(self):
        """Test ProvisionPhoneNumberRequest with webhook URLs."""
        request = ProvisionPhoneNumberRequest(
            tenant_id=uuid4(),
            area_code="555",
            friendly_name="Test Business",
            voice_webhook_url="https://example.com/voice",
            sms_webhook_url="https://example.com/sms"
        )
        
        assert request.voice_webhook_url == "https://example.com/voice"
        assert request.sms_webhook_url == "https://example.com/sms"
        
    def test_release_request_creation(self):
        """Test ReleasePhoneNumberRequest creation."""
        request = ReleasePhoneNumberRequest(
            confirm_release=True,
            reason="No longer needed"
        )
        
        assert request.confirm_release is True
        assert request.reason == "No longer needed"
        
    def test_phone_number_configuration(self):
        """Test PhoneNumberConfiguration model."""
        config = PhoneNumberConfiguration(
            friendly_name="Updated Name",
            webhooks={
                "voiceUrl": "https://example.com/voice",
                "smsUrl": "https://example.com/sms",
                "statusCallbackUrl": "https://example.com/status"
            }
        )
        
        assert config.friendly_name == "Updated Name"
        assert config.webhooks["voiceUrl"] == "https://example.com/voice"
        assert config.webhooks["smsUrl"] == "https://example.com/sms"
        
    def test_status_update_model(self):
        """Test PhoneNumberStatusUpdate model."""
        update = PhoneNumberStatusUpdate(
            status="suspended",
            reason="Payment failed"
        )
        
        assert update.status == "suspended"
        assert update.reason == "Payment failed"


class TestApiResponseModels:
    """Test API response models."""
    
    def test_success_response(self):
        """Test success response creation."""
        data = {"phoneNumber": {"id": str(uuid4())}}
        response = success_response(data, "Phone number retrieved successfully")
        
        assert response["success"] is True
        assert response["message"] == "Phone number retrieved successfully"
        assert response["data"] == data
        assert "timestamp" in response
        
    def test_error_response(self):
        """Test error response creation."""
        response = error_response(
            ErrorCodes.PHONE_NUMBER_NOT_FOUND,
            "Phone number not found",
            {"phoneId": str(uuid4())}
        )
        
        assert response["success"] is False
        assert response["error"]["code"] == ErrorCodes.PHONE_NUMBER_NOT_FOUND
        assert response["error"]["message"] == "Phone number not found"
        assert "phoneId" in response["data"]
        
    def test_api_response_model(self):
        """Test ApiResponse model validation."""
        response_data = {
            "success": True,
            "message": "Operation successful",
            "data": {"result": "success"},
            "timestamp": datetime.now().isoformat()
        }
        
        response = ApiResponse(**response_data)
        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {"result": "success"}
        
    def test_error_codes_enum(self):
        """Test ErrorCodes enum values."""
        assert ErrorCodes.PHONE_NUMBER_NOT_FOUND == "PHONE_NUMBER_NOT_FOUND"
        assert ErrorCodes.TENANT_ALREADY_HAS_NUMBER == "TENANT_ALREADY_HAS_NUMBER"
        assert ErrorCodes.NUMBER_PROVISIONING_FAILED == "NUMBER_PROVISIONING_FAILED"
        assert ErrorCodes.INVALID_AREA_CODE == "INVALID_AREA_CODE"


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_phone_number_e164_format(self):
        """Test phone number E.164 format validation."""
        # Valid E.164 format
        phone = PhoneNumberBase(
            tenant_id=uuid4(),
            phone_number="+15551234567",
            friendly_name="Test"
        )
        assert phone.phone_number == "+15551234567"
        
    def test_invalid_phone_number_format(self):
        """Test invalid phone number format handling."""
        # This should still work - validation happens at service level
        phone = PhoneNumberBase(
            tenant_id=uuid4(),
            phone_number="5551234567",  # Missing +1
            friendly_name="Test"
        )
        assert phone.phone_number == "5551234567"
        
    def test_empty_friendly_name(self):
        """Test empty friendly name validation."""
        with pytest.raises(ValidationError):
            PhoneNumberBase(
                tenant_id=uuid4(),
                phone_number="+15551234567",
                friendly_name=""  # Empty string
            )
            
    def test_uuid_validation(self):
        """Test UUID field validation."""
        # Valid UUID string should work
        valid_uuid = str(uuid4())
        phone = PhoneNumberBase(
            tenant_id=valid_uuid,
            phone_number="+15551234567",
            friendly_name="Test"
        )
        assert isinstance(phone.tenant_id, UUID)
        
        # Invalid UUID should raise error
        with pytest.raises(ValidationError):
            PhoneNumberBase(
                tenant_id="invalid-uuid",
                phone_number="+15551234567",
                friendly_name="Test"
            )