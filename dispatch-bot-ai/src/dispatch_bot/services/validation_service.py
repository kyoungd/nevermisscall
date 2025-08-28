"""
Basic validation service for Phase 1 implementation.
Handles business rules validation and input sanitization.
"""

from datetime import datetime, time
from typing import Dict, Any, Optional, Tuple
import logging

from dispatch_bot.models.basic_schemas import BasicDispatchRequest, UrgencyLevel
from dispatch_bot.utils.address_parser import extract_address_with_confidence


logger = logging.getLogger(__name__)


class ValidationService:
    """
    Handles validation of business rules and request data for Phase 1.
    
    Focus on:
    - Business hours validation
    - Basic input sanitization  
    - Address extraction and confidence scoring
    - Simple business rule enforcement
    """
    
    def __init__(self):
        """Initialize validation service"""
        pass
    
    def validate_business_hours(self, request_time: datetime, 
                               start_time: str, end_time: str) -> Dict[str, Any]:
        """
        Validate if request is within business hours.
        
        Args:
            request_time: When the request was made
            start_time: Business hours start (HH:MM format)
            end_time: Business hours end (HH:MM format)
            
        Returns:
            Dict with validation results
        """
        try:
            # Parse business hours
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            business_start = time(start_hour, start_minute)
            business_end = time(end_hour, end_minute)
            
            # Get current time from request
            current_time = request_time.time()
            
            # Check if within business hours
            within_hours = business_start <= current_time <= business_end
            
            return {
                "within_business_hours": within_hours,
                "current_time": current_time.strftime("%H:%M"),
                "business_start": start_time,
                "business_end": end_time,
                "validation_message": self._get_hours_message(within_hours, business_start, business_end)
            }
            
        except Exception as e:
            logger.error(f"Business hours validation failed: {str(e)}")
            return {
                "within_business_hours": False,
                "validation_message": "Unable to validate business hours",
                "error": str(e)
            }
    
    def validate_request_data(self, request: BasicDispatchRequest) -> Dict[str, Any]:
        """
        Perform comprehensive validation of request data.
        
        Args:
            request: The dispatch request to validate
            
        Returns:
            Dict with validation results and extracted information
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "extracted_info": {}
        }
        
        try:
            # Validate conversation SID (check for duplicates would go here)
            sid_validation = self._validate_conversation_sid(request.conversation_sid)
            validation_results["sid_validation"] = sid_validation
            
            # Validate phone number format (already done by Pydantic, but double-check)
            phone_validation = self._validate_phone_number(request.caller_phone)
            validation_results["phone_validation"] = phone_validation
            
            # Extract and validate message content
            message_validation = self._validate_message_content(request.current_message)
            validation_results["message_validation"] = message_validation
            
            # Validate business configuration
            business_validation = self._validate_business_config(request)
            validation_results["business_validation"] = business_validation
            
            # Extract address from message
            address_info = extract_address_with_confidence(request.current_message)
            validation_results["extracted_info"]["address"] = address_info
            
            # Check business hours (use current time)
            current_time = datetime.now()
            hours_validation = self.validate_business_hours(
                current_time, 
                request.business_hours_start,
                request.business_hours_end
            )
            validation_results["hours_validation"] = hours_validation
            
            # Aggregate validation status
            all_validations = [
                sid_validation.get("valid", False),
                phone_validation.get("valid", False), 
                message_validation.get("valid", False),
                business_validation.get("valid", False)
            ]
            
            validation_results["valid"] = all(all_validations)
            
            # Collect all error messages
            for validation_key in ["sid_validation", "phone_validation", "message_validation", "business_validation"]:
                validation_data = validation_results.get(validation_key, {})
                if validation_data.get("errors"):
                    validation_results["errors"].extend(validation_data["errors"])
                if validation_data.get("warnings"):
                    validation_results["warnings"].extend(validation_data["warnings"])
            
        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def determine_urgency_level(self, message: str) -> Tuple[UrgencyLevel, float]:
        """
        Determine urgency level from customer message.
        Phase 1: Basic keyword detection. Enhanced with ML in Phase 2.
        
        Args:
            message: Customer message text
            
        Returns:
            Tuple of (urgency_level, confidence_score)
        """
        if not message or not message.strip():
            return UrgencyLevel.NORMAL, 0.0
        
        message_lower = message.lower()
        
        # Phase 1: Basic emergency keywords for plumbing
        emergency_keywords = [
            "flooding", "flood", "burst pipe", "water everywhere", 
            "emergency", "urgent", "asap", "immediately", "now",
            "sewage", "backup", "overflow", "gushing"
        ]
        
        urgent_keywords = [
            "leak", "leaking", "drip", "no water", "broken",
            "clogged", "backup", "slow drain"
        ]
        
        # Count emergency keywords
        emergency_count = sum(1 for keyword in emergency_keywords if keyword in message_lower)
        urgent_count = sum(1 for keyword in urgent_keywords if keyword in message_lower)
        
        # Determine urgency based on keyword matches
        if emergency_count > 0:
            confidence = min(0.8, emergency_count * 0.4)
            return UrgencyLevel.EMERGENCY, confidence
        elif urgent_count > 0:
            confidence = min(0.7, urgent_count * 0.3)
            return UrgencyLevel.URGENT, confidence
        else:
            return UrgencyLevel.NORMAL, 0.6
    
    def _validate_conversation_sid(self, sid: str) -> Dict[str, Any]:
        """Validate Twilio conversation SID format and uniqueness"""
        if len(sid) < 10:
            return {
                "valid": False,
                "errors": ["Conversation SID too short"]
            }
        
        # In a real implementation, check for duplicates in storage
        # For Phase 1, just validate format
        return {
            "valid": True,
            "format_valid": True,
            "duplicate": False  # Would check storage in real implementation
        }
    
    def _validate_phone_number(self, phone: str) -> Dict[str, Any]:
        """Additional phone number validation beyond Pydantic"""
        # Pydantic already validated format, so this is mostly for additional checks
        return {
            "valid": True,
            "format_valid": True,
            "international_format": phone.startswith('+')
        }
    
    def _validate_message_content(self, message: str) -> Dict[str, Any]:
        """Validate message content for safety and completeness"""
        errors = []
        warnings = []
        
        if not message or not message.strip():
            errors.append("Message cannot be empty")
        
        if len(message) > 1000:
            warnings.append("Message is very long, may be truncated")
        
        # Basic content validation
        message_clean = message.strip()
        if len(message_clean) < 3:
            errors.append("Message too short to process")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "character_count": len(message),
            "word_count": len(message.split()) if message else 0
        }
    
    def _validate_business_config(self, request: BasicDispatchRequest) -> Dict[str, Any]:
        """Validate business configuration settings"""
        errors = []
        warnings = []
        
        # Validate job estimates make sense
        if request.basic_job_estimate_min >= request.basic_job_estimate_max:
            errors.append("Minimum job estimate must be less than maximum")
        
        # Validate service radius
        if request.service_radius_miles > 50:
            warnings.append("Large service radius may result in long travel times")
        
        # Validate business name
        if len(request.business_name) < 3:
            errors.append("Business name too short")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _get_hours_message(self, within_hours: bool, start_time: time, end_time: time) -> str:
        """Generate user-friendly message about business hours"""
        if within_hours:
            return "Request received during business hours"
        else:
            return f"Request received outside business hours ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})"