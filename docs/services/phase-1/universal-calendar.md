# Universal Calendar Service - Phase 1

## Service Overview

**Service Name**: `universal-calendar`  
**Port**: 3901  
**Technology Stack**: Python 3.10+ with FastAPI  
**Purpose**: Calendar integration service for appointment scheduling across multiple calendar providers  
**Status**: = **IN DEVELOPMENT** - Phase 1 implementation  

### Service Boundaries

**What this service handles:**
- **Calendar Integration**: Google Calendar, Microsoft Outlook, Apple Calendar
- **Field Service Integration**: Jobber, HouseCall Pro scheduling systems
- **Availability Management**: Check free/busy times across all integrated platforms
- **Appointment Creation**: Create, update, delete appointments across all providers
- **Synchronization**: Sync appointments between NeverMissCall and external systems
- **Conflict Resolution**: Detect and prevent double-booking across all platforms

**What this service does NOT handle:**
- **Authentication Management** � `ts-auth-service` (Port 3301)
- **Real-time notifications** � `as-connection-service` (Port 3105)
- **Lead management** � `as-call-service` (Port 3104)
- **Business configuration** � `ts-tenant-service` (Port 3302)

## Technical Architecture

### Technology Stack
- **Runtime**: Python 3.10+
- **Framework**: FastAPI with Pydantic for API validation
- **Database**: PostgreSQL via shared library (asyncpg/SQLAlchemy)
- **External APIs**: Google Calendar API, Microsoft Graph API, Jobber API, HouseCall Pro API
- **Authentication**: OAuth 2.0 for calendar providers
- **HTTP Client**: httpx for external API calls
- **Testing**: pytest with comprehensive test coverage
- **Shared Library**: Uses `shared/` for database, config, auth, logging

### Service Architecture

```mermaid
graph TB
    subgraph "universal-calendar (Port 3901)"
        CalendarController[CalendarController]
        AppointmentController[AppointmentController]
        AvailabilityController[AvailabilityController]
        CalendarService[CalendarService]
        AppointmentService[AppointmentService]
        ProviderService[ProviderService]
        SyncService[SyncService]
        SharedDB[Shared Database<br/>Library]
    end
    
    subgraph "External Services"
        ASCallService[as-call-service<br/>Port 3104]
        TSTenantService[ts-tenant-service<br/>Port 3302]
        TSAuthService[ts-auth-service<br/>Port 3301]
        ASConnectionService[as-connection-service<br/>Port 3105]
    end
    
    subgraph "Calendar Providers"
        GoogleCal[Google Calendar API]
        MSGraph[Microsoft Graph API]
        AppleCal[Apple Calendar API]
    end
    
    subgraph "Field Service Platforms"
        Jobber[Jobber API]
        HouseCallPro[HouseCall Pro API]
    end
    
    subgraph "Database"
        PostgreSQL[(PostgreSQL<br/>nevermisscall)]
    end
    
    ASCallService --> CalendarController
    ASCallService --> AppointmentController
    ASCallService --> AvailabilityController
    
    CalendarController --> CalendarService
    AppointmentController --> AppointmentService
    AvailabilityController --> CalendarService
    
    CalendarService --> ProviderService
    AppointmentService --> ProviderService
    CalendarService --> SyncService
    
    CalendarService --> SharedDB
    AppointmentService --> SharedDB
    SharedDB --> PostgreSQL
    
    CalendarService --> TSTenantService
    ProviderService --> TSAuthService
    AppointmentService --> ASConnectionService
    
    ProviderService --> GoogleCal
    ProviderService --> MSGraph
    ProviderService --> AppleCal
    ProviderService --> Jobber
    ProviderService --> HouseCallPro
```

## API Endpoints

### Calendar Integration

#### POST /calendar/connect
**Purpose**: Connect tenant's calendar provider (OAuth flow)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "provider": "google|microsoft|apple|jobber|housecallpro",
  "tenantId": "tenant-uuid",
  "timezone": "America/Los_Angeles",
  "credentials": {
    "apiKey": "optional-for-api-key-based-providers",
    "subdomain": "optional-for-subdomain-based-providers"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "authUrl": "https://accounts.google.com/oauth/authorize?...",
    "state": "random-state-token",
    "expiresIn": 600
  }
}
```

#### POST /calendar/oauth/callback
**Purpose**: Handle OAuth callback from calendar provider  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "provider": "google|microsoft|apple|jobber|housecallpro",
  "code": "oauth-authorization-code",
  "state": "random-state-token",
  "tenantId": "tenant-uuid",
  "credentials": {
    "apiKey": "for-api-key-based-providers",
    "subdomain": "for-subdomain-based-providers"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "provider": "google",
    "calendarId": "primary",
    "userEmail": "business@example.com",
    "syncEnabled": true
  }
}
```

