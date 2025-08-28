# ts-user-service Design Document

## Service Overview

**Service Name**: ts-user-service  
**Port**: 3303  
**Phase**: 1 - Identity & Onboarding  
**Purpose**: User profiles, basic settings, and user management for business owners  

## Business Requirements

### Primary Functions
- User profile management and updates
- User preferences and settings
- Basic user status tracking (active/inactive)
- User profile validation and data integrity
- Simple user information retrieval for other services

### Success Criteria
- User profiles can be updated in < 500ms
- Profile information is consistent across services
- User preferences are saved and retrievable
- Profile validation prevents invalid data
- Support for basic user management operations

## Technical Specification

### Technology Stack
- **Runtime**: Node.js 18+ with TypeScript 5+
- **Framework**: Express.js 4+
- **Database**: PostgreSQL with Prisma ORM
- **Validation**: Joi for request validation
- **Caching**: Redis for profile caching (optional)

### Service Architecture

```mermaid
graph TB
    subgraph "ts-user-service (Port 3303)"
        UserController[UserController]
        ProfileController[ProfileController]
        UserService[UserService]
        ValidationService[ValidationService]
        Database[(PostgreSQL<br/>nevermisscall)]
    end
    
    WebUI[web-ui] --> UserController
    WebUI --> ProfileController
    TSAuth[ts-auth-service] --> UserController
    ASCall[as-call-service] --> UserController
    
    UserController --> UserService
    ProfileController --> UserService
    UserService --> ValidationService
    UserService --> Database
```

## API Endpoints

### User Profile Management

#### GET /users/:userId/profile
**Purpose**: Get user profile information  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "profile": {
    "userId": "user-uuid",
    "email": "john@smithplumbing.com",
    "firstName": "John",
    "lastName": "Smith",
    "displayName": "John Smith",
    "phoneNumber": "+12125551234",
    "timezone": "America/Los_Angeles",
    "role": "owner",
    "tenantId": "tenant-uuid",
    "isActive": true,
    "profilePhotoUrl": null,
    "lastUpdated": "2024-01-01T10:00:00Z"
  }
}
```

#### PUT /users/:userId/profile
**Purpose**: Update user profile information  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "firstName": "John",
  "lastName": "Smith Jr.",
  "displayName": "John Smith Jr.",
  "phoneNumber": "+12125551234",
  "timezone": "America/New_York"
}
```
**Response (200)**:
```json
{
  "success": true,
  "profile": {
    "userId": "user-uuid",
    "firstName": "John",
    "lastName": "Smith Jr.",
    "displayName": "John Smith Jr.",
    "phoneNumber": "+12125551234",
    "timezone": "America/New_York",
    "updatedAt": "2024-01-01T11:00:00Z"
  }
}
```

#### POST /users/:userId/profile/photo
**Purpose**: Upload profile photo (simple file upload)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request**: Multipart form data with photo file  
**Response (200)**:
```json
{
  "success": true,
  "profilePhotoUrl": "https://storage.nevermisscall.com/profiles/user-uuid/photo.jpg"
}
```

### User Preferences

#### GET /users/:userId/preferences
**Purpose**: Get user preferences and settings  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "preferences": {
    "userId": "user-uuid",
    "notifications": {
      "smsEnabled": true,
      "emailEnabled": true,
      "pushEnabled": true,
      "dashboardSounds": true
    },
    "dashboard": {
      "defaultView": "conversations",
      "refreshInterval": 30,
      "showTutorial": false
    },
    "communication": {
      "autoResponseEnabled": true,
      "aiTakeoverNotifications": true,
      "customerResponseTimeout": 60
    }
  }
}
```

#### PUT /users/:userId/preferences
**Purpose**: Update user preferences  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "notifications": {
    "smsEnabled": true,
    "emailEnabled": false,
    "pushEnabled": true,
    "dashboardSounds": false
  },
  "dashboard": {
    "defaultView": "analytics",
    "refreshInterval": 15
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "preferences": {
    "notifications": {
      "smsEnabled": true,
      "emailEnabled": false,
      "pushEnabled": true,
      "dashboardSounds": false
    },
    "dashboard": {
      "defaultView": "analytics",
      "refreshInterval": 15,
      "showTutorial": false
    },
    "updatedAt": "2024-01-01T11:30:00Z"
  }
}
```

### User Status Management

