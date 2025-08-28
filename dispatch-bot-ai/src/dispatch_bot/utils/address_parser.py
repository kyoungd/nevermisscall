"""
Address parsing utilities for extracting addresses from customer messages.
Phase 1 implementation with basic regex and keyword detection.
"""

import re
from typing import Dict, Optional


def extract_address_from_message(message: str) -> Optional[str]:
    """
    Extract address from customer message using basic pattern matching.
    Phase 1 implementation - will be enhanced with NLP in later phases.
    
    Args:
        message: Customer message text
        
    Returns:
        Extracted address string or None if not found
    """
    if not message or not isinstance(message, str):
        return None
    
    message_lower = message.lower().strip()
    
    # Pattern for common address formats:
    # - Number + street name + street type
    # - May include apartment/suite info
    # - May include city, state, zip
    address_patterns = [
        # Full address with city/state/zip: "123 Main St, Los Angeles, CA 90210"
        r'\b\d+\s+[a-zA-Z\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|way|lane|ln|court|ct|circle|cir|place|pl)\b(?:\s*,?\s*(?:apt|apartment|suite|ste|unit|#)\s*\w+)?(?:\s*,\s*[a-zA-Z\s]+(?:\s*,\s*[a-zA-Z]{2}\s*\d{5}(?:-\d{4})?)?)?',
        
        # Basic address: "123 Main Street" or "456 Oak Ave"
        r'\b\d+\s+[a-zA-Z\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|way|lane|ln|court|ct|circle|cir|place|pl)\b(?:\s*,?\s*(?:apt|apartment|suite|ste|unit|#)\s*\w+)?',
        
        # Simple number + street: "123 Main St"
        r'\b\d+\s+[a-zA-Z]+\s+(?:st|ave|rd|dr|way|ln|blvd)\b',
    ]
    
    for pattern in address_patterns:
        matches = re.finditer(pattern, message_lower, re.IGNORECASE)
        for match in matches:
            # Get the matched address and clean it up
            address = match.group(0).strip()
            
            # Skip if it looks too short or invalid
            if len(address) < 8:
                continue
                
            # Skip if it doesn't have both number and street name
            if not re.search(r'\d+.*[a-zA-Z]', address):
                continue
                
            return _clean_address(address)
    
    return None


def extract_address_with_confidence(message: str) -> Dict[str, any]:
    """
    Extract address with confidence scoring.
    
    Args:
        message: Customer message text
        
    Returns:
        Dict with 'address', 'confidence' keys
    """
    address = extract_address_from_message(message)
    
    if not address:
        return {
            "address": None,
            "confidence": 0.0,
            "extraction_method": "none"
        }
    
    # Calculate confidence based on address completeness
    confidence = _calculate_address_confidence(address, message)
    
    return {
        "address": address,
        "confidence": confidence,
        "extraction_method": "regex_pattern"
    }


def _clean_address(raw_address: str) -> str:
    """
    Clean up extracted address string.
    
    Args:
        raw_address: Raw address string from regex
        
    Returns:
        Cleaned address string
    """
    # Basic cleanup
    address = raw_address.strip()
    
    # Convert to title case for better formatting
    words = address.split()
    cleaned_words = []
    
    for word in words:
        # Keep abbreviations uppercase, title case everything else
        if word.lower() in ['st', 'ave', 'rd', 'dr', 'ln', 'blvd', 'ct', 'pl', 'way']:
            cleaned_words.append(word.upper())
        elif word.lower() in ['apt', 'suite', 'ste', 'unit']:
            cleaned_words.append(word.title())
        elif word.startswith('#'):
            cleaned_words.append(word)
        else:
            cleaned_words.append(word.title())
    
    return ' '.join(cleaned_words)


def _calculate_address_confidence(address: str, original_message: str) -> float:
    """
    Calculate confidence score for extracted address.
    
    Args:
        address: Extracted address
        original_message: Original customer message
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    confidence = 0.0
    
    # Base confidence if we found an address
    confidence += 0.4
    
    # Bonus for having number + street name
    if re.search(r'\d+.*[a-zA-Z]', address):
        confidence += 0.2
    
    # Bonus for street type abbreviation
    if re.search(r'\b(st|street|ave|avenue|rd|road|dr|drive|blvd|boulevard|way|ln|lane)\b', address.lower()):
        confidence += 0.2
    
    # Bonus for apartment/suite info
    if re.search(r'\b(apt|apartment|suite|ste|unit|#)\b', address.lower()):
        confidence += 0.1
    
    # Bonus for city/state/zip pattern
    if re.search(r'[a-zA-Z\s]+,\s*[a-zA-Z]{2}\s*\d{5}', address):
        confidence += 0.2
    
    # Penalty if address seems too short
    if len(address) < 10:
        confidence -= 0.1
    
    # Bonus if message explicitly mentions address keywords
    address_keywords = ['address', 'located at', 'live at', 'house at', 'property at']
    for keyword in address_keywords:
        if keyword in original_message.lower():
            confidence += 0.1
            break
    
    # Ensure confidence is between 0 and 1
    return max(0.0, min(1.0, confidence))