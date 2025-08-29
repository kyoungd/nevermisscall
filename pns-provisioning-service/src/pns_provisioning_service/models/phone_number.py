"""Phone number data models."""

from datetime import datetime
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class PhoneNumberBase(BaseModel):
    """Base phone number model."""
    tenant_id: UUID
    phone_number: str = Field(..., description="E.164 format: +12135551234")
    area_code: str = Field(..., min_length=3, max_length=5)
    region: str = Field(default="US")
    number_type: Literal['local', 'toll-free'] = Field(default='local')
    capabilities: List[Literal['voice', 'sms']] = Field(default=['voice', 'sms'])
    friendly_name: Optional[str] = Field(None, max_length=255)


class PhoneNumberCreate(PhoneNumberBase):
    """Create phone number request."""
    webhook_base_url: str = Field(..., description="Base URL for webhooks")


class PhoneNumber(PhoneNumberBase):
    """Complete phone number entity."""
    id: UUID
    phone_number_sid: str = Field(..., description="Twilio Phone Number SID")
    messaging_service_sid: Optional[str] = Field(None, description="Twilio Messaging Service SID")
    
    # Status and Lifecycle
    status: Literal['provisioning', 'provisioned', 'active', 'suspended', 'released'] = Field(default='provisioning')
    status_reason: Optional[str] = None
    date_provisioned: Optional[datetime] = None
    date_released: Optional[datetime] = None
    
    # Configuration
    webhooks_configured: bool = Field(default=False)
    voice_webhook_url: str
    sms_webhook_url: str
    status_callback_url: Optional[str] = None
    
    # Billing
    monthly_price_cents: int = Field(default=100)
    setup_price_cents: int = Field(default=0)
    currency: str = Field(default="USD")
    
    # Metadata
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhoneNumberStatusUpdate(BaseModel):
    """Update phone number status."""
    status: Literal['provisioning', 'provisioned', 'active', 'suspended', 'released']
    reason: Optional[str] = None


class PhoneNumberConfiguration(BaseModel):
    """Phone number configuration."""
    friendly_name: Optional[str] = None
    webhooks: Optional[Dict[str, str]] = None


class MessagingService(BaseModel):
    """Messaging service entity."""
    phone_number_id: UUID
    messaging_service_sid: str
    friendly_name: str
    inbound_webhook_url: str
    inbound_method: Literal['GET', 'POST'] = Field(default='POST')
    fallback_url: Optional[str] = None
    status_callback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Twilio API models
class AvailableNumber(BaseModel):
    """Available number from Twilio."""
    phone_number: str
    friendly_name: str
    capabilities: List[str]
    
    
class PurchasedNumber(BaseModel):
    """Purchased number from Twilio."""
    sid: str
    phone_number: str
    status: str


class WebhookConfig(BaseModel):
    """Webhook configuration."""
    voice_url: str
    sms_url: str
    status_callback_url: str


class MessagingServiceResponse(BaseModel):
    """Messaging service response from Twilio."""
    sid: str
    friendly_name: str


# Request/Response models
class ProvisionPhoneNumberRequest(BaseModel):
    """Provision phone number request."""
    tenant_id: UUID
    area_code: str = Field(..., min_length=3, max_length=5)
    number_type: Literal['local', 'toll-free'] = Field(default='local')
    webhook_base_url: str


class ProvisionPhoneNumberResponse(BaseModel):
    """Provision phone number response."""
    success: bool
    phone_number: PhoneNumber


class PhoneNumberLookupResponse(BaseModel):
    """Phone number lookup response."""
    tenant_id: UUID
    phone_number: str
    status: str


class PhoneNumberTenantResponse(BaseModel):
    """Get phone number for tenant response."""
    phone_number: PhoneNumber


class PhoneNumberDetailsResponse(BaseModel):
    """Phone number details response."""
    phone_number: Dict[str, Any]


class PhoneNumberConfigurationResponse(BaseModel):
    """Phone number configuration response."""
    configuration: Dict[str, Any]


class ReleasePhoneNumberRequest(BaseModel):
    """Release phone number request."""
    reason: str
    confirm_release: bool = Field(..., description="Must be true to confirm release")


class ReleasePhoneNumberResponse(BaseModel):
    """Release phone number response."""
    success: bool
    phone_number: Dict[str, Any]