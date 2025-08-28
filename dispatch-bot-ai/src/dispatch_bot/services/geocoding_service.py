"""
Google Maps Geocoding Service for Phase 1 implementation.
Handles address geocoding and service area validation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import httpx

from dispatch_bot.models.geocoding_models import (
    GeocodingResult, GeocodingStatus, ServiceAreaResult
)

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Google Maps Geocoding API client for Phase 1.
    
    Provides geocoding of addresses to lat/lng coordinates with confidence scoring.
    Uses real Google Maps API calls as specified in CLAUDE.md.
    """
    
    def __init__(self, api_key: str, timeout_seconds: int = 10):
        """
        Initialize geocoding service.
        
        Args:
            api_key: Google Maps API key
            timeout_seconds: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def geocode_address(self, address: str) -> Optional[GeocodingResult]:
        """
        Geocode an address using Google Maps API.
        
        Args:
            address: Address string to geocode
            
        Returns:
            GeocodingResult or None if geocoding fails
        """
        if not address or not address.strip():
            logger.warning("Empty address provided for geocoding")
            return GeocodingResult.failed_result(
                "Empty address provided", 
                GeocodingStatus.INVALID_REQUEST
            )
        
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return GeocodingResult.failed_result(
                "Google Maps API key not configured",
                GeocodingStatus.REQUEST_DENIED
            )
        
        try:
            params = {
                "address": address.strip(),
                "key": self.api_key
            }
            
            logger.debug(f"Geocoding address: {address}")
            
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Create result from Google response
            result = GeocodingResult.from_google_response(data)
            
            if result.success:
                logger.info(
                    f"Successfully geocoded '{address}' to "
                    f"({result.latitude}, {result.longitude}) "
                    f"with confidence {result.confidence:.2f}"
                )
            else:
                logger.warning(
                    f"Geocoding failed for '{address}': {result.error_message}"
                )
            
            return result
            
        except httpx.TimeoutException:
            logger.error(f"Geocoding request timed out for address: {address}")
            return GeocodingResult.failed_result(
                f"Request timed out after {self.timeout_seconds} seconds",
                GeocodingStatus.UNKNOWN_ERROR
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during geocoding: {e.response.status_code}")
            return GeocodingResult.failed_result(
                f"HTTP error: {e.response.status_code}",
                GeocodingStatus.UNKNOWN_ERROR
            )
            
        except httpx.RequestError as e:
            logger.error(f"Network error during geocoding: {str(e)}")
            return GeocodingResult.failed_result(
                f"Network error: {str(e)}",
                GeocodingStatus.UNKNOWN_ERROR
            )
            
        except ValueError as e:
            logger.error(f"Invalid JSON response from Google Maps API: {str(e)}")
            return GeocodingResult.failed_result(
                "Invalid response from geocoding service",
                GeocodingStatus.UNKNOWN_ERROR
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {str(e)}", exc_info=True)
            return GeocodingResult.failed_result(
                f"Unexpected error: {str(e)}",
                GeocodingStatus.UNKNOWN_ERROR
            )
    
    async def batch_geocode_addresses(self, addresses: list[str]) -> Dict[str, Optional[GeocodingResult]]:
        """
        Geocode multiple addresses concurrently.
        
        Args:
            addresses: List of address strings
            
        Returns:
            Dict mapping addresses to their geocoding results
        """
        if not addresses:
            return {}
        
        logger.info(f"Starting batch geocoding of {len(addresses)} addresses")
        
        # Create concurrent tasks for all addresses
        tasks = [
            self.geocode_address(address) 
            for address in addresses
        ]
        
        # Execute all geocoding requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        geocoding_results = {}
        for address, result in zip(addresses, results):
            if isinstance(result, Exception):
                logger.error(f"Exception during geocoding of '{address}': {result}")
                geocoding_results[address] = GeocodingResult.failed_result(
                    f"Exception: {str(result)}",
                    GeocodingStatus.UNKNOWN_ERROR
                )
            else:
                geocoding_results[address] = result
        
        successful_count = sum(
            1 for result in geocoding_results.values() 
            if result and result.success
        )
        
        logger.info(
            f"Batch geocoding completed: {successful_count}/{len(addresses)} successful"
        )
        
        return geocoding_results
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class ServiceAreaValidator:
    """
    Service area validation using geocoding and distance calculation.
    Phase 1 implementation for basic service area checking.
    """
    
    def __init__(self, geocoding_service: GeocodingService, 
                 business_lat: float, business_lng: float):
        """
        Initialize service area validator.
        
        Args:
            geocoding_service: Geocoding service to use
            business_lat: Business location latitude
            business_lng: Business location longitude
        """
        self.geocoding_service = geocoding_service
        self.business_lat = business_lat
        self.business_lng = business_lng
    
    async def validate_service_area(self, address: str, 
                                  service_radius_miles: float) -> Optional[ServiceAreaResult]:
        """
        Validate if an address is within the service area.
        
        Args:
            address: Customer address to validate
            service_radius_miles: Service radius in miles
            
        Returns:
            ServiceAreaResult with validation results
        """
        if service_radius_miles < 0:
            logger.warning(f"Invalid service radius: {service_radius_miles}")
            return ServiceAreaResult(
                address=address,
                geocoding_success=False,
                business_latitude=self.business_lat,
                business_longitude=self.business_lng,
                error_message="Invalid service radius (must be >= 0)"
            )
        
        # First, geocode the address
        geocoding_result = await self.geocoding_service.geocode_address(address)
        
        if not geocoding_result:
            logger.warning(f"Geocoding returned None for address: {address}")
            return ServiceAreaResult(
                address=address,
                geocoding_success=False,
                business_latitude=self.business_lat,
                business_longitude=self.business_lng,
                error_message="Geocoding service returned no result"
            )
        
        # Create service area result from geocoding result
        result = ServiceAreaResult.from_geocoding_result(
            address=address,
            geocoding_result=geocoding_result,
            business_lat=self.business_lat,
            business_lng=self.business_lng,
            service_radius_miles=service_radius_miles
        )
        
        if result.geocoding_success and result.in_service_area:
            logger.info(
                f"Address '{address}' is IN service area "
                f"({result.distance_miles:.1f} miles, limit: {service_radius_miles} miles)"
            )
        elif result.geocoding_success:
            logger.info(
                f"Address '{address}' is OUTSIDE service area "
                f"({result.distance_miles:.1f} miles, limit: {service_radius_miles} miles)"
            )
        
        return result
    
    async def batch_validate_service_area(self, addresses: list[str], 
                                        service_radius_miles: float) -> Dict[str, Optional[ServiceAreaResult]]:
        """
        Validate multiple addresses for service area inclusion.
        
        Args:
            addresses: List of addresses to validate
            service_radius_miles: Service radius in miles
            
        Returns:
            Dict mapping addresses to their service area results
        """
        if not addresses:
            return {}
        
        logger.info(f"Batch validating {len(addresses)} addresses for service area")
        
        # Batch geocode all addresses first
        geocoding_results = await self.geocoding_service.batch_geocode_addresses(addresses)
        
        # Create service area results for each
        service_area_results = {}
        for address in addresses:
            geocoding_result = geocoding_results.get(address)
            
            if not geocoding_result:
                service_area_results[address] = ServiceAreaResult(
                    address=address,
                    geocoding_success=False,
                    business_latitude=self.business_lat,
                    business_longitude=self.business_lng,
                    error_message="No geocoding result available"
                )
            else:
                service_area_results[address] = ServiceAreaResult.from_geocoding_result(
                    address=address,
                    geocoding_result=geocoding_result,
                    business_lat=self.business_lat,
                    business_lng=self.business_lng,
                    service_radius_miles=service_radius_miles
                )
        
        in_area_count = sum(
            1 for result in service_area_results.values()
            if result and result.in_service_area
        )
        
        logger.info(
            f"Batch service area validation completed: "
            f"{in_area_count}/{len(addresses)} addresses in service area"
        )
        
        return service_area_results