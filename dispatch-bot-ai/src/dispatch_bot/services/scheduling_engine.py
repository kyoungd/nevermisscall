"""
Scheduling engine for appointment booking - Week 3, Day 1-3 implementation.
Simple appointment scheduling for Phase 1 (business hours only, plumbing services).
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Set
from uuid import uuid4

from dispatch_bot.models.scheduling_models import (
    TimeSlot, 
    AppointmentRequest,
    AppointmentConfirmation,
    ConfirmationResponse,
    JobEstimation,
    SchedulingResult,
    UrgencyLevel
)

logger = logging.getLogger(__name__)


class SchedulingEngine:
    """
    Simple scheduling engine for Phase 1.
    
    Features:
    - Business hours only (7 AM - 6 PM, Monday-Friday)
    - 2-hour appointment slots
    - Basic job type estimation
    - Double-booking prevention
    - Simple YES/NO confirmation parsing
    """
    
    def __init__(self, business_hours_start: str = "07:00", 
                 business_hours_end: str = "18:00",
                 slot_duration_hours: int = 2,
                 advance_booking_days: int = 7):
        """
        Initialize scheduling engine.
        
        Args:
            business_hours_start: Start of business hours (HH:MM format)
            business_hours_end: End of business hours (HH:MM format)
            slot_duration_hours: Duration of each appointment slot
            advance_booking_days: How many days ahead to allow booking
        """
        self.business_hours_start = self._parse_time(business_hours_start)
        self.business_hours_end = self._parse_time(business_hours_end)
        self.slot_duration_hours = slot_duration_hours
        self.advance_booking_days = advance_booking_days
        
        # Track booked appointments (in-memory for Phase 1)
        self.booked_slots: Set[datetime] = set()
        
        # Job type cost estimates (Phase 1 simplified)
        self.job_estimates = self._load_job_estimates()
    
    def generate_available_slots(self, days_ahead: int = 0) -> List[TimeSlot]:
        """
        Generate available appointment slots.
        
        Args:
            days_ahead: Number of days from today (0 = today)
            
        Returns:
            List of available TimeSlot objects
        """
        now = datetime.now()
        target_date = now.date() + timedelta(days=days_ahead)
        
        # Skip weekends in Phase 1 (business hours only)
        if target_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return []
        
        slots = []
        
        # Start time calculation
        if days_ahead == 0:
            # Same day - start from next available hour
            start_hour = max(now.hour + 1, self.business_hours_start.hour)
        else:
            # Future day - start from business hours start
            start_hour = self.business_hours_start.hour
        
        # Generate slots for the day
        current_hour = start_hour
        while current_hour + self.slot_duration_hours <= self.business_hours_end.hour:
            slot_start = datetime.combine(target_date, time(current_hour, 0))
            slot_end = slot_start + timedelta(hours=self.slot_duration_hours)
            
            # Check if slot is not already booked
            if slot_start not in self.booked_slots:
                slot = TimeSlot(
                    start_time=slot_start,
                    end_time=slot_end,
                    duration_hours=self.slot_duration_hours,
                    available=True
                )
                slots.append(slot)
            
            # Move to next slot
            current_hour += self.slot_duration_hours
        
        return slots
    
    def estimate_job_cost(self, job_type: str) -> JobEstimation:
        """
        Estimate cost and duration for a job type.
        
        Args:
            job_type: Type of plumbing job
            
        Returns:
            JobEstimation with cost range and details
        """
        estimate_data = self.job_estimates.get(job_type, self.job_estimates["general_plumbing"])
        
        return JobEstimation(
            job_type=estimate_data["job_type"],
            description=estimate_data["description"],
            min_cost=estimate_data["min_cost"],
            max_cost=estimate_data["max_cost"],
            duration_hours=estimate_data["duration_hours"],
            confidence_level=estimate_data["confidence_level"]
        )
    
    def parse_confirmation_response(self, response: str) -> ConfirmationResponse:
        """
        Parse customer confirmation response.
        
        Args:
            response: Customer's response message
            
        Returns:
            ConfirmationResponse with parsed result
        """
        response_lower = response.lower().strip()
        
        # YES variations (exact word matching to avoid false positives)
        yes_keywords = ["yes", "y", "yeah", "yep", "confirm", "book it", "schedule", "ok"]
        response_words = response_lower.split()
        if any(keyword in response_words or keyword == response_lower for keyword in yes_keywords):
            return ConfirmationResponse(
                confirmed=True,
                response_type="confirmation",
                confidence=1.0
            )
        
        # NO variations  
        no_keywords = ["no", "n", "nope", "cancel", "not interested", "nevermind"]
        if any(keyword in response_words or keyword == response_lower for keyword in no_keywords):
            return ConfirmationResponse(
                confirmed=False,
                response_type="rejection", 
                confidence=1.0
            )
        
        # Unclear response
        return ConfirmationResponse(
            confirmed=False,
            response_type="unclear",
            follow_up_message="I need a clear YES or NO to confirm your appointment. Reply YES to book or NO to cancel.",
            confidence=0.5
        )
    
    def confirm_appointment(self, request: AppointmentRequest, response: str) -> AppointmentConfirmation:
        """
        Confirm appointment booking based on customer response.
        
        Args:
            request: Appointment request details
            response: Customer's confirmation response
            
        Returns:
            AppointmentConfirmation with booking result
        """
        # Parse customer response
        confirmation = self.parse_confirmation_response(response)
        
        if not confirmation.confirmed:
            if confirmation.response_type == "rejection":
                message = "No problem! Feel free to reach out if you need plumbing help in the future."
            else:
                message = confirmation.follow_up_message or "I need a clear YES or NO to proceed."
            
            return AppointmentConfirmation(
                confirmed=False,
                confirmation_message=message
            )
        
        # Check if slot is still available
        slot_start = request.preferred_slot.start_time
        if slot_start in self.booked_slots:
            return AppointmentConfirmation(
                confirmed=False,
                confirmation_message="I'm sorry, but that time slot is no longer available. Let me find you another time.",
                slot=request.preferred_slot
            )
        
        # Book the appointment
        appointment_id = self._generate_appointment_id(request.job_type)
        self.booked_slots.add(slot_start)
        
        # Generate confirmation message
        slot = request.preferred_slot
        job_estimate = self.estimate_job_cost(request.job_type)
        
        confirmation_message = (
            f"✅ Appointment confirmed! "
            f"Your plumber will arrive {slot.date_string} "
            f"between {slot.formatted_time_range}. "
            f"Estimated cost: {job_estimate.cost_range_string}. "
            f"Appointment ID: {appointment_id}"
        )
        
        return AppointmentConfirmation(
            confirmed=True,
            appointment_id=appointment_id,
            slot=slot,
            confirmation_message=confirmation_message,
            customer_instructions="Our plumber will call 30 minutes before arrival.",
            business_contact_info="Questions? Call us at (555) 123-PLUMB"
        )
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        hour, minute = map(int, time_str.split(":"))
        return time(hour, minute)
    
    def _generate_appointment_id(self, job_type: str) -> str:
        """Generate unique appointment ID"""
        prefix = "PLB"  # Plumbing prefix for Phase 1
        suffix = str(uuid4()).upper()[:6]
        return f"{prefix}-{suffix}"
    
    def _load_job_estimates(self) -> Dict[str, Dict]:
        """Load job type estimates for Phase 1"""
        return {
            "faucet_repair": {
                "job_type": "faucet_repair",
                "description": "Faucet repair or replacement",
                "min_cost": 100.0,
                "max_cost": 250.0,
                "duration_hours": 2,
                "confidence_level": 0.9
            },
            "toilet_repair": {
                "job_type": "toilet_repair", 
                "description": "Toilet repair or replacement",
                "min_cost": 150.0,
                "max_cost": 350.0,
                "duration_hours": 2,
                "confidence_level": 0.8
            },
            "drain_cleaning": {
                "job_type": "drain_cleaning",
                "description": "Drain cleaning and unclogging",
                "min_cost": 200.0,
                "max_cost": 450.0,
                "duration_hours": 2, 
                "confidence_level": 0.7
            },
            "pipe_repair": {
                "job_type": "pipe_repair",
                "description": "Pipe repair or replacement", 
                "min_cost": 250.0,
                "max_cost": 600.0,
                "duration_hours": 2,
                "confidence_level": 0.6
            },
            "general_plumbing": {
                "job_type": "general_plumbing",
                "description": "General plumbing service",
                "min_cost": 100.0,
                "max_cost": 300.0,
                "duration_hours": 2,
                "confidence_level": 0.5
            }
        }