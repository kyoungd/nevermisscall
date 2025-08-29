"""Conversation data models for the as-call-service."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Model for creating a new conversation."""
    tenant_id: UUID
    call_id: UUID
    customer_phone: str = Field(..., pattern=r'^\+[1-9]\d{1,14}$')
    business_phone: str = Field(..., pattern=r'^\+[1-9]\d{1,14}$')
    status: Literal['active', 'completed', 'abandoned'] = 'active'


class ConversationUpdate(BaseModel):
    """Model for updating an existing conversation."""
    status: Optional[Literal['active', 'completed', 'abandoned']] = None
    ai_active: Optional[bool] = None
    human_active: Optional[bool] = None
    ai_handoff_time: Optional[datetime] = None
    human_takeover_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    last_human_response_time: Optional[datetime] = None
    message_count: Optional[int] = None
    ai_message_count: Optional[int] = None
    human_message_count: Optional[int] = None
    appointment_scheduled: Optional[bool] = None
    outcome: Optional[Literal['appointment_scheduled', 'quote_provided', 'resolved', 'abandoned']] = None
    lead_id: Optional[UUID] = None


class Conversation(BaseModel):
    """Complete conversation model."""
    id: UUID
    tenant_id: UUID
    call_id: UUID
    
    # Participants
    customer_phone: str
    business_phone: str
    
    # Conversation state
    status: Literal['active', 'completed', 'abandoned']
    ai_active: bool = False
    human_active: bool = False
    
    # Timing
    ai_handoff_time: Optional[datetime] = None
    human_takeover_time: Optional[datetime] = None
    last_message_time: datetime
    last_human_response_time: Optional[datetime] = None
    
    # Metrics
    message_count: int = 0
    ai_message_count: int = 0
    human_message_count: int = 0
    
    # Outcomes
    appointment_scheduled: bool = False
    outcome: Optional[Literal['appointment_scheduled', 'quote_provided', 'resolved', 'abandoned']] = None
    
    # Related entities
    lead_id: Optional[UUID] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """Summary model for conversation lists."""
    id: UUID
    customer_phone: str
    status: Literal['active', 'completed', 'abandoned']
    ai_active: bool
    last_message: Optional[str] = None
    last_message_at: datetime
    message_count: int
    lead_status: Optional[str] = None


class ConversationResponse(BaseModel):
    """API response model for conversation operations."""
    success: bool = True
    conversation: Conversation
    message: Optional[str] = None


class ConversationListResponse(BaseModel):
    """API response model for conversation lists."""
    conversations: list[ConversationSummary]
    total_active: int
    ai_handled_count: int
    human_handled_count: int


class ConversationReplyRequest(BaseModel):
    """Request model for human replies to conversations."""
    message: str = Field(..., min_length=1, max_length=1600)
    take_over_from_ai: bool = True


class ConversationReplyResponse(BaseModel):
    """Response model for conversation replies."""
    success: bool = True
    message: dict
    message_sent: bool = True