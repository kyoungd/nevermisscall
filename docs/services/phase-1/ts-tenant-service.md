# ts-tenant-service Design Document

## Service Overview

**Service Name**: ts-tenant-service  
**Port**: 3302  
**Phase**: 1 - Identity & Onboarding  
**Purpose**: Business onboarding, configuration management, and tenant lifecycle  

## Business Requirements

### Primary Functions
- Business registration and onboarding workflow
- Business configuration management (hours, pricing, settings)
- Service area and trade type configuration
- Onboarding progress tracking
- Basic business profile management

### Success Criteria
- New business onboarding completes in < 5 minutes
- Business settings are saved and retrievable
- Onboarding progress is tracked accurately
- Service area validation works correctly
- Business configuration supports all Phase 1 features

## Technical Specification

### Technology Stack
- **Runtime**: Python 3.10+
- **Framework**: FastAPI with pydantic for data validation
- **Database**: PostgreSQL with asyncpg and database connection pooling
- **External APIs**: Google Maps Geocoding API with httpx for address validation
- **ASGI Server**: uvicorn for production deployment

### Service Architecture

```mermaid
graph TB
    subgraph "ts-tenant-service (Port 3302)"
        FastAPIApp[FastAPI Application]
        TenantRouter[TenantRouter]
        OnboardingRouter[OnboardingRouter]
        TenantService[TenantService]
        ValidationService[ValidationService]
        Database[(PostgreSQL<br/>nevermisscall)]
    end
    
    WebUI[web-ui] --> FastAPIApp
    TSAuth[ts-auth-service] --> FastAPIApp
    PNSProvision[pns-provisioning-service] --> FastAPIApp
    
    FastAPIApp --> TenantRouter
    FastAPIApp --> OnboardingRouter
    TenantRouter --> TenantService
    OnboardingRouter --> TenantService
    TenantService --> ValidationService
    TenantService --> Database
    ValidationService --> GoogleMapsAPI[Google Maps API]
```

## API Endpoints

### Tenant Management

#### POST /tenants
**Purpose**: Create new business tenant during onboarding  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "businessName": "Smith Plumbing Services",
  "businessAddress": "123 Main St, Los Angeles, CA 90210",
  "businessPhone": "+12125551234",
  "tradeType": "plumbing",
  "ownerEmail": "john@smithplumbing.com",
  "serviceRadiusMiles": 25
}
```
**Response (201)**:
```json
{
  "success": true,
  "tenant": {
    "id": "tenant-uuid",
    "businessName": "Smith Plumbing Services",
    "businessAddress": "123 Main St, Los Angeles, CA 90210",
    "businessPhone": "+12125551234",
    "tradeType": "plumbing",
    "serviceRadiusMiles": 25,
    "onboardingStep": 2,
    "onboardingCompleted": false,
    "createdAt": "2024-01-01T10:00:00Z"
  }
}
```

#### GET /tenants/:tenantId
**Purpose**: Get tenant information  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "tenant": {
    "id": "tenant-uuid",
    "businessName": "Smith Plumbing Services",
    "businessAddress": "123 Main St, Los Angeles, CA 90210",
    "businessPhone": "+12125551234",
    "tradeType": "plumbing",
    "serviceRadiusMiles": 25,
    "businessHoursStart": "07:00",
    "businessHoursEnd": "18:00",
    "businessTimezone": "America/Los_Angeles",
    "onboardingCompleted": true,
    "phoneNumberProvisioned": true,
    "createdAt": "2024-01-01T10:00:00Z"
  }
}
```

#### PUT /tenants/:tenantId
**Purpose**: Update tenant configuration  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "businessName": "Smith Plumbing & Heating",
  "serviceRadiusMiles": 30,
  "businessHoursStart": "08:00",
  "businessHoursEnd": "17:00"
}
```
**Response (200)**:
```json
{
  "success": true,
  "tenant": {
    "id": "tenant-uuid",
    "businessName": "Smith Plumbing & Heating",
    "serviceRadiusMiles": 30,
    "businessHoursStart": "08:00",
    "businessHoursEnd": "17:00",
    "updatedAt": "2024-01-01T11:00:00Z"
  }
}
```

### Onboarding Management

#### GET /tenants/:tenantId/onboarding
**Purpose**: Get onboarding progress  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "onboarding": {
    "tenantId": "tenant-uuid",
    "currentStep": 3,
    "totalSteps": 5,
    "completedSteps": [
      {
        "step": 1,
        "name": "business_info",
        "completed": true,
        "completedAt": "2024-01-01T10:00:00Z"
      },
      {
        "step": 2,
        "name": "phone_number",
        "completed": true,
        "completedAt": "2024-01-01T10:05:00Z"
      }
    ],
    "nextStep": {
      "step": 3,
      "name": "ai_configuration",
      "required": true
    }
  }
}
```

