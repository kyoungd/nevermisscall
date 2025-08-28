# Dispatch Bot AI API - Conversation Examples

## Happy Path Examples

### Example 1: Same-Day Plumbing Emergency (Perfect Flow)

**Customer calls +1-555-PLUMB at 2:15 PM, no answer**

#### Turn 1: Initial Auto-Response
**Twilio Server → Dispatch API Request:**
```json
{
  "caller_phone": "+12125551234",
  "called_number": "+15555551111",
  "conversation_history": [],
  "current_message": "MISSED_CALL_TRIGGER",
  "business_name": "Prime Plumbing",
  "trade_type": "plumbing",
  "business_hours": {
    "tuesday": {"start": "08:00", "end": "18:00"}
  },
  "phone_hours": {
    "tuesday": {"start": "06:00", "end": "22:00"}
  },
  "business_address": {
    "street_address": "123 Main St",
    "city": "Los Angeles",
    "state": "CA",
    "postal_code": "90210"
  },
  "job_estimates": [
    {
      "job_type": "water_heater_repair",
      "description": "Water heater repair/replacement",
      "estimated_hours": 2.0,
      "estimated_cost_min": 150.0,
      "estimated_cost_max": 400.0,
      "urgency_multiplier": 1.5
    }
  ],
  "business_settings": {
    "accept_emergencies": true,
    "out_of_office": false,
    "max_jobs_per_day": 6,
    "min_buffer_between_jobs": 30,
    "service_radius_miles": 25,
    "max_travel_time_minutes": 60,
    "max_travel_distance_miles": 25,
    "emergency_multiplier": 1.5,
    "overtime_allowed": false
  },
  "existing_calendar": [
    {
      "event_id": "job_1",
      "start_time": "2025-08-06T15:30:00Z",
      "end_time": "2025-08-06T17:00:00Z",
      "location_address": "456 Oak Ave, Beverly Hills, CA 90210",
      "location_latitude": 34.0736,
      "location_longitude": -118.4004,
      "job_type": "faucet_repair",
      "booking_type": "confirmed",
      "customer_phone": "+12125559999"
    }
  ]
}
```

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": null,
    "job_confidence": 0.0,
    "urgency_level": "normal",
    "customer_address": null,
    "address_verified": false
  },
  "validation": {
    "service_area_valid": true,
    "trade_supported": true,
    "capacity_available": true,
    "validation_errors": []
  },
  "proposed_slot": null,
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)? I'll check our next available window right now.",
    "follow_up_needed": false
  },
  "conversation_stage": "initial"
}
```

**Twilio Server Action:** Sends SMS to customer

---

#### Turn 2: Customer Responds with Issue + Address
**Customer SMS:** "Water heater burst in basement! 789 Sunset Blvd, 90210"

**Twilio Server → Dispatch API Request:**
```json
{
  "caller_phone": "+12125551234",
  "called_number": "+15555551111",
  "conversation_history": [
    {
      "timestamp": "2025-08-06T14:15:30",
      "sender": "bot",
      "message": "Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?"
    },
    {
      "timestamp": "2025-08-06T14:16:45",
      "sender": "customer",
      "message": "Water heater burst in basement! 789 Sunset Blvd, 90210"
    }
  ],
  "current_message": "Water heater burst in basement! 789 Sunset Blvd, 90210",
  [... same business config as above ...]
}
```

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "water_heater_emergency",
    "job_confidence": 0.95,
    "urgency_level": "emergency",
    "urgency_confidence": 0.92,
    "customer_address": "789 Sunset Blvd, Los Angeles, CA 90210",
    "address_verified": true,
    "address_latitude": 34.0928,
    "address_longitude": -118.3287,
    "preferred_date": "today"
  },
  "validation": {
    "service_area_valid": true,
    "trade_supported": true,
    "job_type_supported": true,
    "within_business_hours": true,
    "capacity_available": true,
    "address_reachable": true,
    "validation_errors": []
  },
  "proposed_slot": {
    "slot_id": "emergency_slot_001",
    "start_time": "2025-08-06T17:30:00",
    "end_time": "2025-08-06T20:00:00",
    "duration_minutes": 150,
    "price_min": 225.0,
    "price_max": 600.0,
    "booking_type": "confirmed",
    "travel_time_minutes": 25,
    "requires_confirmation": true
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "🚨 Water heater emergency - I can get our tech to you today 5:30-8:00 PM. Emergency rate $225-$600. Reply YES to confirm this appointment.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 3
  },
  "conversation_stage": "confirming",
  "needs_geocoding": false
}
```

