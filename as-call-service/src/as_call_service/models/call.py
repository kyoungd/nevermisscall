"""Call data models for the as-call-service."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CallCreate(BaseModel):
    """Model for creating a new call."""
    call_sid: str = Field(..., description="Twilio Call SID")
    tenant_id: UUID
    customer_phone: str = Field(..., pattern=r'^\+[1-9]\d{1,14}$')
    business_phone: str = Field(..., pattern=r'^\+[1-9]\d{1,14}$')
    direction: Literal['inbound', 'outbound'] = 'inbound'
    status: Literal['ringing', 'in-progress', 'completed', 'missed', 'failed']
    start_time: datetime
    caller_city: Optional[str] = None
    caller_state: Optional[str] = None
    caller_country: Optional[str] = 'US'


class CallUpdate(BaseModel):
    """Model for updating an existing call."""
    status: Optional[Literal['ringing', 'in-progress', 'completed', 'missed', 'failed']] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    processed: Optional[bool] = None
    sms_triggered: Optional[bool] = None
    conversation_created: Optional[bool] = None
    lead_created: Optional[bool] = None
    conversation_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None


class Call(BaseModel):
    """Complete call model."""
    id: UUID
    call_sid: str
    tenant_id: UUID
    
    # Call participants
    customer_phone: str
    business_phone: str
    
    # Call details
    direction: Literal['inbound', 'outbound']
    status: Literal['ringing', 'in-progress', 'completed', 'missed', 'failed']
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: int = 0  # seconds
    
    # Processing status
    processed: bool = False
    sms_triggered: bool = False
    conversation_created: bool = False
    lead_created: bool = False
    
    # Related entities
    conversation_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    
    # Geographic data
    caller_city: Optional[str] = None
    caller_state: Optional[str] = None
    caller_country: Optional[str] = 'US'
    
    # Metadata
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CallWebhook(BaseModel):
    """Model for Twilio webhook call events."""
    callSid: str = Field(..., alias="CallSid")
    from_: str = Field(..., alias="From")
    to: str = Field(..., alias="To")
    tenant_id: Optional[UUID] = Field(None, alias="tenantId")
    call_status: str = Field(..., alias="CallStatus")
    direction: str = Field(..., alias="Direction")
    timestamp: Optional[datetime] = None
    call_duration: Optional[int] = Field(None, alias="CallDuration")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    
    model_config = {"populate_by_name": True}


class CallResponse(BaseModel):
    """API response model for call operations."""
    success: bool = True
    call: Call
    message: Optional[str] = None


class CallListResponse(BaseModel):
    """API response model for call lists."""
    calls: list[Call]
    total: int
    page: int
    page_size: int