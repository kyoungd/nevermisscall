"""
Unit tests for validation utilities.

Tests validation functions following the unittest patterns and
"honest failure over eager passing" principle from documentation-requirement.md.
"""

import unittest
from unittest.mock import patch, Mock

from shared.utils.validation import (
    validate_required,
    validate_email,
    validate_phone_number,
    validate_uuid,
    validate_password,
    validate_tenant_id,
    validate_user_id,
    validate_phone_number_required,
    validate_email_required,
    validate_string_length,
    validate_choice,
    validate_positive_integer,
    validate_business_hours
)
from shared.models.exceptions import ValidationError


class TestValidationFunctions(unittest.TestCase):
    """Test validation utility functions with real business logic validation."""
    
    def test_validate_required_with_valid_values(self):
        """Test validate_required with valid non-empty values."""
        # Should not raise for valid values
        validate_required("test", "test_field")
        validate_required(123, "number_field")
        validate_required(["item"], "list_field")
        validate_required({"key": "value"}, "dict_field")
    
    def test_validate_required_fails_with_none(self):
        """Test validate_required raises ValidationError for None values."""
        with self.assertRaises(ValidationError) as context:
            validate_required(None, "test_field")
        
        error = context.exception
        self.assertEqual(error.field, "test_field")
        self.assertIn("test_field is required", str(error))
    
    def test_validate_required_fails_with_empty_string(self):
        """Test validate_required raises ValidationError for empty/whitespace strings."""
        with self.assertRaises(ValidationError) as context:
            validate_required("", "test_field")
        
        error = context.exception
        self.assertEqual(error.field, "test_field")
        self.assertIn("cannot be empty", str(error))
        
        # Test whitespace-only string
        with self.assertRaises(ValidationError):
            validate_required("   ", "whitespace_field")
    
    def test_validate_required_fails_with_empty_collections(self):
        """Test validate_required raises ValidationError for empty collections."""
        with self.assertRaises(ValidationError):
            validate_required([], "list_field")
        
        with self.assertRaises(ValidationError):
            validate_required({}, "dict_field")
        
        with self.assertRaises(ValidationError):
            validate_required((), "tuple_field")
    
    def test_validate_email_with_valid_emails(self):
        """Test validate_email accepts valid email formats."""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
            "a@b.co"
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(validate_email(email), f"Should accept valid email: {email}")
    
    def test_validate_email_with_invalid_emails(self):
        """Test validate_email rejects invalid email formats."""
        invalid_emails = [
            "",
            "invalid",
            "@example.com",
            "user@",
            "user@.com",
            "user.example.com",
            "user@example",
            None,
            123
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(validate_email(email), f"Should reject invalid email: {email}")
    
    def test_validate_phone_number_with_valid_formats(self):
        """Test validate_phone_number accepts valid phone number formats."""
        valid_phones = [
            "+15551234567",  # E.164 format
            "15551234567",   # 11-digit US
            "5551234567",    # 10-digit US
            "+442071234567", # UK number
            "+33123456789"   # French number
        ]
        
        for phone in valid_phones:
            with self.subTest(phone=phone):
                self.assertTrue(validate_phone_number(phone), f"Should accept valid phone: {phone}")
    
    def test_validate_phone_number_with_invalid_formats(self):
        """Test validate_phone_number rejects invalid phone number formats."""
        invalid_phones = [
            "",
            "123",
            "abc1234567",
            "25551234567",  # Invalid US number (starts with 2)
            None,
            123
        ]
        
        for phone in invalid_phones:
            with self.subTest(phone=phone):
                self.assertFalse(validate_phone_number(phone), f"Should reject invalid phone: {phone}")
    
    def test_validate_uuid_with_valid_formats(self):
        """Test validate_uuid accepts valid UUID formats."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "123E4567-E89B-12D3-A456-426614174000",  # Uppercase
            "00000000-0000-0000-0000-000000000000"   # All zeros
        ]
        
        for uuid_str in valid_uuids:
            with self.subTest(uuid=uuid_str):
                self.assertTrue(validate_uuid(uuid_str), f"Should accept valid UUID: {uuid_str}")
    
    def test_validate_uuid_with_invalid_formats(self):
        """Test validate_uuid rejects invalid UUID formats."""
        invalid_uuids = [
            "",
            "not-a-uuid",
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
            None,
            123
        ]
        
        for uuid_str in invalid_uuids:
            with self.subTest(uuid=uuid_str):
                self.assertFalse(validate_uuid(uuid_str), f"Should reject invalid UUID: {uuid_str}")
    
    def test_validate_password_strength_requirements(self):
        """Test validate_password enforces business rule password requirements."""
        # Valid password meeting all requirements
        result = validate_password("SecureP@ss123")
        self.assertTrue(result['valid'])
        self.assertEqual(result['errors'], [])
        
        # Test each requirement separately
        weak_passwords = {
            "short": "Abc1!",  # Too short
            "no_upper": "lowercase123!",  # No uppercase
            "no_lower": "UPPERCASE123!",  # No lowercase  
            "no_digit": "NoDigits!",  # No digits
            "no_special": "NoSpecial123",  # No special chars
            "": ""  # Empty password
        }
        
        for description, password in weak_passwords.items():
            with self.subTest(password=description):
                result = validate_password(password)
                self.assertFalse(result['valid'], f"Should reject weak password: {description}")
                self.assertGreater(len(result['errors']), 0, "Should provide specific error messages")
    
    def test_validate_tenant_id_business_rule(self):
        """Test validate_tenant_id enforces business rule for tenant isolation."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        
        # Should not raise for valid UUID
        validate_tenant_id(valid_uuid)
        
        # Should raise for invalid formats (business rule violation)
        with self.assertRaises(ValidationError) as context:
            validate_tenant_id("invalid-tenant-id")
        
        error = context.exception
        self.assertEqual(error.field, "tenant_id")
        self.assertIn("valid UUID", str(error))
    
    def test_validate_string_length_business_constraints(self):
        """Test validate_string_length enforces business field length constraints."""
        # Valid length
        validate_string_length("valid", "test_field", min_length=2, max_length=10)
        
        # Too short
        with self.assertRaises(ValidationError) as context:
            validate_string_length("x", "name", min_length=2, max_length=100)
        
        error = context.exception
        self.assertEqual(error.field, "name")
        self.assertIn("at least 2 characters", str(error))
        
        # Too long
        with self.assertRaises(ValidationError) as context:
            validate_string_length("x" * 101, "description", min_length=1, max_length=100)
        
        error = context.exception
        self.assertEqual(error.field, "description")
        self.assertIn("no more than 100 characters", str(error))
    
    def test_validate_choice_business_options(self):
        """Test validate_choice enforces business rule option constraints."""
        valid_statuses = ['active', 'inactive', 'suspended']
        
        # Valid choice
        validate_choice('active', 'status', valid_statuses)
        
        # Invalid choice
        with self.assertRaises(ValidationError) as context:
            validate_choice('invalid_status', 'status', valid_statuses)
        
        error = context.exception
        self.assertEqual(error.field, 'status')
        self.assertIn("active, inactive, suspended", str(error))
    
    def test_validate_positive_integer_business_constraint(self):
        """Test validate_positive_integer enforces business value constraints."""
        # Valid positive integer
        validate_positive_integer(5, 'quantity')
        validate_positive_integer(1, 'minimum_value')
        
        # Invalid values
        invalid_values = [0, -1, -5, 0.5, "5", None]
        
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as context:
                    validate_positive_integer(value, 'test_field')
                
                error = context.exception
                self.assertEqual(error.field, 'test_field')
                self.assertIn("positive integer", str(error))
    
    def test_validate_business_hours_real_business_logic(self):
        """Test validate_business_hours enforces real business hour constraints."""
        # Valid business hours
        valid_hours = {
            "monday": {"open": "09:00", "close": "17:00", "enabled": True},
            "tuesday": {"open": "09:00", "close": "17:00", "enabled": True},
            "wednesday": {"open": "09:00", "close": "17:00", "enabled": True},
            "thursday": {"open": "09:00", "close": "17:00", "enabled": True},
            "friday": {"open": "09:00", "close": "17:00", "enabled": True},
            "saturday": {"open": "10:00", "close": "14:00", "enabled": False},
            "sunday": {"open": "10:00", "close": "14:00", "enabled": False}
        }
        
        # Should not raise for valid hours
        validate_business_hours(valid_hours)
        
        # Missing day should raise ValidationError
        incomplete_hours = valid_hours.copy()
        del incomplete_hours["monday"]
        
        with self.assertRaises(ValidationError) as context:
            validate_business_hours(incomplete_hours)
        
        error = context.exception
        self.assertEqual(error.field, 'business_hours')
        self.assertIn("missing monday", str(error))
        
        # Invalid day format should raise ValidationError
        invalid_day_hours = valid_hours.copy()
        invalid_day_hours["monday"] = "invalid"
        
        with self.assertRaises(ValidationError) as context:
            validate_business_hours(invalid_day_hours)
        
        error = context.exception
        self.assertEqual(error.field, 'business_hours')
        self.assertIn("monday must be a dictionary", str(error))
    
    def test_validation_errors_provide_actionable_feedback(self):
        """Test that validation errors provide actionable feedback for developers."""
        # This tests the "What real bug would this catch?" principle
        
        # Test that field names are preserved for API error responses
        with self.assertRaises(ValidationError) as context:
            validate_email_required("invalid-email", "customer_email")
        
        error = context.exception
        self.assertEqual(error.field, "customer_email")
        self.assertIn("valid email address", str(error))
        
        # Test that business context is clear
        with self.assertRaises(ValidationError) as context:
            validate_phone_number_required("123", "business_phone")
        
        error = context.exception
        self.assertEqual(error.field, "business_phone")
        self.assertIn("valid phone number", str(error))


if __name__ == '__main__':
    unittest.main()