---

#### Turn 3: Customer Confirms
**Customer SMS:** "YES"

**Twilio Server → Dispatch API Request:** (with YES in current_message)

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "customer_confirmed": true,
    [... previous extraction data ...]
  },
  "validation": {
    "service_area_valid": true,
    [... all validations pass ...]
  },
  "proposed_slot": {
    "slot_id": "emergency_slot_001",
    "booking_type": "confirmed",
    [... same slot details ...]
  },
  "next_action": {
    "action_type": "book_appointment",
    "message_to_customer": "✅ Confirmed! Tech will arrive 5:30-8:00 PM today for your water heater emergency. You'll get an ETA text 30 mins before arrival. Total: $225-$600 (emergency rate). Job #EMR-001.",
    "follow_up_needed": false
  },
  "conversation_stage": "complete"
}
```

**Twilio Server Actions:** 
1. Sends confirmation SMS to customer
2. Creates calendar event 
3. Notifies business owner
4. Sets up ETA reminder

---

### Example 2: Next-Day Electrical Job (Standard Flow)

#### Turn 1: Initial Contact
**Customer calls +1-555-ELECT at 7:45 PM (after hours)**

**Dispatch API Response:**
```json
{
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "Hi, this is ElectriPro! We missed your call - what's the issue and the service address (street + ZIP)? Since it's after hours, I'll check tomorrow's availability.",
    "follow_up_needed": false
  },
  "conversation_stage": "initial"
}
```

#### Turn 2: Customer Response
**Customer SMS:** "Need outlet installed in kitchen, 123 Main St 90210"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "outlet_installation",
    "job_confidence": 0.88,
    "urgency_level": "normal",
    "customer_address": "123 Main St, Los Angeles, CA 90210",
    "address_verified": true,
    "preferred_date": "tomorrow"
  },
  "proposed_slot": {
    "slot_id": "tentative_slot_002",
    "start_time": "2025-08-07T10:00:00",
    "end_time": "2025-08-07T12:00:00",
    "duration_minutes": 120,
    "price_min": 125.0,
    "price_max": 200.0,
    "booking_type": "tentative",
    "requires_confirmation": true
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "I can schedule outlet installation tomorrow 10:00 AM - 12:00 PM. Cost: $125-$200. Reply YES to hold this slot (final time confirmed tonight).",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 5
  },
  "conversation_stage": "confirming"
}
```

---

## Unhappy Path Examples

### Example 3: Out of Service Area

#### Turn 1-2: Normal flow until address extraction
**Customer SMS:** "Leaky faucet at 456 Remote Rd, 93555" (Ridgecrest, CA - 150+ miles away)

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "faucet_repair",
    "job_confidence": 0.92,
    "customer_address": "456 Remote Rd, Ridgecrest, CA 93555",
    "address_verified": true,
    "address_latitude": 35.6225,
    "address_longitude": -117.6708
  },
  "validation": {
    "service_area_valid": false,
    "trade_supported": true,
    "address_reachable": false,
    "validation_errors": ["Address is 157 miles outside service radius of 25 miles"]
  },
  "proposed_slot": null,
  "next_action": {
    "action_type": "end_conversation",
    "message_to_customer": "Sorry, Ridgecrest is outside our 25-mile service area from LA. Try searching 'plumber near Ridgecrest CA' for local options. Thanks for thinking of Prime Plumbing!",
    "follow_up_needed": false
  },
  "conversation_stage": "complete"
}
```

---

### Example 4: Unclear Message + Low Confidence

#### Turn 1-2: Vague customer response
**Customer SMS:** "Something's broken, help!"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": null,
    "job_confidence": 0.15,
    "urgency_level": "normal",
    "customer_address": null,
    "address_verified": false
  },
  "validation": {
    "service_area_valid": false,
    "trade_supported": true,
    "validation_errors": ["Insufficient information - missing job type and address"]
  },
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "I'd love to help! Can you tell me specifically what plumbing issue you're having and your street address + ZIP code? (For example: 'leaky toilet, 123 Main St 90210')",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 10
  },
  "conversation_stage": "collecting_info"
}
```

