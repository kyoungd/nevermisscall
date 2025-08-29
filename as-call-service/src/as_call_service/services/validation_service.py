"""Validation service for business rules and data validation."""

import re
from typing import Dict, Any, Optional
from uuid import UUID

from ..utils import (
    logger,
    service_client,
    validateRequired,
    ValidationError,
    ServiceError,
)
from ..config import settings


class ValidationService:
    """Service class for validation operations."""
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format (E.164)."""
        if not phone_number:
            return False
        
        # E.164 format: +[country code][number] (1-15 digits after +)
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone_number))
    
    def validate_message_content(self, message: str) -> bool:
        """Validate message content length and format."""
        if not message:
            return False
        
        # SMS length limit
        if len(message) > 1600:
            return False
        
        # Basic content validation (no malicious patterns)
        suspicious_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',    # Event handlers
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        return True
    
    async def validate_tenant_exists(self, tenant_id: UUID) -> Dict[str, Any]:
        """Validate that tenant exists and is active."""
        try:
            validateRequired(tenant_id, "tenant_id")
            
            tenant_validation = await service_client.validate_tenant_and_service_area(
                str(tenant_id)
            )
            
            if not tenant_validation.get('exists', False):
                raise ValidationError(f"Tenant {tenant_id} does not exist")
            
            if not tenant_validation.get('active', True):
                raise ValidationError(f"Tenant {tenant_id} is not active")
            
            logger.info("Tenant validation successful", tenant_id=str(tenant_id))
            return tenant_validation
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Tenant validation failed",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise ServiceError(f"Failed to validate tenant: {str(e)}")
    
    async def validate_service_area(
        self, 
        tenant_id: UUID, 
        customer_address: str
    ) -> Dict[str, Any]:
        """Validate customer address is within service area."""
        if not settings.service_area_validation_enabled:
            logger.info("Service area validation disabled")
            return {
                "valid": True,
                "reason": "validation_disabled",
                "withinServiceArea": True,
                "addressValidated": False,
            }
        
        try:
            validateRequired(tenant_id, "tenant_id")
            validateRequired(customer_address, "customer_address")
            
            validation_result = await service_client.validate_tenant_and_service_area(
                str(tenant_id),
                customer_address
            )
            
            service_area_valid = validation_result.get('serviceAreaValid', False)
            address_validated = validation_result.get('addressValidated', False)
            
            if not address_validated:
                logger.warning(
                    "Address could not be validated",
                    tenant_id=str(tenant_id),
                    address=customer_address
                )
                return {
                    "valid": False,
                    "reason": "address_validation_failed",
                    "withinServiceArea": False,
                    "addressValidated": False,
                }
            
            if not service_area_valid:
                logger.info(
                    "Address outside service area",
                    tenant_id=str(tenant_id),
                    address=customer_address
                )
                return {
                    "valid": False,
                    "reason": "outside_service_area",
                    "withinServiceArea": False,
                    "addressValidated": True,
                }
            
            logger.info(
                "Service area validation successful",
                tenant_id=str(tenant_id),
                address=customer_address
            )
            
            return {
                "valid": True,
                "reason": "within_service_area",
                "withinServiceArea": True,
                "addressValidated": True,
                "distanceFromBusiness": validation_result.get('distanceMiles'),
                "travelTimeMinutes": validation_result.get('travelTimeMinutes'),
            }
            
        except Exception as e:
            logger.error(
                "Service area validation failed",
                tenant_id=str(tenant_id),
                address=customer_address,
                error=str(e)
            )
            # Don't fail the entire process for service area validation
            return {
                "valid": True,  # Default to valid when validation fails
                "reason": "validation_error",
                "withinServiceArea": True,
                "addressValidated": False,
                "error": str(e),
            }
    
    def validate_business_hours(
        self, 
        business_hours: Dict[str, Any], 
        check_time: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Validate if current time is within business hours."""
        from datetime import datetime, time
        
        if check_time is None:
            check_time = datetime.now()
        
        current_day = check_time.strftime('%A').lower()
        current_time = check_time.time()
        
        day_hours = business_hours.get(current_day)
        
        if not day_hours:
            # Business closed on this day
            return {
                "withinHours": False,
                "reason": "closed_on_day",
                "currentDay": current_day,
                "currentTime": current_time.strftime('%H:%M'),
            }
        
        try:
            start_time = time.fromisoformat(day_hours['start'])
            end_time = time.fromisoformat(day_hours['end'])
            
            within_hours = start_time <= current_time <= end_time
            
            return {
                "withinHours": within_hours,
                "reason": "within_hours" if within_hours else "outside_hours",
                "currentDay": current_day,
                "currentTime": current_time.strftime('%H:%M'),
                "businessStart": day_hours['start'],
                "businessEnd": day_hours['end'],
            }
            
        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid business hours format",
                business_hours=business_hours,
                error=str(e)
            )
            return {
                "withinHours": False,
                "reason": "invalid_hours_format",
                "error": str(e),
            }
    
    async def validate_conversation_limits(
        self, 
        tenant_id: UUID, 
        conversation_id: UUID
    ) -> Dict[str, Any]:
        """Validate conversation message limits."""
        try:
            from ..utils import query
            
            # Check message count for conversation
            result = await query(
                "SELECT message_count FROM conversations WHERE id = $1 AND tenant_id = $2",
                [conversation_id, tenant_id]
            )
            
            if not result:
                raise ValidationError("Conversation not found")
            
            message_count = result[0]['message_count']
            
            if message_count >= settings.max_conversation_messages:
                logger.warning(
                    "Conversation message limit exceeded",
                    conversation_id=str(conversation_id),
                    message_count=message_count,
                    limit=settings.max_conversation_messages
                )
                return {
                    "valid": False,
                    "reason": "message_limit_exceeded",
                    "messageCount": message_count,
                    "limit": settings.max_conversation_messages,
                }
            
            return {
                "valid": True,
                "messageCount": message_count,
                "limit": settings.max_conversation_messages,
                "remainingMessages": settings.max_conversation_messages - message_count,
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to validate conversation limits",
                conversation_id=str(conversation_id),
                error=str(e)
            )
            raise ServiceError(f"Failed to validate conversation limits: {str(e)}")
    
    def extract_address_from_message(self, message: str) -> Optional[str]:
        """Extract potential address from message content."""
        # Common address patterns
        patterns = [
            # Street address with number
            r'\b\d+\s+[A-Za-z\s]+(street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|circle|cir|court|ct|place|pl)\b',
            # Address with zip code
            r'\b\d+\s+[A-Za-z\s]+,?\s*[A-Za-z\s]*\s+\d{5}(-\d{4})?\b',
            # General address pattern
            r'\b\d+\s+[A-Za-z\s]{2,50}\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # Clean up the extracted address
                address = match.group().strip()
                # Basic validation - must have number and letters
                if re.search(r'\d+', address) and re.search(r'[A-Za-z]{2,}', address):
                    return address
        
        return None
    
    def extract_phone_from_message(self, message: str) -> Optional[str]:
        """Extract phone number from message content."""
        # Phone number patterns
        patterns = [
            r'\+1[-\s]?\(?(\d{3})\)?[-\s]?(\d{3})[-\s]?(\d{4})',  # +1 (555) 123-4567
            r'\(?(\d{3})\)?[-\s]?(\d{3})[-\s]?(\d{4})',  # (555) 123-4567
            r'(\d{3})[-\.](\d{3})[-\.](\d{4})',  # 555.123.4567
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                # Normalize to E.164 format
                if pattern.startswith(r'\+1'):
                    # Already has country code
                    digits = re.sub(r'\D', '', match.group())
                    return f"+{digits}"
                else:
                    # Add US country code
                    digits = re.sub(r'\D', '', match.group())
                    if len(digits) == 10:
                        return f"+1{digits}"
        
        return None


# Global service instance
validation_service = ValidationService()