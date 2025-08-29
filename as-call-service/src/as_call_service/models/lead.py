"""Lead data models for the as-call-service."""

from datetime import datetime
from typing import Dict, Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIAnalysis(BaseModel):
    """AI analysis results for lead classification."""
    confidence: float = Field(..., ge=0.0, le=1.0)
    job_classification: str
    urgency_score: float = Field(..., ge=0.0, le=1.0)
    service_area_valid: bool
    address_validated: bool


class LeadCreate(BaseModel):
    """Model for creating a new lead."""
    tenant_id: UUID
    conversation_id: UUID
    call_id: UUID
    customer_phone: str = Field(..., pattern=r'^\+[1-9]\d{1,14}$')
    problem_description: str = Field(..., min_length=1)
    urgency_level: Literal['low', 'normal', 'high', 'emergency'] = 'normal'
    status: Literal['new', 'qualified', 'appointment_scheduled', 'completed', 'lost'] = 'new'
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    job_type: Optional[str] = None
    estimated_value: Optional[float] = None
    ai_analysis: Optional[AIAnalysis] = None


class LeadUpdate(BaseModel):
    """Model for updating an existing lead."""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    problem_description: Optional[str] = None
    job_type: Optional[str] = None
    urgency_level: Optional[Literal['low', 'normal', 'high', 'emergency']] = None
    status: Optional[Literal['new', 'qualified', 'appointment_scheduled', 'completed', 'lost']] = None
    estimated_value: Optional[float] = None
    status_notes: Optional[str] = None
    ai_analysis: Optional[AIAnalysis] = None
    appointment_id: Optional[UUID] = None
    conversion_value: Optional[float] = None
    lost_reason: Optional[str] = None


class Lead(BaseModel):
    """Complete lead model."""
    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    call_id: UUID
    
    # Customer information
    customer_phone: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    
    # Lead details
    problem_description: str
    job_type: Optional[str] = None
    urgency_level: Literal['low', 'normal', 'high', 'emergency']
    estimated_value: Optional[float] = None
    
    # Lead status
    status: Literal['new', 'qualified', 'appointment_scheduled', 'completed', 'lost']
    status_notes: Optional[str] = None
    
    # AI analysis
    ai_analysis: Optional[AIAnalysis] = None
    
    # Outcomes
    appointment_id: Optional[UUID] = None
    conversion_value: Optional[float] = None
    lost_reason: Optional[str] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    """Request model for updating lead status."""
    status: Literal['new', 'qualified', 'appointment_scheduled', 'completed', 'lost']
    notes: Optional[str] = None
    estimated_value: Optional[float] = None


class LeadResponse(BaseModel):
    """API response model for lead operations."""
    success: bool = True
    lead: Lead
    message: Optional[str] = None


class LeadListResponse(BaseModel):
    """API response model for lead lists."""
    leads: list[Lead]
    total: int
    page: int
    page_size: int