#### GET /calendar/status/{tenantId}
**Purpose**: Get calendar connection status for tenant  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "provider": "google",
    "lastSyncAt": "2024-01-01T10:00:00Z",
    "syncStatus": "active",
    "calendarCount": 3,
    "calendars": [
      {
        "id": "primary",
        "name": "Business Calendar",
        "primary": true,
        "syncEnabled": true
      }
    ]
  }
}
```

### Availability Management

#### GET /availability/check
**Purpose**: Check availability for appointment scheduling  
**Headers**: `X-Service-Key: internal-service-key`  
**Query Parameters**:
- `tenantId`: string (required)
- `startDate`: string (ISO date, required)
- `endDate`: string (ISO date, required) 
- `duration`: number (minutes, required)
- `timezone`: string (optional, default from tenant)

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "tenantId": "tenant-uuid",
    "timezone": "America/Los_Angeles",
    "availability": [
      {
        "date": "2024-01-01",
        "slots": [
          {
            "startTime": "2024-01-01T09:00:00Z",
            "endTime": "2024-01-01T10:00:00Z",
            "available": true,
            "duration": 60
          },
          {
            "startTime": "2024-01-01T14:00:00Z", 
            "endTime": "2024-01-01T15:30:00Z",
            "available": true,
            "duration": 90
          }
        ]
      }
    ]
  }
}
```

#### POST /availability/block
**Purpose**: Block time slot (for emergency or maintenance)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "startTime": "2024-01-01T14:00:00Z",
  "endTime": "2024-01-01T16:00:00Z",
  "reason": "emergency_service",
  "title": "Emergency Service Call",
  "blockType": "soft|hard"
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "blockId": "block-uuid",
    "created": true,
    "conflictingAppointments": []
  }
}
```

### Appointment Management

#### POST /appointments
**Purpose**: Create new appointment  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "customerId": "customer-uuid",
  "leadId": "lead-uuid",
  "conversationId": "conversation-uuid",
  "appointmentData": {
    "startTime": "2024-01-01T14:00:00Z",
    "endTime": "2024-01-01T16:00:00Z",
    "title": "Plumbing Service - Kitchen Sink Repair",
    "description": "Emergency plumbing repair for kitchen sink leak",
    "location": {
      "address": "123 Main St, Los Angeles, CA 90210",
      "latitude": 34.0522,
      "longitude": -118.2437
    },
    "customerInfo": {
      "name": "John Smith",
      "phone": "+12125551234",
      "email": "john@example.com"
    },
    "serviceDetails": {
      "jobType": "plumbing",
      "urgency": "emergency",
      "estimatedDuration": 120,
      "estimatedCost": 350.00
    }
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "appointmentId": "appointment-uuid",
    "calendarEventId": "google-event-id",
    "created": true,
    "conflicts": [],
    "confirmationSent": true
  }
}
```

#### GET /appointments/{appointmentId}
**Purpose**: Get appointment details  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "appointment": {
      "id": "appointment-uuid",
      "tenantId": "tenant-uuid",
      "customerId": "customer-uuid",
      "startTime": "2024-01-01T14:00:00Z",
      "endTime": "2024-01-01T16:00:00Z",
      "status": "confirmed",
      "title": "Plumbing Service - Kitchen Sink Repair",
      "calendarEventId": "google-event-id",
      "createdAt": "2024-01-01T10:00:00Z",
      "updatedAt": "2024-01-01T10:00:00Z"
    }
  }
}
```

#### PUT /appointments/{appointmentId}
**Purpose**: Update existing appointment  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**: Same as create appointment (partial updates supported)  
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "appointmentId": "appointment-uuid",
    "updated": true,
    "calendarUpdated": true,
    "conflicts": [],
    "notificationsSent": ["customer", "provider"]
  }
}
```

