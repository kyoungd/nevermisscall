"""
Enhanced conversation processor with fail-fast error handling.
Week 2, Day 4-5 implementation - integrates error handling and fallback services.
"""

import logging
from typing import Optional
from datetime import datetime

from dispatch_bot.models.basic_schemas import BasicDispatchRequest, BasicDispatchResponse, ConversationStage
from dispatch_bot.services.error_handler import get_error_handler, ErrorSeverity
from dispatch_bot.services.conversation_manager import get_conversation_manager
from dispatch_bot.services.fallback_service import get_fallback_service
from dispatch_bot.services.validation_service import ValidationService
from dispatch_bot.services.geocoding_service import GeocodingService, ServiceAreaValidator

logger = logging.getLogger(__name__)


class ConversationProcessor:
    """
    Enhanced conversation processor with comprehensive error handling.
    
    Implements fail-fast patterns and graceful degradation:
    1. Uses fallback services when primary services fail
    2. Provides user-friendly error messages
    3. Manages conversation timeouts
    4. Tracks error patterns to prevent loops
    """
    
    def __init__(self):
        """Initialize conversation processor with services"""
        self.error_handler = get_error_handler()
        self.conversation_manager = get_conversation_manager()
        self.fallback_service = get_fallback_service()
        self.validation_service = ValidationService()
    
    async def process_message_with_degradation(self, request: BasicDispatchRequest) -> BasicDispatchResponse:
        """
        Process message with full error handling and graceful degradation.
        
        Args:
            request: Customer request to process
            
        Returns:
            BasicDispatchResponse with appropriate error handling
        """
        conversation_id = request.conversation_sid
        
        try:
            # Start or update conversation tracking
            if not self.conversation_manager.get_timeout_info(conversation_id):
                self.conversation_manager.start_conversation(conversation_id)
            else:
                self.conversation_manager.update_activity(conversation_id)
            
            # Check for conversation timeout
            if self.conversation_manager.is_conversation_expired(conversation_id):
                return self.conversation_manager.generate_timeout_response(
                    conversation_id, request.business_name
                )
            
            # Check for timeout warning
            warning_response = self.conversation_manager.check_for_timeout_warning(
                conversation_id, request.business_name
            )
            if warning_response:
                return warning_response
            
            # Process message with error handling
            return await self._process_with_fallback(request)
            
        except Exception as e:
            logger.error(f"Critical error processing conversation {conversation_id}: {str(e)}")
            
            # Create emergency fallback response
            error_response = self.error_handler.create_user_friendly_response(
                error_type="system_error",
                original_error=str(e),
                context={
                    "business_name": request.business_name,
                    "business_phone": getattr(request, 'business_phone', 'our office')
                }
            )
            
            return BasicDispatchResponse(
                next_message=error_response.user_message,
                conversation_stage=ConversationStage.COMPLETE,
                requires_followup=False
            )
    
    async def _process_with_fallback(self, request: BasicDispatchRequest) -> BasicDispatchResponse:
        """
        Process request with fallback handling for external services.
        
        Args:
            request: Customer request
            
        Returns:
            Response with fallback handling applied
        """
        conversation_id = request.conversation_sid
        response_data = {}
        
        # Step 1: Extract intent with fallback
        try:
            # This would normally use OpenAI, but for Phase 1 we'll use fallback
            intent_result = await self.fallback_service.extract_intent_with_fallback(
                request.current_message, 
                primary_service=None  # OpenAI not implemented yet
            )
            
            if intent_result.success:
                response_data.update(intent_result.data or {})
            else:
                # Handle intent extraction failure
                error_response = self.error_handler.create_user_friendly_response(
                    "intent_extraction_failed",
                    "Could not understand message",
                    {"business_name": request.business_name}
                )
                return BasicDispatchResponse(
                    next_message=error_response.user_message,
                    conversation_stage=ConversationStage.COLLECTING_INFO
                )
                
        except Exception as e:
            logger.warning(f"Intent extraction failed: {e}")
            response_data["job_type"] = "general_plumbing"
        
        # Step 2: Geocode address with fallback
        customer_address = response_data.get("address")
        if customer_address:
            try:
                # This would use Google Maps API
                geocoding_result = await self.fallback_service.geocode_with_fallback(
                    customer_address,
                    primary_service=None  # Will use fallback
                )
                
                if geocoding_result.success:
                    response_data.update(geocoding_result.data or {})
                    
            except Exception as e:
                logger.warning(f"Geocoding failed: {e}")
                # Continue with address validation error
                error_response = self.error_handler.get_error_response_for_conversation(
                    conversation_id, "address_not_found", str(e)
                )
                return BasicDispatchResponse(
                    next_message=error_response.user_message,
                    conversation_stage=error_response.conversation_stage
                )
        
        # Generate appropriate response based on what we collected
        if not customer_address:
            return BasicDispatchResponse(
                next_message=f"I can help you with your plumbing issue! Please tell me what's wrong and your complete address so I can check if we serve your area.",
                conversation_stage=ConversationStage.COLLECTING_INFO
            )
        
        # If we have address but limited validation
        if geocoding_result and geocoding_result.fallback_used:
            return BasicDispatchResponse(
                next_message=f"{geocoding_result.user_message} For the most accurate service information, please call {request.business_name} directly.",
                conversation_stage=ConversationStage.COLLECTING_INFO,
                customer_address=customer_address,
                job_type=response_data.get("job_type"),
                address_valid=True,  # Assume valid for fallback
                in_service_area=response_data.get("in_service_area", True)
            )
        
        # Success case
        return BasicDispatchResponse(
            next_message=f"I understand you need help with {response_data.get('job_type', 'plumbing')} at {customer_address}. Let me check our availability.",
            conversation_stage=ConversationStage.CONFIRMING,
            customer_address=customer_address,
            job_type=response_data.get("job_type"),
            address_valid=True,
            in_service_area=True
        )


