# pns-provisioning-service Design Document

## Service Overview

**Service Name**: pns-provisioning-service  
**Port**: 3501  
**Phase**: 1 - Identity & Onboarding  
**Purpose**: Basic phone number provisioning via Twilio (no compliance features)  

## Business Requirements

### Primary Functions
- Automatic phone number provisioning for new businesses
- Phone number configuration with Twilio webhooks
- Basic phone number management (status, release)
- Integration with Twilio Messaging Services
- Support for onboarding workflow automation

### Success Criteria
- Phone numbers provisioned automatically during onboarding
- Numbers configured with correct webhook URLs
- Messaging services created and linked properly
- Number status tracking works reliably
- One-number-per-tenant constraint enforced

## Technical Specification

### Technology Stack
- **Runtime**: Node.js 18+ with TypeScript 5+
- **Framework**: Express.js 4+
- **Database**: PostgreSQL with Prisma ORM
- **External API**: Twilio REST API
- **Validation**: Joi for request validation

### Service Architecture

```mermaid
graph TB
    subgraph "pns-provisioning-service (Port 3501)"
        ProvisioningController[ProvisioningController]
        NumberController[NumberController]
        ProvisioningService[ProvisioningService]
        TwilioClient[TwilioClient]
        Database[(PostgreSQL<br/>nevermisscall)]
    end
    
    TSTenant[ts-tenant-service] --> ProvisioningController
    WebUI[web-ui] --> NumberController
    TwilioServer[twilio-server] --> NumberController
    
    ProvisioningController --> ProvisioningService
    NumberController --> ProvisioningService
    ProvisioningService --> TwilioClient
    ProvisioningService --> Database
    TwilioClient -.-> TwilioAPI[Twilio REST API]
```

## API Endpoints

### Phone Number Provisioning

#### POST /phone-numbers/provision
**Purpose**: Provision new phone number for tenant  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "areaCode": "213",
  "numberType": "local",
  "webhookBaseUrl": "https://api.nevermisscall.com"
}
```
**Response (201)**:
```json
{
  "success": true,
  "phoneNumber": {
    "id": "phone-uuid",
    "tenantId": "tenant-uuid",
    "phoneNumber": "+12135551234",
    "phoneNumberSid": "PN1234567890abcdef",
    "messagingServiceSid": "MG1234567890abcdef",
    "areaCode": "213",
    "region": "CA",
    "status": "provisioned",
    "webhooksConfigured": true,
    "monthlyPriceCents": 100,
    "provisionedAt": "2024-01-01T10:00:00Z"
  }
}
```

#### GET /phone-numbers/lookup/:phoneNumber
**Purpose**: Resolve phone number to tenantId (internal use)  
**Headers**: `X-Service-Key: internal-service-key`  
**Response (200)**:
```json
{
  "tenantId": "tenant-uuid",
  "phoneNumber": "+12135551234",
  "status": "active"
}
```

#### GET /phone-numbers/tenant/:tenantId
**Purpose**: Get phone number for tenant  
**Headers**: `X-Service-Key: internal-service-key`  
**Response (200)**:
```json
{
  "phoneNumber": {
    "id": "phone-uuid",
    "tenantId": "tenant-uuid",
    "phoneNumber": "+12135551234",
    "phoneNumberSid": "PN1234567890abcdef",
    "messagingServiceSid": "MG1234567890abcdef",
    "status": "active",
    "webhooksConfigured": true,
    "dateProvisioned": "2024-01-01T10:00:00Z"
  }
}
```

#### PUT /phone-numbers/:phoneId/status
**Purpose**: Update phone number status  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "status": "active",
  "reason": "Tenant onboarding completed"
}
```
**Response (200)**:
```json
{
  "success": true,
  "phoneNumber": {
    "id": "phone-uuid",
    "status": "active",
    "statusReason": "Tenant onboarding completed",
    "updatedAt": "2024-01-01T11:00:00Z"
  }
}
```

### Phone Number Management

