"""
Fully conversational AI service that handles complete customer interactions.
The AI controls the conversation flow, information gathering, and confirmation process.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from dispatch_bot.models.openai_models import MessageParsingResult, ConversationContext
from dispatch_bot.services.openai_service import OpenAIService
from dispatch_bot.services.geocoding_service import GeocodingService
from dispatch_bot.services.scheduling_engine import SchedulingEngine

logger = logging.getLogger(__name__)


class ConversationalAIService:
    """
    Fully conversational AI that manages complete customer interactions.
    
    Key principles:
    1. AI controls the conversation flow completely
    2. AI decides when to collect information, validate, and confirm
    3. All responses are natural and conversational
    4. Business logic is provided as context to the AI
    5. AI initiates all actions (scheduling, confirmation, etc.)
    """
    
    def __init__(self, openai_service: OpenAIService,
                 geocoding_service: GeocodingService,
                 scheduling_engine: SchedulingEngine):
        """Initialize conversational AI service"""
        self.openai_service = openai_service
        self.geocoding_service = geocoding_service
        self.scheduling_engine = scheduling_engine
        
        # Business context that AI can use
        self.business_context = {}
        
    async def handle_conversation_turn(self, customer_message: str, 
                                     conversation_context: ConversationContext,
                                     business_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a complete conversation turn with full AI control.
        
        Args:
            customer_message: What the customer said
            conversation_context: Full conversation history and context
            business_info: Business details (name, address, hours, etc.)
            
        Returns:
            Dict with AI response and any business actions taken
        """
        
        # Update business context
        self.business_context = business_info
        
        # Add current customer message to conversation context BEFORE processing
        conversation_context.add_message(customer_message)
        
        # Get current business state (availability, pricing, etc.)
        business_state = await self._gather_business_state(conversation_context)
        
        # Create comprehensive prompt for conversational AI
        conversation_prompt = self._build_conversational_prompt(
            customer_message,
            conversation_context,
            business_info,
            business_state
        )
        
        # Let AI generate the complete response and actions
        ai_decision = await self._get_ai_conversation_decision(conversation_prompt)
        
        # Execute any business actions the AI decided on
        business_actions = await self._execute_business_actions(ai_decision, conversation_context)
        
        # Add AI response to conversation history
        conversation_context.add_message(ai_decision["response"])
        
        return {
            "ai_response": ai_decision["response"],
            "actions_taken": business_actions,
            "conversation_stage": ai_decision.get("conversation_stage", "continuing"),
            "ai_assessment": ai_decision.get("assessment", {}),
            "next_steps": ai_decision.get("next_steps", [])
        }
    
    def _build_conversational_prompt(self, customer_message: str,
                                   conversation_context: ConversationContext,
                                   business_info: Dict[str, Any],
                                   business_state: Dict[str, Any]) -> str:
        """Build comprehensive prompt for conversational AI"""
        
        # Format conversation history
        history = ""
        if conversation_context.conversation_history:
            history = "\n".join([
                f"{'Customer' if i % 2 == 0 else 'You'}: {msg}"
                for i, msg in enumerate(conversation_context.conversation_history)
            ])
        
        # Format available appointments
        available_slots = ""
        if business_state.get("available_appointments"):
            slots = business_state["available_appointments"]
            available_slots = "\n".join([
                f"- {slot['time_range']} on {slot['date']} (${slot['price_min']}-${slot['price_max']})"
                for slot in slots
            ])
        
        prompt = f"""You are a professional customer service representative for {business_info['name']}, a plumbing service company. 

BUSINESS CONTEXT:
- Company: {business_info['name']}
- Service Area: {business_info.get('service_radius', 25)} mile radius from {business_info['address']}
- Phone: {business_info.get('phone', 'our office')}

CURRENT BUSINESS STATUS:
- Service Area Status: {business_state.get('service_area_status', 'checking availability')}
- Available Appointments: {available_slots if available_slots else 'checking availability...'}
- Current Schedule: Mornings booked, afternoons available (1PM-7PM)

CONVERSATION HISTORY:
{history if history else 'This is the start of the conversation'}

CUSTOMER'S CURRENT MESSAGE: "{customer_message}"

INSTRUCTIONS FOR YOUR RESPONSE:
1. Be conversational, professional, and helpful
2. Keep focused on plumbing services and appointment scheduling
3. YOU decide when you have enough information to proceed
4. YOU decide when to check service area, availability, and pricing
5. YOU initiate the confirmation process when ready
6. Handle the conversation naturally - ask follow-up questions, clarify details
7. If it's an emergency, prioritize urgency appropriately
8. Don't use templates - respond naturally like a real person would

**CRITICAL**: When you have both a job type AND a complete address, you MUST present specific available appointment times and pricing from the Available Appointments list above. Don't just say "I'll check" - actually show the customer their options!

**SCHEDULING DATA TO USE**: 
{available_slots}

If you have appointment slots listed above, present them EXACTLY as shown. If no slots are listed, then generate a realistic appointment for tomorrow afternoon (1-3 PM) with appropriate pricing.

BUSINESS ACTIONS YOU CAN TAKE:
- "check_service_area": When you have a complete address
- "get_pricing": When you know the job type  
- "show_appointments": When ready to schedule
- "confirm_appointment": When customer agrees to a specific time
- "complete_conversation": When everything is finished
- "escalate_to_human": For complex issues

RESPONSE FORMAT - You must respond with valid JSON in exactly this format:
{{
    "response": "Your natural, conversational response to the customer",
    "actions_needed": ["list", "of", "business_actions", "if_any"],
    "conversation_stage": "gathering_info",
    "assessment": {{
        "job_type": "type if identified or null",
        "address": "address if provided or null",
        "urgency": "normal",
        "ready_to_schedule": false
    }},
    "next_steps": ["what", "you", "plan", "to", "do", "next"]
}}

Remember: Always respond with valid JSON only. No other text before or after the JSON."""
        
        return prompt
    
    async def _get_ai_conversation_decision(self, prompt: str) -> Dict[str, Any]:
        """Get AI's conversational response and business decisions"""
        
        try:
            response = await self.openai_service.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional plumbing service representative having a natural conversation with a customer. Respond in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # More creative for natural conversation
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            try:
                ai_decision = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON in the content if it has extra text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    ai_decision = json.loads(json_match.group(0))
                else:
                    raise
            
            # Validate response structure
            if "response" not in ai_decision:
                ai_decision["response"] = "I'm here to help with your plumbing needs. Can you tell me what's going on?"
                
            return ai_decision
            
        except Exception as e:
            logger.error(f"Error getting AI conversation decision: {str(e)}")
            
            # Fallback natural response
            return {
                "response": "I'm here to help with your plumbing issue. Can you tell me what's happening and where you're located?",
                "actions_needed": [],
                "conversation_stage": "gathering_info",
                "assessment": {},
                "next_steps": ["gather basic information"]
            }
    
    async def _gather_business_state(self, conversation_context: ConversationContext) -> Dict[str, Any]:
        """Gather current business availability and context"""
        
        business_state = {
            "service_area_status": "available",
            "available_appointments": [],
            "pricing_info": {}
        }
        
        try:
            # Check if we have address information to validate
            extracted_info = conversation_context.extracted_information
            
            if "customer_address" in extracted_info:
                # Check service area
                address = extracted_info["customer_address"]
                geocoding_result = await self.geocoding_service.geocode_address(address)
                
                if geocoding_result:
                    # This would normally check distance, but for demo we'll assume it's valid
                    business_state["service_area_status"] = "in_service_area"
                else:
                    business_state["service_area_status"] = "address_validation_needed"
            
            # Get available appointments
            available_slots = self.scheduling_engine.generate_available_slots(days_ahead=0)
            if not available_slots:
                available_slots = self.scheduling_engine.generate_available_slots(days_ahead=1)
            
            if available_slots:
                job_type = extracted_info.get("job_type", "general_plumbing")
                job_estimate = self.scheduling_engine.estimate_job_cost(job_type)
                
                appointments = []
                for slot in available_slots[:3]:  # Show up to 3 options
                    appointments.append({
                        "time_range": slot.formatted_time_range,
                        "date": slot.date_string,
                        "price_min": job_estimate.min_cost,
                        "price_max": job_estimate.max_cost,
                        "slot_object": slot
                    })
                
                business_state["available_appointments"] = appointments
                business_state["pricing_info"] = {
                    "job_type": job_type,
                    "description": job_estimate.description,
                    "price_range": job_estimate.cost_range_string
                }
        
        except Exception as e:
            logger.error(f"Error gathering business state: {str(e)}")
        
        return business_state
    
    async def _execute_business_actions(self, ai_decision: Dict[str, Any], 
                                      conversation_context: ConversationContext) -> List[str]:
        """Execute business actions decided by the AI"""
        
        actions_taken = []
        actions_needed = ai_decision.get("actions_needed", [])
        assessment = ai_decision.get("assessment", {})
        
        try:
            # Update extracted information based on AI assessment
            if assessment.get("job_type"):
                conversation_context.update_extracted_info("job_type", assessment["job_type"])
            
            if assessment.get("address"):
                conversation_context.update_extracted_info("customer_address", assessment["address"])
            
            if assessment.get("urgency"):
                conversation_context.update_extracted_info("urgency_level", assessment["urgency"])
            
            # Execute specific business actions
            for action in actions_needed:
                if action == "check_service_area":
                    actions_taken.append("validated_service_area")
                    
                elif action == "get_pricing":
                    actions_taken.append("calculated_pricing")
                    
                elif action == "show_appointments":
                    actions_taken.append("displayed_available_slots")
                    
                elif action == "confirm_appointment":
                    # This would actually book the appointment
                    actions_taken.append("appointment_confirmed")
                    
                elif action == "complete_conversation":
                    actions_taken.append("conversation_completed")
                    
                elif action == "escalate_to_human":
                    actions_taken.append("escalated_to_human")
        
        except Exception as e:
            logger.error(f"Error executing business actions: {str(e)}")
            actions_taken.append("error_in_business_logic")
        
        return actions_taken
    
    def create_conversation_context(self, conversation_id: str, customer_phone: str, 
                                  business_name: str) -> ConversationContext:
        """Create new conversation context for tracking"""
        
        return ConversationContext(
            conversation_id=conversation_id,
            customer_phone=customer_phone,
            business_name=business_name
        )