"""
Validation functions for NeverMissCall shared library.

Provides common validation utilities following the patterns
defined in shared.md documentation.
"""

import re
import uuid
from typing import Any, Dict, List
from ..models.exceptions import ValidationError


def validate_required(value: Any, field_name: str) -> None:
    """
    Validate that a required field has a value.
    
    Args:
        value: Value to check
        field_name: Name of the field for error messages
        
    Raises:
        ValidationError: If value is None, empty string, or empty collection
    """
    if value is None:
        raise ValidationError(f"{field_name} is required", field=field_name)
    
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)
    
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    
    Supports E.164 format and common US phone number formats.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone format is valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # E.164 format (international)
    if phone.startswith('+'):
        return len(digits_only) >= 10 and len(digits_only) <= 15
    
    # US phone number (10 or 11 digits)
    if len(digits_only) == 10:
        return True
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return True
    
    return False


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: UUID string to validate
        
    Returns:
        True if UUID format is valid, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def validate_password(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Password requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if not password or not isinstance(password, str):
        errors.append("Password is required")
        return {'valid': False, 'errors': errors}
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def validate_tenant_id(tenant_id: str) -> None:
    """
    Validate tenant ID format and requirement.
    
    Args:
        tenant_id: Tenant ID to validate
        
    Raises:
        ValidationError: If tenant ID is invalid
    """
    validate_required(tenant_id, 'tenant_id')
    
    if not validate_uuid(tenant_id):
        raise ValidationError("tenant_id must be a valid UUID", field='tenant_id')


def validate_user_id(user_id: str) -> None:
    """
    Validate user ID format and requirement.
    
    Args:
        user_id: User ID to validate
        
    Raises:
        ValidationError: If user ID is invalid
    """
    validate_required(user_id, 'user_id')
    
    if not validate_uuid(user_id):
        raise ValidationError("user_id must be a valid UUID", field='user_id')


def validate_phone_number_required(phone: str, field_name: str = 'phone_number') -> None:
    """
    Validate required phone number.
    
    Args:
        phone: Phone number to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If phone number is invalid or missing
    """
    validate_required(phone, field_name)
    
    if not validate_phone_number(phone):
        raise ValidationError(f"{field_name} must be a valid phone number", field=field_name)


def validate_email_required(email: str, field_name: str = 'email') -> None:
    """
    Validate required email address.
    
    Args:
        email: Email address to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If email is invalid or missing
    """
    validate_required(email, field_name)
    
    if not validate_email(email):
        raise ValidationError(f"{field_name} must be a valid email address", field=field_name)


def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: int = None) -> None:
    """
    Validate string length constraints.
    
    Args:
        value: String value to validate
        field_name: Field name for error messages
        min_length: Minimum length (default 0)
        max_length: Maximum length (optional)
        
    Raises:
        ValidationError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    length = len(value)
    
    if length < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long", field=field_name)
    
    if max_length is not None and length > max_length:
        raise ValidationError(f"{field_name} must be no more than {max_length} characters long", field=field_name)


def validate_choice(value: Any, field_name: str, choices: List[Any]) -> None:
    """
    Validate that value is one of allowed choices.
    
    Args:
        value: Value to validate
        field_name: Field name for error messages
        choices: List of allowed values
        
    Raises:
        ValidationError: If value is not in choices
    """
    if value not in choices:
        choices_str = ', '.join(str(choice) for choice in choices)
        raise ValidationError(f"{field_name} must be one of: {choices_str}", field=field_name)


def validate_positive_integer(value: Any, field_name: str) -> None:
    """
    Validate that value is a positive integer.
    
    Args:
        value: Value to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If value is not a positive integer
    """
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer", field=field_name)


def validate_non_negative_integer(value: Any, field_name: str) -> None:
    """
    Validate that value is a non-negative integer (>= 0).
    
    Args:
        value: Value to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If value is not a non-negative integer
    """
    if not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer", field=field_name)


def validate_decimal_places(value: Any, field_name: str, max_places: int) -> None:
    """
    Validate decimal places in a number.
    
    Args:
        value: Numeric value to validate
        field_name: Field name for error messages
        max_places: Maximum number of decimal places
        
    Raises:
        ValidationError: If value has too many decimal places
    """
    if isinstance(value, (int, float)):
        # Convert to string and check decimal places
        value_str = str(value)
        if '.' in value_str:
            decimal_places = len(value_str.split('.')[1])
            if decimal_places > max_places:
                raise ValidationError(f"{field_name} can have at most {max_places} decimal places", field=field_name)


def validate_business_hours(hours: Dict[str, Any]) -> None:
    """
    Validate business hours format.
    
    Args:
        hours: Business hours dictionary
        
    Raises:
        ValidationError: If business hours format is invalid
    """
    if not isinstance(hours, dict):
        raise ValidationError("business_hours must be a dictionary", field='business_hours')
    
    required_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in required_days:
        if day not in hours:
            raise ValidationError(f"business_hours missing {day}", field='business_hours')
        
        day_config = hours[day]
        if not isinstance(day_config, dict):
            raise ValidationError(f"business_hours {day} must be a dictionary", field='business_hours')
        
        required_fields = ['open', 'close', 'enabled']
        for field in required_fields:
            if field not in day_config:
                raise ValidationError(f"business_hours {day} missing {field}", field='business_hours')
        
        if day_config['enabled'] and (not day_config['open'] or not day_config['close']):
            raise ValidationError(f"business_hours {day} must have open and close times when enabled", field='business_hours')


def validate_timezone(timezone: str) -> None:
    """
    Validate timezone string.
    
    Args:
        timezone: Timezone string to validate
        
    Raises:
        ValidationError: If timezone is invalid
    """
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(timezone)
    except:
        try:
            import pytz
            pytz.timezone(timezone)
        except:
            raise ValidationError("Invalid timezone", field='timezone')