#### Turn 3: Still unclear
**Customer SMS:** "Stuff is wet"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "water_leak_diagnostic",
    "job_confidence": 0.45,
    "urgency_level": "urgent",
    "customer_address": null
  },
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "Water issue understood. What's your service address? We'll send someone for a diagnostic visit ($150-200, 1 hour) to assess and fix the problem.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 5
  },
  "conversation_stage": "collecting_info"
}
```

---

### Example 5: Capacity Exceeded

#### Normal flow until slot checking
**Customer SMS:** "Bathroom faucet dripping, 789 Oak St 90210"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "faucet_repair",
    "job_confidence": 0.94,
    "customer_address": "789 Oak St, Los Angeles, CA 90210",
    "address_verified": true
  },
  "validation": {
    "service_area_valid": true,
    "trade_supported": true,
    "job_type_supported": true,
    "capacity_available": false,
    "validation_errors": ["Today's capacity exceeded (6/6 jobs booked)"]
  },
  "proposed_slot": {
    "slot_id": "next_available_003",
    "start_time": "2025-08-07T09:00:00",
    "end_time": "2025-08-07T10:30:00",
    "duration_minutes": 90,
    "price_min": 75.0,
    "price_max": 125.0,
    "booking_type": "tentative"
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "Today is fully booked, but I can schedule your faucet repair tomorrow 9:00-10:30 AM for $75-$125. Reply YES to hold this slot.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 5
  },
  "conversation_stage": "confirming"
}
```

---

### Example 6: Emergency During "Out of Office" Mode

**Customer SMS:** "URGENT! No hot water, family of 6! 555 Pine St 90210"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "water_heater_repair",
    "job_confidence": 0.89,
    "urgency_level": "emergency",
    "urgency_confidence": 0.78,
    "customer_address": "555 Pine St, Los Angeles, CA 90210",
    "address_verified": true
  },
  "validation": {
    "service_area_valid": true,
    "trade_supported": true,
    "capacity_available": false,
    "validation_errors": ["Business is in 'Out of Office' mode"]
  },
  "next_action": {
    "action_type": "escalate_to_owner",
    "message_to_customer": "Water heater emergency received. Our owner will call you within 15 minutes to assess if we can help tonight, or schedule first thing tomorrow. Your address: 555 Pine St.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 15,
    "escalation_reason": "Emergency during out-of-office hours"
  },
  "conversation_stage": "escalated"
}
```

---

### Example 7: Address Geocoding Failure

**Customer SMS:** "Broken pipe, corner of that big street near the mall"

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "pipe_repair",
    "job_confidence": 0.87,
    "urgency_level": "urgent",
    "customer_address": "corner of that big street near the mall",
    "address_verified": false
  },
  "validation": {
    "service_area_valid": false,
    "address_reachable": false,
    "validation_errors": ["Cannot verify address - geocoding failed"]
  },
  "needs_geocoding": true,
  "geocoding_query": "corner of that big street near the mall",
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "I need a specific street address to dispatch our tech. Can you provide the street number and name + ZIP? (Example: '123 Main St, 90210')",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 5
  },
  "conversation_stage": "collecting_info"
}
```

---

### Example 8: Customer Never Confirms

#### Normal flow through confirmation request
**Turn 3: Customer goes silent after confirmation request**

**After 3-minute timeout, Twilio server sends follow-up:**

**Dispatch API Response (Follow-up trigger):**
```json
{
  "next_action": {
    "action_type": "continue_conversation",
    "message_to_customer": "Still need that plumbing repair? Reply YES to confirm your 2-4 PM slot today, or let me know if you need a different time.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 5
  },
  "conversation_stage": "confirming"
}
```

**After 5 more minutes of silence:**
```json
{
  "next_action": {
    "action_type": "end_conversation",
    "message_to_customer": "No worries! Feel free to call us again when you're ready to schedule. Thanks for contacting Prime Plumbing!",
    "follow_up_needed": false
  },
  "conversation_stage": "rejected"
}
```

