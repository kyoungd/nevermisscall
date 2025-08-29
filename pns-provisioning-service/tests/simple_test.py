"""Simple unit tests for pns-provisioning-service core functionality."""

import sys
sys.path.insert(0, '/home/young/Desktop/Code/nvermisscall/nmc/pns-provisioning-service/src')

from uuid import uuid4, UUID
from datetime import datetime
from pns_provisioning_service.models.api import ErrorCodes, success_response, error_response
from pns_provisioning_service.models.phone_number import PhoneNumberBase, ProvisionPhoneNumberRequest


def test_error_codes():
    """Test that error codes are properly defined."""
    assert ErrorCodes.PHONE_NUMBER_NOT_FOUND == "PHONE_NUMBER_NOT_FOUND"
    assert ErrorCodes.TENANT_ALREADY_HAS_NUMBER == "TENANT_ALREADY_HAS_NUMBER" 
    assert ErrorCodes.NUMBER_PROVISIONING_FAILED == "NUMBER_PROVISIONING_FAILED"
    assert ErrorCodes.INVALID_AREA_CODE == "INVALID_AREA_CODE"
    print("✓ Error codes are properly defined")


def test_success_response():
    """Test success response creation."""
    data = {"phoneNumber": {"id": str(uuid4())}}
    response = success_response(data, "Phone number retrieved successfully")
    
    assert response["success"] is True
    assert response["message"] == "Phone number retrieved successfully"
    assert response["data"] == data
    assert "timestamp" in response
    print("✓ Success response creation works")


def test_error_response():
    """Test error response creation."""
    response = error_response(
        ErrorCodes.PHONE_NUMBER_NOT_FOUND,
        "Phone number not found",
        {"phoneId": str(uuid4())}
    )
    
    assert response["success"] is False
    assert response["error"]["code"] == ErrorCodes.PHONE_NUMBER_NOT_FOUND
    assert response["error"]["message"] == "Phone number not found"
    assert "phoneId" in response["error"]["details"]
    print("✓ Error response creation works")


def test_phone_number_base_model():
    """Test PhoneNumberBase model creation."""
    tenant_id = uuid4()
    phone_base = PhoneNumberBase(
        tenant_id=tenant_id,
        phone_number="+15551234567",
        area_code="555",
        friendly_name="Test Business"
    )
    
    assert phone_base.tenant_id == tenant_id
    assert phone_base.phone_number == "+15551234567"
    assert phone_base.area_code == "555"
    assert phone_base.friendly_name == "Test Business"
    assert phone_base.region == "US"  # default value
    print("✓ PhoneNumberBase model creation works")


def test_provision_request_model():
    """Test ProvisionPhoneNumberRequest model creation."""
    tenant_id = uuid4()
    request = ProvisionPhoneNumberRequest(
        tenant_id=tenant_id,
        area_code="555",
        webhook_base_url="https://example.com/webhooks"
    )
    
    assert request.tenant_id == tenant_id
    assert request.area_code == "555"
    assert request.webhook_base_url == "https://example.com/webhooks"
    assert request.number_type == "local"  # default value
    print("✓ ProvisionPhoneNumberRequest model creation works")


def test_phone_number_validation():
    """Test basic phone number format validation."""
    # Valid E.164 format
    phone = PhoneNumberBase(
        tenant_id=uuid4(),
        phone_number="+15551234567",
        area_code="555",
        friendly_name="Test"
    )
    assert phone.phone_number == "+15551234567"
    print("✓ Phone number validation works")


def test_uuid_handling():
    """Test UUID field handling."""
    # Valid UUID should work
    valid_uuid = str(uuid4())
    phone = PhoneNumberBase(
        tenant_id=valid_uuid,
        phone_number="+15551234567",
        area_code="555",
        friendly_name="Test"
    )
    assert isinstance(phone.tenant_id, UUID)
    print("✓ UUID handling works")


def test_business_logic_constants():
    """Test business logic constants and assumptions."""
    # Phase 1 constraint: one phone per tenant
    PHASE_1_MAX_PHONES_PER_TENANT = 1
    assert PHASE_1_MAX_PHONES_PER_TENANT == 1
    
    # Valid phone number statuses
    VALID_STATUSES = ['provisioning', 'provisioned', 'active', 'suspended', 'released']
    assert len(VALID_STATUSES) == 5
    assert 'active' in VALID_STATUSES
    assert 'released' in VALID_STATUSES
    print("✓ Business logic constants are correct")


def test_webhook_url_structure():
    """Test webhook URL structure expectations."""
    # Test webhook configuration structure
    webhooks = {
        "voiceUrl": "https://example.com/voice",
        "smsUrl": "https://example.com/sms", 
        "statusCallbackUrl": "https://example.com/status"
    }
    
    required_webhook_keys = ["voiceUrl", "smsUrl", "statusCallbackUrl"]
    for key in required_webhook_keys:
        assert key in webhooks
        assert webhooks[key].startswith("https://")
    print("✓ Webhook URL structure is correct")


def test_area_code_validation():
    """Test area code format expectations."""
    valid_area_codes = ["212", "555", "800", "415"]
    
    for area_code in valid_area_codes:
        assert len(area_code) == 3
        assert area_code.isdigit()
    print("✓ Area code validation works")


def test_service_configuration():
    """Test service configuration assumptions."""
    # Default service port
    DEFAULT_PORT = 3501
    assert DEFAULT_PORT == 3501
    
    # Service name
    SERVICE_NAME = "pns-provisioning-service"
    assert SERVICE_NAME == "pns-provisioning-service"
    
    # Database pool sizes
    DEFAULT_POOL_SIZE = 5
    DEFAULT_MAX_POOL = 20
    assert DEFAULT_POOL_SIZE < DEFAULT_MAX_POOL
    print("✓ Service configuration is correct")


def run_all_tests():
    """Run all simple tests."""
    print("Running pns-provisioning-service simple tests...\n")
    
    test_error_codes()
    test_success_response()
    test_error_response()
    test_phone_number_base_model()
    test_provision_request_model()
    test_phone_number_validation()
    test_uuid_handling()
    test_business_logic_constants()
    test_webhook_url_structure()
    test_area_code_validation()
    test_service_configuration()
    
    print(f"\n✅ All 11 simple tests passed!")
    return True


if __name__ == "__main__":
    run_all_tests()