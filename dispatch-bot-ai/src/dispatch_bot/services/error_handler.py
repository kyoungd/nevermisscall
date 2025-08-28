"""
Comprehensive error handling service for fail-fast patterns.
Week 2, Day 4-5 implementation - graceful degradation and user-friendly responses.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

from dispatch_bot.models.basic_schemas import ConversationStage

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for classification"""
    LOW = "low"           # User input issues, retryable
    MEDIUM = "medium"     # Service issues, degraded functionality  
    HIGH = "high"         # API failures, major functionality loss
    CRITICAL = "critical" # System failures, requires immediate attention


class ErrorCategory(str, Enum):
    """Categories of errors for different handling strategies"""
    USER_INPUT = "user_input"
    VALIDATION = "validation"
    EXTERNAL_API = "external_api"
    NETWORK = "network"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


@dataclass
class ErrorClassification:
    """Result of error classification"""
    severity: ErrorSeverity
    category: ErrorCategory
    should_continue_conversation: bool
    should_escalate_to_human: bool
    retry_possible: bool


@dataclass
class ErrorResponse:
    """User-friendly error response"""
    user_message: str
    conversation_stage: ConversationStage
    recovery_options: List[str]
    should_escalate_to_human: bool = False
    technical_details: Optional[str] = None
    retry_possible: bool = False