#### PUT /tenants/:tenantId/onboarding/step
**Purpose**: Update onboarding step progress  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "step": 3,
  "completed": true,
  "data": {
    "greetingTemplate": "Hi! Sorry we missed your call at Smith Plumbing. How can we help?",
    "pricingMin": 150,
    "pricingMax": 350
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "onboarding": {
    "currentStep": 4,
    "stepCompleted": true,
    "nextStep": {
      "step": 4,
      "name": "test_setup",
      "required": false
    }
  }
}
```

### Business Settings Management

#### GET /tenants/:tenantId/settings
**Purpose**: Get business operational settings  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "settings": {
    "tenantId": "tenant-uuid",
    "greetingTemplate": "Hi! Sorry we missed your call at {businessName}. How can we help?",
    "aiTakeoverDelaySeconds": 60,
    "basicJobEstimateMin": 150.00,
    "basicJobEstimateMax": 350.00,
    "businessHours": {
      "start": "07:00",
      "end": "18:00",
      "timezone": "America/Los_Angeles"
    }
  }
}
```

#### PUT /tenants/:tenantId/settings
**Purpose**: Update business settings  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "greetingTemplate": "Hello! You've reached Smith Plumbing. We're busy helping another customer. What plumbing issue can we help with?",
  "aiTakeoverDelaySeconds": 45,
  "basicJobEstimateMin": 175.00,
  "basicJobEstimateMax": 400.00
}
```
**Response (200)**:
```json
{
  "success": true,
  "settings": {
    "greetingTemplate": "Hello! You've reached Smith Plumbing...",
    "aiTakeoverDelaySeconds": 45,
    "basicJobEstimateMin": 175.00,
    "basicJobEstimateMax": 400.00,
    "updatedAt": "2024-01-01T12:00:00Z"
  }
}
```

### Validation Endpoints

#### POST /tenants/validate-address
**Purpose**: Validate business address using Google Maps  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "address": "123 Main St, Los Angeles, CA 90210"
}
```
**Response (200)**:
```json
{
  "valid": true,
  "address": {
    "formatted": "123 Main St, Los Angeles, CA 90210, USA",
    "latitude": 34.0522,
    "longitude": -118.2437,
    "city": "Los Angeles",
    "state": "CA",
    "zipCode": "90210"
  }
}
```

#### POST /tenants/validate-service-area
**Purpose**: Check if address is within service area  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "customerAddress": "456 Oak St, Los Angeles, CA 90211"
}
```
**Response (200)**:
```json
{
  "inServiceArea": true,
  "distance": {
    "miles": 12.5,
    "maxRadius": 25
  },
  "customerLocation": {
    "latitude": 34.0622,
    "longitude": -118.2537
  }
}
```

## Data Models

### Tenant Entity
```python
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class Tenant(BaseModel):
    id: str
    business_name: str
    business_address: str
    trade_type: Literal['plumbing', 'electrical', 'hvac', 'locksmith', 'garage_door']
    service_radius_miles: int
    
    # Onboarding tracking
    onboarding_step: int
    onboarding_completed: bool
    phone_number_provisioned: bool
    
    # Business hours (simplified for Phase 1)
    business_hours_start: str  # "07:00"
    business_hours_end: str    # "18:00"
    business_timezone: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Set after phone provisioning
    business_phone: Optional[str] = None
    business_latitude: Optional[float] = None
    business_longitude: Optional[float] = None
```

### Business Settings Entity
```python
from pydantic import BaseModel
from datetime import datetime

class BusinessSettings(BaseModel):
    id: str
    tenant_id: str
    
    # AI Configuration
    greeting_template: str
    ai_takeover_delay_seconds: int
    
    # Basic Pricing
    basic_job_estimate_min: float
    basic_job_estimate_max: float
    
    # Metadata
    created_at: datetime
    updated_at: datetime
```

### Onboarding Progress
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class OnboardingStep(BaseModel):
    step: int
    name: str
    completed: bool
    required: bool
    completed_at: Optional[datetime] = None

class OnboardingProgress(BaseModel):
    tenant_id: str
    current_step: int
    total_steps: int
    completed_steps: List[OnboardingStep]
```

## Database Schema

### Tenants Table
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(255) NOT NULL,
    business_address TEXT NOT NULL,
    business_phone VARCHAR(20), -- Set after provisioning
    business_latitude DECIMAL(10, 8),
    business_longitude DECIMAL(11, 8),
    trade_type VARCHAR(50) DEFAULT 'plumbing',
    service_radius_miles INTEGER DEFAULT 25,
    
    -- Onboarding tracking
    onboarding_step INTEGER DEFAULT 1,
    onboarding_completed BOOLEAN DEFAULT false,
    phone_number_provisioned BOOLEAN DEFAULT false,
    
    -- Business hours (simplified)
    business_hours_start TIME DEFAULT '07:00',
    business_hours_end TIME DEFAULT '18:00',
    business_timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Business Settings Table