#### GET /phone-numbers/:phoneId
**Purpose**: Get phone number details  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "phoneNumber": {
    "id": "phone-uuid",
    "phoneNumber": "+12135551234",
    "friendlyName": "Smith Plumbing Main Line",
    "status": "active",
    "capabilities": ["voice", "sms"],
    "webhookUrls": {
      "voice": "https://api.nevermisscall.com/webhooks/twilio/call",
      "sms": "https://api.nevermisscall.com/webhooks/twilio/sms"
    },
    "messagingService": {
      "sid": "MG1234567890abcdef",
      "friendlyName": "Smith Plumbing Messaging"
    }
  }
}
```

#### POST /phone-numbers/:phoneId/release
**Purpose**: Release phone number (future use)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "reason": "Business closure",
  "confirmRelease": true
}
```
**Response (200)**:
```json
{
  "success": true,
  "phoneNumber": {
    "id": "phone-uuid",
    "status": "released",
    "releasedAt": "2024-01-01T15:00:00Z",
    "releaseReason": "Business closure"
  }
}
```

### Configuration Management

#### GET /phone-numbers/:phoneId/configuration
**Purpose**: Get phone number configuration  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "configuration": {
    "phoneId": "phone-uuid",
    "webhooks": {
      "voiceUrl": "https://api.nevermisscall.com/webhooks/twilio/call",
      "voiceMethod": "POST",
      "smsUrl": "https://api.nevermisscall.com/webhooks/twilio/sms",
      "smsMethod": "POST",
      "statusCallbackUrl": "https://api.nevermisscall.com/webhooks/twilio/call/status"
    },
    "messagingService": {
      "sid": "MG1234567890abcdef",
      "inboundWebhookUrl": "https://api.nevermisscall.com/webhooks/twilio/sms"
    }
  }
}
```

#### PUT /phone-numbers/:phoneId/configuration
**Purpose**: Update phone number configuration  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "friendlyName": "Smith Plumbing & Heating Main Line",
  "webhooks": {
    "voiceUrl": "https://api.nevermisscall.com/webhooks/twilio/call"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "configuration": {
    "friendlyName": "Smith Plumbing & Heating Main Line",
    "webhooks": {
      "voiceUrl": "https://api.nevermisscall.com/webhooks/twilio/call"
    },
    "updatedAt": "2024-01-01T12:00:00Z"
  }
}
```

## Data Models

### Phone Number Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal, List
from datetime import datetime

@dataclass
class PhoneNumber:
    id: str
    tenant_id: str  # One phone number per tenant in Phase 1
    
    # Twilio Information
    phone_number: str  # E.164 format: +12135551234
    phone_number_sid: str  # Twilio Phone Number SID
    
    # Number Details
    area_code: str
    region: str
    number_type: Literal['local', 'toll-free']
    capabilities: List[Literal['voice', 'sms']]
    
    # Status and Lifecycle
    status: Literal['provisioning', 'provisioned', 'active', 'suspended', 'released']
    date_provisioned: datetime
    
    # Configuration
    webhooks_configured: bool
    voice_webhook_url: str
    sms_webhook_url: str
    status_callback_url: str
    
    # Billing
    monthly_price_cents: int
    setup_price_cents: int
    currency: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Optional fields
    messaging_service_sid: Optional[str] = None  # Twilio Messaging Service SID
    friendly_name: Optional[str] = None
    status_reason: Optional[str] = None
    date_released: Optional[datetime] = None
```

### Messaging Service Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class MessagingService:
    phone_number_id: str
    messaging_service_sid: str
    friendly_name: str
    inbound_webhook_url: str
    inbound_method: Literal['GET', 'POST']
    created_at: datetime
    updated_at: datetime
    fallback_url: Optional[str] = None
    status_callback: Optional[str] = None
```

## Database Schema

