"""
Conversation service that orchestrates OpenAI, geocoding, and scheduling.
Week 3, Day 4-5 implementation - End-to-end conversation handling.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from dispatch_bot.models.basic_schemas import (
    BasicDispatchRequest, 
    BasicDispatchResponse,
    ConversationStage
)
from dispatch_bot.models.openai_models import ConversationContext, MessageParsingResult
from dispatch_bot.models.geocoding_models import ServiceAreaResult
from dispatch_bot.services.openai_service import OpenAIService
from dispatch_bot.services.geocoding_service import GeocodingService
from dispatch_bot.services.scheduling_engine import SchedulingEngine
from dispatch_bot.services.validation_service import ValidationService
from dispatch_bot.services.error_handler import get_error_handler

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Orchestrates complete conversation flow from message to appointment.
    
    Flow:
    1. Parse customer message with OpenAI
    2. Validate address and service area
    3. Generate appointment options if ready
    4. Handle multi-turn conversations
    5. Manage conversation timeouts and errors
    """
    
    def __init__(self, openai_service: OpenAIService,
                 geocoding_service: GeocodingService,
                 scheduling_engine: SchedulingEngine):
        """
        Initialize conversation service.
        
        Args:
            openai_service: OpenAI integration service
            geocoding_service: Address validation service
            scheduling_engine: Appointment scheduling service
        """
        self.openai_service = openai_service
        self.geocoding_service = geocoding_service
        self.scheduling_engine = scheduling_engine
        self.validation_service = ValidationService()
        self.error_handler = get_error_handler()
        
        # Track active conversations (in-memory for Phase 1)
        self.active_conversations: Dict[str, ConversationContext] = {}
    
    async def process_conversation_turn(self, request: BasicDispatchRequest) -> BasicDispatchResponse:
        """
        Process a complete conversation turn.
        
        Args:
            request: Incoming customer message request
            
        Returns:
            BasicDispatchResponse with next message and state
        """
        try:
            # Get or create conversation context
            context = self._get_conversation_context(request)
            
            # Parse customer message with OpenAI
            parsing_result = await self.openai_service.parse_customer_message(
                request.current_message,
                conversation_history=request.conversation_history,
                context=context
            )
            
            # Update conversation context
            context.add_message(request.current_message)
            context.update_extracted_info("job_type", parsing_result.job_type)
            context.update_extracted_info("problem_description", parsing_result.problem_description)
            
            # Process based on what information we have
            response = await self._process_parsing_result(request, parsing_result, context)
            
            # Update conversation tracking
            self._update_conversation_state(context, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing conversation turn: {str(e)}")
            
            # Create error response
            error_response = self.error_handler.create_user_friendly_response(
                "conversation_processing_error",
                str(e),
                context={"business_name": request.business_name}
            )
            
            return BasicDispatchResponse(
                next_message=error_response.user_message,
                conversation_stage=ConversationStage.COMPLETE,
                requires_followup=False
            )
    
    async def _process_parsing_result(self, request: BasicDispatchRequest,
                                    parsing_result: MessageParsingResult,
                                    context: ConversationContext) -> BasicDispatchResponse:
        """Process the parsed message and determine next steps"""
        
        # Check if we have enough information to proceed
        if parsing_result.customer_address is None:
            return await self._handle_missing_address(request, parsing_result, context)
        
        # Validate address and service area
        address_result = await self._validate_customer_address(
            parsing_result.customer_address, 
            request
        )
        
        if not address_result["valid"]:
            return await self._handle_invalid_address(request, parsing_result, address_result)
        
        if not address_result["in_service_area"]:
            return await self._handle_out_of_service_area(request, address_result)
        
        # We have valid information - offer appointment
        return await self._offer_appointment(request, parsing_result, address_result)
    
    async def _handle_missing_address(self, request: BasicDispatchRequest,
                                    parsing_result: MessageParsingResult,
                                    context: ConversationContext) -> BasicDispatchResponse:
        """Handle case where customer address is missing"""
        
        context.information_still_needed.append("complete_address")
        
        response_message = (
            f"I can help you with your {parsing_result.problem_description.lower()}! "
            f"To schedule an appointment, I'll need your complete address "
            f"(street number, street name, city, and state). What's your address?"
        )
        
        return BasicDispatchResponse(
            job_type=parsing_result.job_type,
            urgency_level=parsing_result.urgency_level,
            next_message=response_message,
            conversation_stage=ConversationStage.COLLECTING_INFO,
            requires_followup=True,
            conversation_timeout_minutes=5
        )
    
    async def _validate_customer_address(self, address: str, 
                                       request: BasicDispatchRequest) -> Dict[str, Any]:
        """Validate customer address and check service area"""
        
        try:
            # Geocode the address
            geocoding_result = await self.geocoding_service.geocode_address(address)
            
            if geocoding_result is None:
                return {"valid": False, "error": "address_not_found"}
            
            # Check service area
            business_coords = await self.geocoding_service.geocode_address(
                request.business_address
            )
            
            if business_coords is None:
                logger.warning(f"Could not geocode business address: {request.business_address}")
                # Assume in service area if we can't validate business address
                return {
                    "valid": True,
                    "in_service_area": True,
                    "geocoding_result": geocoding_result,
                    "distance_miles": None
                }
            
            # Calculate distance using ServiceAreaResult method
            distance_miles = ServiceAreaResult._calculate_distance_miles(
                geocoding_result.latitude, geocoding_result.longitude,
                business_coords.latitude, business_coords.longitude
            )
            
            in_service_area = distance_miles <= request.service_radius_miles
            
            return {
                "valid": True,
                "in_service_area": in_service_area,
                "geocoding_result": geocoding_result,
                "distance_miles": distance_miles
            }
            
        except Exception as e:
            logger.error(f"Address validation error: {str(e)}")
            return {"valid": False, "error": "address_validation_failed"}
    
    async def _handle_invalid_address(self, request: BasicDispatchRequest,
                                    parsing_result: MessageParsingResult,
                                    address_result: Dict[str, Any]) -> BasicDispatchResponse:
        """Handle invalid or unfindable address"""
        
        error_response = self.error_handler.create_user_friendly_response(
            "address_not_found",
            address_result.get("error", "Address validation failed"),
            context={"business_phone": "(555) 123-PLUMB"}
        )
        
        return BasicDispatchResponse(
            job_type=parsing_result.job_type,
            customer_address=parsing_result.customer_address,
            address_valid=False,
            next_message=error_response.user_message,
            conversation_stage=ConversationStage.COLLECTING_INFO,
            requires_followup=True
        )
    
    async def _handle_out_of_service_area(self, request: BasicDispatchRequest,
                                        address_result: Dict[str, Any]) -> BasicDispatchResponse:
        """Handle address outside service area"""
        
        distance = address_result.get("distance_miles", 0)
        
        error_response = self.error_handler.create_user_friendly_response(
            "out_of_service_area",
            f"Address is {distance:.1f} miles away",
            context={
                "service_radius": request.service_radius_miles,
                "business_phone": "(555) 123-PLUMB"
            }
        )
        
        return BasicDispatchResponse(
            customer_address=address_result["geocoding_result"].formatted_address,
            address_valid=True,
            in_service_area=False,
            next_message=error_response.user_message,
            conversation_stage=ConversationStage.COMPLETE,
            requires_followup=False
        )
    
    async def _offer_appointment(self, request: BasicDispatchRequest,
                               parsing_result: MessageParsingResult,
                               address_result: Dict[str, Any]) -> BasicDispatchResponse:
        """Offer appointment when we have all required information"""
        
        try:
            # Generate available slots
            available_slots = self.scheduling_engine.generate_available_slots(days_ahead=0)
            
            if not available_slots:
                # Try next day
                available_slots = self.scheduling_engine.generate_available_slots(days_ahead=1)
            
            if not available_slots:
                return BasicDispatchResponse(
                    job_type=parsing_result.job_type,
                    customer_address=address_result["geocoding_result"].formatted_address,
                    address_valid=True,
                    in_service_area=True,
                    next_message="I don't have any available appointments in the next few days. Please call our office at (555) 123-PLUMB to schedule.",
                    conversation_stage=ConversationStage.COMPLETE
                )
            
            # Get cost estimate
            job_estimate = self.scheduling_engine.estimate_job_cost(parsing_result.job_type)
            
            # Offer first available slot
            first_slot = available_slots[0]
            
            appointment_message = (
                f"I can help with your {parsing_result.problem_description.lower()}! "
                f"I have an appointment available {first_slot.date_string} "
                f"from {first_slot.formatted_time_range}. "
                f"The estimated cost is {job_estimate.cost_range_string} for {job_estimate.description.lower()}. "
                f"\\n\\nReply YES to confirm this appointment or NO if you'd like different options."
            )
            
            return BasicDispatchResponse(
                job_type=parsing_result.job_type,
                customer_address=address_result["geocoding_result"].formatted_address,
                urgency_level=parsing_result.urgency_level,
                address_valid=True,
                in_service_area=True,
                appointment_offered=True,
                proposed_start_time=first_slot.start_time,
                proposed_end_time=first_slot.end_time,
                estimated_price_min=job_estimate.min_cost,
                estimated_price_max=job_estimate.max_cost,
                next_message=appointment_message,
                conversation_stage=ConversationStage.CONFIRMING,
                requires_followup=True,
                conversation_timeout_minutes=5
            )
            
        except Exception as e:
            logger.error(f"Error generating appointment offer: {str(e)}")
            
            return BasicDispatchResponse(
                job_type=parsing_result.job_type,
                customer_address=address_result["geocoding_result"].formatted_address,
                address_valid=True,
                in_service_area=True,
                next_message="I'm having trouble scheduling right now. Please call our office at (555) 123-PLUMB for assistance.",
                conversation_stage=ConversationStage.COMPLETE
            )
    
    def _get_conversation_context(self, request: BasicDispatchRequest) -> ConversationContext:
        """Get or create conversation context"""
        
        if request.conversation_sid not in self.active_conversations:
            self.active_conversations[request.conversation_sid] = ConversationContext(
                conversation_id=request.conversation_sid,
                customer_phone=request.caller_phone,
                business_name=request.business_name
            )
        
        return self.active_conversations[request.conversation_sid]
    
    def _update_conversation_state(self, context: ConversationContext, 
                                 response: BasicDispatchResponse) -> None:
        """Update conversation state after processing"""
        
        # Add response to conversation history
        context.add_message(response.next_message)
        
        # Clean up completed conversations
        if response.conversation_stage == ConversationStage.COMPLETE:
            if context.conversation_id in self.active_conversations:
                del self.active_conversations[context.conversation_id]
        
        # Update information tracking
        if response.address_valid and response.customer_address:
            context.update_extracted_info("customer_address", response.customer_address)
        
        if response.job_type:
            context.update_extracted_info("job_type", response.job_type)
    
    def cleanup_expired_conversations(self, timeout_minutes: int = 15) -> None:
        """Clean up conversations that have timed out"""
        
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        expired_conversations = [
            conv_id for conv_id, context in self.active_conversations.items()
            if context.last_message_timestamp < cutoff_time
        ]
        
        for conv_id in expired_conversations:
            del self.active_conversations[conv_id]
            logger.info(f"Cleaned up expired conversation: {conv_id}")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics for monitoring"""
        
        return {
            "active_conversations": len(self.active_conversations),
            "openai_avg_response_time": self.openai_service.get_average_response_time(),
            "openai_request_count": self.openai_service.request_count
        }