class ServiceHealthMonitor:
    """Monitor health of external services for degradation decisions"""
    
    def __init__(self):
        """Initialize health monitor"""
        self.service_health = {
            "google_maps": {"healthy": True, "last_check": datetime.now()},
            "openai": {"healthy": True, "last_check": datetime.now()},
        }
    
    async def check_service_health(self, service_name: str) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            service_name: Name of service to check
            
        Returns:
            True if healthy, False if degraded
        """
        # This would implement actual health checks
        return self.service_health.get(service_name, {}).get("healthy", False)
    
    def mark_service_unhealthy(self, service_name: str, error: str) -> None:
        """Mark a service as unhealthy"""
        if service_name in self.service_health:
            self.service_health[service_name]["healthy"] = False
            self.service_health[service_name]["last_error"] = error
            self.service_health[service_name]["last_check"] = datetime.now()
            
            logger.warning(f"Marked {service_name} as unhealthy: {error}")
    
    def get_degradation_level(self) -> int:
        """
        Get current system degradation level.
        
        Returns:
            0 = Full service
            1 = Minor degradation
            2 = Major degradation  
            3 = Emergency mode
        """
        unhealthy_services = sum(
            1 for service in self.service_health.values()
            if not service["healthy"]
        )
        
        if unhealthy_services == 0:
            return 0  # Full service
        elif unhealthy_services == 1:
            return 1  # Minor degradation
        elif unhealthy_services == 2:
            return 2  # Major degradation
        else:
            return 3  # Emergency mode


# Global instances
conversation_processor = ConversationProcessor()
health_monitor = ServiceHealthMonitor()


def get_conversation_processor() -> ConversationProcessor:
    """Get the global conversation processor instance"""
    return conversation_processor


def get_health_monitor() -> ServiceHealthMonitor:
    """Get the global health monitor instance"""
    return health_monitor