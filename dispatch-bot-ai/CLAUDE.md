# Never Missed Call AI - TDD Development Roadmap

## Table of Contents

1. [Project Overview & Development Philosophy](#project-overview--development-philosophy)
2. [Incremental Development Milestones](#incremental-development-milestones)
3. [Phase 1: Basic Working System (Weeks 1-3)](#phase-1-basic-working-system-weeks-1-3)
4. [Phase 2: Emergency Detection & Multi-Trade (Weeks 4-6)](#phase-2-emergency-detection--multi-trade-weeks-4-6)
5. [Phase 3: Advanced Scheduling (Weeks 7-9)](#phase-3-advanced-scheduling-weeks-7-9)
6. [Phase 4: Production Features (Weeks 10-12)](#phase-4-production-features-weeks-10-12)
7. [Test-Driven Development Strategy](#test-driven-development-strategy)
8. [Technology Stack & Architecture](#technology-stack--architecture)
9. [Data Models & Implementation Details](#data-models--implementation-details)

---

## 1. Project Overview & Development Philosophy

### 1.1 What We're Building

**Never Missed Call AI** is a stateless, intelligent conversation handler that processes SMS/call conversations for field service businesses. It captures missed calls, extracts customer intent, validates requirements, and schedules appointments automatically.

**Initial Focus**: Plumbing services, business hours only (7 AM - 6 PM), with basic scheduling functionality.

### 1.2 Development Philosophy

**Start Simple, Build Incrementally**: Each phase delivers working software that provides real business value.

**Fail-Fast Approach**: Better to clearly say "no" than create incorrect appointments. When uncertain, fail gracefully with clear messaging.

**Test-Driven Development**: Every feature is driven by comprehensive tests that validate both happy paths and edge cases.

**Real Service Integration**: Use actual Google Maps and OpenAI APIs from the start - these are too critical to mock effectively.

### 1.3 Key Success Principles

1. **Working Software First**: Each milestone produces deployable software
2. **Unit Tests Drive Development**: Write tests before implementing features
3. **Continuous Integration**: Each commit must pass all existing tests
4. **Business Value**: Every feature solves a real customer problem
5. **Performance from Day 1**: API responses under 2 seconds at each phase

---

## 2. Incremental Development Milestones

### 2.1 Development Approach

Each milestone represents a fully working, testable system that can be deployed and used in production. We build confidence through working software at each stage.

### 2.2 Milestone Overview

```
Milestone 1: "Hello World" API (Week 1)
├── Basic FastAPI endpoint
├── Pydantic models for request/response
├── Basic conversation flow test
└── API health check

Milestone 2: Address Validation (Week 1-2)  
├── Google Maps geocoding integration
├── Service area validation
├── Fail-fast error handling
└── Address validation tests

Milestone 3: Basic Scheduling (Week 2-3)
├── Simple appointment slot generation
├── Business hours validation
├── Basic conversation flow
└── End-to-end scheduling tests

Milestone 4: Complete Phase 1 System (Week 3)
├── Conversation timeout handling
├── Twilio SID deduplication
├── OpenAI basic integration
└── Production-ready Phase 1 deployment
```

### 2.3 Continuous Integration Checkpoints

At each milestone:
- All existing tests must pass
- Code coverage must be maintained above 80%
- API performance under 2 seconds
- No breaking changes to existing functionality
- Clear documentation for new features

---

## 3. Phase 1: Basic Working System (Weeks 1-3)

### 3.1 Simplified Scope for Phase 1

**Business Rules**:
- Single trade only: Plumbing services
- Business hours only: 7 AM - 6 PM (no emergency/after-hours logic)
- Service area: 25-mile radius from business address
- Simple scheduling: Next available slot approach

**Core Features**:
- Process missed call SMS messages
- Extract customer problem and address
- Validate address and service area
- Generate basic appointment slots
- Handle confirmations and rejections
- Fail fast on invalid requests

### 3.2 Minimum Viable Conversation Flow

```
1. Customer calls, no answer -> Twilio sends SMS
2. Bot: "Hi from [Business]! What plumbing issue and your address?"
3. Customer: "Leaky faucet, 123 Main St 90210"
4. Bot validates: address → service area → availability
5. Bot: "I can fix your faucet tomorrow 10-12 PM for $150-$200. YES to confirm?"
6. Customer: "YES"
7. Bot: "✅ Confirmed! Plumber arrives 10 AM-12 PM tomorrow. Job #PLB-001."
```

### 3.3 Week-by-Week Development Plan

#### Week 1: Foundation & Testing Framework

**Day 1-2: Project Setup**
```python
# TDD Task List - Week 1
MILESTONE_1_TASKS = [
    "test_api_health_check",           # Test: GET /health returns 200
    "test_basic_request_validation",   # Test: Invalid requests return 422
    "test_conversation_endpoint",      # Test: POST /process accepts valid request
    "test_pydantic_models",           # Test: Request/response model validation
    "implement_basic_fastapi_app",     # Code: Basic FastAPI structure
]
```

**Test-First Implementation**:
1. Write test for health check endpoint
2. Write test for basic request validation
3. Write test for conversation processing endpoint
4. Implement minimal FastAPI app to make tests pass
5. Add structured logging and error handling

**Day 3-5: Core Models and Validation**
```python
MILESTONE_2_TASKS = [
    "test_phone_number_validation",    # Test: Phone format validation
    "test_business_hours_validation",  # Test: Hours validation logic
    "test_address_parsing",           # Test: Address extraction from messages
    "test_twilio_sid_deduplication",  # Test: Duplicate request handling
    "implement_pydantic_models",       # Code: Request/response models
    "implement_basic_validation",      # Code: Input validation logic
]
```

#### Week 2: Address Validation & Service Area

**Day 1-3: Google Maps Integration**
```python
MILESTONE_3_TASKS = [
    "test_google_maps_geocoding",     # Test: Address geocoding (real API)
    "test_service_area_calculation",  # Test: Distance calculation
    "test_invalid_address_handling",  # Test: Failed geocoding scenarios
    "test_out_of_area_rejection",     # Test: Outside service area
    "implement_geocoding_service",    # Code: Google Maps integration
    "implement_distance_validation",  # Code: Service area logic
]
```

**Day 4-5: Fail-Fast Error Handling**
```python
MILESTONE_4_TASKS = [
    "test_graceful_error_responses",  # Test: User-friendly error messages
    "test_external_service_fallback", # Test: API failure handling
    "test_conversation_timeout",      # Test: No response timeout
    "implement_error_handling",       # Code: Exception handling
    "implement_timeout_logic",        # Code: Conversation timeouts
]
```

#### Week 3: Basic Scheduling & OpenAI Integration

**Day 1-3: Simple Appointment Scheduling**
```python
MILESTONE_5_TASKS = [
    "test_business_hours_slots",      # Test: Generate available slots
    "test_appointment_confirmation",  # Test: YES/NO response handling
    "test_slot_availability",        # Test: No double-booking
    "test_job_type_estimation",      # Test: Basic job estimates
    "implement_scheduling_engine",    # Code: Simple slot generation
    "implement_confirmation_logic",   # Code: Response parsing
]
```

**Day 4-5: OpenAI Integration & End-to-End Testing**
```python
MILESTONE_6_TASKS = [
    "test_openai_message_parsing",    # Test: Extract problem + address
    "test_complete_conversation_flow", # Test: Full happy path
    "test_multiple_conversation_turns", # Test: Multi-turn dialogue
    "test_api_performance",           # Test: < 2 second response
    "implement_openai_integration",   # Code: GPT-4 message processing
    "implement_conversation_manager", # Code: Multi-turn handling
]
```

### 3.4 Phase 1 Success Criteria

**Functional Requirements**:
- ✅ Process basic plumbing requests during business hours
- ✅ Validate addresses and reject out-of-service-area requests
- ✅ Generate and confirm appointment slots
- ✅ Handle conversation timeouts gracefully
- ✅ Prevent duplicate processing via Twilio SID

**Performance Requirements**:
- ✅ API response time < 2 seconds (95th percentile)
- ✅ Handle 100 concurrent requests
- ✅ 99% uptime during business hours

**Quality Requirements**:
- ✅ Unit test coverage > 80%
- ✅ Integration tests for all external APIs
- ✅ Error messages are clear and actionable
- ✅ All edge cases handled gracefully

### 3.5 Phase 1 Test Strategy

**Unit Tests** (60% of test suite):
```python
# Core business logic tests
def test_address_validation():
    """Test address parsing and validation"""
    
def test_service_area_calculation():
    """Test distance-based service area validation"""
    
def test_appointment_slot_generation():
    """Test basic scheduling algorithm"""
    
def test_conversation_flow_logic():
    """Test conversation state transitions"""
```

**Integration Tests** (30% of test suite):
```python
# External API integration tests  
def test_google_maps_integration():
    """Test real Google Maps geocoding"""
    
def test_openai_integration():
    """Test real OpenAI message processing"""
    
def test_end_to_end_conversation():
    """Test complete conversation flow"""
```

**Performance Tests** (10% of test suite):
```python
# Performance and load tests
def test_api_response_time():
    """Test API performance requirements"""
    
def test_concurrent_request_handling():
    """Test system under load"""
```

---

## 4. Phase 2: Emergency Detection & Multi-Trade (Weeks 4-6)

### 4.1 Phase 2 Scope

**New Features**:
- Emergency keyword detection for all 5 trades
- Time-based pricing multipliers (1.5x-3x)
- After-hours emergency handling (6 PM - 7 AM)
- Customer choice between immediate emergency vs next morning
- Support for all trades: Plumbing, Electrical, HVAC, Locksmith, Garage Door

### 4.2 Emergency Detection Requirements

**Emergency Keywords by Trade**:
```python
EMERGENCY_KEYWORDS = {
    "plumbing": ["flooding", "burst pipe", "no hot water", "sewage backup"],
    "electrical": ["sparks", "smoke", "power out", "exposed wires"], 
    "hvac": ["no heat", "no cooling", "gas smell", "carbon monoxide"],
    "locksmith": ["locked out", "break-in", "security breach"],
    "garage_door": ["won't close", "stuck open", "spring broken"]
}
```

**Time-Based Pricing**:
- Work hours (7 AM - 6 PM): 1.0x base rate
- Evening (6 PM - 8 PM): 1.5x emergency rate  
- Night (8 PM - 7 AM): 2.5x emergency rate OR 1.25x early morning (6 AM start)

### 4.3 Phase 2 Development Tasks

#### Week 4: Emergency Detection Engine

**Test-Driven Tasks**:
```python
PHASE_2_WEEK_1 = [
    "test_emergency_keyword_detection",      # Test: Emergency detection per trade
    "test_urgency_confidence_scoring",       # Test: Confidence levels
    "test_false_positive_prevention",        # Test: Avoid false emergencies
    "test_context_aware_detection",          # Test: Context boosts confidence
    "implement_emergency_detector",          # Code: Emergency detection engine
    "implement_confidence_scoring",          # Code: Confidence algorithms
]
```

#### Week 5: Time-Based Pricing & After-Hours Logic  

**Test-Driven Tasks**:
```python
PHASE_2_WEEK_2 = [
    "test_time_based_pricing_calculation",   # Test: Pricing multipliers
    "test_after_hours_customer_choice",      # Test: Emergency vs morning
    "test_weekend_emergency_handling",       # Test: Weekend pricing
    "test_pricing_edge_cases",              # Test: Boundary conditions
    "implement_pricing_calculator",          # Code: Time-based pricing
    "implement_customer_choice_logic",       # Code: Emergency choices
]
```

#### Week 6: Multi-Trade Support & Integration

**Test-Driven Tasks**:
```python
PHASE_2_WEEK_3 = [
    "test_trade_specific_job_estimates",     # Test: Job estimates per trade
    "test_multi_trade_intent_classification", # Test: Trade detection
    "test_trade_specific_scheduling",        # Test: Different scheduling rules
    "test_complete_emergency_flows",         # Test: End-to-end emergency
    "implement_multi_trade_support",         # Code: All 5 trades
    "implement_trade_routing",              # Code: Trade-specific logic
]
```

### 4.4 Phase 2 Success Criteria

- ✅ Emergency detection accuracy > 90% across all trades
- ✅ Time-based pricing calculations are precise
- ✅ Customer emergency choice scenarios work correctly  
- ✅ All 5 trades supported with proper job classification
- ✅ After-hours emergency handling functions properly

---

## 5. Phase 3: Advanced Scheduling (Weeks 7-9)

### 5.1 Phase 3 Scope

**Advanced Features**:
- Google Maps Traffic API integration
- Real-time travel time calculations  
- Rush hour vs off-peak scheduling optimization
- Multi-day appointment optimization
- Weather-sensitive scheduling adjustments

### 5.2 Phase 3 Development Tasks

#### Week 7: Traffic Integration & Travel Time Optimization

**Test-Driven Tasks**:
```python
PHASE_3_WEEK_1 = [
    "test_google_traffic_integration",       # Test: Real traffic API calls
    "test_rush_hour_travel_calculations",    # Test: Peak vs off-peak times
    "test_travel_time_constraints",          # Test: Max travel limits
    "test_route_optimization",              # Test: Minimize total travel
    "implement_traffic_service",             # Code: Google Traffic API
    "implement_travel_optimization",         # Code: Smart routing
]
```

#### Week 8: Advanced Scheduling Algorithm

**Test-Driven Tasks**:  
```python
PHASE_3_WEEK_2 = [
    "test_calendar_conflict_detection",      # Test: Prevent double booking
    "test_multi_day_optimization",          # Test: Schedule across days
    "test_job_buffer_time_calculation",     # Test: Job-specific buffers
    "test_schedule_density_optimization",    # Test: Maximize daily efficiency
    "implement_advanced_scheduler",          # Code: Optimization algorithms
    "implement_conflict_resolution",         # Code: Handle scheduling conflicts
]
```

#### Week 9: Weather & External Factor Integration

**Test-Driven Tasks**:
```python  
PHASE_3_WEEK_3 = [
    "test_weather_impact_scheduling",        # Test: Weather delays
    "test_external_service_fallbacks",       # Test: API failure handling
    "test_performance_under_load",          # Test: Complex scheduling load
    "test_scheduling_accuracy_metrics",      # Test: Optimization effectiveness
    "implement_weather_integration",         # Code: Weather API
    "implement_fallback_mechanisms",         # Code: Graceful degradation
]
```

---

## 6. Phase 4: Production Features (Weeks 10-12)

### 6.1 Phase 4 Scope

**Production Features**:
- Comprehensive monitoring and alerting
- Performance optimization and caching
- Security hardening and rate limiting  
- Advanced analytics and business metrics
- Multi-business support architecture

### 6.2 Phase 4 Development Tasks

#### Week 10: Monitoring & Observability

**Test-Driven Tasks**:
```python
PHASE_4_WEEK_1 = [
    "test_prometheus_metrics_collection",    # Test: Metrics accuracy
    "test_alerting_rules_trigger",          # Test: Alert conditions
    "test_performance_monitoring",          # Test: Response time tracking
    "test_error_rate_monitoring",           # Test: Error rate alerts
    "implement_metrics_collection",          # Code: Prometheus integration
    "implement_alerting_system",            # Code: Grafana dashboards
]
```

#### Week 11: Performance & Security

**Test-Driven Tasks**:
```python
PHASE_4_WEEK_2 = [
    "test_response_caching_effectiveness",   # Test: Cache hit rates
    "test_rate_limiting_enforcement",        # Test: Rate limit protection
    "test_security_vulnerability_scanning",  # Test: Security audit
    "test_concurrent_load_handling",         # Test: 1000+ concurrent users
    "implement_intelligent_caching",         # Code: Performance optimization
    "implement_security_hardening",          # Code: Security measures
]
```

#### Week 12: Business Analytics & Multi-Tenant Support

**Test-Driven Tasks**:
```python
PHASE_4_WEEK_3 = [
    "test_business_analytics_accuracy",      # Test: Conversion metrics
    "test_multi_business_data_isolation",    # Test: Tenant separation
    "test_business_performance_insights",    # Test: Analytics reports
    "test_scalability_architecture",         # Test: 100+ business support
    "implement_analytics_engine",            # Code: Business insights
    "implement_multi_tenant_support",        # Code: Scalable architecture
]
```

---

## 7. Test-Driven Development Strategy

### 7.1 TDD Workflow for Each Feature

**Red-Green-Refactor Cycle**:
```python
# Step 1: RED - Write failing test
def test_emergency_detection():
    detector = EmergencyDetector()
    result = detector.detect_emergency("burst pipe flooding basement", "plumbing")
    assert result["is_emergency"] == True
    assert result["confidence"] > 0.8

# Step 2: GREEN - Make test pass with minimal code
class EmergencyDetector:
    def detect_emergency(self, message, trade):
        if "burst pipe" in message.lower():
            return {"is_emergency": True, "confidence": 0.9}
        return {"is_emergency": False, "confidence": 0.0}

# Step 3: REFACTOR - Improve implementation while keeping tests green
class EmergencyDetector:
    KEYWORDS = {"plumbing": ["burst pipe", "flooding", "sewage backup"]}
    
    def detect_emergency(self, message, trade):
        keywords = self.KEYWORDS.get(trade, [])
        detected = [k for k in keywords if k in message.lower()]
        confidence = min(len(detected) * 0.4, 1.0)
        return {"is_emergency": confidence >= 0.6, "confidence": confidence}
```

### 7.2 Test Categories by Priority

**1. Unit Tests (70% of test suite)**
- Business logic validation
- Input/output transformations  
- Edge case handling
- Error condition testing

**2. Integration Tests (20% of test suite)**
- External API interactions (Google Maps, OpenAI)
- Database operations (if added later)
- Service-to-service communication

**3. End-to-End Tests (10% of test suite)**
- Complete conversation flows
- API contract validation
- Performance requirements

### 7.3 Test Coverage Requirements

```python
# Minimum test coverage by component
TEST_COVERAGE_REQUIREMENTS = {
    "core_business_logic": 95,    # Emergency detection, pricing, scheduling
    "api_endpoints": 90,          # Request validation, response formatting
    "external_services": 85,      # Google Maps, OpenAI integration
    "error_handling": 90,         # Exception scenarios, fallbacks
    "utilities": 80,              # Helper functions, data transformations
}
```

### 7.4 Testing External Services

**Google Maps API Testing**:
```python
class TestGoogleMapsIntegration:
    """Test real Google Maps API with known addresses"""
    
    def test_valid_address_geocoding(self):
        """Test geocoding with known valid address"""
        service = GeocodingService()
        result = service.geocode("1600 Amphitheatre Parkway, Mountain View, CA")
        
        assert result.latitude is not None
        assert result.longitude is not None
        assert "Mountain View" in result.formatted_address
        assert result.confidence > 0.9
    
    def test_invalid_address_handling(self):
        """Test graceful handling of invalid addresses"""
        service = GeocodingService()
        result = service.geocode("123 Fake Street, Nowhere, XX 00000")
        
        assert result is None or result.confidence < 0.5
```

**OpenAI API Testing**:
```python
class TestOpenAIIntegration:
    """Test real OpenAI API with controlled prompts"""
    
    def test_message_intent_extraction(self):
        """Test intent extraction from customer messages"""
        service = NLPService()
        result = service.extract_intent(
            "My faucet is leaking badly at 123 Main St 90210"
        )
        
        assert result["job_type"] in ["faucet_repair", "leak_repair"]
        assert result["urgency_level"] in ["normal", "urgent"]
        assert "123 Main St" in result["customer_address"]
        assert result["confidence"] > 0.7
```

---

## 8. Technology Stack & Architecture

### 8.1 Core Technology Stack

```python
# Production Stack
TECHNOLOGY_STACK = {
    "runtime": "Python 3.9+",
    "web_framework": "FastAPI",
    "validation": "Pydantic v2",
    "testing": "pytest + pytest-asyncio",
    "http_client": "httpx",
    "deployment": "Docker",
    "monitoring": "Prometheus + Grafana",
}

# External Services
EXTERNAL_SERVICES = {
    "geocoding": "Google Maps Geocoding API",
    "traffic": "Google Maps Distance Matrix API",
    "llm": "OpenAI GPT-4",
    "communication": "Twilio (handled externally)",
}
```

### 8.2 Stateless Architecture Principles

**No Persistent State**:
- All context provided in each API request
- No session storage or user state management
- Each request contains complete conversation history
- Twilio SID prevents duplicate processing

**Request Processing Pipeline**:
```python
REQUEST_PROCESSING_PIPELINE = [
    "validate_request_schema",      # Pydantic validation
    "check_twilio_sid_deduplication", # Prevent duplicates  
    "extract_intent_and_entities",  # OpenAI processing
    "validate_business_rules",      # Service area, hours
    "find_available_slots",         # Basic scheduling
    "calculate_pricing",           # Time-based pricing
    "generate_response",           # Customer message
    "log_interaction"              # Structured logging
]
```

### 8.3 Project Structure

```
nmc-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request_response.py    # API models
│   │   └── business.py           # Business logic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── conversation_processor.py # Main processing logic
│   │   ├── geocoding_service.py   # Google Maps integration
│   │   ├── nlp_service.py         # OpenAI integration
│   │   ├── emergency_detector.py  # Emergency detection
│   │   ├── pricing_calculator.py  # Time-based pricing
│   │   └── scheduler.py          # Appointment scheduling
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration
│   │   ├── exceptions.py         # Custom exceptions
│   │   └── logging.py            # Structured logging
│   └── utils/
│       ├── __init__.py
│       ├── datetime_utils.py      # Time handling
│       └── distance_utils.py      # Geographic calculations
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Test configuration
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── pytest.ini
```

---

## 9. Data Models & Implementation Details

### 9.1 Core Pydantic Models

**Phase 1 Basic Models**:
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Basic Enums for Phase 1
class TradeType(str, Enum):
    PLUMBING = "plumbing"
    # Additional trades added in Phase 2

class UrgencyLevel(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"  # Added in Phase 2
    EMERGENCY = "emergency"  # Added in Phase 2

class ConversationStage(str, Enum):
    INITIAL = "initial"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    COMPLETE = "complete"
    TIMEOUT = "timeout"

# Phase 1 Request Model (Simplified)
class BasicDispatchRequest(BaseModel):
    """Simplified request model for Phase 1"""
    conversation_sid: str = Field(..., min_length=10)  # Twilio SID for deduplication
    caller_phone: str = Field(..., regex=r'^\+\d{10,15}$')
    current_message: str = Field(..., min_length=1, max_length=1000)
    
    # Business Configuration
    business_name: str = Field(..., min_length=3, max_length=100)
    trade_type: TradeType = TradeType.PLUMBING
    
    # Business Hours (simplified for Phase 1)
    business_hours_start: str = Field(default="07:00", regex=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    business_hours_end: str = Field(default="18:00", regex=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    
    # Service Area
    business_address: str = Field(..., min_length=10)
    service_radius_miles: int = Field(default=25, ge=1, le=100)
    
    # Basic Job Estimates
    basic_job_estimate_min: float = Field(default=100.0, ge=25.0)
    basic_job_estimate_max: float = Field(default=300.0, ge=50.0)
    
    # Conversation History (optional for Phase 1)
    conversation_history: List[str] = Field(default=[])

# Phase 1 Response Model (Simplified)  
class BasicDispatchResponse(BaseModel):
    """Simplified response model for Phase 1"""
    
    # Extracted Information
    customer_address: Optional[str] = None
    job_type: Optional[str] = None
    urgency_level: UrgencyLevel = UrgencyLevel.NORMAL
    
    # Validation Results
    address_valid: bool = False
    in_service_area: bool = False
    within_business_hours: bool = True
    
    # Proposed Action
    next_message: str = Field(..., min_length=10)
    conversation_stage: ConversationStage
    appointment_offered: bool = False
    
    # Appointment Details (if offered)
    proposed_start_time: Optional[datetime] = None
    proposed_end_time: Optional[datetime] = None
    estimated_price_min: Optional[float] = None
    estimated_price_max: Optional[float] = None
    
    # Metadata
    requires_followup: bool = False
    conversation_timeout_minutes: int = Field(default=5)
```

### 9.2 Phase 1 Service Implementation Templates

**Basic Geocoding Service**:
```python
class GeocodingService:
    """Simple Google Maps geocoding for Phase 1"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    async def geocode_address(self, address: str) -> Optional[dict]:
        """Geocode address and return lat/lng if valid"""
        try:
            params = {
                "address": address,
                "key": self.api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                data = response.json()
                
                if data["status"] == "OK" and data["results"]:
                    location = data["results"][0]["geometry"]["location"]
                    return {
                        "latitude": location["lat"],
                        "longitude": location["lng"],
                        "formatted_address": data["results"][0]["formatted_address"]
                    }
                    
                return None
                
        except Exception as e:
            logger.error(f"Geocoding failed for {address}: {str(e)}")
            return None
            
    def calculate_distance(self, lat1: float, lng1: float, 
                          lat2: float, lng2: float) -> float:
        """Calculate distance between two points in miles"""
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine formula
        R = 3959  # Earth's radius in miles
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
```

**Basic Conversation Processor**:
```python
class ConversationProcessor:
    """Main conversation processing logic for Phase 1"""
    
    def __init__(self, geocoding_service: GeocodingService, 
                 openai_client, business_lat: float, business_lng: float):
        self.geocoding = geocoding_service
        self.openai_client = openai_client
        self.business_lat = business_lat
        self.business_lng = business_lng
        
    async def process_message(self, request: BasicDispatchRequest) -> BasicDispatchResponse:
        """Process a single conversation turn"""
        
        # Step 1: Extract information from message
        extracted_info = await self._extract_message_info(
            request.current_message, request.conversation_history
        )
        
        # Step 2: Validate address if provided
        address_result = None
        if extracted_info.get("address"):
            address_result = await self._validate_address(
                extracted_info["address"], request.service_radius_miles
            )
        
        # Step 3: Determine conversation stage and response
        return self._generate_response(request, extracted_info, address_result)
    
    async def _extract_message_info(self, message: str, history: List[str]) -> dict:
        """Extract job type and address using OpenAI (simplified)"""
        
        system_prompt = """
        Extract plumbing job information from customer message.
        Return JSON with: job_type, customer_address, confidence_score (0-1).
        Common job types: faucet_repair, toilet_repair, drain_cleaning, pipe_repair.
        """
        
        user_prompt = f"Customer message: {message}"
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            # Fallback: Basic keyword detection
            return self._fallback_extraction(message)
    
    def _fallback_extraction(self, message: str) -> dict:
        """Simple keyword-based extraction as fallback"""
        message_lower = message.lower()
        
        # Basic job type detection
        job_type = "general_plumbing"
        if any(word in message_lower for word in ["faucet", "tap", "sink"]):
            job_type = "faucet_repair"
        elif any(word in message_lower for word in ["toilet", "bathroom"]):
            job_type = "toilet_repair"
        elif any(word in message_lower for word in ["drain", "clog", "backup"]):
            job_type = "drain_cleaning"
            
        # Basic address extraction (look for numbers + common address words)
        import re
        address_pattern = r'\d+.*(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|way|ln|lane)'
        address_match = re.search(address_pattern, message_lower)
        address = address_match.group(0) if address_match else None
        
        return {
            "job_type": job_type,
            "customer_address": address,
            "confidence_score": 0.6 if address else 0.3
        }
```

### 9.3 Phase 1 Testing Templates

**Basic Unit Tests**:
```python
class TestConversationProcessor:
    """Unit tests for Phase 1 conversation processing"""
    
    @pytest.fixture
    def processor(self):
        geocoding_service = Mock()
        openai_client = Mock()
        return ConversationProcessor(geocoding_service, openai_client, 34.0522, -118.2437)
    
    def test_extract_faucet_repair_request(self, processor):
        """Test extraction of faucet repair from customer message"""
        message = "My kitchen faucet is leaking at 123 Main St"
        
        result = processor._fallback_extraction(message)
        
        assert result["job_type"] == "faucet_repair"
        assert "123 main st" in result["customer_address"].lower()
        assert result["confidence_score"] > 0.5
    
    def test_address_validation_in_service_area(self, processor):
        """Test address validation for in-service-area address"""
        # Mock geocoding service
        processor.geocoding.geocode_address.return_value = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "formatted_address": "123 Main St, Los Angeles, CA"
        }
        
        result = await processor._validate_address("123 Main St", 25)
        
        assert result["valid"] == True
        assert result["in_service_area"] == True
        assert result["distance_miles"] < 25
        
    def test_conversation_timeout_handling(self, processor):
        """Test that conversations timeout after no response"""
        request = BasicDispatchRequest(
            conversation_sid="test_sid",
            caller_phone="+12125551234",
            current_message="timeout_test",
            business_name="Test Plumbing"
        )
        
        # Simulate timeout scenario
        response = await processor.process_message(request)
        
        assert response.conversation_stage == ConversationStage.TIMEOUT
        assert "no longer available" in response.next_message.lower()
```

---

## 10. Getting Started - Phase 1 Implementation

### 10.1 Day 1: Setup and First Test

**Create the basic project structure and write your first failing test:**

```bash
mkdir nmc-ai
cd nmc-ai
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pytest pytest-asyncio httpx pydantic

# Create basic structure
mkdir -p app/{api,models,services,core} tests/{unit,integration,e2e}
touch app/__init__.py app/main.py tests/__init__.py tests/conftest.py
```

**First Test (tests/unit/test_health_check.py)**:
```python
from fastapi.testclient import TestClient

def test_health_check_endpoint():
    """Test: API health check returns 200 OK"""
    from app.main import app
    client = TestClient(app)
    
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

**Make it pass (app/main.py)**:
```python
from fastapi import FastAPI

app = FastAPI(title="Never Missed Call AI", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nmc-ai"}
```

**Run your first test:**
```bash
pytest tests/unit/test_health_check.py -v
```

### 10.2 Success Criteria for Each Day

- **Day 1**: Health check test passes
- **Day 3**: Basic request validation tests pass
- **Day 5**: Address geocoding integration tests pass  
- **Week 1 End**: Complete basic conversation flow test passes
- **Phase 1 End**: All acceptance criteria met and deployable system

This TDD roadmap ensures you always have working software and build confidence through incremental development. Each test drives the implementation, and each phase delivers real business value.
