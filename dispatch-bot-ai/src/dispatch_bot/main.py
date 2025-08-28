"""
Main FastAPI application for Dispatch Bot AI API.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dispatch_bot.models.schemas import (
    ProcessConversationRequest,
    ProcessConversationResponse,
    ExtractedInfo,
    ValidationResult,
    NextAction,
    ConfidenceScores,
    ConversationStage,
    ActionType,
    UrgencyLevel
)
from dispatch_bot.config.logging import setup_logging, get_logger
from dispatch_bot.config.settings import get_settings
from dispatch_bot.api.exceptions import setup_exception_handlers


# Store app startup time for uptime calculation
_startup_time = time.time()


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]
    uptime_seconds: int


class HealthResponseDegraded(BaseModel):
    """Response model for degraded health check endpoint."""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]
    uptime_seconds: int
    warnings: list[str]


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    # Setup logging first
    settings = get_settings()
    setup_logging(
        level=settings.logging.level,
        json_logs=settings.logging.json_logs
    )
    
    logger = get_logger(__name__)
    logger.info("Starting Dispatch Bot AI API", version="1.0.0", environment=settings.environment)
    
    app = FastAPI(
        title=settings.api.title,
        description=settings.api.description,
        version=settings.api.version,
        docs_url=settings.api.docs_url,
        redoc_url=settings.api.redoc_url,
        debug=settings.api.debug
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    @app.get("/health", response_model=HealthResponse, status_code=200)
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.
        
        Returns:
            Dict containing API health status, version, and service status
        """
        current_time = datetime.now(timezone.utc)
        uptime_seconds = int(time.time() - _startup_time)
        
        # Mock service status checks - in production these would be real health checks
        services = {
            "database": "healthy",
            "geocoding": "healthy", 
            "llm": "healthy",
            "traffic": "healthy"
        }
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": current_time.isoformat(),
            "services": services,
            "uptime_seconds": uptime_seconds
        }
    
    @app.post("/dispatch/process", response_model=ProcessConversationResponse, status_code=200)
    async def process_conversation(request: ProcessConversationRequest) -> ProcessConversationResponse:
        """
        Process a conversation turn and determine next actions.
        
        Args:
            request: The conversation processing request
            
        Returns:
            ProcessConversationResponse with extracted info, validation, and next actions
        """
        logger = get_logger(__name__)
        logger.info(
            "Processing conversation",
            caller_phone=request.caller_phone,
            trade_type=request.trade_type,
            business_name=request.business_name
        )
        
        # Mock processing logic - in production this would integrate with real AI services
        
        # Extract basic information from the message
        message = request.current_message.lower()
        
        # Basic job type detection
        job_type = None
        job_confidence = 0.0
        
        if any(keyword in message for keyword in ["water", "heater", "hot"]):
            job_type = "water_heater_repair"
            job_confidence = 0.85
        elif any(keyword in message for keyword in ["faucet", "tap", "leak"]):
            job_type = "faucet_repair" 
            job_confidence = 0.80
        elif any(keyword in message for keyword in ["toilet", "clogged", "flush"]):
            job_type = "toilet_repair"
            job_confidence = 0.75
        
        # Basic urgency detection
        urgency_level = UrgencyLevel.NORMAL
        urgency_confidence = 0.0
        
        if any(keyword in message for keyword in ["burst", "flooding", "emergency", "urgent"]):
            urgency_level = UrgencyLevel.EMERGENCY
            urgency_confidence = 0.90
        elif any(keyword in message for keyword in ["soon", "asap", "today"]):
            urgency_level = UrgencyLevel.URGENT
            urgency_confidence = 0.75
        
        # Basic address extraction (simplified)
        customer_address = None
        address_verified = False
        
        # Look for common address patterns
        import re
        address_pattern = r'\d+\s+\w+.*\d{5}'
        address_match = re.search(address_pattern, request.current_message)
        if address_match:
            customer_address = address_match.group()
            address_verified = True
        
        # Create extracted info
        extracted_info = ExtractedInfo(
            job_type=job_type,
            job_confidence=job_confidence,
            urgency_level=urgency_level,
            urgency_confidence=urgency_confidence,
            customer_address=customer_address,
            address_verified=address_verified,
            preferred_date="today" if urgency_level == UrgencyLevel.EMERGENCY else None,
            customer_confirmed=False
        )
        
        # Basic validation
        validation = ValidationResult(
            service_area_valid=True,  # Mock - would check against service radius
            trade_supported=request.trade_type in ["plumbing", "electrical", "hvac", "locksmith", "garage_door"],
            job_type_supported=job_type is not None if job_type else True,
            within_business_hours=True,  # Mock - would check actual business hours
            capacity_available=not request.business_settings.out_of_office,
            address_reachable=customer_address is not None,
            validation_errors=[]
        )
        
        # Add validation errors if needed
        if not validation.address_reachable:
            validation.validation_errors.append("Customer address not provided or unclear")
        if not validation.job_type_supported:
            validation.validation_errors.append("Unable to determine job type from message")
        
        # Determine next action
        if validation.validation_errors:
            next_action = NextAction(
                action_type=ActionType.CONTINUE_CONVERSATION,
                message_to_customer="I need a bit more information. What's the service address?",
                follow_up_needed=True,
                follow_up_delay_minutes=5
            )
        elif urgency_level == UrgencyLevel.EMERGENCY and customer_address:
            next_action = NextAction(
                action_type=ActionType.REQUEST_CONFIRMATION,
                message_to_customer=f"🚨 Emergency detected! I can get our tech to you today. Reply YES to confirm.",
                follow_up_needed=True,
                follow_up_delay_minutes=3
            )
        else:
            next_action = NextAction(
                action_type=ActionType.CONTINUE_CONVERSATION,
                message_to_customer="Thanks for the info! Let me check our availability and get back to you.",
                follow_up_needed=False,
                follow_up_delay_minutes=0
            )
        
        # Set conversation stage
        if validation.validation_errors:
            stage = ConversationStage.COLLECTING_INFO
        elif next_action.action_type == ActionType.REQUEST_CONFIRMATION:
            stage = ConversationStage.CONFIRMING
        else:
            stage = ConversationStage.INITIAL
        
        # Create confidence scores
        confidence_scores = ConfidenceScores(
            job_type_confidence=job_confidence,
            urgency_confidence=urgency_confidence,
            address_confidence=0.8 if address_verified else 0.0,
            overall_confidence=(job_confidence + urgency_confidence + (0.8 if address_verified else 0.0)) / 3
        )
        
        return ProcessConversationResponse(
            extracted_info=extracted_info,
            validation=validation,
            proposed_slot=None,  # Would be populated with actual scheduling logic
            next_action=next_action,
            conversation_stage=stage,
            needs_geocoding=customer_address is not None and not address_verified,
            geocoding_query=customer_address,
            confidence_scores=confidence_scores
        )
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)