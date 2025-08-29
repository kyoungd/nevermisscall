"""Test validation logic directly without service dependencies."""

import pytest
import re
from datetime import datetime, time


def test_phone_number_validation_logic():
    """Test phone number validation logic directly."""
    # E.164 format validation logic
    def validate_phone_number(phone_number: str) -> bool:
        if not phone_number:
            return False
        # E.164 format: +[country code][number] (1-15 digits after +)
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone_number))
    
    # Valid phone numbers
    assert validate_phone_number("+12125551234") is True
    assert validate_phone_number("+447700900000") is True
    assert validate_phone_number("+33123456789") is True
    
    # Invalid phone numbers
    assert validate_phone_number("") is False  # Empty
    assert validate_phone_number("12125551234") is False  # Missing +
    assert validate_phone_number("+1") is False  # Too short
    assert validate_phone_number("+123456789012345678") is False  # Too long
    assert validate_phone_number("+0123456789") is False  # Starts with 0


def test_message_content_validation_logic():
    """Test message content validation logic directly."""
    def validate_message_content(message: str) -> bool:
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
    
    # Valid messages
    assert validate_message_content("Hello, I need help with my plumbing") is True
    assert validate_message_content("Can you come tomorrow at 2 PM?") is True
    assert validate_message_content("My address is 123 Main St") is True
    assert validate_message_content("A" * 1600) is True  # Max length
    
    # Invalid messages
    assert validate_message_content("") is False  # Empty
    assert validate_message_content("A" * 1601) is False  # Too long
    assert validate_message_content("<script>alert('xss')</script>") is False  # Script tag
    assert validate_message_content("javascript:alert('xss')") is False  # JavaScript URL
    assert validate_message_content('<img onload="alert(1)">') is False  # Event handler


def test_business_hours_validation_logic():
    """Test business hours validation logic directly."""
    def validate_business_hours(business_hours: dict, check_time: datetime = None) -> dict:
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
            
        except (ValueError, KeyError):
            return {
                "withinHours": False,
                "reason": "invalid_hours_format",
            }
    
    business_hours = {
        'monday': {'start': '08:00', 'end': '17:00'},
        'tuesday': {'start': '08:00', 'end': '17:00'},
        'sunday': None,  # Closed on Sunday
    }
    
    # During business hours (Monday 10 AM)
    monday_10am = datetime(2024, 1, 1, 10, 0, 0)  # Monday
    result = validate_business_hours(business_hours, monday_10am)
    assert result['withinHours'] is True
    assert result['reason'] == 'within_hours'
    
    # Outside business hours (Monday 6 AM)
    monday_6am = datetime(2024, 1, 1, 6, 0, 0)  # Monday
    result = validate_business_hours(business_hours, monday_6am)
    assert result['withinHours'] is False
    assert result['reason'] == 'outside_hours'
    
    # Closed day (Sunday)
    sunday_10am = datetime(2024, 1, 7, 10, 0, 0)  # Sunday
    result = validate_business_hours(business_hours, sunday_10am)
    assert result['withinHours'] is False
    assert result['reason'] == 'closed_on_day'


def test_address_extraction_logic():
    """Test address extraction logic directly."""
    def extract_address_from_message(message: str) -> str:
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
    
    # Should extract addresses
    assert "123 Main Street" in extract_address_from_message("I live at 123 Main Street")
    assert "456 Oak Avenue" in extract_address_from_message("My address is 456 Oak Avenue, Los Angeles")
    assert "789 Pine Road" in extract_address_from_message("Come to 789 Pine Road please")
    
    # Should return None for no address
    assert extract_address_from_message("I need help with my plumbing") is None
    assert extract_address_from_message("Can you come tomorrow?") is None
    assert extract_address_from_message("Emergency repair needed") is None


def test_phone_extraction_logic():
    """Test phone number extraction logic directly."""
    def extract_phone_from_message(message: str) -> str:
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
    
    # Should extract phone numbers
    assert extract_phone_from_message("Call me at (555) 123-4567") == "+15551234567"
    assert extract_phone_from_message("My number is 555.123.4567") == "+15551234567"
    assert extract_phone_from_message("Contact 555-123-4567") == "+15551234567"
    
    # Should return None for no phone
    assert extract_phone_from_message("I need help with plumbing") is None
    assert extract_phone_from_message("Visit 123 Main St") is None


def test_conversation_limit_logic():
    """Test conversation limit validation logic directly."""
    def validate_conversation_limits(message_count: int, max_messages: int = 1000) -> dict:
        if message_count >= max_messages:
            return {
                "valid": False,
                "reason": "message_limit_exceeded",
                "messageCount": message_count,
                "limit": max_messages,
            }
        
        return {
            "valid": True,
            "messageCount": message_count,
            "limit": max_messages,
            "remainingMessages": max_messages - message_count,
        }
    
    # Within limits
    result = validate_conversation_limits(50, 1000)
    assert result['valid'] is True
    assert result['remainingMessages'] == 950
    
    # At limit
    result = validate_conversation_limits(1000, 1000)
    assert result['valid'] is False
    assert result['reason'] == 'message_limit_exceeded'
    
    # Over limit
    result = validate_conversation_limits(1001, 1000)
    assert result['valid'] is False


def test_urgency_level_mapping():
    """Test urgency level mapping logic."""
    def map_urgency_level(ai_urgency: str) -> str:
        mapping = {
            'emergency': 'emergency',
            'urgent': 'high',
            'high': 'high',
            'normal': 'normal',
            'low': 'low',
        }
        
        return mapping.get(ai_urgency.lower(), 'normal')
    
    # Test mappings
    assert map_urgency_level('emergency') == 'emergency'
    assert map_urgency_level('urgent') == 'high'
    assert map_urgency_level('high') == 'high'
    assert map_urgency_level('normal') == 'normal'
    assert map_urgency_level('low') == 'low'
    assert map_urgency_level('unknown') == 'normal'  # Default fallback