#### GET /users/:userId/status
**Purpose**: Get user current status and activity  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "status": {
    "userId": "user-uuid",
    "isActive": true,
    "isOnline": true,
    "lastSeenAt": "2024-01-01T12:00:00Z",
    "currentStatus": "available",
    "statusMessage": null
  }
}
```

#### PUT /users/:userId/status
**Purpose**: Update user status (available, busy, offline)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "currentStatus": "busy",
  "statusMessage": "In a meeting until 3pm"
}
```
**Response (200)**:
```json
{
  "success": true,
  "status": {
    "currentStatus": "busy",
    "statusMessage": "In a meeting until 3pm",
    "updatedAt": "2024-01-01T12:15:00Z"
  }
}
```

### User Validation Endpoints (For Other Services)

#### POST /users/validate
**Purpose**: Validate user exists and is active  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "userId": "user-uuid",
  "tenantId": "tenant-uuid"
}
```
**Response (200)**:
```json
{
  "valid": true,
  "user": {
    "id": "user-uuid",
    "email": "john@smithplumbing.com",
    "firstName": "John",
    "lastName": "Smith",
    "tenantId": "tenant-uuid",
    "role": "owner",
    "isActive": true
  }
}
```

#### GET /users/by-tenant/:tenantId
**Purpose**: Get all users for a tenant (Phase 1: always single user)  
**Headers**: `X-Service-Key: internal-service-key`  
**Response (200)**:
```json
{
  "users": [
    {
      "id": "user-uuid",
      "email": "john@smithplumbing.com",
      "firstName": "John",
      "lastName": "Smith",
      "role": "owner",
      "isActive": true,
      "lastSeenAt": "2024-01-01T12:00:00Z"
    }
  ]
}
```

## Data Models

### User Profile Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class UserProfile:
    user_id: str
    email: str  # Read-only, managed by auth service
    first_name: str
    last_name: str
    display_name: str
    timezone: str
    role: Literal['owner', 'operator', 'viewer']
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
```

### User Preferences Entity
```python
from dataclasses import dataclass
from typing import Literal
from datetime import datetime

@dataclass
class NotificationPreferences:
    sms_enabled: bool
    email_enabled: bool
    push_enabled: bool
    dashboard_sounds: bool

@dataclass
class DashboardPreferences:
    default_view: Literal['conversations', 'analytics', 'settings']
    refresh_interval: int  # seconds
    show_tutorial: bool

@dataclass
class CommunicationPreferences:
    auto_response_enabled: bool
    ai_takeover_notifications: bool
    customer_response_timeout: int  # seconds

@dataclass
class UserPreferences:
    user_id: str
    notifications: NotificationPreferences
    dashboard: DashboardPreferences
    communication: CommunicationPreferences
    created_at: datetime
    updated_at: datetime
```

### User Status Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class UserStatus:
    user_id: str
    is_active: bool
    is_online: bool
    last_seen_at: datetime
    current_status: Literal['available', 'busy', 'offline']
    updated_at: datetime
    status_message: Optional[str] = None
```

## Database Schema

### User Profiles Table
```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL, -- Synced from auth service
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    phone_number VARCHAR(20),
    profile_photo_url TEXT,
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    role VARCHAR(50) DEFAULT 'owner',
    tenant_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_profiles_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
```

### User Preferences Table
```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    
    -- Notification preferences
    sms_notifications_enabled BOOLEAN DEFAULT true,
    email_notifications_enabled BOOLEAN DEFAULT true,
    push_notifications_enabled BOOLEAN DEFAULT true,
    dashboard_sounds_enabled BOOLEAN DEFAULT true,
    
    -- Dashboard preferences
    dashboard_default_view VARCHAR(50) DEFAULT 'conversations',
    dashboard_refresh_interval INTEGER DEFAULT 30,
    show_tutorial BOOLEAN DEFAULT true,
    
    -- Communication preferences
    auto_response_enabled BOOLEAN DEFAULT true,
    ai_takeover_notifications BOOLEAN DEFAULT true,
    customer_response_timeout INTEGER DEFAULT 60,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### User Status Table
