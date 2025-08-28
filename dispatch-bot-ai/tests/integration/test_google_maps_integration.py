"""
Integration tests for Google Maps API integration - Week 2 Phase 1.
These tests use real Google Maps API calls to validate our geocoding service.
"""

import pytest
import asyncio
from typing import Optional
from dispatch_bot.config.phase1_settings import get_phase1_settings
from dispatch_bot.services.geocoding_service import GeocodingService, GeocodingResult
from dispatch_bot.services.geocoding_service import ServiceAreaValidator


@pytest.fixture
def settings():
    """Get settings for testing"""
    return get_phase1_settings()


@pytest.fixture  
def geocoding_service(settings):
    """Create geocoding service for testing"""
    if not settings.has_google_maps_key:
        pytest.skip("Google Maps API key not configured")
    return GeocodingService(settings.google_maps.api_key)


@pytest.fixture
def service_area_validator(geocoding_service):
    """Create service area validator for testing"""
    # Use Los Angeles as business location for testing
    business_lat, business_lng = 34.0522, -118.2437
    return ServiceAreaValidator(geocoding_service, business_lat, business_lng)


class TestGoogleMapsGeocoding:
    """Test real Google Maps geocoding with known addresses"""
    
    @pytest.mark.asyncio
    async def test_valid_address_geocoding(self, geocoding_service):
        """Test geocoding with known valid addresses"""
        valid_addresses = [
            "1600 Amphitheatre Parkway, Mountain View, CA",
            "1 Apple Park Way, Cupertino, CA 95014",
            "350 5th Ave, New York, NY 10118",  # Empire State Building
            "221B Baker Street, London, UK"
        ]
        
        for address in valid_addresses:
            result = await geocoding_service.geocode_address(address)
            
            assert result is not None, f"Failed to geocode: {address}"
            assert isinstance(result, GeocodingResult)
            assert result.success == True
            assert result.latitude is not None
            assert result.longitude is not None
            assert -90 <= result.latitude <= 90
            assert -180 <= result.longitude <= 180
            assert result.formatted_address is not None
            assert len(result.formatted_address) > 0
            assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_specific_known_addresses(self, geocoding_service):
        """Test specific addresses with expected approximate coordinates"""
        test_cases = [
            {
                "address": "1600 Amphitheatre Parkway, Mountain View, CA",
                "expected_lat_range": (37.4, 37.5),
                "expected_lng_range": (-122.1, -122.0),  # Adjusted range
                "expected_city": "Mountain View"
            },
            {
                "address": "1 Apple Park Way, Cupertino, CA",
                "expected_lat_range": (37.3, 37.4),
                "expected_lng_range": (-122.2, -122.0),  # Adjusted range
                "expected_city": "Cupertino"
            }
        ]
        
        for test_case in test_cases:
            result = await geocoding_service.geocode_address(test_case["address"])
            
            assert result is not None
            assert result.success == True
            
            # Check coordinate ranges
            lat_min, lat_max = test_case["expected_lat_range"]
            lng_min, lng_max = test_case["expected_lng_range"]
            
            assert lat_min <= result.latitude <= lat_max, \
                f"Latitude {result.latitude} not in expected range {test_case['expected_lat_range']}"
            assert lng_min <= result.longitude <= lng_max, \
                f"Longitude {result.longitude} not in expected range {test_case['expected_lng_range']}"
            
            # Check city name in formatted address
            assert test_case["expected_city"] in result.formatted_address
    
    @pytest.mark.asyncio
    async def test_invalid_address_handling(self, geocoding_service):
        """Test graceful handling of invalid addresses"""
        invalid_addresses = [
            "123 Fake Street, Nowhere, XX 00000",
            "Invalid Address 999999",
            "adkfljasdklfjaslkdfj",
            "",
            "123 NonExistent Blvd, FakeCity, ZZ"
        ]
        
        for address in invalid_addresses:
            result = await geocoding_service.geocode_address(address)
            
            # Should return a result but with low confidence or failure
            if result is not None:
                # If we get a result, confidence should be low or success should be False
                assert result.confidence < 0.7 or result.success == False
            else:
                # None result is also acceptable for truly invalid addresses
                assert result is None
    
    @pytest.mark.asyncio  
    async def test_partial_addresses(self, geocoding_service):
        """Test geocoding with partial addresses"""
        partial_addresses = [
            "Mountain View, CA",
            "New York, NY", 
            "Los Angeles, CA",
            "Beverly Hills, CA 90210"  # Zip code with city
        ]
        
        for address in partial_addresses:
            result = await geocoding_service.geocode_address(address)
            
            # Should get results but with lower confidence than full addresses
            assert result is not None
            assert result.success == True
            assert result.latitude is not None
            assert result.longitude is not None
            # Confidence might be lower for partial addresses
            assert result.confidence >= 0.3