---

### Example 9: Travel Time Constraint Violation

**Customer SMS:** "Toilet won't flush, 45678 Remote Valley Rd, 91390" (Acton, CA - 45 miles from LA)

**Twilio Server → Dispatch API Request:**
```json
{
  "caller_phone": "+12125557777",
  "current_message": "Toilet won't flush, 45678 Remote Valley Rd, 91390",
  "business_settings": {
    "service_radius_miles": 50,
    "max_travel_time_minutes": 60,
    "max_travel_distance_miles": 25
  },
  "existing_calendar": [
    {
      "event_id": "job_morning",
      "start_time": "2025-08-06T14:00:00Z",
      "end_time": "2025-08-06T15:00:00Z", 
      "location_address": "123 Downtown LA",
      "location_latitude": 34.0522,
      "location_longitude": -118.2437
    }
  ]
}
```

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "toilet_repair",
    "job_confidence": 0.91,
    "customer_address": "45678 Remote Valley Rd, Acton, CA 91390",
    "address_verified": true,
    "address_latitude": 34.4839,
    "address_longitude": -118.1969
  },
  "validation": {
    "service_area_valid": true,
    "address_reachable": false,
    "validation_errors": ["Travel time exceeds maximum: 75 minutes > 60 minute limit", "Travel distance exceeds maximum: 35 miles > 25 mile limit"]
  },
  "proposed_slot": null,
  "next_action": {
    "action_type": "end_conversation", 
    "message_to_customer": "Acton is within our service area but exceeds our travel limits (75 min/35 miles vs our 60 min/25 mile max). Try searching 'plumber Acton CA' for closer options. Thanks for thinking of Prime Plumbing!",
    "follow_up_needed": false
  },
  "conversation_stage": "complete"
}
```

---

### Example 10: Rush Hour vs Off-Peak Travel Calculation

**Customer SMS at 3:30 PM:** "Kitchen sink clogged, 789 Westwood Blvd, 90024"

**Existing Calendar:**
- 2:00-3:00 PM: Job at Downtown LA (34.0522, -118.2437) 
- 5:00-6:00 PM: Job at Santa Monica (34.0195, -118.4912)

**Available Slot Analysis:**
```json
{
  "proposed_slot": {
    "slot_id": "rush_hour_slot",
    "start_time": "2025-08-06T16:15:00Z", 
    "end_time": "2025-08-06T17:45:00Z",
    "travel_calculations": {
      "from_downtown_la": {
        "distance_miles": 8.2,
        "travel_time_rush_hour": 35,
        "travel_time_off_peak": 18,
        "departure_time": "15:40:00Z",
        "traffic_factor": 1.9
      },
      "to_santa_monica": {
        "distance_miles": 6.1, 
        "travel_time_rush_hour": 28,
        "departure_time": "17:45:00Z",
        "traffic_factor": 2.1
      }
    },
    "time_breakdown": {
      "travel_from_previous": 35,
      "buffer_time": 15,
      "job_duration": 60,
      "buffer_time": 15,
      "travel_to_next": 28,
      "total_required": 153,
      "available_gap": 165,
      "feasible": true
    }
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "I can fit your kitchen sink repair today 4:15-5:45 PM (rush hour travel factored in). Cost: $95-$150. Reply YES to confirm.",
    "follow_up_needed": true
  }
}
```

---

### Example 11: After-Hours Emergency Slot (Within Phone Hours)

**Customer SMS at 6:45 PM (after business hours, within phone hours):** "URGENT! Sewage backing up into house! 456 Elm St, 90210"

**Twilio Server → Dispatch API Request:**
```json
{
  "current_message": "URGENT! Sewage backing up into house! 456 Elm St, 90210",
  "business_hours": {
    "tuesday": {"start": "08:00", "end": "18:00"}
  },
  "phone_hours": {
    "tuesday": {"start": "06:00", "end": "22:00"}
  },
  "business_settings": {
    "accept_after_hours_emergency": true,
    "after_hours_emergency_multiplier": 2.5,
    "max_after_hours_jobs_per_day": 1,
    "max_jobs_per_day": 6
  },
  "existing_calendar": [
    {
      "start_time": "2025-08-06T08:00:00Z",
      "end_time": "2025-08-06T18:00:00Z",
      "location_address": "Full day - 6 regular jobs booked"
    }
  ]
}
```

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "sewage_emergency",
    "job_confidence": 0.96,
    "urgency_level": "emergency",
    "urgency_confidence": 0.94,
    "customer_address": "456 Elm St, Los Angeles, CA 90210",
    "address_verified": true
  },
  "validation": {
    "service_area_valid": true,
    "within_business_hours": false,
    "capacity_available": false,
    "after_hours_emergency_available": true,
    "validation_errors": []
  },
  "proposed_slot": {
    "slot_id": "after_hours_emergency_001",
    "start_time": "2025-08-06T18:30:00Z",
    "end_time": "2025-08-06T21:00:00Z", 
    "duration_minutes": 150,
    "price_min": 375.0,
    "price_max": 1000.0,
    "booking_type": "confirmed",
    "slot_type": "after_hours_emergency",
    "multiplier_applied": 2.5
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "🚨 SEWAGE EMERGENCY - I can get our tech there tonight 6:30-9:00 PM (after-hours emergency rate 2.5x: $375-$1000). This is our only after-hours slot today. Reply YES to confirm.",
    "follow_up_needed": true,
    "follow_up_delay_minutes": 2
  },
  "conversation_stage": "confirming"
}
```

