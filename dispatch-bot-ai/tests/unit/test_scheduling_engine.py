"""
Tests for scheduling engine - Week 3, Day 1-3 implementation.
Test-driven development for simple appointment scheduling.
"""

import pytest
from datetime import datetime, timedelta, time
from unittest.mock import Mock, patch
from typing import List, Optional

from dispatch_bot.services.scheduling_engine import (
    SchedulingEngine, 
    TimeSlot, 
    AppointmentRequest,
    AppointmentConfirmation,
    SchedulingResult
)
from dispatch_bot.models.basic_schemas import BasicDispatchRequest


class TestSchedulingEngine:
    """Test scheduling engine functionality"""
    
    @pytest.fixture
    def scheduling_engine(self):
        """Create scheduling engine with basic configuration"""
        return SchedulingEngine(
            business_hours_start="07:00",
            business_hours_end="18:00", 
            slot_duration_hours=2,  # 2-hour appointment slots
            advance_booking_days=7  # Book up to 7 days ahead
        )
    
    def test_generate_business_hours_slots_same_day(self, scheduling_engine):
        """Test: Generate available slots during business hours for same day"""
        # Test with a weekday during business hours (10 AM)
        test_time = datetime(2025, 8, 7, 10, 0)  # Thursday 10:00 AM
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            mock_datetime.combine = datetime.combine  # Keep original combine method
            
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # Should have slots for remaining business hours
            assert len(slots) > 0
            
            # All slots should be today and within business hours
            for slot in slots:
                assert slot.start_time.date() == test_time.date()
                assert slot.start_time.time() >= time(7, 0)  # After 7 AM
                assert slot.end_time.time() <= time(18, 0)   # Before 6 PM
                assert slot.duration_hours == 2
    
    def test_generate_next_day_slots(self, scheduling_engine):
        """Test: Generate slots for next business day"""
        test_time = datetime(2025, 8, 7, 16, 0)  # Thursday 4:00 PM (late in day)
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            mock_datetime.combine = datetime.combine  # Keep original combine method
            
            slots = scheduling_engine.generate_available_slots(days_ahead=1)
            
            # Should have full day of slots for tomorrow
            assert len(slots) > 0
            
            expected_date = (test_time + timedelta(days=1)).date()
            for slot in slots:
                assert slot.start_time.date() == expected_date
                assert slot.start_time.time() >= time(7, 0)
                assert slot.end_time.time() <= time(18, 0)
    
    def test_no_weekend_slots_generated(self, scheduling_engine):
        """Test: No slots generated for weekends (Phase 1 business hours only)"""
        # Test with Saturday
        saturday = datetime(2025, 8, 9, 10, 0)  # Saturday 10:00 AM
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = saturday
            
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # No slots on weekends in Phase 1
            assert len(slots) == 0
    
    def test_slots_are_properly_spaced(self, scheduling_engine):
        """Test: Generated slots don't overlap and are properly spaced"""
        test_time = datetime(2025, 8, 7, 8, 0)  # Thursday 8:00 AM
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # Sort slots by start time
            sorted_slots = sorted(slots, key=lambda s: s.start_time)
            
            # Check that slots don't overlap
            for i in range(len(sorted_slots) - 1):
                current_slot = sorted_slots[i]
                next_slot = sorted_slots[i + 1]
                
                # Next slot should start after current slot ends
                assert next_slot.start_time >= current_slot.end_time
    
    def test_late_day_has_limited_slots(self, scheduling_engine):
        """Test: Late in business day has fewer available slots"""
        # Test late in business day (4 PM, only 2 hours left for 2-hour slots)
        late_time = datetime(2025, 8, 7, 16, 0)  # Thursday 4:00 PM
        early_time = datetime(2025, 8, 7, 8, 0)   # Thursday 8:00 AM
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            # Test late day
            mock_datetime.now.return_value = late_time
            late_slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # Test early day  
            mock_datetime.now.return_value = early_time
            early_slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # Should have fewer slots available late in the day
            assert len(late_slots) < len(early_slots)
    
    def test_no_slots_after_business_hours(self, scheduling_engine):
        """Test: No slots offered after business hours end"""
        # Test after business hours (7 PM)
        after_hours = datetime(2025, 8, 7, 19, 0)  # Thursday 7:00 PM
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = after_hours
            
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # No slots available after business hours
            assert len(slots) == 0


