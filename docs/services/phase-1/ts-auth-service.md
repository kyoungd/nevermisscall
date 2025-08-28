# auth-service Design Document

## Service Overview

**Service Name**: auth-service  
**Port**: 3301  
**Phase**: 1 - Identity & Onboarding  
**Purpose**: User registration, login, and JWT token management for business owners  

## Business Requirements

### Primary Functions
- Business owner account registration
- User login and authentication
- JWT token generation and validation
- Session management and refresh
- Password reset functionality
- Basic user profile management

### Success Criteria
- New business owners can register in < 30 seconds
- Login process completes in < 2 seconds
- JWT tokens are secure and properly validated
- Session management prevents unauthorized access
- Password reset works reliably

## Technical Specification

### Technology Stack
- **Runtime**: Python 3.11+
- **Framework**: FastAPI with Pydantic for validation
- **Database**: PostgreSQL with asyncpg/SQLAlchemy
- **Authentication**: JWT with bcrypt for password hashing
- **Testing**: unittest for comprehensive test coverage
- **HTTP Client**: httpx for service-to-service communication

### Service Architecture

```mermaid
graph TB
    subgraph "ts-auth-service (Port 3301)"
        AuthController[AuthController]
        AuthService[AuthService]
        TokenService[TokenService]
        ValidationMiddleware[ValidationMiddleware]
        Database[(PostgreSQL<br/>nevermisscall)]
    end
    
    WebUI[web-ui] --> AuthController
    ASCallService[as-call-service] --> AuthController
    AuthController --> AuthService
    AuthService --> TokenService
    AuthService --> Database
```

## API Endpoints

### Authentication Endpoints

#### POST /auth/register
**Purpose**: Register new business owner account  
**Request Body**:
```json
{
  "email": "owner@business.com",
  "password": "securePassword123",
  "firstName": "John",
  "lastName": "Smith",
  "businessName": "Smith Plumbing"
}
```
**Response (201)**:
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "owner@business.com",
    "firstName": "John",
    "lastName": "Smith"
  },
  "tokens": {
    "accessToken": "jwt-token",
    "refreshToken": "refresh-token",
    "expiresIn": 3600
  }
}
```

#### POST /auth/login
**Purpose**: Authenticate existing user  
**Request Body**:
```json
{
  "email": "owner@business.com",
  "password": "securePassword123"
}
```
**Response (200)**:
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "owner@business.com",
    "firstName": "John",
    "lastName": "Smith",
    "tenantId": "tenant-uuid"
  },
  "tokens": {
    "accessToken": "jwt-token",
    "refreshToken": "refresh-token",
    "expiresIn": 3600
  }
}
```

#### POST /auth/refresh
**Purpose**: Refresh expired access token  
**Request Body**:
```json
{
  "refreshToken": "refresh-token"
}
```
**Response (200)**:
```json
{
  "success": true,
  "tokens": {
    "accessToken": "new-jwt-token",
    "expiresIn": 3600
  }
}
```

#### POST /auth/logout
**Purpose**: Invalidate user session  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Validation Endpoints

#### POST /auth/validate
**Purpose**: Validate JWT token (for other services)  
**Request Body**:
```json
{
  "token": "jwt-token"
}
```
**Response (200)**:
```json
{
  "valid": true,
  "user": {
    "id": "uuid",
    "email": "owner@business.com",
    "tenantId": "tenant-uuid",
    "role": "owner"
  }
}
```

#### GET /auth/me
**Purpose**: Get current user information  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "user": {
    "id": "uuid",
    "email": "owner@business.com",
    "firstName": "John",
    "lastName": "Smith",
    "tenantId": "tenant-uuid",
    "role": "owner"
  }
}
```

## Data Models

### User Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    tenant_id: str
    role: Literal['owner', 'operator', 'viewer']
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
```

### Session Entity
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class UserSession:
    id: str
    user_id: str
    refresh_token: str
    expires_at: datetime
    is_active: bool
    created_at: datetime
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
```

### JWT Payload
```python
from dataclasses import dataclass

@dataclass
class JWTPayload:
    sub: str  # user ID
    email: str
    tenant_id: str
    role: str
    iat: int
    exp: int
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    tenant_id UUID, -- Initially null, set during onboarding
    role VARCHAR(50) DEFAULT 'owner',
    email_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### User Sessions Table
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    device_info TEXT,
    ip_address INET,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## Business Logic

