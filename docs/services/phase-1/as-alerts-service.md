# AS Alerts Service - Application Specification

## Overview

The AS Alerts Service is a simple, functional alert management system for the NeverMissCall platform. It provides basic alert creation, management, and status tracking capabilities designed for small market deployment.

## Service Information

- **Service Name**: as-alerts-service
- **Port**: 3101
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **Database**: PostgreSQL (asyncpg connection)
- **Architecture**: Simple, single-file implementation

## Design Philosophy

This service follows the NeverMissCall "small market" philosophy:
- **Simple**: Direct database queries, no abstractions
- **Functional**: Real alert management capabilities
- **Stable**: Minimal dependencies, proven patterns  
- **Small Market Ready**: Single-server deployment optimized

## Core Features

### 1. Alert Management
- Create new alerts with tenant isolation
- Retrieve alerts by tenant with filtering
- Update alert status (acknowledge, resolve)
- Basic alert statistics and reporting

### 2. Status Workflow
- **triggered** → **acknowledged** → **resolved**
- Manual acknowledgment with optional notes
- Manual resolution with optional notes
- Status history tracking via timestamps

### 3. Multi-Tenant Support
- All alerts isolated by `tenant_id`
- Tenant-specific statistics
- Secure data separation

### 4. Internal Service Integration
- Service-to-service authentication
- Internal endpoints for microservice communication
- Standardized API responses

## API Endpoints

### Public Endpoints

#### Health Check
```
GET /health
Response: {"status": "healthy", "service": "as-alerts-service"}
```

#### Create Alert
```
POST /alerts
Headers: Content-Type: application/json
Body: {
  "tenant_id": "uuid",
  "rule_name": "string",
  "message": "string", 
  "severity": "low|medium|high|critical"
}
Response: Alert object with generated ID
```

#### Get Alerts for Tenant
```
GET /alerts?tenant_id=uuid&status=triggered&severity=high
Query Parameters:
  - tenant_id (required): Tenant UUID
  - status (optional): Filter by status
  - severity (optional): Filter by severity
Response: Array of alert objects (max 50)
```

#### Get Specific Alert
```
GET /alerts/{alert_id}
Response: Single alert object or 404
```

#### Acknowledge Alert
```
PUT /alerts/{alert_id}/acknowledge
Body: {"note": "optional acknowledgment note"}
Response: Updated alert object
```

#### Resolve Alert
```
PUT /alerts/{alert_id}/resolve  
Body: {"note": "optional resolution note"}
Response: Updated alert object
```

#### Get Statistics
```
GET /stats/{tenant_id}
Response: {
  "total": int,
  "triggered": int,
  "acknowledged": int, 
  "resolved": int
}
```

### Internal Service Endpoints

#### Create Internal Alert
```
POST /internal/alerts
Headers: x-service-key: nmc-internal-services-auth-key-phase1
Body: Same as public alert creation
Response: Alert object
```

## Data Model

### Alert Object Structure
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class Alert(BaseModel):
    id: str                                    # Auto-generated UUID
    tenant_id: str                            # Required UUID
    rule_name: str                            # Alert rule name
    message: str                              # Alert description
    severity: AlertSeverity = AlertSeverity.MEDIUM
    status: AlertStatus = AlertStatus.TRIGGERED
    created_at: datetime                      # Auto-set
    updated_at: datetime                      # Auto-updated
    acknowledged_at: Optional[datetime] = None
    acknowledgment_note: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
```

### Database Schema

```sql
CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  rule_name VARCHAR(255),
  message TEXT NOT NULL,
  severity VARCHAR(50) DEFAULT 'medium',
  status VARCHAR(50) DEFAULT 'triggered',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  acknowledged_at TIMESTAMP NULL,
  acknowledgment_note TEXT NULL,
  resolved_at TIMESTAMP NULL,
  resolution_note TEXT NULL
);

