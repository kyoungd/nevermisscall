"""
Tests for fail-fast error handling - Week 2, Day 4-5.
Focus on graceful degradation and user-friendly error messages.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio
import httpx

from dispatch_bot.services.error_handler import ErrorHandler, ErrorResponse, ErrorSeverity
from dispatch_bot.services.conversation_manager import ConversationManager, ConversationTimeout
from dispatch_bot.services.fallback_service import FallbackService
from dispatch_bot.models.basic_schemas import BasicDispatchRequest, BasicDispatchResponse, ConversationStage


class TestErrorHandler:
    """Test comprehensive error handling and user-friendly responses"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing"""
        return ErrorHandler()
    
    def test_create_user_friendly_error_response(self, error_handler):
        """Test creation of user-friendly error messages"""
        test_cases = [
            {
                "error_type": "address_not_found",
                "original_error": "ZERO_RESULTS from Google Maps API",
                "expected_message": "I couldn't find that address. Could you please provide a more complete address with street, city, and state?"
            },
            {
                "error_type": "out_of_service_area", 
                "original_error": "Address is 45 miles from business location",
                "expected_message": "I'm sorry, but that address is outside our service area. We currently serve within 25 miles of our location."
            },
            {
                "error_type": "api_unavailable",
                "original_error": "Google Maps API timeout",
                "expected_message": "I'm having trouble validating addresses right now. Please call our office directly at [phone] for immediate assistance."
            },
            {
                "error_type": "invalid_phone",
                "original_error": "Phone number format validation failed",
                "expected_message": "I need a valid phone number to help you. Please provide your number in format: (555) 123-4567"
            }
        ]
        
        for case in test_cases:
            response = error_handler.create_user_friendly_response(
                error_type=case["error_type"],
                original_error=case["original_error"],
                context={"business_phone": "(555) 123-4567"}
            )
            
            assert response.user_message is not None
            assert len(response.user_message) > 20  # Should be descriptive
            assert "error" not in response.user_message.lower()  # Should not expose technical errors
            assert "failed" not in response.user_message.lower()  # Should be positive language
    
    def test_error_severity_classification(self, error_handler):
        """Test proper classification of error severity levels"""
        severity_tests = [
            {
                "error": "Phone number validation failed",
                "expected_severity": ErrorSeverity.LOW,
                "should_continue": True
            },
            {
                "error": "Address not found in service area",
                "expected_severity": ErrorSeverity.MEDIUM,
                "should_continue": True
            },
            {
                "error": "Google Maps API key invalid",
                "expected_severity": ErrorSeverity.HIGH,
                "should_continue": False
            },
            {
                "error": "Database connection failed",
                "expected_severity": ErrorSeverity.CRITICAL,
                "should_continue": False
            }
        ]
        
        for test in severity_tests:
            result = error_handler.classify_error_severity(test["error"])
            
            assert result.severity == test["expected_severity"]
            assert result.should_continue_conversation == test["should_continue"]
    
    def test_error_logging_and_monitoring(self, error_handler):
        """Test that errors are properly logged for monitoring"""
        with patch('dispatch_bot.services.error_handler.logger') as mock_logger:
            error_handler.handle_and_log_error(
                error_type="geocoding_failure",
                original_error="Network timeout after 10 seconds",
                conversation_sid="test_sid_123",
                customer_phone="+12125551234",
                severity=ErrorSeverity.MEDIUM
            )
            
            # Should log error with appropriate level
            mock_logger.warning.assert_called()
            log_call = mock_logger.warning.call_args[0][0]
            assert "geocoding_failure" in log_call
            assert "test_sid_123" in log_call
    
    def test_error_response_includes_recovery_options(self, error_handler):
        """Test that error responses include recovery options"""
        response = error_handler.create_user_friendly_response(
            error_type="service_temporarily_unavailable",
            original_error="OpenAI API rate limit exceeded",
            context={
                "business_phone": "(555) 123-4567",
                "business_name": "Joe's Plumbing"
            }
        )
        
        assert response.user_message is not None
        assert response.recovery_options is not None
        assert len(response.recovery_options) > 0
        
        # Should include alternative contact methods
        recovery_text = " ".join(response.recovery_options)
        assert "call" in recovery_text.lower() or "phone" in recovery_text.lower()
    
    def test_prevent_error_message_loops(self, error_handler):
        """Test prevention of repetitive error messages"""
        conversation_id = "test_conversation_123"
        error_type = "address_validation_failed"
        
        # First error - should get full message
        response1 = error_handler.get_error_response_for_conversation(
            conversation_id, error_type, "Address not found"
        )
        
        # Second same error in same conversation - should get shorter message
        response2 = error_handler.get_error_response_for_conversation(
            conversation_id, error_type, "Address not found"  
        )
        
        # Third same error - should escalate to human
        response3 = error_handler.get_error_response_for_conversation(
            conversation_id, error_type, "Address not found"
        )
        
        assert len(response1.user_message) > len(response2.user_message)
        assert response3.should_escalate_to_human == True