#### DELETE /appointments/{appointmentId}
**Purpose**: Cancel/delete appointment  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "reason": "customer_cancellation|business_cancellation|rescheduling",
  "notifyCustomer": true,
  "cancellationNotes": "Customer requested cancellation"
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "cancelled": true,
    "calendarEventDeleted": true,
    "refundIssued": false,
    "notificationsSent": ["customer"]
  }
}
```

#### GET /appointments
**Purpose**: List appointments for tenant  
**Headers**: `Authorization: Bearer jwt-token`  
**Query Parameters**:
- `tenantId`: string (required)
- `startDate`: string (ISO date, optional)
- `endDate`: string (ISO date, optional)
- `status`: string (optional: confirmed|pending|cancelled|completed)
- `page`: number (default: 1)
- `limit`: number (default: 20, max: 100)

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "appointments": [
      {
        "id": "appointment-uuid",
        "startTime": "2024-01-01T14:00:00Z",
        "endTime": "2024-01-01T16:00:00Z",
        "status": "confirmed",
        "title": "Plumbing Service",
        "customerName": "John Smith",
        "customerPhone": "+12125551234"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "pages": 8
    }
  }
}
```

### Synchronization

#### POST /sync/trigger
**Purpose**: Trigger manual sync with calendar provider  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "syncType": "full|incremental",
  "provider": "google|microsoft|apple"
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "syncId": "sync-uuid",
    "status": "started",
    "estimatedDuration": 30,
    "lastSyncAt": "2024-01-01T09:00:00Z"
  }
}
```

#### GET /sync/status/{syncId}
**Purpose**: Check synchronization status  
**Headers**: `X-Service-Key: internal-service-key`  
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "syncId": "sync-uuid",
    "status": "completed|running|failed",
    "progress": 100,
    "eventsProcessed": 25,
    "eventsCreated": 5,
    "eventsUpdated": 3,
    "eventsDeleted": 1,
    "errors": [],
    "completedAt": "2024-01-01T09:01:30Z"
  }
}
```

### Field Service Platform Integration

#### POST /integrations/jobber/connect
**Purpose**: Connect to Jobber account for scheduling integration  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "apiKey": "jobber-api-key",
  "subdomain": "your-business-subdomain",
  "timezone": "America/Los_Angeles"
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "provider": "jobber",
    "companyName": "ABC Plumbing",
    "syncEnabled": true,
    "lastSyncAt": null
  }
}
```

#### POST /integrations/housecallpro/connect  
**Purpose**: Connect to HouseCall Pro account for scheduling integration  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "apiKey": "housecallpro-api-key",
  "companyId": "your-company-id",
  "timezone": "America/Los_Angeles"
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "provider": "housecallpro",
    "companyName": "XYZ Services",
    "syncEnabled": true,
    "lastSyncAt": null
  }
}
```

#### GET /integrations/{provider}/jobs
**Purpose**: Get jobs/appointments from field service platform  
**Headers**: `Authorization: Bearer jwt-token`  
**Query Parameters**:
- `tenantId`: string (required)
- `startDate`: string (ISO date, required)
- `endDate`: string (ISO date, required)
- `status`: string (optional: scheduled|in_progress|completed|cancelled)

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "id": "jobber-job-123",
        "title": "Kitchen Sink Repair",
        "status": "scheduled",
        "startTime": "2024-01-01T14:00:00Z",
        "endTime": "2024-01-01T16:00:00Z",
        "customer": {
          "name": "John Smith",
          "phone": "+12125551234",
          "address": "123 Main St, Los Angeles, CA"
        },
        "technician": {
          "name": "Mike Johnson",
          "id": "tech-456"
        },
        "jobType": "plumbing",
        "estimatedValue": 350.00
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 45
    }
  }
}
```

#### POST /integrations/{provider}/jobs
**Purpose**: Create new job in field service platform  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "leadId": "lead-uuid",
  "conversationId": "conversation-uuid",
  "jobData": {
    "title": "Emergency Plumbing Repair",
    "description": "Kitchen sink leak - customer reports water damage",
    "startTime": "2024-01-01T14:00:00Z",
    "endTime": "2024-01-01T16:00:00Z",
    "customer": {
      "name": "John Smith",
      "phone": "+12125551234",
      "email": "john@example.com",
      "address": "123 Main St, Los Angeles, CA 90210"
    },
    "jobType": "plumbing",
    "urgency": "emergency",
    "estimatedValue": 350.00,
    "notes": "Customer mentioned water spreading to adjacent rooms"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "jobId": "jobber-job-789",
    "created": true,
    "scheduledTechnician": "tech-456",
    "confirmationSent": true,
    "invoiceCreated": false
  }
}
```

