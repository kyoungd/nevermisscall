# AS Alerts Service

Simple, functional alert management system for the NeverMissCall platform. Uses the shared library for database access, configuration, authentication, and common utilities.

## Quick Start

### Prerequisites
- Shared library installed and configured (located at `../shared/`)
- PostgreSQL database configured
- Environment variables set

### Installation
```bash
pip install -r requirements.txt
```

### Environment Variables
```bash
# Database (provided via shared library configuration)
DATABASE_URL=postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall

# Authentication (provided via shared library configuration)  
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1

# Application
PYTHON_ENV=development
LOG_LEVEL=debug
```

### Run the Service
```bash
python main.py
# Service runs on http://localhost:3101
```

### Alternative with uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 3101 --reload
```

## Shared Library Integration

This service uses the NeverMissCall shared library for:

✅ **Database Operations**: Connection pooling, queries, health checks  
✅ **Configuration Management**: Environment variables, service ports  
✅ **Authentication**: Service-to-service API key validation  
✅ **Logging**: Structured JSON logging with context  
✅ **API Responses**: Standardized success/error response formats  
✅ **Validation**: Common validation functions and error handling  

### Shared Library Usage
```python
from shared import (
    init_database,
    query,
    health_check,
    logger,
    get_common_config,
    success_response,
    error_response,
    require_service_auth
)
```

## API Usage

### Health Check
```bash
curl http://localhost:3101/health
```

### Create Alert
```bash
curl -X POST http://localhost:3101/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "rule_name": "high_call_volume",
    "message": "Call volume exceeded threshold",
    "severity": "high"
  }'
```

### Get Alerts
```bash
# All alerts for tenant
curl "http://localhost:3101/alerts?tenant_id=123e4567-e89b-12d3-a456-426614174000"

# Filter by status
curl "http://localhost:3101/alerts?tenant_id=123e4567-e89b-12d3-a456-426614174000&status=triggered"

# Filter by severity
curl "http://localhost:3101/alerts?tenant_id=123e4567-e89b-12d3-a456-426614174000&severity=critical"
```

### Acknowledge Alert
```bash
curl -X PUT http://localhost:3101/alerts/ALERT_ID/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"note": "Investigating the issue"}'
```

### Resolve Alert
```bash
curl -X PUT http://localhost:3101/alerts/ALERT_ID/resolve \
  -H "Content-Type: application/json" \
  -d '{"note": "Issue resolved by restarting service"}'
```

### Get Statistics
```bash
curl http://localhost:3101/stats/123e4567-e89b-12d3-a456-426614174000
```

### Internal Service Call
```bash
curl -X POST http://localhost:3101/internal/alerts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer nmc-internal-services-auth-key-phase1" \
  -d '{
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "rule_name": "system_alert",
    "message": "System maintenance required"
  }'
```

## Alert Workflow

1. **triggered** - Alert created, requires attention
2. **acknowledged** - Someone is investigating (optional note)
3. **resolved** - Issue fixed, alert closed (optional note)

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:3101/docs`
- ReDoc: `http://localhost:3101/redoc`

## Database Schema

The service uses the `alerts` table in PostgreSQL:

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
```

## Development

### Testing
```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py unit

# Verbose output
python run_tests.py -v
```

### Monitoring
Check logs for service activity:
- Health status via `/health` endpoint
- Database connection status via shared library
- Structured logging for troubleshooting

## Architecture

This service follows the NeverMissCall shared library architecture:

- **Single Database**: PostgreSQL connection via shared library
- **Standardized Configuration**: Environment variables via shared config
- **Service Authentication**: Fixed API keys for internal communication
- **Async Operations**: FastAPI + asyncpg for high performance
- **Tenant Isolation**: All operations filtered by tenant_id
- **Error Handling**: Consistent error responses across platform

## Production Notes

- Service runs on port 3101 (configured via shared library)
- Uses shared library connection pooling for database access
- Tenant isolation via `tenant_id` filtering on all queries
- Service-to-service authentication for internal endpoints
- Auto-generated UUIDs for alert IDs
- Structured JSON logging via shared library logger

## Features

✅ **Alert Management**: Create, view, update alert status via shared library  
✅ **Tenant Isolation**: All operations filtered by tenant_id  
✅ **Status Workflow**: triggered → acknowledged → resolved  
✅ **Filtering**: By status and severity with validation  
✅ **Statistics**: Alert counts by status per tenant  
✅ **Internal API**: Service-to-service authenticated endpoints  
✅ **Health Monitoring**: Database connectivity via shared library  
✅ **Error Handling**: Standardized error responses  
✅ **Shared Library**: Database, config, auth, logging integration