class TestExternalServiceFallback:
    """Test fallback handling when external APIs fail"""
    
    @pytest.fixture
    def fallback_service(self):
        """Create fallback service for testing"""
        return FallbackService()
    
    @pytest.mark.asyncio
    async def test_google_maps_api_fallback(self, fallback_service):
        """Test fallback when Google Maps API is unavailable"""
        # Mock Google Maps service failure
        mock_geocoding_service = AsyncMock()
        mock_geocoding_service.geocode_address.return_value = None
        
        # Should fall back to basic address parsing
        result = await fallback_service.geocode_with_fallback(
            address="123 Main St, Los Angeles, CA",
            primary_service=mock_geocoding_service
        )
        
        assert result is not None
        assert result.fallback_used == True
        assert result.confidence < 0.7  # Lower confidence for fallback
        assert result.user_message is not None
        assert "limited" in result.user_message.lower()
    
    @pytest.mark.asyncio
    async def test_openai_api_fallback(self, fallback_service):
        """Test fallback when OpenAI API is unavailable"""
        mock_nlp_service = AsyncMock()
        mock_nlp_service.extract_intent.side_effect = Exception("API rate limit exceeded")
        
        # Should fall back to keyword-based extraction
        result = await fallback_service.extract_intent_with_fallback(
            message="My faucet is leaking at 123 Main St",
            primary_service=mock_nlp_service
        )
        
        assert result is not None
        assert result.fallback_used == True
        assert result.job_type is not None  # Should still extract something
        assert result.confidence < 0.8  # Lower confidence for fallback
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self, fallback_service):
        """Test behavior when some services work but others fail"""
        # Mock scenario: geocoding works, but distance calculation fails
        mock_geocoding_result = Mock()
        mock_geocoding_result.success = True
        mock_geocoding_result.latitude = 34.0522
        mock_geocoding_result.longitude = -118.2437
        
        mock_distance_service = AsyncMock()
        mock_distance_service.calculate_distance.side_effect = Exception("Network error")
        
        result = await fallback_service.validate_service_area_with_fallback(
            geocoding_result=mock_geocoding_result,
            business_location=(34.0, -118.0),
            service_radius=25,
            distance_service=mock_distance_service
        )
        
        # Should provide approximate validation
        assert result is not None
        assert result.approximate_validation == True
        assert result.confidence < 0.9
        assert "approximate" in result.user_message.lower()
    
    def test_fallback_service_quality_degradation(self, fallback_service):
        """Test that fallback services indicate reduced quality"""
        fallback_responses = [
            fallback_service.create_geocoding_fallback_response(),
            fallback_service.create_nlp_fallback_response(),  
            fallback_service.create_scheduling_fallback_response()
        ]
        
        for response in fallback_responses:
            assert response.fallback_used == True
            assert response.confidence < 0.8  # Reduced confidence
            assert response.user_message is not None
            # Should inform user of reduced capability
            message = response.user_message.lower()
            assert any(word in message for word in ["limited", "approximate", "basic", "reduced"])