```sql
CREATE TABLE business_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE,
    
    -- AI Configuration
    greeting_template TEXT DEFAULT 'Hi! Sorry we missed your call at {businessName}. How can we help?',
    ai_takeover_delay_seconds INTEGER DEFAULT 60,
    
    -- Basic Pricing
    basic_job_estimate_min DECIMAL(10,2) DEFAULT 150.00,
    basic_job_estimate_max DECIMAL(10,2) DEFAULT 300.00,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_business_settings_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_tenants_business_location ON tenants (business_latitude, business_longitude);
CREATE INDEX idx_tenants_trade_type ON tenants (trade_type);
CREATE INDEX idx_tenants_onboarding ON tenants (onboarding_completed, onboarding_step);
CREATE INDEX idx_business_settings_tenant ON business_settings (tenant_id);
```

## Business Logic

### Onboarding Workflow
```python
from pydantic import BaseModel
from typing import List

class OnboardingStepDefinition(BaseModel):
    step: int
    name: str
    required: bool

onboarding_steps = [
    OnboardingStepDefinition(step=1, name='business_info', required=True),
    OnboardingStepDefinition(step=2, name='phone_number', required=True),
    OnboardingStepDefinition(step=3, name='ai_configuration', required=True),
    OnboardingStepDefinition(step=4, name='test_setup', required=False),
    OnboardingStepDefinition(step=5, name='complete', required=True)
]
```

**Step 1 - Business Info**: Business name, address, trade type, service radius  
**Step 2 - Phone Number**: Trigger phone number provisioning  
**Step 3 - AI Configuration**: Greeting template and basic pricing  
**Step 4 - Test Setup**: Optional testing of the system  
**Step 5 - Complete**: Mark onboarding as finished  

### Address Validation Process
1. **Google Maps Geocoding**: Convert address to lat/lng coordinates
2. **Store Coordinates**: Save business location for service area calculations
3. **Validation Response**: Return formatted address and coordinates
4. **Error Handling**: Graceful fallback for invalid addresses

### Service Area Validation
1. **Get Business Location**: Retrieve stored lat/lng from database
2. **Geocode Customer Address**: Convert customer address to coordinates
3. **Calculate Distance**: Use haversine formula for distance calculation
4. **Check Radius**: Compare distance to service radius setting
5. **Return Result**: Boolean result with distance information

## Security Considerations

### Authorization
- All endpoints require valid JWT token from ts-auth-service
- Tenant ID validation: Users can only access their own tenant data
- Role-based access control (owner role required for most operations)

### Data Protection
- Business address and contact information encrypted at rest
- API rate limiting to prevent abuse
- Input validation and sanitization for all endpoints

### External API Security
- Google Maps API key secured and rate limited
- Geocoding results cached to reduce API usage
- Fallback handling for API failures

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "TENANT_NOT_FOUND",
    "message": "Business tenant not found",
    "details": {
      "tenantId": "invalid-uuid"
    }
  }
}
```

### Common Error Codes
- `TENANT_NOT_FOUND`: Tenant ID doesn't exist
- `UNAUTHORIZED_TENANT_ACCESS`: User accessing wrong tenant
- `INVALID_ADDRESS`: Address validation failed
- `ONBOARDING_STEP_INVALID`: Invalid onboarding step progression
- `GEOCODING_FAILED`: Google Maps API error
- `SERVICE_AREA_CALCULATION_FAILED`: Distance calculation error

## Testing Strategy

### Unit Tests
- Tenant CRUD operations
- Onboarding step progression logic
- Address validation and geocoding
- Service area calculation accuracy
- Business settings management

### Integration Tests
- Full onboarding workflow
- Google Maps API integration
- Database operations and constraints
- Service-to-service communication

### End-to-End Tests
- Complete business registration flow
- Settings updates and retrieval
- Address and service area validation

## Performance Requirements

- **Tenant Creation**: < 1000ms (95th percentile)
- **Settings Updates**: < 500ms (95th percentile)
- **Address Validation**: < 2000ms (includes Google Maps API)
- **Service Area Check**: < 300ms (95th percentile)
- **Concurrent Operations**: Support 50+ simultaneous tenant operations

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# Google Maps API
GOOGLE_MAPS_API_KEY=your-api-key-here

# Default Business Settings
DEFAULT_SERVICE_RADIUS=25
DEFAULT_BUSINESS_HOURS_START=07:00
DEFAULT_BUSINESS_HOURS_END=18:00
DEFAULT_TIMEZONE=America/Los_Angeles

# Service Configuration
PORT=3302
SERVICE_NAME=ts-tenant-service
```

## Dependencies

### Core Dependencies
- FastAPI with pydantic for data validation and API framework
- asyncpg for PostgreSQL async database operations
- httpx for Google Maps API calls and HTTP client operations
- pydantic-settings for configuration management
- Python logging with structured JSON output

### External Services
- **ts-auth-service**: JWT token validation
- **pns-provisioning-service**: Phone number provisioning trigger
- **Google Maps API**: Address geocoding and validation

This tenant service manages the complete business onboarding experience and ongoing configuration management, providing the foundation for all other Phase 1 services.