class ErrorHandler:
    """
    Central error handling service implementing fail-fast patterns.
    
    Key principles:
    1. Fail fast with clear user messages
    2. Never expose technical details to users
    3. Provide recovery options when possible
    4. Track error patterns to prevent loops
    5. Escalate appropriately based on severity
    """
    
    def __init__(self):
        """Initialize error handler"""
        self.conversation_error_counts = defaultdict(lambda: defaultdict(int))
        self.error_templates = self._load_error_templates()
        self.classification_rules = self._load_classification_rules()
    
    def create_user_friendly_response(self, error_type: str, original_error: str, 
                                    context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
        """
        Create user-friendly error response from technical error.
        
        Args:
            error_type: Type of error (e.g., "address_not_found")
            original_error: Original technical error message
            context: Additional context (business info, etc.)
            
        Returns:
            ErrorResponse with user-friendly message
        """
        context = context or {}
        
        # Get error template
        template = self.error_templates.get(error_type, self.error_templates["generic"])
        
        # Generate user message with safe formatting
        user_message = template["message"]
        try:
            user_message = user_message.format(**context)
        except KeyError:
            # If context keys are missing, use message as-is
            pass
        
        # Generate recovery options with safe formatting
        recovery_options = []
        for option_template in template.get("recovery_options", []):
            try:
                recovery_options.append(option_template.format(**context))
            except KeyError:
                recovery_options.append(option_template)
        
        # Classify error
        classification = self.classify_error_severity(original_error)
        
        return ErrorResponse(
            user_message=user_message,
            conversation_stage=template["conversation_stage"],
            recovery_options=recovery_options,
            should_escalate_to_human=classification.should_escalate_to_human,
            technical_details=original_error if logger.isEnabledFor(logging.DEBUG) else None,
            retry_possible=classification.retry_possible
        )
    
    def classify_error_severity(self, error_message: str) -> ErrorClassification:
        """
        Classify error severity based on error message content.
        
        Args:
            error_message: Original error message
            
        Returns:
            ErrorClassification with severity and handling guidance
        """
        error_lower = error_message.lower()
        
        # Check classification rules
        for rule in self.classification_rules:
            if any(keyword in error_lower for keyword in rule["keywords"]):
                return ErrorClassification(
                    severity=ErrorSeverity(rule["severity"]),
                    category=ErrorCategory(rule["category"]),
                    should_continue_conversation=rule["continue_conversation"],
                    should_escalate_to_human=rule["escalate_to_human"],
                    retry_possible=rule["retry_possible"]
                )
        
        # Default classification
        return ErrorClassification(
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            should_continue_conversation=True,
            should_escalate_to_human=False,
            retry_possible=True
        )
    
    def handle_and_log_error(self, error_type: str, original_error: str,
                           conversation_sid: str, customer_phone: str,
                           severity: ErrorSeverity) -> None:
        """
        Handle error logging and monitoring.
        
        Args:
            error_type: Type of error for categorization
            original_error: Original error message
            conversation_sid: Conversation identifier
            customer_phone: Customer phone number
            severity: Error severity level
        """
        # Log with appropriate level based on severity
        log_message = (
            f"Error in conversation {conversation_sid}: "
            f"{error_type} - {original_error} "
            f"(Customer: {customer_phone})"
        )
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={
                "conversation_sid": conversation_sid,
                "customer_phone": customer_phone,
                "error_type": error_type,
                "severity": severity.value
            })
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={
                "conversation_sid": conversation_sid,
                "error_type": error_type,
                "severity": severity.value
            })
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={
                "conversation_sid": conversation_sid,
                "error_type": error_type
            })
        else:
            logger.info(log_message)
    
    def get_error_response_for_conversation(self, conversation_id: str, 
                                          error_type: str, error_message: str) -> ErrorResponse:
        """
        Get error response considering conversation history to prevent loops.
        
        Args:
            conversation_id: Conversation identifier
            error_type: Type of error
            error_message: Error message
            
        Returns:
            ErrorResponse with appropriate escalation
        """
        # Track error count for this conversation
        self.conversation_error_counts[conversation_id][error_type] += 1
        error_count = self.conversation_error_counts[conversation_id][error_type]
        
        # Progressive escalation based on repeated errors
        if error_count == 1:
            # First occurrence - full helpful message
            return self.create_user_friendly_response(error_type, error_message)
            
        elif error_count == 2:
            # Second occurrence - shorter, more direct message
            return self.create_user_friendly_response(
                f"{error_type}_repeated", 
                error_message
            )
            
        else:
            # Third+ occurrence - escalate to human
            return ErrorResponse(
                user_message="I'm having trouble helping you with this. Let me connect you with someone who can assist you directly. Please call our office.",
                conversation_stage=ConversationStage.COMPLETE,
                recovery_options=["Call our office for immediate assistance"],
                should_escalate_to_human=True,
                retry_possible=False
            )
    
    def clear_conversation_errors(self, conversation_id: str) -> None:
        """Clear error tracking for completed conversation"""
        if conversation_id in self.conversation_error_counts:
            del self.conversation_error_counts[conversation_id]
    
    def _load_error_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load user-friendly error message templates"""
        return {
            "address_not_found": {
                "message": "I couldn't find that address. Could you please provide a more complete address with street number, street name, city, and state?",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Try providing a more complete address",
                    "Include nearby cross streets or landmarks",
                    "Call our office at {business_phone} if you need immediate help"
                ]
            },
            "out_of_service_area": {
                "message": "I'm sorry, but that address appears to be outside our service area. We currently serve within {service_radius} miles of our location.",
                "conversation_stage": ConversationStage.COMPLETE,
                "recovery_options": [
                    "Call our office at {business_phone} to confirm service availability",
                    "We may be able to refer you to a partner in your area"
                ]
            },
            "api_unavailable": {
                "message": "I'm having trouble with our systems right now. For immediate assistance, please call our office directly.",
                "conversation_stage": ConversationStage.COMPLETE,
                "recovery_options": [
                    "Call {business_name} at {business_phone}",
                    "Try again in a few minutes"
                ]
            },
            "invalid_phone": {
                "message": "I need a valid phone number to help you. Please provide your number in this format: (555) 123-4567",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Include area code with your phone number",
                    "Use format: (555) 123-4567"
                ]
            },
            "timeout_warning": {
                "message": "I haven't heard from you in a while. I'll be available for about 1 more minute if you'd like to continue.",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Reply to continue our conversation",
                    "Call {business_phone} if you need immediate help"
                ]
            },
            "conversation_timeout": {
                "message": "Our conversation has timed out, but I'm here to help! Please start a new conversation or call us directly.",
                "conversation_stage": ConversationStage.TIMEOUT,
                "recovery_options": [
                    "Send a new message to start over",
                    "Call {business_name} at {business_phone}"
                ]
            },
            "address_not_found_repeated": {
                "message": "I'm still having trouble finding your address. Could you try calling our office?",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Call {business_phone} for address assistance"
                ]
            },
            "address_validation_failed_repeated": {
                "message": "Still having trouble with that address. Let's connect you with our office.",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Call for direct assistance"
                ]
            },
            "service_degraded": {
                "message": "Some of our systems are running slowly right now, but I can still help you with basic information. For full service, please call our office.",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Call {business_phone} for full service",
                    "Continue with limited assistance"
                ]
            },
            "generic": {
                "message": "I'm having a technical issue right now. Please call our office for immediate assistance.",
                "conversation_stage": ConversationStage.COMPLETE,
                "recovery_options": [
                    "Call our office for immediate help",
                    "Try again in a few minutes"
                ]
            },
            "address_validation_failed": {
                "message": "I'm having trouble validating that address. Could you double-check and provide your complete address with street number, street name, city, and state?",
                "conversation_stage": ConversationStage.COLLECTING_INFO,
                "recovery_options": [
                    "Provide complete address with street, city, state",
                    "Call our office if you need help with your address"
                ]
            }
        }
    
    def _load_classification_rules(self) -> List[Dict[str, Any]]:
        """Load error classification rules"""
        return [
            # User input errors - low severity
            {
                "keywords": ["phone number validation failed", "invalid format", "required field"],
                "severity": "low",
                "category": "user_input",
                "continue_conversation": True,
                "escalate_to_human": False,
                "retry_possible": True
            },
            # Address/geocoding errors - medium severity
            {
                "keywords": ["zero_results", "address not found", "geocoding", "service area"],
                "severity": "medium", 
                "category": "validation",
                "continue_conversation": True,
                "escalate_to_human": False,
                "retry_possible": True
            },
            # External API errors - high severity
            {
                "keywords": ["google maps api key invalid", "api key invalid", "request_denied", "quota exceeded", "rate limit"],
                "severity": "high",
                "category": "external_api", 
                "continue_conversation": False,
                "escalate_to_human": True,
                "retry_possible": False
            },
            # Network errors - medium severity
            {
                "keywords": ["timeout", "connection", "network", "unreachable"],
                "severity": "medium",
                "category": "network",
                "continue_conversation": True,
                "escalate_to_human": False,
                "retry_possible": True
            },
            # System errors - critical severity  
            {
                "keywords": ["database connection failed", "memory", "disk", "system", "internal server error"],
                "severity": "critical",
                "category": "system",
                "continue_conversation": False,
                "escalate_to_human": True,
                "retry_possible": False
            }
        ]


# Global error handler instance
error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    return error_handler