```sql
CREATE TABLE user_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT true,
    is_online BOOLEAN DEFAULT false,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    current_status VARCHAR(20) DEFAULT 'available',
    status_message TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_status_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_user_profiles_user_id ON user_profiles (user_id);
CREATE INDEX idx_user_profiles_tenant ON user_profiles (tenant_id);
CREATE INDEX idx_user_profiles_email ON user_profiles (email);
CREATE INDEX idx_user_preferences_user_id ON user_preferences (user_id);
CREATE INDEX idx_user_status_user_id ON user_status (user_id);
CREATE INDEX idx_user_status_active ON user_status (is_active, is_online);
CREATE INDEX idx_user_status_last_seen ON user_status (last_seen_at);
```

## Business Logic

### Profile Management
- **Profile Updates**: Validate all fields, update only changed data
- **Email Sync**: Keep email in sync with auth service (read-only)
- **Display Name**: Auto-generate from first/last name if not provided
- **Timezone Validation**: Ensure valid timezone strings
- **Phone Number Format**: Validate and format phone numbers

### Preferences Management
- **Default Values**: Provide sensible defaults for new users
- **Validation**: Ensure preference values are within valid ranges
- **Cascading Updates**: Update related services when preferences change
- **Backward Compatibility**: Handle missing preference fields gracefully

### Status Management
- **Online Tracking**: Update last seen timestamp on activity
- **Status Changes**: Validate status transitions
- **Auto-Offline**: Mark users offline after inactivity period
- **Status Messages**: Optional custom status messages

## Security Considerations

### Authorization
- Users can only access their own profile data
- JWT token validation for all user-facing endpoints
- Internal service authentication for service-to-service calls
- Role-based access control (future phases)

### Data Protection
- Profile photos stored securely with proper access controls
- Phone numbers encrypted at rest
- Personal information access logging
- GDPR compliance for profile data

### Input Validation
- Strict validation for all profile fields
- Phone number format validation
- Timezone validation against known timezones
- File upload validation for profile photos

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User profile not found",
    "details": {
      "userId": "invalid-uuid"
    }
  }
}
```

### Common Error Codes
- `USER_NOT_FOUND`: User profile doesn't exist
- `UNAUTHORIZED_ACCESS`: User accessing wrong profile
- `INVALID_PHONE_NUMBER`: Phone number format invalid
- `INVALID_TIMEZONE`: Timezone not recognized
- `PROFILE_PHOTO_TOO_LARGE`: Photo exceeds size limit
- `PREFERENCES_VALIDATION_FAILED`: Invalid preference values

## Testing Strategy

### Unit Tests
- Profile CRUD operations
- Preferences validation and updates
- Status management logic
- Data validation functions
- Default value assignment

### Integration Tests
- Profile synchronization with auth service
- Preferences updates affecting other services
- Status tracking across user sessions
- Database constraints and relationships

### End-to-End Tests
- Complete profile management workflow
- Preferences updates reflecting in dashboard
- Status changes affecting system behavior

## Performance Requirements

- **Profile Updates**: < 300ms (95th percentile)
- **Preferences Retrieval**: < 200ms (95th percentile)
- **Status Updates**: < 100ms (95th percentile)
- **Profile Photo Upload**: < 2000ms for files < 5MB
- **Concurrent Users**: Support 100+ simultaneous profile operations

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# File Storage (for profile photos)
STORAGE_PROVIDER=local # or s3, gcs
STORAGE_PATH=./uploads/profiles
MAX_PHOTO_SIZE_MB=5

# Caching (optional)
REDIS_URL=redis://localhost:6379
PROFILE_CACHE_TTL=300 # 5 minutes

# Service Configuration
PORT=3303
SERVICE_NAME=ts-user-service
```

## Dependencies

### Core Dependencies
- Express.js, Prisma ORM, PostgreSQL driver
- Joi for validation, Winston for logging
- Multer for file uploads (profile photos)

### External Services
- **ts-auth-service**: User authentication and email sync
- **ts-tenant-service**: Tenant validation and relationship
- **Storage Service**: Profile photo storage (local or cloud)

### Optional Dependencies
- **Redis**: Profile caching for improved performance
- **Image Processing**: Profile photo resizing and optimization

## Integration Points

### With ts-auth-service
- Sync user email when auth profile changes
- Validate user existence and active status
- Handle user deactivation cascades

### With ts-tenant-service
- Validate tenant membership
- Handle tenant deletion cascades
- Support tenant-scoped user queries

### With Dashboard Services
- Provide user preferences for UI customization
- Supply user status for availability features
- Support real-time status updates

This user service provides comprehensive profile and preference management while maintaining simplicity appropriate for Phase 1, with clear extension points for future multi-user functionality.