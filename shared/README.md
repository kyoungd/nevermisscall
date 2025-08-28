# NeverMissCall Shared Library

The shared library provides common utilities, database access, configuration management, and models for all NeverMissCall microservices following the patterns defined in the project documentation.

## Overview

This shared library implements:
- **Single Database Architecture**: Shared PostgreSQL database with connection pooling
- **Service-to-Service Authentication**: Using fixed API keys for internal communication
- **Standardized API Responses**: Consistent response formats across all services
- **Comprehensive Validation**: Business rule validation with actionable error messages
- **Three-Tier Testing**: Unit, integration, and E2E tests following documentation standards

## Quick Start

### Installation

```bash
cd shared/
pip install -r requirements.txt
```

### Basic Usage

```python
# Initialize database connection
from shared import init_database, get_common_config

config = get_common_config()
db = await init_database(config.database)
await db.connect()

# Query data
from shared import query
users = await query('SELECT * FROM users WHERE tenant_id = $1', [tenant_id])

# Create API responses
from shared import success_response, error_response
return success_response(users, 'Users retrieved successfully')

# Service-to-service communication
from shared import ServiceClient, get_service_url

client = ServiceClient('nmc-internal-services-auth-key-phase1')
auth_url = get_service_url('auth-service')
response = await client.get(f'{auth_url}/internal/users')
```

## Architecture

### Database Module (`/database`)
- `SimpleDatabase`: Main database connection and query management
- `BaseRepository`: Generic repository pattern for CRUD operations
- `SimpleMigrationManager`: Database migration management

### Configuration Module (`/config`)
- `get_common_config()`: Load configuration from environment variables
- `get_service_url()`: Generate service URLs for communication
- `SERVICE_PORTS`: Mapping of service names to ports

### Utilities Module (`/utils`)
- `logger`: Structured JSON logging with context
- `ServiceClient`: HTTP client for service-to-service communication
- Validation functions: Email, phone, UUID, password validation
- Helper functions: Date formatting, ID generation, FastAPI middleware

### Models Module (`/models`)
- `ApiResponse`: Standardized API response format
- Authentication models: User, Tenant, JwtPayload
- Core business models: Call, Conversation, Message, Lead, PhoneNumber
- Exception classes: ValidationError, NotFoundError, UnauthorizedError

## Environment Variables

Required environment variables with defaults:

```env
# Database (required)
DATABASE_URL=postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall

# Authentication (required)
JWT_SECRET=e8a3b5c7d9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1

# Application
PYTHON_ENV=development
LOG_LEVEL=debug
DB_MAX_CONNECTIONS=5
JWT_EXPIRES_IN=24h
```

## Database Management

### Running Migrations

```python
from shared.database import SimpleMigrationManager

manager = SimpleMigrationManager()

# Check status
status = await manager.get_status()
print(f"Executed: {status['total_executed']}, Pending: {status['total_pending']}")

# Run migrations
executed = await manager.run_migrations()
print(f"Executed {len(executed)} migrations")

# Create new migration
filename = await manager.create_migration("add user preferences table")
```

### Using Repository Pattern

```python
from shared.database import BaseRepository
from shared.models import User

class UsersRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__('users', User)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        users = await self.find_by_filters({'email': email})
        return users[0] if users else None

# Usage
users_repo = UsersRepository()
user = await users_repo.find_by_id('user-uuid')
users = await users_repo.find_by_filters({'tenant_id': 'tenant-uuid'})
```

## Testing

The shared library follows the three-tier testing architecture defined in the documentation:

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test tier
python run_tests.py unit
python run_tests.py integration
python run_tests.py e2e

# Verbose output
python run_tests.py -v
```

### Test Organization

```
tests/
├── unit/                    # Tier 1: Unit tests with heavy mocking
│   ├── test_validation.py   # Validation function tests
│   ├── test_models.py       # Pydantic model tests
│   └── test_config.py       # Configuration tests
├── integration/             # Tier 2: Integration tests with selective mocking
│   └── test_database.py     # Database integration tests
└── e2e/                     # Tier 3: End-to-end tests with no mocking
    └── test_full_system.py  # Complete system tests
```

### Testing Philosophy

Following the "Honest Failure Over Eager Passing" principle:
- Tests validate actual behavior, not just mock interactions
- Business logic validation with real error conditions
- Meaningful test failures that help identify real bugs
- Three-tier coverage ensures comprehensive validation

## Service Integration

### Authentication Patterns

#### User-Facing Endpoints
```python
from shared.utils import require_jwt_auth

@app.get("/users/profile")
async def get_profile(jwt_payload: dict = Depends(require_jwt_auth())):
    user_id = jwt_payload['user_id']
    tenant_id = jwt_payload['tenant_id']
    # ... handle request
```

#### Service-to-Service Endpoints
```python
from shared.utils import require_service_auth

@app.post("/internal/users")
async def create_user(
    user_data: dict,
    authenticated: bool = Depends(require_service_auth('nmc-internal-services-auth-key-phase1'))
):
    # ... handle internal request
```

### Error Handling

```python
from shared import ValidationError, success_response, error_response

try:
    validate_email_required(email, 'customer_email')
    # ... business logic
    return success_response(result, 'Operation completed successfully')
    
except ValidationError as error:
    return error_response(str(error), details={
        'code': error.code,
        'field': error.field
    })
```

## Development Patterns

### Logging with Context

```python
from shared import logger

# Basic logging
logger.info('User login successful', extra={'user_id': '123', 'tenant_id': '456'})

# Context logging for request handling
with logger.set_context(request_id='req-123', tenant_id='tenant-456') as ctx:
    ctx.info('Processing user request')
    ctx.error('Validation failed', error=exception)
```

### Database Operations

```python
from shared import query, get_database

# Direct queries
users = await query('SELECT * FROM users WHERE tenant_id = $1', [tenant_id])

# Transactions
db = get_database()
async with db.get_pool().acquire() as conn:
    async with conn.transaction():
        await conn.execute('INSERT INTO users ...', values)
        await conn.execute('INSERT INTO user_profiles ...', profile_values)
```

## Performance Considerations

- **Connection Pooling**: Single shared connection pool for all services
- **Async Operations**: All database operations are async for performance
- **Structured Logging**: JSON logging for efficient log aggregation
- **Caching**: Application-level caching for configuration data
- **Pagination**: Built-in pagination support for large datasets

## Security Features

- **Input Validation**: Comprehensive validation with business rule enforcement
- **SQL Injection Prevention**: Parameterized queries throughout
- **JWT Security**: Secure token validation with configurable expiration
- **Service Authentication**: Fixed API key validation for internal services
- **Data Sanitization**: Automatic sanitization of user input

## Documentation

- Complete API documentation in `/docs/services/phase-1/shared.md`
- Database schema in `/docs/services/phase-1/database-migration-order.md`
- Authentication patterns in `/docs/services/phase-1/authentication-standards.md`
- Testing standards in `/documentation-requirement.md`

This shared library provides the foundation for all NeverMissCall microservices, ensuring consistency, reliability, and maintainability across the platform.