### Phone Numbers Table
```sql
CREATE TABLE phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE, -- One number per tenant in Phase 1
    
    -- Twilio Information
    phone_number VARCHAR(20) NOT NULL UNIQUE, -- E.164 format
    phone_number_sid VARCHAR(100) UNIQUE NOT NULL,
    messaging_service_sid VARCHAR(100),
    
    -- Number Details
    friendly_name VARCHAR(255),
    area_code VARCHAR(5) NOT NULL,
    region VARCHAR(100),
    number_type VARCHAR(20) DEFAULT 'local',
    capabilities TEXT[] DEFAULT ARRAY['voice', 'sms'],
    
    -- Status and Lifecycle
    status VARCHAR(50) DEFAULT 'provisioning',
    status_reason TEXT,
    date_provisioned TIMESTAMP,
    date_released TIMESTAMP,
    
    -- Configuration
    webhooks_configured BOOLEAN DEFAULT false,
    voice_webhook_url TEXT NOT NULL,
    sms_webhook_url TEXT NOT NULL,
    status_callback_url TEXT,
    
    -- Billing
    monthly_price_cents INTEGER DEFAULT 100,
    setup_price_cents INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_phone_numbers_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
```

### Messaging Services Table
```sql
CREATE TABLE messaging_services (
    phone_number_id UUID PRIMARY KEY,
    messaging_service_sid VARCHAR(100) UNIQUE NOT NULL,
    friendly_name VARCHAR(255) NOT NULL,
    inbound_webhook_url TEXT NOT NULL,
    inbound_method VARCHAR(10) DEFAULT 'POST',
    fallback_url TEXT,
    status_callback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_messaging_services_phone FOREIGN KEY (phone_number_id) REFERENCES phone_numbers(id) ON DELETE CASCADE
);
```

### Indexes
```sql
-- Performance and constraint indexes
CREATE UNIQUE INDEX idx_phone_numbers_tenant ON phone_numbers (tenant_id);
CREATE UNIQUE INDEX idx_phone_numbers_phone ON phone_numbers (phone_number);
CREATE UNIQUE INDEX idx_phone_numbers_sid ON phone_numbers (phone_number_sid);
CREATE INDEX idx_phone_numbers_status ON phone_numbers (status);
CREATE INDEX idx_phone_numbers_area_code ON phone_numbers (area_code, region);
```

## Business Logic

### Phone Number Provisioning Workflow
1. **Validate Request**: Check tenant exists, no existing number
2. **Search Available Numbers**: Query Twilio for available numbers in area code
3. **Purchase Number**: Buy first available number from Twilio
4. **Create Messaging Service**: Set up Twilio Messaging Service for SMS
5. **Configure Webhooks**: Set voice and SMS webhook URLs
6. **Store Record**: Save phone number details in database
7. **Update Tenant**: Mark tenant as having provisioned number
8. **Return Success**: Provide complete phone number information

### Webhook Configuration
```python
import os

webhook_configuration = {
    'voice': {
        'url': f"{os.environ.get('WEBHOOK_BASE_URL')}/webhooks/twilio/call",
        'method': 'POST',
        'status_callback': f"{os.environ.get('WEBHOOK_BASE_URL')}/webhooks/twilio/call/status"
    },
    'sms': {
        'url': f"{os.environ.get('WEBHOOK_BASE_URL')}/webhooks/twilio/sms",
        'method': 'POST'
    }
}
```

### Number Selection Logic (Phase 1 - Simplified)
1. **Area Code Priority**: Search in requested area code first
2. **Local Numbers Only**: No toll-free numbers in Phase 1
3. **Voice + SMS Capability**: Ensure both capabilities are available
4. **First Available**: Take first number that meets criteria
5. **Fallback Areas**: Expand search to nearby area codes if needed

### Cost Tracking
- **Setup Cost**: One-time purchase price (usually free)
- **Monthly Cost**: Standard $1.00/month for local numbers
- **Usage Tracking**: Prepare for future usage-based billing

## External Service Integration

### Twilio REST API Integration
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class AvailableNumber:
    phone_number: str
    friendly_name: str
    capabilities: List[str]

@dataclass
class PurchasedNumber:
    sid: str
    phone_number: str
    status: str

@dataclass
class WebhookConfig:
    voice_url: str
    sms_url: str
    status_callback_url: str

@dataclass
class MessagingService:
    sid: str
    friendly_name: str