CREATE INDEX idx_alerts_tenant_id ON alerts(tenant_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_created_at ON alerts(created_at);
```

## Environment Variables

```env
# Application
AS_ALERTS_PORT=3101
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall

# Authentication
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1
```

## Service Dependencies

### Required Services
- **PostgreSQL Database**: For alert storage and retrieval
- **None**: Service runs independently without external service dependencies

### Integration Points
- **Internal Services**: Other NeverMissCall services can create alerts via internal API
- **Database**: Direct PostgreSQL connection for data persistence

## File Structure

```
as-alerts-service/
├── main.py                     # Main FastAPI application file
├── requirements.txt            # Python dependencies
├── README.md                   # Basic usage instructions
└── as-alerts-service.md        # This specification document
```

## Implementation Details

### Technology Stack
- **Runtime**: Python 3.10+
- **Framework**: FastAPI (async/await support)
- **Database**: PostgreSQL with `asyncpg` driver
- **Dependencies**: FastAPI, asyncpg, pydantic, uvicorn

### Key Implementation Choices
- **Direct SQL Queries**: No ORM, direct PostgreSQL queries with asyncpg for performance
- **Async/Await**: FastAPI async endpoints for better concurrency
- **Pydantic Models**: Type-safe request/response validation
- **Connection Pooling**: PostgreSQL connection pool with 5 max connections
- **Synchronous Processing**: No background jobs, immediate processing
- **Structured Logging**: Python logging with JSON formatting

### Security Features
- **Input Validation**: Pydantic model validation
- **SQL Injection Protection**: Parameterized queries with asyncpg
- **Service Authentication**: Internal endpoint protection via dependency injection
- **Tenant Isolation**: All queries filtered by tenant_id

## Operational Considerations

### Startup
```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 3101 --reload
# Service runs on port 3101
```

### Health Monitoring
- Health endpoint provides service status
- Database connectivity verification
- Simple uptime tracking

### Performance Characteristics
- **Lightweight**: Minimal Python FastAPI application, low memory footprint
- **Fast Startup**: Starts in <2 seconds
- **Async Database Access**: Non-blocking asyncpg operations
- **High Concurrency**: FastAPI async support for multiple concurrent requests

### Scaling Considerations
- **Single Instance**: Designed for single-server deployment  
- **Database Bottleneck**: PostgreSQL connection limit is the constraint
- **Stateless**: Can run multiple instances if needed (with load balancer)
- **Async Benefits**: Better resource utilization with Python async/await

## Error Handling

### Error Response Format
```python
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
```

### HTTP Status Codes
- **200**: Success
- **201**: Alert created
- **422**: Validation errors (Pydantic validation)
- **404**: Alert not found
- **500**: Internal server error
- **503**: Service unavailable (health check failure)

### Common Error Scenarios
- **Missing tenant_id**: 422 with Pydantic validation error
- **Invalid UUID format**: 422 with validation error details
- **Database connection failure**: 500 with connection error
- **Alert not found**: 404 with "Alert not found" message

## Testing Strategy

### Manual Testing
```bash
# Health check
curl http://localhost:3101/health

# Create alert
curl -X POST http://localhost:3101/alerts \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"123e4567-e89b-12d3-a456-426614174000","message":"Test alert","rule_name":"test_rule"}'

# Get alerts
curl "http://localhost:3101/alerts?tenant_id=123e4567-e89b-12d3-a456-426614174000"

# Acknowledge alert
curl -X PUT http://localhost:3101/alerts/ALERT_ID/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"note":"Investigating issue"}'
```

### Integration Testing
- Verify database schema compatibility
- Test service-to-service authentication using FastAPI dependencies
- Validate tenant isolation
- Confirm alert workflow completeness
- Test async database operations

## Future Considerations

### Possible Enhancements (if needed)
- **Email Notifications**: Add SMTP integration for alert notifications
- **Webhook Support**: HTTP callbacks when alerts are created/updated
- **Alert Rules**: Configurable alert triggering rules
- **Bulk Operations**: Batch alert creation and updates
- **Audit Trail**: Detailed change history tracking

### Scaling Options (if needed)
- **Read Replicas**: Database read scaling
- **Caching**: Redis for frequently accessed data
- **Message Queue**: Async processing for high volumes
- **Multi-Instance**: Load balanced deployment

## Maintenance

### Regular Operations
- **Log Monitoring**: Check structured Python logs for errors
- **Database Health**: Monitor PostgreSQL connection status via asyncpg
- **Disk Space**: Alert data grows over time
- **Performance**: Monitor async response times under load

### Backup Strategy
- **Database Backup**: Regular PostgreSQL backups
- **Configuration Backup**: Environment variables and deployment scripts
- **Code Backup**: Version control system

This specification documents the as-alerts-service as a simple, functional, and reliable component of the NeverMissCall platform, designed specifically for small market deployment needs.