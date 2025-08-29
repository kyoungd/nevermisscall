"""Message data models for the as-call-service."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Model for creating a new message."""
    conversation_id: UUID
    tenant_id: UUID
    direction: Literal['inbound', 'outbound']
    sender: Literal['customer', 'system', 'ai', 'human']
    body: str = Field(..., min_length=1, max_length=1600)
    message_sid: Optional[str] = None
    sent_at: Optional[datetime] = None


class MessageUpdate(BaseModel):
    """Model for updating an existing message."""
    processed: Optional[bool] = None
    ai_processed: Optional[bool] = None
    status: Optional[Literal['sent', 'delivered', 'undelivered', 'failed']] = None
    confidence: Optional[float] = None
    intent: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None


class Message(BaseModel):
    """Complete message model."""
    id: UUID
    conversation_id: UUID
    tenant_id: UUID
    
    # Message details
    direction: Literal['inbound', 'outbound']
    sender: Literal['customer', 'system', 'ai', 'human']
    body: str
    message_sid: Optional[str] = None
    
    # Processing
    processed: bool = False
    ai_processed: bool = False
    confidence: Optional[float] = None
    intent: Optional[str] = None
    
    # Delivery
    status: Literal['sent', 'delivered', 'undelivered', 'failed'] = 'sent'
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    
    # Timing
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageWebhook(BaseModel):
    """Model for Twilio webhook message events."""
    message_sid: str = Field(..., alias="MessageSid")
    from_: str = Field(..., alias="From")
    to: str = Field(..., alias="To")
    body: str = Field(..., alias="Body")
    timestamp: Optional[datetime] = None
    
    model_config = {"populate_by_name": True}


class MessageResponse(BaseModel):
    """API response model for message operations."""
    success: bool = True
    message: dict
    processed: bool = True
    ai_processing_triggered: Optional[bool] = None
    human_response_window: Optional[int] = None


class MessageHistoryResponse(BaseModel):
    """API response model for message history."""
    conversation: dict
    messages: list[Message]