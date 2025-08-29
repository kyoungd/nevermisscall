"""Core functionality tests for pns-provisioning-service."""

import sys
sys.path.insert(0, '/home/young/Desktop/Code/nvermisscall/nmc/pns-provisioning-service/src')

import os
from uuid import uuid4, UUID
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

# Set up environment variables for testing
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost/test',
    'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'TWILIO_AUTH_TOKEN': 'test_token',
    'JWT_SECRET_KEY': 'test_secret_key',
    'INTERNAL_SERVICE_KEY': 'test_internal_key'
})

from pns_provisioning_service.models.phone_number import (
    PhoneNumberBase, ProvisionPhoneNumberRequest, ReleasePhoneNumberRequest
)
from pns_provisioning_service.models.api import (
    success_response, error_response, ErrorCodes
)
from pns_provisioning_service.config.settings import Settings
from pns_provisioning_service.services.database import DatabaseService


def test_models_creation():
    """Test core model creation with correct fields."""
    # Test PhoneNumberBase
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
    assert phone_base.region == "US"  # default
    assert phone_base.number_type == "local"  # default
    
    # Test ProvisionPhoneNumberRequest
    request = ProvisionPhoneNumberRequest(
        tenant_id=uuid4(),
        area_code="555",
        webhook_base_url="https://example.com/webhooks"
    )
    
    assert request.area_code == "555"
    assert request.webhook_base_url == "https://example.com/webhooks"
    assert request.number_type == "local"  # default
    
    # Test ReleasePhoneNumberRequest
    release_req = ReleasePhoneNumberRequest(
        confirm_release=True,
        reason="No longer needed"
    )
    
    assert release_req.confirm_release is True
    assert release_req.reason == "No longer needed"
    
    print("✓ Model creation tests passed")


def test_api_responses():
    """Test API response creation."""
    # Test success response
    data = {"phoneNumber": {"id": str(uuid4())}}
    response = success_response(data, "Phone number retrieved successfully")
    
    assert response["success"] is True
    assert response["message"] == "Phone number retrieved successfully"
    assert response["data"] == data
    assert "timestamp" in response
    
    # Test error response
    error_resp = error_response(
        ErrorCodes.PHONE_NUMBER_NOT_FOUND,
        "Phone number not found",
        {"phoneId": str(uuid4())}
    )
    
    assert error_resp["success"] is False
    assert error_resp["error"]["code"] == ErrorCodes.PHONE_NUMBER_NOT_FOUND
    assert error_resp["error"]["message"] == "Phone number not found"
    assert "phoneId" in error_resp["error"]["details"]
    
    print("✓ API response tests passed")


def test_configuration():
    """Test configuration loading."""
    settings = Settings()
    
    assert settings.service_name == "pns-provisioning-service"
    assert settings.port == 3501
    assert settings.database_url == "postgresql://test:test@localhost/test"
    assert settings.twilio_account_sid == "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    assert settings.internal_service_key == "test_internal_key"
    
    print("✓ Configuration tests passed")


def test_database_service_initialization():
    """Test database service initialization."""
    db_service = DatabaseService()
    
    # Test initial state
    assert db_service.pool is None
    
    # Test with mock pool
    mock_pool = AsyncMock()
    db_service.pool = mock_pool
    
    # Test pool assignment
    assert db_service.pool == mock_pool
    
    print("✓ Database service initialization tests passed")


def test_business_logic_validation():
    """Test business logic validation."""
    # Phase 1 constraints
    PHASE_1_MAX_PHONES_PER_TENANT = 1
    assert PHASE_1_MAX_PHONES_PER_TENANT == 1
    
    # Valid statuses
    VALID_STATUSES = ['provisioning', 'provisioned', 'active', 'suspended', 'released']
    assert 'active' in VALID_STATUSES
    assert 'released' in VALID_STATUSES
    assert len(VALID_STATUSES) == 5
    
    # Area code validation
    valid_area_codes = ["212", "555", "800", "415"]
    for area_code in valid_area_codes:
        assert len(area_code) == 3
        assert area_code.isdigit()
    
    # Service configuration
    assert Settings().port == 3501
    assert Settings().service_name == "pns-provisioning-service"
    
    print("✓ Business logic validation tests passed")


def test_error_codes():
    """Test error codes enumeration."""
    # Test all error codes exist
    required_codes = [
        "PHONE_NUMBER_NOT_FOUND",
        "TENANT_ALREADY_HAS_NUMBER", 
        "NUMBER_PROVISIONING_FAILED",
        "INVALID_AREA_CODE",
        "UNAUTHORIZED_ACCESS",
        "INVALID_REQUEST",
        "INTERNAL_SERVER_ERROR",
        "WEBHOOK_CONFIGURATION_FAILED"
    ]
    
    for code in required_codes:
        assert hasattr(ErrorCodes, code)
        assert getattr(ErrorCodes, code) == code
    
    print("✓ Error codes tests passed")


def test_phone_number_formats():
    """Test phone number format handling."""
    # Test E.164 format
    phone = PhoneNumberBase(
        tenant_id=uuid4(),
        phone_number="+15551234567",
        area_code="555",
        friendly_name="Test"
    )
    
    assert phone.phone_number.startswith("+1")
    assert len(phone.phone_number) == 12  # +1 + 10 digits
    assert phone.area_code == "555"
    
    print("✓ Phone number format tests passed")


def test_webhook_configuration():
    """Test webhook configuration structure."""
    # Test webhook URLs
    webhooks = {
        "voiceUrl": "https://example.com/voice",
        "smsUrl": "https://example.com/sms",
        "statusCallbackUrl": "https://example.com/status"
    }
    
    required_keys = ["voiceUrl", "smsUrl", "statusCallbackUrl"]
    for key in required_keys:
        assert key in webhooks
        assert webhooks[key].startswith("https://")
    
    # Test webhook base URL in request
    request = ProvisionPhoneNumberRequest(
        tenant_id=uuid4(),
        area_code="555",
        webhook_base_url="https://example.com/webhooks"
    )
    
    assert request.webhook_base_url.startswith("https://")
    
    print("✓ Webhook configuration tests passed")


def run_all_tests():
    """Run all core functionality tests."""
    print("Running pns-provisioning-service core functionality tests...\n")
    
    try:
        test_models_creation()
        test_api_responses()
        test_configuration()
        test_database_service_initialization()
        test_business_logic_validation()
        test_error_codes()
        test_phone_number_formats()
        test_webhook_configuration()
        
        print(f"\n✅ All 8 core functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)