class TestConversationTimeout:
    """Test conversation timeout handling and management"""
    
    @pytest.fixture
    def conversation_manager(self):
        """Create conversation manager for testing"""
        return ConversationManager(default_timeout_minutes=5)
    
    def test_conversation_timeout_tracking(self, conversation_manager):
        """Test tracking of conversation timeouts"""
        conversation_id = "test_conv_123"
        
        # Start conversation
        conversation_manager.start_conversation(conversation_id)
        
        # Check that timeout is set
        timeout_info = conversation_manager.get_timeout_info(conversation_id)
        assert timeout_info is not None
        assert timeout_info.started_at is not None
        assert timeout_info.expires_at is not None
        assert timeout_info.timeout_minutes == 5
    
    def test_conversation_timeout_expiration(self, conversation_manager):
        """Test detection of expired conversations"""
        conversation_id = "test_conv_expired"
        
        # Start conversation with very short timeout for testing
        conversation_manager.start_conversation(conversation_id, timeout_minutes=0.001)  # ~0.06 seconds
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        # Should be expired
        is_expired = conversation_manager.is_conversation_expired(conversation_id)
        assert is_expired == True
        
        # Should generate timeout response
        timeout_response = conversation_manager.generate_timeout_response(
            conversation_id, 
            business_name="Joe's Plumbing"
        )
        
        assert timeout_response is not None
        assert timeout_response.conversation_stage == ConversationStage.TIMEOUT
        assert "no longer available" in timeout_response.next_message.lower()
    
    def test_conversation_timeout_extension(self, conversation_manager):
        """Test extending conversation timeout on customer activity"""
        conversation_id = "test_conv_extend"
        
        # Start conversation
        conversation_manager.start_conversation(conversation_id, timeout_minutes=5)
        original_timeout = conversation_manager.get_timeout_info(conversation_id)
        
        # Extend timeout due to customer activity
        conversation_manager.extend_conversation_timeout(conversation_id, additional_minutes=5)
        extended_timeout = conversation_manager.get_timeout_info(conversation_id)
        
        assert extended_timeout.expires_at > original_timeout.expires_at
        assert extended_timeout.timeout_minutes == 10  # 5 + 5
    
    def test_conversation_cleanup_after_timeout(self, conversation_manager):
        """Test cleanup of expired conversations"""
        conversation_id = "test_conv_cleanup"
        
        # Start and expire conversation
        conversation_manager.start_conversation(conversation_id, timeout_minutes=0.001)
        import time
        time.sleep(0.1)
        
        # Clean up expired conversations
        cleaned_count = conversation_manager.cleanup_expired_conversations()
        
        assert cleaned_count >= 1
        assert conversation_manager.get_timeout_info(conversation_id) is None
    
    def test_conversation_timeout_warning_messages(self, conversation_manager):
        """Test warning messages before timeout"""
        conversation_id = "test_conv_warning"
        
        # Start conversation with 5 minute timeout
        conversation_manager.start_conversation(conversation_id, timeout_minutes=5)
        
        # Mock being near timeout (4 minutes elapsed)
        with patch.object(conversation_manager, '_get_minutes_elapsed', return_value=4):
            warning_response = conversation_manager.check_for_timeout_warning(
                conversation_id,
                business_name="Joe's Plumbing"
            )
            
            assert warning_response is not None
            assert "1 minute" in warning_response.next_message.lower()
            assert "respond soon" in warning_response.next_message.lower()