### Registration Process
1. **Validate Input**: Email format, password strength, required fields
2. **Check Uniqueness**: Ensure email doesn't already exist
3. **Hash Password**: Use bcrypt with salt rounds = 12
4. **Create User**: Store user record (tenantId initially null)
5. **Generate Tokens**: Create JWT access token and refresh token
6. **Create Session**: Store refresh token in sessions table
7. **Return Response**: User info + tokens

### Login Process
1. **Validate Input**: Email and password provided
2. **Find User**: Look up user by email
3. **Verify Password**: Compare with stored hash using bcrypt
4. **Generate Tokens**: Create new JWT and refresh token
5. **Update Session**: Store/update refresh token
6. **Update Last Login**: Record login timestamp
7. **Return Response**: User info + tokens

### Token Validation (for other services)
1. **Extract Token**: From Authorization header or request body
2. **Verify JWT**: Check signature, expiration, format
3. **Return User Data**: If valid, return user information
4. **Handle Errors**: Return appropriate error for invalid tokens

## Security Considerations

### Password Security
- Minimum 8 characters, must include letters and numbers
- Bcrypt hashing with salt rounds = 12
- No password storage in logs or responses

### JWT Security
- Short expiration time (1 hour) for access tokens
- Secure random refresh tokens with 30-day expiration
- HS256 algorithm with strong secret key
- Include user ID, tenant ID, and role in payload

### Session Management
- Refresh tokens stored securely in database
- Automatic cleanup of expired sessions
- Device tracking for suspicious activity detection
- IP address logging for security analysis

### API Security
- Rate limiting on auth endpoints (10 attempts/minute/IP)
- CORS configuration for web UI only
- Input validation and sanitization
- SQL injection prevention with parameterized queries

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect",
    "details": {}
  }
}
```

### Common Error Codes
- `INVALID_CREDENTIALS`: Wrong email/password
- `EMAIL_ALREADY_EXISTS`: Registration with existing email
- `INVALID_TOKEN`: Malformed or expired JWT
- `SESSION_EXPIRED`: Refresh token expired
- `VALIDATION_ERROR`: Request validation failed
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Testing Strategy

Uses **unittest** (Python's built-in testing framework) for comprehensive test coverage.

### Unit Tests (70% coverage minimum)
```python
import unittest
from unittest.mock import AsyncMock, patch
from auth_service import AuthService, TokenService

class TestAuthService(unittest.TestCase):
    async def test_password_hashing_verification(self)
    async def test_jwt_token_generation_validation(self)
    def test_input_validation_logic(self)
    def test_error_handling_scenarios(self)
```

### Integration Tests
```python
class TestAuthIntegration(unittest.TestCase):
    async def test_database_operations_crud(self)
    async def test_full_authentication_flows(self)
    async def test_token_refresh_process(self)
    async def test_session_management(self)
```

### Security Tests
```python
class TestAuthSecurity(unittest.TestCase):
    def test_password_strength_enforcement(self)
    def test_jwt_token_security(self)
    async def test_rate_limiting_effectiveness(self)
    def test_sql_injection_prevention(self)
```

### Running Tests
```bash
python -m unittest discover tests/
python -m unittest discover tests/ -v
```

## Performance Requirements

- **Login Response**: < 500ms (95th percentile)
- **Registration Response**: < 1000ms (95th percentile) 
- **Token Validation**: < 100ms (95th percentile)
- **Concurrent Users**: 100+ simultaneous authentications
- **Database Connections**: Connection pooling with max 10 connections

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# JWT Configuration
JWT_SECRET=secure-random-256-bit-key
JWT_EXPIRES_IN=1h
REFRESH_TOKEN_EXPIRES_IN=30d

# Security
BCRYPT_SALT_ROUNDS=12
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=10

# Service
PORT=3301
NODE_ENV=development
```

## Deployment Notes

### Health Check
- `GET /health` - Returns service status and database connectivity
- Database connection test included
- Response time monitoring

### Logging
- Structured JSON logging with Python logging
- Log levels: error, warn, info, debug
- User actions logged (without sensitive data)
- Performance metrics collected

### Dependencies
- FastAPI, SQLAlchemy/asyncpg, bcrypt, PyJWT
- Pydantic for validation, Python logging
- asyncpg PostgreSQL driver, CORS middleware

This auth service provides the foundation for secure user management in Phase 1, with simple but robust authentication that can be extended in future phases.