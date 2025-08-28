"""
Core business models for NeverMissCall shared library.

Provides Call, Conversation, Message, Lead, and PhoneNumber models
following the database schema defined in database-migration-order.md.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from decimal import Decimal


class Call(BaseModel):
    """
    Call model following the database schema from database-migration-order.md.
    
    Maps to the 'calls' table for call tracking and processing.
    """
    id: str
    call_sid: str  # Twilio call SID
    tenant_id: str
    
    # Call participants
    customer_phone: str
    business_phone: str
    
    # Call details
    direction: str = 'inbound'  # inbound, outbound
    status: str = 'ringing'  # ringing, in-progress, completed, etc.
    start_time: str
    end_time: Optional[str] = None
    duration: int = 0  # seconds
    
    # Processing status
    processed: bool = False
    sms_triggered: bool = False
    conversation_created: bool = False
    lead_created: bool = False
    
    # Related entities
    conversation_id: Optional[str] = None
    lead_id: Optional[str] = None
    
    # Geographic data
    caller_city: Optional[str] = None
    caller_state: Optional[str] = None
    caller_country: str = 'US'
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Conversation(BaseModel):
    """
    Conversation model following the database schema.
    
    Maps to the 'conversations' table for SMS conversation tracking.
    """
    id: str
    tenant_id: str
    call_id: str
    
    # Participants
    customer_phone: str
    business_phone: str
    
    # Conversation state
    status: str = 'active'  # active, completed, abandoned
    ai_active: bool = False
    human_active: bool = False
    
    # Timing
    ai_handoff_time: Optional[str] = None
    human_takeover_time: Optional[str] = None
    last_message_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_human_response_time: Optional[str] = None
    
    # Metrics
    message_count: int = 0
    ai_message_count: int = 0
    human_message_count: int = 0
    
    # Outcomes
    outcome: Optional[str] = None  # scheduled, quoted, declined, etc.
    appointment_scheduled: bool = False
    
    # Related entities
    lead_id: Optional[str] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Message(BaseModel):
    """
    Message model following the database schema.
    
    Maps to the 'messages' table for individual SMS messages.
    """
    id: str
    conversation_id: str
    tenant_id: str
    
    # Message details
    message_sid: Optional[str] = None  # Twilio message SID
    direction: str  # inbound, outbound
    sender: str  # phone number
    body: str  # message content
    
    # Processing
    processed: bool = False
    ai_processed: bool = False
    confidence: Optional[Decimal] = None
    intent: Optional[str] = None
    
    # Delivery
    status: str = 'sent'  # sent, delivered, failed, etc.
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    
    # Timing
    sent_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    delivered_at: Optional[str] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Lead(BaseModel):
    """
    Lead model following the database schema.
    
    Maps to the 'leads' table for lead tracking and management.
    """
    id: str
    tenant_id: str
    conversation_id: str
    call_id: str
    
    # Customer information
    customer_phone: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    
    # Lead details
    problem_description: str
    job_type: Optional[str] = None
    urgency_level: str = 'normal'  # low, normal, high, emergency
    estimated_value: Optional[Decimal] = None
    
    # Lead status
    status: str = 'new'  # new, contacted, qualified, quoted, won, lost
    status_notes: Optional[str] = None
    
    # AI analysis (stored as JSONB in database)
    ai_analysis: Optional[Dict[str, Any]] = None
    
    # Outcomes
    appointment_id: Optional[str] = None
    conversion_value: Optional[Decimal] = None
    lost_reason: Optional[str] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PhoneNumber(BaseModel):
    """
    Phone number model following the database schema.
    
    Maps to the 'phone_numbers' table for Twilio phone number management.
    """
    id: str
    tenant_id: str  # One number per tenant in Phase 1
    
    # Twilio Information
    phone_number: str  # E.164 format
    phone_number_sid: str
    messaging_service_sid: Optional[str] = None
    
    # Number Details
    friendly_name: Optional[str] = None
    area_code: str
    region: Optional[str] = None
    number_type: str = 'local'  # local, toll-free, mobile
    capabilities: List[str] = Field(default_factory=lambda: ['voice', 'sms'])
    
    # Status and Lifecycle
    status: str = 'provisioning'  # provisioning, active, inactive, released
    status_reason: Optional[str] = None
    date_provisioned: Optional[str] = None
    date_released: Optional[str] = None
    
    # Configuration
    webhooks_configured: bool = False
    voice_webhook_url: str
    sms_webhook_url: str
    status_callback_url: Optional[str] = None
    
    # Billing
    monthly_price_cents: int = 100
    setup_price_cents: int = 0
    currency: str = 'USD'
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MessagingService(BaseModel):
    """
    Messaging service model following the database schema.
    
    Maps to the 'messaging_services' table for Twilio messaging services.
    """
    phone_number_id: str
    messaging_service_sid: str
    friendly_name: str
    inbound_webhook_url: str
    inbound_method: str = 'POST'
    fallback_url: Optional[str] = None
    status_callback: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Appointment(BaseModel):
    """
    Appointment model for scheduled appointments from conversations.
    """
    id: str
    tenant_id: str
    lead_id: str
    conversation_id: str
    
    # Appointment details
    customer_phone: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    
    # Scheduling
    scheduled_date: str  # ISO date
    scheduled_time: str  # HH:MM format
    duration_minutes: int = 60
    timezone: str = 'America/New_York'
    
    # Appointment details
    service_type: Optional[str] = None
    description: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    
    # Status
    status: str = 'scheduled'  # scheduled, confirmed, completed, cancelled, no_show
    confirmation_sent: bool = False
    reminder_sent: bool = False
    
    # Integration
    external_calendar_id: Optional[str] = None
    calendar_provider: Optional[str] = None  # google, microsoft, etc.
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Request/Response models for API endpoints
class CreateCallRequest(BaseModel):
    """Request model for creating a new call."""
    call_sid: str
    customer_phone: str
    business_phone: str
    direction: str = 'inbound'
    start_time: Optional[str] = None


class UpdateCallStatusRequest(BaseModel):
    """Request model for updating call status."""
    status: str
    end_time: Optional[str] = None
    duration: Optional[int] = None


class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation."""
    call_id: str
    customer_phone: str
    business_phone: str


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    conversation_id: str
    body: str
    sender: str
    direction: str = 'outbound'


class CreateLeadRequest(BaseModel):
    """Request model for creating a new lead."""
    conversation_id: str
    call_id: str
    customer_phone: str
    problem_description: str
    customer_name: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    urgency_level: str = 'normal'


class ScheduleAppointmentRequest(BaseModel):
    """Request model for scheduling an appointment."""
    lead_id: str
    customer_name: str
    customer_phone: str
    scheduled_date: str
    scheduled_time: str
    service_type: Optional[str] = None
    description: Optional[str] = None