class TestSystemDegradation:
    """Test system behavior under various failure conditions"""
    
    @pytest.mark.asyncio
    async def test_complete_api_outage_handling(self):
        """Test behavior when all external APIs are down"""
        # Mock all services failing
        mock_request = BasicDispatchRequest(
            conversation_sid="test_sid_outage",
            caller_phone="+12125551234",
            current_message="My sink is broken at 123 Main St",
            business_name="Joe's Plumbing",
            business_address="456 Business Ave"
        )
        
        # All external services fail
        with patch('dispatch_bot.services.geocoding_service.GeocodingService.geocode_address') as mock_geocoding, \
             patch('dispatch_bot.services.nlp_service.NLPService.extract_intent') as mock_nlp:
            
            mock_geocoding.side_effect = Exception("Service unavailable")
            mock_nlp.side_effect = Exception("Service unavailable")
            
            from dispatch_bot.services.conversation_processor import ConversationProcessor
            processor = ConversationProcessor()
            
            response = await processor.process_message_with_degradation(mock_request)
            
            # Should still provide a response, not crash
            assert response is not None
            assert response.next_message is not None
            assert response.conversation_stage == ConversationStage.COLLECTING_INFO
            # Should ask customer to call directly
            assert "call" in response.next_message.lower()
    
    def test_rate_limit_handling(self):
        """Test handling of API rate limits"""
        from dispatch_bot.services.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter(max_requests_per_minute=10)
        
        # Should allow requests under limit
        for i in range(8):
            assert rate_limiter.is_request_allowed("test_user") == True
        
        # Should start throttling near limit
        for i in range(5):
            result = rate_limiter.is_request_allowed("test_user")
            # May allow or throttle based on timing
        
        # Should provide retry information
        retry_info = rate_limiter.get_retry_info("test_user")
        assert retry_info.seconds_until_reset >= 0
    
    @pytest.mark.asyncio
    async def test_network_partition_recovery(self):
        """Test recovery from network partitions"""
        from dispatch_bot.services.health_monitor import HealthMonitor
        
        health_monitor = HealthMonitor()
        
        # Mock network partition (all external services fail)
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Network unreachable")
            
            # Should detect unhealthy state
            health_status = await health_monitor.check_external_services()
            assert health_status.overall_healthy == False
            assert health_status.google_maps_healthy == False
            assert health_status.openai_healthy == False
        
        # Mock recovery
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # Should recover
            health_status = await health_monitor.check_external_services()
            assert health_status.recovery_detected == True
    
    def test_memory_pressure_handling(self):
        """Test handling of high memory usage"""
        from dispatch_bot.services.resource_monitor import ResourceMonitor
        
        monitor = ResourceMonitor()
        
        # Mock high memory usage
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95  # 95% memory usage
            
            should_shed_load = monitor.should_shed_load()
            assert should_shed_load == True
            
            # Should provide simplified responses under memory pressure
            simplified_response = monitor.create_simplified_response(
                "I can help with your plumbing issue. What's the problem and your address?"
            )
            
            assert len(simplified_response) < 200  # Shorter response
            assert "plumbing" in simplified_response


class TestErrorRecoveryPatterns:
    """Test error recovery and retry patterns"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self):
        """Test exponential backoff for transient failures"""
        from dispatch_bot.services.retry_handler import RetryHandler
        
        retry_handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"
        
        # Should retry and eventually succeed
        result = await retry_handler.execute_with_retry(failing_function)
        
        assert result == "success"
        assert call_count == 3  # Should have retried twice
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker for preventing cascade failures"""
        from dispatch_bot.services.circuit_breaker import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # Cause multiple failures to open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Service down")))
        
        # Circuit should be open
        assert circuit_breaker.state == "OPEN"
        
        # Should fail fast without calling service
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(lambda: "should not be called")
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    def test_graceful_degradation_levels(self):
        """Test multiple levels of graceful degradation"""
        from dispatch_bot.services.degradation_manager import DegradationManager
        
        manager = DegradationManager()
        
        # Level 1: Minor degradation - reduce features
        manager.set_degradation_level(1)
        capabilities = manager.get_current_capabilities()
        assert capabilities.address_validation == True
        assert capabilities.smart_scheduling == False  # Reduced feature
        
        # Level 2: Major degradation - essential only  
        manager.set_degradation_level(2)
        capabilities = manager.get_current_capabilities()
        assert capabilities.address_validation == False  # Basic only
        assert capabilities.emergency_detection == True  # Essential
        
        # Level 3: Emergency mode - manual fallback
        manager.set_degradation_level(3)
        capabilities = manager.get_current_capabilities()
        assert capabilities.automated_response == False
        assert capabilities.manual_escalation == True