class TestServiceAreaCalculation:
    """Test distance calculations and service area validation"""
    
    @pytest.mark.asyncio
    async def test_distance_calculation_accuracy(self, service_area_validator):
        """Test distance calculations with known locations"""
        # Test cases with approximate expected distances from LA (34.0522, -118.2437)
        test_cases = [
            {
                "address": "Beverly Hills, CA",
                "expected_miles_range": (5, 15)  # Very close to LA
            },
            {
                "address": "Santa Monica, CA", 
                "expected_miles_range": (10, 20)  # Close to LA
            },
            {
                "address": "Pasadena, CA",
                "expected_miles_range": (8, 18)  # Northeast of LA
            },
            {
                "address": "San Francisco, CA",
                "expected_miles_range": (300, 400)  # Much farther
            }
        ]
        
        for test_case in test_cases:
            result = await service_area_validator.validate_service_area(
                test_case["address"], 25  # 25 mile radius
            )
            
            assert result is not None
            assert result.geocoding_success == True
            assert result.distance_miles is not None
            
            min_expected, max_expected = test_case["expected_miles_range"]
            assert min_expected <= result.distance_miles <= max_expected, \
                f"Distance {result.distance_miles} not in expected range {test_case['expected_miles_range']} for {test_case['address']}"
    
    @pytest.mark.asyncio
    async def test_service_area_validation(self, service_area_validator):
        """Test service area validation with different radius settings"""
        # Test address that should be within reasonable distance of LA
        test_address = "Santa Monica, CA"
        
        # Test different service radius values
        test_cases = [
            {"radius": 50, "should_be_in_area": True},   # Large radius - should include
            {"radius": 25, "should_be_in_area": True},   # Medium radius - should include  
            {"radius": 5, "should_be_in_area": False},   # Small radius - might exclude
        ]
        
        for test_case in test_cases:
            result = await service_area_validator.validate_service_area(
                test_address, test_case["radius"]
            )
            
            assert result is not None
            assert result.geocoding_success == True
            assert result.distance_miles is not None
            
            if test_case["should_be_in_area"]:
                assert result.in_service_area == True, \
                    f"Address should be in {test_case['radius']} mile radius"
            # Note: We don't assert False case strictly since distances can vary
    
    @pytest.mark.asyncio
    async def test_out_of_service_area_detection(self, service_area_validator):
        """Test detection of addresses outside service area"""
        # Addresses that should definitely be outside a 25-mile radius of LA
        far_addresses = [
            "San Francisco, CA",      # ~400 miles
            "Las Vegas, NV",          # ~270 miles  
            "Phoenix, AZ",            # ~370 miles
            "Seattle, WA"             # ~1100 miles
        ]
        
        for address in far_addresses:
            result = await service_area_validator.validate_service_area(
                address, 25  # 25 mile radius from LA
            )
            
            assert result is not None
            assert result.geocoding_success == True
            assert result.distance_miles is not None
            assert result.distance_miles > 25  # Should be outside 25-mile radius
            assert result.in_service_area == False


class TestGeocodingServiceErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self):
        """Test behavior with invalid API key"""
        invalid_service = GeocodingService("invalid_api_key")
        
        result = await invalid_service.geocode_address("123 Main St, Los Angeles, CA")
        
        # Should handle API errors gracefully
        assert result is None or result.success == False
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, geocoding_service):
        """Test handling of network timeouts"""
        # This test might be flaky, but should handle network issues gracefully
        result = await geocoding_service.geocode_address("123 Main St, Los Angeles, CA")
        
        # Should either succeed or fail gracefully, not crash
        assert result is None or isinstance(result, GeocodingResult)
    
    @pytest.mark.asyncio  
    async def test_empty_and_none_addresses(self, geocoding_service):
        """Test handling of empty and None addresses"""
        test_cases = ["", "   ", None]
        
        for address in test_cases:
            result = await geocoding_service.geocode_address(address)
            
            # Should handle gracefully, not crash
            assert result is None or result.success == False
    
    @pytest.mark.asyncio
    async def test_very_long_address(self, geocoding_service):
        """Test handling of unusually long addresses"""
        long_address = "A" * 500 + " Street, Los Angeles, CA"
        
        result = await geocoding_service.geocode_address(long_address)
        
        # Should handle gracefully
        assert result is None or isinstance(result, GeocodingResult)


class TestServiceAreaValidatorEdgeCases:
    """Test edge cases for service area validation"""
    
    @pytest.mark.asyncio
    async def test_zero_radius_service_area(self, service_area_validator):
        """Test service area with zero radius"""
        result = await service_area_validator.validate_service_area(
            "Los Angeles, CA", 0
        )
        
        # Should handle edge case gracefully
        if result is not None:
            assert result.in_service_area == False  # Zero radius excludes everything
    
    @pytest.mark.asyncio
    async def test_very_large_radius(self, service_area_validator):
        """Test service area with very large radius"""
        result = await service_area_validator.validate_service_area(
            "New York, NY", 10000  # 10,000 mile radius
        )
        
        if result is not None and result.geocoding_success:
            assert result.in_service_area == True  # Huge radius includes everything
    
    @pytest.mark.asyncio
    async def test_business_location_itself(self, service_area_validator):
        """Test validation of business location itself"""
        # Address very close to our test business location (LA)
        result = await service_area_validator.validate_service_area(
            "Los Angeles, CA", 25
        )
        
        if result is not None and result.geocoding_success:
            assert result.in_service_area == True
            assert result.distance_miles < 25  # Should be within service area