class TwilioPhoneNumberService(ABC):
    @abstractmethod
    async def search_available_numbers(self, area_code: str) -> List[AvailableNumber]:
        pass
    
    @abstractmethod
    async def purchase_number(self, phone_number: str) -> PurchasedNumber:
        pass
    
    @abstractmethod
    async def configure_webhooks(self, sid: str, config: WebhookConfig) -> None:
        pass
    
    @abstractmethod
    async def create_messaging_service(self, name: str) -> MessagingService:
        pass
    
    @abstractmethod
    async def release_number(self, sid: str) -> None:
        pass
```

### Error Handling for Twilio API
- **Rate Limiting**: Respect Twilio API rate limits
- **Retry Logic**: Exponential backoff for transient errors
- **Cost Protection**: Prevent accidental bulk purchases
- **Webhook Validation**: Verify webhook URLs are reachable

## Security Considerations

### API Security
- Internal service authentication for provisioning endpoints
- JWT token validation for user-facing endpoints
- Rate limiting on provisioning endpoints (max 1/minute/tenant)
- Input validation for all phone number operations

### Twilio Security
- Secure storage of Twilio credentials
- Webhook signature validation (future enhancement)
- Access logging for all Twilio API calls
- Cost monitoring and alerts

### Data Protection
- Phone number data encrypted at rest
- Audit logging for all number operations
- Tenant isolation enforced at database level
- Secure deletion of released numbers

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "NUMBER_PROVISIONING_FAILED",
    "message": "Unable to provision phone number",
    "details": {
      "areaCode": "213",
      "twilioError": "No available numbers in area code"
    }
  }
}
```

### Common Error Codes
- `TENANT_ALREADY_HAS_NUMBER`: One number per tenant limit
- `NUMBER_PROVISIONING_FAILED`: Twilio provisioning error
- `INVALID_AREA_CODE`: Area code not supported
- `WEBHOOK_CONFIGURATION_FAILED`: Unable to set webhooks
- `MESSAGING_SERVICE_CREATION_FAILED`: SMS service setup error
- `TWILIO_API_ERROR`: General Twilio API issues

## Testing Strategy

### Unit Tests
- Phone number provisioning workflow
- Webhook configuration logic
- Number status management
- Cost calculation functions
- Input validation

### Integration Tests
- Twilio API integration (with test credentials)
- Database operations and constraints
- Complete provisioning workflow
- Error handling and rollback

### Mock Testing
- Twilio API responses for edge cases
- Webhook delivery simulation
- Cost calculation accuracy
- Number availability scenarios

## Performance Requirements

- **Number Provisioning**: < 10 seconds (includes Twilio API calls)
- **Number Status Updates**: < 500ms (95th percentile)
- **Configuration Updates**: < 1000ms (95th percentile)
- **Number Queries**: < 200ms (95th percentile)
- **Concurrent Provisioning**: Support 5+ simultaneous operations

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# Twilio Configuration
TWILIO_ACCOUNT_SID=AC1234567890abcdef
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_API_VERSION=2010-04-01

# Webhook Configuration
WEBHOOK_BASE_URL=https://api.nevermisscall.com
WEBHOOK_VOICE_PATH=/webhooks/twilio/call
WEBHOOK_SMS_PATH=/webhooks/twilio/sms
WEBHOOK_STATUS_PATH=/webhooks/twilio/call/status

# Service Authentication
INTERNAL_SERVICE_KEY=shared-secret-key-for-phase-1

# Service Configuration
PORT=3501
SERVICE_NAME=pns-provisioning-service
MAX_CONCURRENT_PROVISIONING=5
```

## Dependencies

### Core Dependencies
- Express.js, Prisma ORM, PostgreSQL driver
- Joi for validation, Winston for logging
- Twilio SDK for REST API integration

### External Services
- **Twilio REST API**: Phone number management
- **ts-tenant-service**: Tenant validation and updates
- **Webhook endpoints**: Configured during provisioning

## Operational Considerations

### Monitoring
- Phone number provisioning success rates
- Twilio API response times and error rates
- Webhook configuration validation
- Cost tracking and billing alerts

### Maintenance
- Regular cleanup of failed provisioning attempts
- Monitoring of unused/inactive numbers
- Twilio account balance and usage tracking
- Webhook endpoint health monitoring

This provisioning service provides the essential phone number functionality needed for Phase 1, with simplified provisioning that can be enhanced with compliance features in future phases.