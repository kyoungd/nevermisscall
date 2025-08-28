"""
Fallback service for graceful degradation when external APIs fail.
Week 2, Day 4-5 implementation - maintains service with reduced capability.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from dispatch_bot.models.geocoding_models import GeocodingResult, GeocodingStatus
from dispatch_bot.utils.address_parser import extract_address_with_confidence

logger = logging.getLogger(__name__)


@dataclass
class FallbackResult:
    """Result from fallback service operation"""
    success: bool
    fallback_used: bool
    confidence: float
    user_message: str
    data: Optional[Dict[str, Any]] = None
    approximate_validation: bool = False


class FallbackService:
    """
    Provides fallback functionality when external services fail.
    
    Key principles:
    1. Always provide some level of service
    2. Clearly communicate reduced capabilities 
    3. Lower confidence scores for fallback results
    4. Graceful degradation of features
    """
    
    def __init__(self):
        """Initialize fallback service"""
        self.job_type_keywords = self._load_job_type_keywords()
        self.city_coordinates = self._load_basic_city_coordinates()
        self.emergency_keywords = self._load_emergency_keywords()
    
    async def geocode_with_fallback(self, address: str, 
                                  primary_service=None) -> FallbackResult:
        """
        Attempt geocoding with fallback to basic address parsing.
        
        Args:
            address: Address to geocode
            primary_service: Primary geocoding service (may be failing)
            
        Returns:
            FallbackResult with geocoding information
        """
        # Try primary service first
        if primary_service:
            try:
                result = await primary_service.geocode_address(address)
                if result and result.success:
                    return FallbackResult(
                        success=True,
                        fallback_used=False,
                        confidence=result.confidence,
                        user_message="Address validated successfully.",
                        data={"latitude": result.latitude, "longitude": result.longitude}
                    )
            except Exception as e:
                logger.warning(f"Primary geocoding service failed: {e}")
        
        # Fallback to basic parsing and city-level coordinates
        logger.info(f"Using fallback geocoding for address: {address}")
        return await self._fallback_geocode(address)
    
    async def extract_intent_with_fallback(self, message: str,
                                         primary_service=None) -> FallbackResult:
        """
        Extract intent with fallback to keyword matching.
        
        Args:
            message: Customer message
            primary_service: Primary NLP service (may be failing)
            
        Returns:
            FallbackResult with extracted intent
        """
        # Try primary service first
        if primary_service:
            try:
                result = await primary_service.extract_intent(message)
                if result:
                    return FallbackResult(
                        success=True,
                        fallback_used=False,
                        confidence=result.confidence,
                        user_message="Message understood.",
                        data={
                            "job_type": result.job_type,
                            "urgency": result.urgency_level,
                            "address": result.customer_address
                        }
                    )
            except Exception as e:
                logger.warning(f"Primary NLP service failed: {e}")
        
        # Fallback to keyword-based extraction
        logger.info(f"Using fallback intent extraction for message: {message[:50]}...")
        return self._fallback_extract_intent(message)
    
    async def validate_service_area_with_fallback(self, geocoding_result,
                                                business_location: tuple,
                                                service_radius: float,
                                                distance_service=None) -> FallbackResult:
        """
        Validate service area with fallback to approximate validation.
        
        Args:
            geocoding_result: Result from geocoding
            business_location: Business lat/lng coordinates
            service_radius: Service radius in miles
            distance_service: Primary distance service (may be failing)
            
        Returns:
            FallbackResult with service area validation
        """
        # Try primary distance calculation
        if distance_service and hasattr(geocoding_result, 'latitude'):
            try:
                distance = await distance_service.calculate_distance(
                    business_location[0], business_location[1],
                    geocoding_result.latitude, geocoding_result.longitude
                )
                
                in_area = distance <= service_radius
                return FallbackResult(
                    success=True,
                    fallback_used=False,
                    confidence=0.9,
                    user_message="Service area validated." if in_area else "Address is outside our service area.",
                    data={"distance": distance, "in_service_area": in_area}
                )
            except Exception as e:
                logger.warning(f"Primary distance service failed: {e}")
        
        # Fallback to approximate validation
        return self._fallback_validate_service_area(geocoding_result, business_location, service_radius)
    
    def create_geocoding_fallback_response(self) -> FallbackResult:
        """Create standard geocoding fallback response"""
        return FallbackResult(
            success=True,
            fallback_used=True,
            confidence=0.4,
            user_message="I'm using basic address validation right now. Service may be limited, but I can still help you.",
            approximate_validation=True
        )
    
    def create_nlp_fallback_response(self) -> FallbackResult:
        """Create standard NLP fallback response"""
        return FallbackResult(
            success=True,
            fallback_used=True,
            confidence=0.5,
            user_message="I'm using basic message processing right now. Please be specific about your plumbing issue and address.",
            approximate_validation=True
        )
    
    def create_scheduling_fallback_response(self) -> FallbackResult:
        """Create standard scheduling fallback response"""
        return FallbackResult(
            success=True,
            fallback_used=True,
            confidence=0.3,
            user_message="Our scheduling system is running with reduced functionality. Please call our office for the most accurate scheduling.",
            approximate_validation=True
        )
    
    async def _fallback_geocode(self, address: str) -> FallbackResult:
        """
        Fallback geocoding using basic city/state parsing.
        
        Args:
            address: Address to geocode
            
        Returns:
            FallbackResult with basic geocoding
        """
        # Extract city and state from address
        city_state = self._extract_city_state(address)
        
        if city_state:
            city, state = city_state
            coordinates = self.city_coordinates.get(f"{city.lower()}, {state.lower()}")
            
            if coordinates:
                return FallbackResult(
                    success=True,
                    fallback_used=True,
                    confidence=0.4,  # Lower confidence for city-level
                    user_message="I found your general area but with limited precision. Service availability will be confirmed when we contact you.",
                    data={"latitude": coordinates[0], "longitude": coordinates[1]},
                    approximate_validation=True
                )
        
        # Could not geocode at all
        return FallbackResult(
            success=False,
            fallback_used=True,
            confidence=0.0,
            user_message="I'm having trouble finding your address. Please call our office with your complete address for assistance."
        )
    
    def _fallback_extract_intent(self, message: str) -> FallbackResult:
        """
        Fallback intent extraction using keyword matching.
        
        Args:
            message: Customer message
            
        Returns:
            FallbackResult with extracted intent
        """
        message_lower = message.lower()
        
        # Extract job type using keywords
        job_type = "general_plumbing"  # Default
        for job, keywords in self.job_type_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                job_type = job
                break
        
        # Check for emergency keywords
        urgency = "normal"
        if any(keyword in message_lower for keyword in self.emergency_keywords):
            urgency = "urgent"
        
        # Extract address using existing parser
        address_info = extract_address_with_confidence(message)
        
        return FallbackResult(
            success=True,
            fallback_used=True,
            confidence=0.6,
            user_message="I understand you need help with plumbing. I'm using basic processing, so please be specific about your issue and address.",
            data={
                "job_type": job_type,
                "urgency": urgency,
                "address": address_info["address"],
                "address_confidence": address_info["confidence"]
            }
        )
    
    def _fallback_validate_service_area(self, geocoding_result, business_location: tuple, 
                                      service_radius: float) -> FallbackResult:
        """
        Fallback service area validation using approximate distance.
        
        Args:
            geocoding_result: Geocoding result (may be approximate)
            business_location: Business coordinates
            service_radius: Service radius in miles
            
        Returns:
            FallbackResult with approximate validation
        """
        if not hasattr(geocoding_result, 'latitude') or not geocoding_result.latitude:
            return FallbackResult(
                success=False,
                fallback_used=True,
                confidence=0.0,
                user_message="I cannot validate your service area right now. Please call our office to confirm we serve your area.",
                approximate_validation=True
            )
        
        # Simple distance approximation (1 degree ≈ 69 miles)
        lat_diff = abs(geocoding_result.latitude - business_location[0])
        lng_diff = abs(geocoding_result.longitude - business_location[1])
        
        # Rough distance approximation
        approx_distance = ((lat_diff ** 2) + (lng_diff ** 2)) ** 0.5 * 69
        
        in_area = approx_distance <= service_radius * 1.2  # Add 20% margin for approximation
        
        return FallbackResult(
            success=True,
            fallback_used=True,
            confidence=0.6,
            user_message="I've done an approximate check of your service area. We'll confirm exact service availability when we contact you." if in_area else "Your address appears to be outside our service area, but we'll double-check when you call.",
            data={"approximate_distance": approx_distance, "in_service_area": in_area},
            approximate_validation=True
        )
    
    def _extract_city_state(self, address: str) -> Optional[tuple]:
        """
        Extract city and state from address string.
        
        Args:
            address: Full address string
            
        Returns:
            (city, state) tuple or None
        """
        # Pattern for city, state (with optional zip)
        pattern = r'([A-Za-z\s]+),\s*([A-Z]{2})(?:\s+\d{5})?'
        match = re.search(pattern, address)
        
        if match:
            city = match.group(1).strip()
            state = match.group(2).strip()
            return (city, state)
        
        return None
    
    def _load_job_type_keywords(self) -> Dict[str, List[str]]:
        """Load job type keywords for fallback classification"""
        return {
            "faucet_repair": ["faucet", "tap", "spigot", "sink drip", "dripping"],
            "toilet_repair": ["toilet", "bathroom", "flush", "tank", "bowl"],
            "drain_cleaning": ["drain", "clog", "blocked", "slow drain", "backup"],
            "pipe_repair": ["pipe", "burst", "leak", "broken pipe", "water damage"],
            "water_heater": ["water heater", "hot water", "no hot water", "heater"],
            "garbage_disposal": ["disposal", "garbage disposal", "grinder", "kitchen sink"]
        }
    
    def _load_basic_city_coordinates(self) -> Dict[str, tuple]:
        """Load basic city coordinates for major cities"""
        return {
            "los angeles, ca": (34.0522, -118.2437),
            "san francisco, ca": (37.7749, -122.4194),
            "new york, ny": (40.7128, -74.0060),
            "chicago, il": (41.8781, -87.6298),
            "houston, tx": (29.7604, -95.3698),
            "phoenix, az": (33.4484, -112.0740),
            "philadelphia, pa": (39.9526, -75.1652),
            "san antonio, tx": (29.4241, -98.4936),
            "san diego, ca": (32.7157, -117.1611),
            "dallas, tx": (32.7767, -96.7970),
            "austin, tx": (30.2672, -97.7431),
            "jacksonville, fl": (30.3322, -81.6557),
            "fort worth, tx": (32.7555, -97.3308),
            "columbus, oh": (39.9612, -82.9988),
            "charlotte, nc": (35.2271, -80.8431),
            "seattle, wa": (47.6062, -122.3321),
            "denver, co": (39.7392, -104.9903),
            "boston, ma": (42.3601, -71.0589),
            "el paso, tx": (31.7619, -106.4850),
            "detroit, mi": (42.3314, -83.0458),
            "nashville, tn": (36.1627, -86.7816),
            "portland, or": (45.5152, -122.6784),
            "memphis, tn": (35.1495, -90.0490),
            "oklahoma city, ok": (35.4676, -97.5164),
            "las vegas, nv": (36.1699, -115.1398),
            "louisville, ky": (38.2527, -85.7585),
            "baltimore, md": (39.2904, -76.6122),
            "milwaukee, wi": (43.0389, -87.9065),
            "albuquerque, nm": (35.0844, -106.6504),
            "tucson, az": (32.2226, -110.9747),
            "fresno, ca": (36.7378, -119.7871),
            "mesa, az": (33.4152, -111.8315),
            "sacramento, ca": (38.5816, -121.4944),
            "atlanta, ga": (33.7490, -84.3880),
            "kansas city, mo": (39.0997, -94.5786),
            "colorado springs, co": (38.8339, -104.8214),
            "omaha, ne": (41.2565, -95.9345),
            "raleigh, nc": (35.7796, -78.6382),
            "miami, fl": (25.7617, -80.1918),
            "cleveland, oh": (41.4993, -81.6944),
            "tulsa, ok": (36.1540, -95.9928),
            "minneapolis, mn": (44.9778, -93.2650),
            "wichita, ks": (37.6872, -97.3301),
            "arlington, tx": (32.7357, -97.1081)
        }
    
    def _load_emergency_keywords(self) -> List[str]:
        """Load emergency keywords for urgency detection"""
        return [
            "emergency", "urgent", "asap", "immediately", "now", "help",
            "flooding", "flood", "burst", "leak", "water everywhere",
            "no water", "sewage", "backup", "overflow", "gushing"
        ]


# Global fallback service instance
fallback_service = FallbackService()


def get_fallback_service() -> FallbackService:
    """Get the global fallback service instance"""
    return fallback_service