class TestAppointmentConfirmation:
    """Test appointment confirmation logic"""
    
    @pytest.fixture 
    def scheduling_engine(self):
        return SchedulingEngine(
            business_hours_start="07:00",
            business_hours_end="18:00",
            slot_duration_hours=2
        )
    
    def test_parse_yes_confirmation(self, scheduling_engine):
        """Test: Parse various forms of YES confirmation"""
        yes_variations = ["YES", "yes", "Yes", "Y", "y", "yeah", "yep", "confirm", "book it"]
        
        for variation in yes_variations:
            result = scheduling_engine.parse_confirmation_response(variation)
            assert result.confirmed == True
            assert result.response_type == "confirmation"
    
    def test_parse_no_rejection(self, scheduling_engine):
        """Test: Parse various forms of NO rejection"""
        no_variations = ["NO", "no", "No", "N", "n", "nope", "cancel", "not interested"]
        
        for variation in no_variations:
            result = scheduling_engine.parse_confirmation_response(variation)
            assert result.confirmed == False
            assert result.response_type == "rejection"
    
    def test_parse_unclear_response(self, scheduling_engine):
        """Test: Handle unclear confirmation responses"""
        unclear_responses = ["maybe", "I'll think about it", "what time exactly?", "how much?"]
        
        for response in unclear_responses:
            result = scheduling_engine.parse_confirmation_response(response)
            assert result.confirmed == False
            assert result.response_type == "unclear"
            assert "need a clear" in result.follow_up_message.lower()
    
    def test_confirm_specific_appointment_slot(self, scheduling_engine):
        """Test: Confirm a specific appointment slot"""
        # Create a test slot
        test_slot = TimeSlot(
            start_time=datetime(2025, 8, 8, 10, 0),  # Tomorrow 10 AM
            end_time=datetime(2025, 8, 8, 12, 0),    # Tomorrow 12 PM  
            duration_hours=2,
            available=True,
            job_type="faucet_repair"
        )
        
        # Create appointment request
        request = AppointmentRequest(
            job_type="faucet_repair",
            customer_phone="+12125551234",
            customer_address="123 Main St, Los Angeles, CA",
            preferred_slot=test_slot,
            urgency_level="normal"
        )
        
        # Confirm the appointment
        confirmation = scheduling_engine.confirm_appointment(request, "YES")
        
        assert confirmation.confirmed == True
        assert confirmation.appointment_id is not None
        assert confirmation.slot == test_slot
        assert "confirmed" in confirmation.confirmation_message.lower()
        assert "PLB-" in confirmation.appointment_id  # Plumbing job ID format


class TestJobTypeEstimation:
    """Test job type estimation and pricing"""
    
    @pytest.fixture
    def scheduling_engine(self):
        return SchedulingEngine(
            business_hours_start="07:00", 
            business_hours_end="18:00"
        )
    
    def test_faucet_repair_estimation(self, scheduling_engine):
        """Test: Basic estimation for faucet repair jobs"""
        estimation = scheduling_engine.estimate_job_cost("faucet_repair")
        
        assert estimation.job_type == "faucet_repair"
        assert estimation.min_cost >= 100  # Minimum job cost
        assert estimation.max_cost <= 300   # Phase 1 basic range
        assert estimation.duration_hours == 2  # Standard 2-hour slot
        assert "faucet" in estimation.description.lower()
    
    def test_toilet_repair_estimation(self, scheduling_engine):
        """Test: Basic estimation for toilet repair jobs"""
        estimation = scheduling_engine.estimate_job_cost("toilet_repair")
        
        assert estimation.job_type == "toilet_repair"
        assert estimation.min_cost >= 150  # Slightly higher for toilet work
        assert estimation.max_cost <= 400
        assert estimation.duration_hours == 2
    
    def test_drain_cleaning_estimation(self, scheduling_engine):
        """Test: Basic estimation for drain cleaning jobs"""
        estimation = scheduling_engine.estimate_job_cost("drain_cleaning")
        
        assert estimation.job_type == "drain_cleaning"
        assert estimation.min_cost >= 200  # Higher for drain work
        assert estimation.max_cost <= 500
        assert estimation.duration_hours == 2
    
    def test_general_plumbing_fallback(self, scheduling_engine):
        """Test: Fallback estimation for unknown job types"""
        estimation = scheduling_engine.estimate_job_cost("unknown_job_type")
        
        assert estimation.job_type == "general_plumbing"
        assert estimation.min_cost >= 100
        assert estimation.max_cost <= 300
        assert "general plumbing" in estimation.description.lower()
    
    def test_business_hours_pricing(self, scheduling_engine):
        """Test: Standard business hours pricing (no multiplier in Phase 1)"""
        # Phase 1 only supports business hours, so no time-based pricing yet
        morning_estimation = scheduling_engine.estimate_job_cost("faucet_repair")
        afternoon_estimation = scheduling_engine.estimate_job_cost("faucet_repair") 
        
        # In Phase 1, pricing should be the same regardless of time
        assert morning_estimation.min_cost == afternoon_estimation.min_cost
        assert morning_estimation.max_cost == afternoon_estimation.max_cost