#### PUT /integrations/{provider}/jobs/{jobId}
**Purpose**: Update existing job in field service platform  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**: Same as create job (partial updates supported)  
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "jobId": "jobber-job-789",
    "updated": true,
    "changes": ["start_time", "technician"],
    "notificationsSent": ["customer", "technician"]
  }
}
```

#### POST /integrations/{provider}/sync/customers
**Purpose**: Sync customer data between NeverMissCall and field service platform  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "tenantId": "tenant-uuid",
  "customerData": {
    "phone": "+12125551234",
    "name": "John Smith",
    "email": "john@example.com",
    "address": "123 Main St, Los Angeles, CA 90210",
    "notes": "Preferred contact method: SMS"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "data": {
    "customerId": "jobber-customer-456",
    "created": true,
    "matched": false,
    "duplicateCheck": "passed"
  }
}
```

## Data Models

### Appointment Entity
```python
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed" 
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class Appointment(BaseModel):
    id: str
    tenant_id: str
    customer_id: Optional[str] = None
    lead_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    # Calendar/Platform integration
    provider: str = Field(..., description="google|microsoft|apple|jobber|housecallpro")
    provider_event_id: Optional[str] = None  # Calendar event ID or Job ID
    
    # Appointment details
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    title: str
    description: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.PENDING
    
    # Location
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Customer information
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = Field(None, pattern=r'^\+[1-9]\d{1,14}$')
    customer_email: Optional[str] = None
    
    # Service details
    job_type: Optional[str] = None
    urgency_level: Optional[str] = "normal"
    estimated_duration_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Calendar Integration Entity
```python
class CalendarIntegration(BaseModel):
    id: str
    tenant_id: str
    provider: Literal["google", "microsoft", "apple", "jobber", "housecallpro"]
    
    # OAuth details
    access_token: str  # Encrypted
    refresh_token: Optional[str] = None  # Encrypted
    token_expires_at: Optional[datetime] = None
    
    # Provider details
    provider_user_id: str
    provider_email: str
    calendar_id: str
    calendar_name: str
    
    # Sync settings
    sync_enabled: bool = True
    sync_direction: Literal["bidirectional", "from_provider", "to_provider"] = "bidirectional"
    last_sync_at: Optional[datetime] = None
    sync_status: Literal["active", "error", "disabled"] = "active"
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## Database Schema

### Appointments Table
```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID,
    lead_id UUID,
    conversation_id UUID,
    
    -- Provider integration (calendar or field service platform)
    provider VARCHAR(50) NOT NULL,
    provider_event_id VARCHAR(255), -- Calendar event ID or Job ID
    
    -- Appointment details
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Location
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Customer information
    customer_name VARCHAR(255),
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    
    -- Service details
    job_type VARCHAR(100),
    urgency_level VARCHAR(20) DEFAULT 'normal',
    estimated_duration_minutes INTEGER,
    estimated_cost DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_appointments_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

### Calendar Integrations Table
```sql
CREATE TABLE calendar_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    
    -- OAuth details (encrypted)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    
    -- Provider details
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255) NOT NULL,
    calendar_id VARCHAR(255) NOT NULL,
    calendar_name VARCHAR(255) NOT NULL,
    
    -- Sync settings
    sync_enabled BOOLEAN DEFAULT true,
    sync_direction VARCHAR(20) DEFAULT 'bidirectional',
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'active',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_calendar_integrations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    UNIQUE(tenant_id, provider)
);
```

### Performance Indexes
```sql
-- Critical performance indexes
CREATE INDEX idx_appointments_tenant_time ON appointments (tenant_id, start_time);
CREATE INDEX idx_appointments_status ON appointments (status, start_time);
CREATE INDEX idx_appointments_customer_phone ON appointments (customer_phone);
CREATE INDEX idx_appointments_provider_event ON appointments (provider, provider_event_id);

