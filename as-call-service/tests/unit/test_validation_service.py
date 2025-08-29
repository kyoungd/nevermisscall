"""Unit tests for ValidationService."""

import pytest
from datetime import datetime, time
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.as_call_service.services.validation_service import ValidationService
from src.as_call_service.utils import ValidationError, ServiceError


class TestValidationService:
    """Test cases for ValidationService."""

    @pytest.fixture
    def validation_service(self):
        """Create ValidationService instance for testing."""
        return ValidationService()

    def test_validate_phone_number_valid_formats(self, validation_service):
        """Test phone number validation with valid formats."""
        valid_numbers = [
            "+12125551234",      # US number
            "+447700900000",     # UK number
            "+33123456789",      # French number
            "+491234567890",     # German number
        ]

        for number in valid_numbers:
            assert validation_service.validate_phone_number(number) is True

    def test_validate_phone_number_invalid_formats(self, validation_service):
        """Test phone number validation with invalid formats."""
        invalid_numbers = [
            "",                  # Empty string
            "12125551234",       # Missing +
            "+1",                # Too short
            "+123456789012345678",  # Too long
            "+0123456789",       # Starts with 0 after country code
            "abc",               # Non-numeric
            "+1-212-555-1234",   # Contains hyphens
            "+1 212 555 1234",   # Contains spaces
        ]

        for number in invalid_numbers:
            assert validation_service.validate_phone_number(number) is False

    def test_validate_message_content_valid(self, validation_service):
        """Test message content validation with valid content."""
        valid_messages = [
            "Hello, I need help with my plumbing",
            "Can you come tomorrow at 2 PM?",
            "My address is 123 Main St, Los Angeles",
            "Emergency! Water is flooding my basement!",
            "A" * 1600,  # Max length
        ]

        for message in valid_messages:
            assert validation_service.validate_message_content(message) is True

    def test_validate_message_content_invalid(self, validation_service):
        """Test message content validation with invalid content."""
        invalid_messages = [
            "",                           # Empty string
            "A" * 1601,                   # Too long
            "<script>alert('xss')</script>",  # Script tag
            "javascript:alert('xss')",    # JavaScript URL
            '<img onload="alert(1)">',    # Event handler
        ]

        for message in invalid_messages:
            assert validation_service.validate_message_content(message) is False

    @pytest.mark.asyncio
    async def test_validate_tenant_exists_success(self, validation_service):
        """Test successful tenant validation."""
        tenant_id = uuid4()
        mock_validation_result = {
            'exists': True,
            'active': True,
            'businessName': 'Test Plumbing',
            'serviceRadiusMiles': 25,
        }

        with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
            mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

            result = await validation_service.validate_tenant_exists(tenant_id)

            # Verify service client was called
            mock_client.validate_tenant_and_service_area.assert_called_once_with(str(tenant_id))

            # Verify result
            assert result == mock_validation_result

    @pytest.mark.asyncio
    async def test_validate_tenant_exists_not_found(self, validation_service):
        """Test tenant validation when tenant doesn't exist."""
        tenant_id = uuid4()
        mock_validation_result = {
            'exists': False,
            'active': False,
        }

        with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
            mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

            with pytest.raises(ValidationError, match="does not exist"):
                await validation_service.validate_tenant_exists(tenant_id)

    @pytest.mark.asyncio
    async def test_validate_tenant_exists_inactive(self, validation_service):
        """Test tenant validation when tenant is inactive."""
        tenant_id = uuid4()
        mock_validation_result = {
            'exists': True,
            'active': False,
        }

        with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
            mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

            with pytest.raises(ValidationError, match="is not active"):
                await validation_service.validate_tenant_exists(tenant_id)

    @pytest.mark.asyncio
    async def test_validate_service_area_disabled(self, validation_service):
        """Test service area validation when disabled."""
        tenant_id = uuid4()
        customer_address = "123 Main St, Los Angeles, CA"

        with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
            mock_settings.service_area_validation_enabled = False

            result = await validation_service.validate_service_area(tenant_id, customer_address)

            # Should return valid when validation is disabled
            assert result['valid'] is True
            assert result['reason'] == 'validation_disabled'

    @pytest.mark.asyncio
    async def test_validate_service_area_within_area(self, validation_service):
        """Test service area validation for address within service area."""
        tenant_id = uuid4()
        customer_address = "123 Main St, Los Angeles, CA"
        mock_validation_result = {
            'serviceAreaValid': True,
            'addressValidated': True,
            'distanceMiles': 15.5,
            'travelTimeMinutes': 25,
        }

        with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
            mock_settings.service_area_validation_enabled = True

            with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
                mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

                result = await validation_service.validate_service_area(tenant_id, customer_address)

                # Verify service client was called
                mock_client.validate_tenant_and_service_area.assert_called_once_with(
                    str(tenant_id), customer_address
                )

                # Verify result
                assert result['valid'] is True
                assert result['withinServiceArea'] is True
                assert result['addressValidated'] is True
                assert result['distanceFromBusiness'] == 15.5

    @pytest.mark.asyncio
    async def test_validate_service_area_outside_area(self, validation_service):
        """Test service area validation for address outside service area."""
        tenant_id = uuid4()
        customer_address = "999 Far Away St, San Francisco, CA"
        mock_validation_result = {
            'serviceAreaValid': False,
            'addressValidated': True,
        }

        with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
            mock_settings.service_area_validation_enabled = True

            with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
                mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

                result = await validation_service.validate_service_area(tenant_id, customer_address)

                # Verify result
                assert result['valid'] is False
                assert result['reason'] == 'outside_service_area'
                assert result['withinServiceArea'] is False

    @pytest.mark.asyncio
    async def test_validate_service_area_address_invalid(self, validation_service):
        """Test service area validation for invalid address."""
        tenant_id = uuid4()
        customer_address = "Invalid Address 123"
        mock_validation_result = {
            'serviceAreaValid': False,
            'addressValidated': False,
        }

        with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
            mock_settings.service_area_validation_enabled = True

            with patch('src.as_call_service.services.validation_service.service_client') as mock_client:
                mock_client.validate_tenant_and_service_area = AsyncMock(return_value=mock_validation_result)

                result = await validation_service.validate_service_area(tenant_id, customer_address)

                # Verify result
                assert result['valid'] is False
                assert result['reason'] == 'address_validation_failed'
                assert result['addressValidated'] is False

    def test_validate_business_hours_within_hours(self, validation_service):
        """Test business hours validation during business hours."""
        business_hours = {
            'monday': {'start': '08:00', 'end': '17:00'},
            'tuesday': {'start': '08:00', 'end': '17:00'},
            'wednesday': {'start': '08:00', 'end': '17:00'},
            'thursday': {'start': '08:00', 'end': '17:00'},
            'friday': {'start': '08:00', 'end': '17:00'},
            'saturday': {'start': '09:00', 'end': '15:00'},
            'sunday': None,
        }

        # Test during business hours (Tuesday 10 AM)
        tuesday_10am = datetime(2024, 1, 2, 10, 0, 0)  # Tuesday
        result = validation_service.validate_business_hours(business_hours, tuesday_10am)

        assert result['withinHours'] is True
        assert result['reason'] == 'within_hours'
        assert result['currentDay'] == 'tuesday'

    def test_validate_business_hours_outside_hours(self, validation_service):
        """Test business hours validation outside business hours."""
        business_hours = {
            'monday': {'start': '08:00', 'end': '17:00'},
        }

        # Test outside business hours (Monday 6 AM)
        monday_6am = datetime(2024, 1, 1, 6, 0, 0)  # Monday
        result = validation_service.validate_business_hours(business_hours, monday_6am)

        assert result['withinHours'] is False
        assert result['reason'] == 'outside_hours'

    def test_validate_business_hours_closed_day(self, validation_service):
        """Test business hours validation on closed day."""
        business_hours = {
            'monday': {'start': '08:00', 'end': '17:00'},
            'sunday': None,  # Closed on Sunday
        }

        # Test on closed day (Sunday)
        sunday_10am = datetime(2024, 1, 7, 10, 0, 0)  # Sunday
        result = validation_service.validate_business_hours(business_hours, sunday_10am)

        assert result['withinHours'] is False
        assert result['reason'] == 'closed_on_day'
        assert result['currentDay'] == 'sunday'

    @pytest.mark.asyncio
    async def test_validate_conversation_limits_within_limit(self, validation_service):
        """Test conversation limits validation within limits."""
        tenant_id = uuid4()
        conversation_id = uuid4()

        with patch('src.as_call_service.services.validation_service.query') as mock_query:
            mock_query.return_value = [{'message_count': 50}]

            with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
                mock_settings.max_conversation_messages = 1000

                result = await validation_service.validate_conversation_limits(tenant_id, conversation_id)

                # Verify result
                assert result['valid'] is True
                assert result['messageCount'] == 50
                assert result['remainingMessages'] == 950

    @pytest.mark.asyncio
    async def test_validate_conversation_limits_exceeded(self, validation_service):
        """Test conversation limits validation when limit exceeded."""
        tenant_id = uuid4()
        conversation_id = uuid4()

        with patch('src.as_call_service.services.validation_service.query') as mock_query:
            mock_query.return_value = [{'message_count': 1000}]

            with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
                mock_settings.max_conversation_messages = 1000

                result = await validation_service.validate_conversation_limits(tenant_id, conversation_id)

                # Verify result
                assert result['valid'] is False
                assert result['reason'] == 'message_limit_exceeded'
                assert result['messageCount'] == 1000

    @pytest.mark.asyncio
    async def test_validate_conversation_limits_not_found(self, validation_service):
        """Test conversation limits validation when conversation not found."""
        tenant_id = uuid4()
        conversation_id = uuid4()

        with patch('src.as_call_service.services.validation_service.query') as mock_query:
            mock_query.return_value = []  # No results

            with pytest.raises(ValidationError, match="Conversation not found"):
                await validation_service.validate_conversation_limits(tenant_id, conversation_id)

    def test_extract_address_from_message_valid_addresses(self, validation_service):
        """Test address extraction from messages with valid addresses."""
        test_cases = [
            ("I live at 123 Main Street", "123 Main Street"),
            ("My address is 456 Oak Avenue, Los Angeles", "456 Oak Avenue"),
            ("Come to 789 Pine Road please", "789 Pine Road"),
            ("Visit 321 Elm Drive, CA 90210", "321 Elm Drive, CA 90210"),
            ("The leak is at 555 Sunset Boulevard", "555 Sunset Boulevard"),
        ]

        for message, expected_address in test_cases:
            result = validation_service.extract_address_from_message(message)
            assert expected_address in result

    def test_extract_address_from_message_no_address(self, validation_service):
        """Test address extraction from messages without addresses."""
        no_address_messages = [
            "I need help with my plumbing",
            "Can you come tomorrow?",
            "The sink is broken",
            "Emergency repair needed",
            "Call me back please",
        ]

        for message in no_address_messages:
            result = validation_service.extract_address_from_message(message)
            assert result is None

    def test_extract_phone_from_message_valid_numbers(self, validation_service):
        """Test phone number extraction from messages."""
        test_cases = [
            ("Call me at (555) 123-4567", "+15551234567"),
            ("My number is 555.123.4567", "+15551234567"),
            ("Contact 555-123-4567", "+15551234567"),
            ("Phone +1-555-123-4567", "+15551234567"),
            ("Reach me at 5551234567", "+15551234567"),
        ]

        for message, expected_phone in test_cases:
            result = validation_service.extract_phone_from_message(message)
            assert result == expected_phone

    def test_extract_phone_from_message_no_phone(self, validation_service):
        """Test phone number extraction from messages without phone numbers."""
        no_phone_messages = [
            "I need help with my plumbing",
            "Visit my address at 123 Main St",
            "The emergency is urgent",
            "Come tomorrow morning",
        ]

        for message in no_phone_messages:
            result = validation_service.extract_phone_from_message(message)
            assert result is None