---

### Example 12: Call Outside Phone Hours (Fully Closed)

**Customer SMS at 11:30 PM (outside both business and phone hours):** "Emergency! Toilet overflowing! 123 Oak St, 90210"

**Twilio Server → Dispatch API Request:**
```json
{
  "current_message": "Emergency! Toilet overflowing! 123 Oak St, 90210",
  "business_hours": {
    "tuesday": {"start": "08:00", "end": "18:00"}
  },
  "phone_hours": {
    "tuesday": {"start": "06:00", "end": "22:00"}
  },
  "current_time": "2025-08-06T23:30:00Z"
}
```

**Dispatch API Response:**
```json
{
  "extracted_info": {
    "job_type": "toilet_emergency",
    "job_confidence": 0.89,
    "urgency_level": "emergency",
    "customer_address": "123 Oak St, Los Angeles, CA 90210",
    "address_verified": true
  },
  "validation": {
    "service_area_valid": true,
    "within_business_hours": false,
    "within_phone_hours": false,
    "validation_errors": ["Outside phone hours - no service available"]
  },
  "proposed_slot": null,
  "next_action": {
    "action_type": "end_conversation",
    "message_to_customer": "We're currently closed (phone hours: 6 AM - 10 PM). For true emergencies, call our emergency line at +1-555-911-HELP. Otherwise, text us tomorrow after 6 AM. Thanks for thinking of Prime Plumbing!",
    "follow_up_needed": false
  },
  "conversation_stage": "complete"
}
```

---

## Summary

These examples show how the Dispatch Bot AI API handles:

**Happy Paths:**
- Same-day emergency booking with immediate confirmation
- Next-day standard appointment with tentative hold
- Time-aware travel calculation considering rush hour traffic
- Clear communication with appropriate pricing

**Unhappy Paths:**
- Geographic limitations (out of service area)
- Travel time/distance constraint violations
- Low confidence/unclear messages requiring clarification
- Capacity constraints leading to alternative offers
- Emergency situations during off-hours
- Address validation failures
- Customer abandonment scenarios

**New Scheduling Features:**
- **Time-aware travel calculations**: Traffic at 4:00 PM vs 10:00 AM properly factored
- **Travel constraint validation**: Respects `max_travel_time_minutes` and `max_travel_distance_miles`
- **Efficient routing**: Uses lat/lng coordinates from `existing_calendar` for precise travel calculations
- **Separate phone/business hours**: AI accepts calls 6 AM-10 PM, regular work 8 AM-6 PM
- **After-hours emergency slots**: Limited 1 per day with 1.5x-3.0x pricing multiplier
- **No redundant data**: Removed `last_job_location` - derived from calendar instead

The API consistently provides structured responses that enable the Twilio server to take appropriate actions while maintaining a professional, helpful tone throughout all scenarios.