CREATE INDEX idx_calendar_integrations_tenant ON calendar_integrations (tenant_id);
CREATE INDEX idx_calendar_integrations_provider ON calendar_integrations (provider, sync_enabled);
```

## Business Logic

### Appointment Scheduling Workflow
1. **Availability Check**: Query calendar provider for free/busy times
2. **Conflict Detection**: Check for overlapping appointments
3. **Time Zone Handling**: Convert times between customer, business, and provider zones
4. **Calendar Event Creation**: Create event in external calendar
5. **Confirmation**: Send confirmation to customer via SMS/email
6. **Sync Status**: Track synchronization with external calendar

### Provider Integration Architecture

#### Calendar Provider Integration
```python
class CalendarProvider:
    """Base class for calendar provider integrations."""
    
    async def get_availability(self, start_date: date, end_date: date) -> List[TimeSlot]:
        """Get available time slots from calendar provider."""
        pass
    
    async def create_event(self, appointment: Appointment) -> str:
        """Create calendar event and return provider event ID."""
        pass
    
    async def update_event(self, event_id: str, appointment: Appointment) -> bool:
        """Update existing calendar event."""
        pass
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete calendar event."""
        pass
```

#### Field Service Platform Integration
```python
class FieldServiceProvider:
    """Base class for field service platform integrations."""
    
    async def get_jobs(self, start_date: date, end_date: date, status: Optional[str] = None) -> List[Job]:
        """Get jobs/appointments from field service platform."""
        pass
    
    async def create_job(self, job_data: JobData) -> str:
        """Create new job in field service platform."""
        pass
    
    async def update_job(self, job_id: str, job_data: JobData) -> bool:
        """Update existing job in field service platform."""
        pass
    
    async def cancel_job(self, job_id: str, reason: str) -> bool:
        """Cancel job in field service platform."""
        pass
    
    async def sync_customer(self, customer_data: CustomerData) -> str:
        """Sync customer data with field service platform."""
        pass
```

#### Integration Approaches

**Jobber Integration:**
- **API Type**: GraphQL API
- **Authentication**: API Key-based
- **Real-time Updates**: Webhooks for job status changes
- **Data Sync**: Bidirectional sync for jobs and customers
- **Limitations**: Rate limiting (500 requests per minute)

**HouseCall Pro Integration:**
- **API Type**: REST API
- **Authentication**: API Key-based
- **Real-time Updates**: Webhooks for job and customer events
- **Data Sync**: Bidirectional sync for jobs, customers, and schedules
- **Limitations**: Rate limiting (100 requests per minute)

**Calendar Providers (Google, Microsoft, Apple):**
- **API Type**: REST API
- **Authentication**: OAuth 2.0
- **Real-time Updates**: Calendar webhooks and push notifications
- **Data Sync**: Bidirectional sync for calendar events
- **Limitations**: OAuth token refresh required

## Environment Configuration

```bash
# Database
DATABASE_URL=postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall

# External Services
TS_TENANT_SERVICE_URL=http://localhost:3302
TS_AUTH_SERVICE_URL=http://localhost:3301
AS_CONNECTION_SERVICE_URL=http://localhost:3105
AS_CALL_SERVICE_URL=http://localhost:3104

# Service Authentication
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1
JWT_SECRET=your-32-character-jwt-secret-key-here

# Calendar Providers
GOOGLE_CALENDAR_CLIENT_ID=your-google-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=your-google-client-secret
MICROSOFT_GRAPH_CLIENT_ID=your-microsoft-client-id
MICROSOFT_GRAPH_CLIENT_SECRET=your-microsoft-client-secret

# Field Service Platform Integration
JOBBER_API_BASE_URL=https://api.getjobber.com/api/graphql
JOBBER_WEBHOOK_SECRET=your-jobber-webhook-secret
HOUSECALLPRO_API_BASE_URL=https://api.housecallpro.com/v1
HOUSECALLPRO_WEBHOOK_SECRET=your-housecallpro-webhook-secret

# Service Configuration
PORT=3901
SERVICE_NAME=universal-calendar
NODE_ENV=development

# Logging
LOG_LEVEL=info

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# CORS
CORS_ORIGIN=*
```

## Security Considerations

### OAuth Token Management
- All OAuth tokens encrypted at rest using tenant-specific keys
- Automatic token refresh before expiration
- Secure token storage with proper access controls
- Audit logging for all calendar access

### Data Protection
- Customer appointment data encrypted with tenant-specific keys
- Automatic PII redaction in logs
- Compliance with calendar provider data policies
- Secure webhook validation

### API Security
- Internal service endpoints use API key authentication
- User-facing endpoints require JWT token validation
- Rate limiting on all public endpoints
- Input validation with Pydantic models

This service specification provides comprehensive calendar integration capabilities while following the established Phase 1 architecture patterns and security standards.