class TestSlotAvailability:
    """Test slot availability and double-booking prevention"""
    
    @pytest.fixture
    def scheduling_engine(self):
        return SchedulingEngine(
            business_hours_start="07:00",
            business_hours_end="18:00"
        )
    
    def test_book_slot_marks_unavailable(self, scheduling_engine):
        """Test: Booking a slot marks it as unavailable"""
        test_time = datetime(2025, 8, 7, 9, 0)
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            mock_datetime.combine = datetime.combine  # Keep original combine method
            
            # Get available slots
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            assert len(slots) > 0
            
            first_slot = slots[0]
            assert first_slot.available == True
            
            # Book the slot
            request = AppointmentRequest(
                job_type="faucet_repair",
                customer_phone="+12125551234",
                customer_address="123 Main St",
                preferred_slot=first_slot,
                urgency_level="normal"
            )
            
            confirmation = scheduling_engine.confirm_appointment(request, "YES")
            assert confirmation.confirmed == True
            
            # Slot should now be unavailable
            mock_datetime.now.return_value = test_time  # Reset for second call
            updated_slots = scheduling_engine.generate_available_slots(days_ahead=0)
            booked_slot = next((s for s in updated_slots if s.start_time == first_slot.start_time), None)
            
            # Slot should either be marked unavailable or not included in available slots
            if booked_slot:
                assert booked_slot.available == False
            # Or it should be completely filtered out (preferred approach)
    
    def test_cannot_double_book_same_slot(self, scheduling_engine):
        """Test: Cannot book the same slot twice"""
        test_slot = TimeSlot(
            start_time=datetime(2025, 8, 8, 10, 0),
            end_time=datetime(2025, 8, 8, 12, 0),
            duration_hours=2,
            available=True,
            job_type="faucet_repair"
        )
        
        # First booking
        request1 = AppointmentRequest(
            job_type="faucet_repair",
            customer_phone="+12125551234",
            customer_address="123 Main St",
            preferred_slot=test_slot,
            urgency_level="normal"
        )
        
        confirmation1 = scheduling_engine.confirm_appointment(request1, "YES")
        assert confirmation1.confirmed == True
        
        # Attempt second booking of same slot
        request2 = AppointmentRequest(
            job_type="toilet_repair", 
            customer_phone="+12125555678",
            customer_address="456 Oak Ave",
            preferred_slot=test_slot,
            urgency_level="normal"
        )
        
        confirmation2 = scheduling_engine.confirm_appointment(request2, "YES")
        assert confirmation2.confirmed == False
        assert "no longer available" in confirmation2.confirmation_message.lower()
    
    def test_generate_alternative_slots_when_preferred_unavailable(self, scheduling_engine):
        """Test: Offer alternative slots when preferred slot is unavailable"""
        test_time = datetime(2025, 8, 7, 9, 0)
        
        with patch('dispatch_bot.services.scheduling_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            mock_datetime.combine = datetime.combine  # Keep original combine method
            
            # Get available slots and book the first one
            slots = scheduling_engine.generate_available_slots(days_ahead=0)
            first_slot = slots[0]
            
            # Book first slot
            request = AppointmentRequest(
                job_type="faucet_repair",
                customer_phone="+12125551234", 
                customer_address="123 Main St",
                preferred_slot=first_slot,
                urgency_level="normal"
            )
            
            scheduling_engine.confirm_appointment(request, "YES")
            
            # Generate alternatives - should not include the booked slot
            mock_datetime.now.return_value = test_time  # Reset for second call
            available_slots = scheduling_engine.generate_available_slots(days_ahead=0)
            
            # Should have fewer slots available
            assert len(available_slots) < len(slots)
            
            # Should not include the booked slot
            booked_slot_times = [s.start_time for s in available_slots if s.start_time == first_slot.start_time]
            assert len(booked_slot_times) == 0