# NeverMissCall Shared Library Documentation

The shared library provides common utilities, database access, configuration management, and models for all NeverMissCall microservices. This documentation covers all available classes, functions, and data models.

## Overview

The shared library follows these principles:
- **Simple**: No complex patterns or abstractions
- **Stable**: Focus on reliability over features  
- **File-based**: Direct imports, no published packages
- **Small Market**: Perfect for single-server deployments

## Installation & Import

```python
# Import specific functions/classes
from shared import init_database, get_common_config, logger, success_response

# Or import from specific modules
from shared.database import SimpleDatabase
from shared.utils import ServiceClient
```

---

## 📁 Database Module (`/database`)

### SimpleDatabase Class

Main database connection and query management class.

```python
class SimpleDatabase:
    def __init__(self, config: DatabaseConfig)
    async def connect(self) -> None
    async def query(self, sql: str, params: list = None) -> Any
    async def health_check(self) -> bool
    def get_pool(self) -> asyncpg.Pool
    async def close(self) -> None
```

**Usage:**
```python
db = SimpleDatabase({'url': 'postgresql://...'})
await db.connect()
result = await db.query('SELECT * FROM users WHERE id = $1', [user_id])
```

### DatabaseConfig Model

```python
from pydantic import BaseModel
from typing import Optional

class DatabaseConfig(BaseModel):
    url: Optional[str] = None           # Full connection string
    host: Optional[str] = 'localhost'   # Database host
    port: Optional[int] = 5432          # Database port
    database: Optional[str] = 'nevermisscall'  # Database name
    username: Optional[str] = 'nevermisscall_user'  # Username
    password: Optional[str] = 'nevermisscall_admin411'  # Password
    max_connections: Optional[int] = 5  # Max pool connections
```

### Database Helper Functions

```python
# Initialize singleton database instance
def init_database(config: DatabaseConfig) -> SimpleDatabase

# Get existing database instance
def get_database() -> SimpleDatabase

# Direct query helper (uses singleton instance)
async def query(sql: str, params: list = None) -> Any

# Database health check
async def health_check() -> bool

# Simple database object for compatibility
database = {
    'query': lambda sql, params=None: query(sql, params),
    'health_check': lambda: health_check()
}
```

**Usage Examples:**
```python
import os

# Initialize database
db = init_database({'url': os.getenv('DATABASE_URL')})
await db.connect()

# Direct queries
users = await query('SELECT * FROM users')
user = await query('SELECT * FROM users WHERE id = $1', [user_id])

# Health check
is_healthy = await health_check()
```

### BaseRepository Class

Simple base repository for common database operations.

```python
from typing import Generic, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    def __init__(self, table_name: str, model_class: type[T])
    
    async def create(self, data: Dict[str, Any]) -> T
    async def find_by_id(self, id: str) -> Optional[T]
    async def find_by_filters(self, filters: Dict[str, Any]) -> List[T]
    async def get_paginated(self, page: int, limit: int, filters: Dict[str, Any] = None) -> Dict[str, Any]
    async def update_status(self, id: str, status: str, additional_data: Dict[str, Any] = None) -> Optional[T]
    async def get_statistics(self, tenant_id: str = None) -> Dict[str, int]
```

**Usage:**
```python
from shared.models import User

class UsersRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__('users', User)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        users = await self.find_by_filters({'email': email})
        return users[0] if users else None
```

---

## ⚙️ Configuration Module (`/config`)

### CommonConfig Model

```python
from pydantic import BaseModel

class DatabaseConfigSection(BaseModel):
    url: str
    max_connections: int

class JwtConfigSection(BaseModel):
    secret: str
    expires_in: str

class ServiceAuthConfigSection(BaseModel):
    key: str

class CommonConfig(BaseModel):
    node_env: str
    log_level: str
    database: DatabaseConfigSection
    jwt: JwtConfigSection
    service_auth: ServiceAuthConfigSection
```

### Configuration Functions

```python
from typing import Any, Optional

# Get common configuration from environment variables
def get_common_config() -> CommonConfig

# Get service-specific configuration  
def get_service_config(service_name: str, service_specific_config: Any) -> Any

# Get service URL by name
def get_service_url(service_name: str, host: Optional[str] = None) -> str
```

**Usage:**
```python
config = get_common_config()
db_url = config.database.url
jwt_secret = config.jwt.secret

# Service URLs
auth_url = get_service_url('auth-service')  # http://localhost:3301
alerts_url = get_service_url('alerts-service')  # http://localhost:3101
```

### SERVICE_PORTS Constants

```python
from typing import Dict, Literal

SERVICE_PORTS: Dict[str, int] = {
    'auth-service': 3301,
    'tenant-service': 3302,
    'user-service': 3303,
    'config-service': 3304,
    'call-service': 3305,
    'alerts-service': 3101,
    'analytics-service': 3102,
    'provisioning-service': 3501,
    'connection-service': 3105,
    'infrastructure-service': 3106,
    'web-ui': 3000,
    'twilio-service': 3701,
    'ai-service': 3801,
    'calendar-service': 3901,
}

ServiceName = Literal[
    'auth-service', 'tenant-service', 'user-service', 'config-service',
    'call-service', 'alerts-service', 'analytics-service', 'provisioning-service',
    'connection-service', 'infrastructure-service', 'web-ui', 'twilio-service',
    'ai-service', 'calendar-service'
]
```

---

## 🛠️ Utilities Module (`/utils`)

### Logger Object

Simple console-based logger with timestamps.

```python
import logging
from typing import Any, Optional

class Logger:
    def info(self, message: str, extra: Optional[dict] = None) -> None
    def error(self, message: str, error: Optional[Exception] = None) -> None
    def warn(self, message: str, extra: Optional[dict] = None) -> None
    def debug(self, message: str, extra: Optional[dict] = None) -> None  # Only in development

logger = Logger()
```

**Usage:**
```python
logger.info('User created successfully', extra={'user_id': 'user-123'})
logger.error('Database connection failed', error=exception)
logger.warn('High memory usage detected')
logger.debug('Processing request', extra=request_data)
```

### ServiceClient Class

HTTP client for service-to-service communication.

```python
import httpx
from typing import Any, Optional, Dict
from shared.models import ApiResponse

class ServiceClient:
    def __init__(self, service_key: str)
    
    async def get(self, url: str) -> ApiResponse
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> ApiResponse
```

**Usage:**
```python
client = ServiceClient('nmc-internal-services-auth-key-phase1')

# GET request
users_response = await client.get('http://localhost:3303/internal/users')

# POST request  
new_user_response = await client.post('http://localhost:3303/internal/users', {
    'email': 'user@example.com',
    'tenant_id': 'tenant-123'
})
```

### Validation Functions

```python
from typing import Any, Dict, List

# Required field validation
def validate_required(value: Any, field_name: str) -> None

# Email validation
def validate_email(email: str) -> bool

# Phone number validation  
def validate_phone_number(phone: str) -> bool

# UUID validation
def validate_uuid(uuid: str) -> bool

# Password validation
def validate_password(password: str) -> Dict[str, Any]  # {'valid': bool, 'errors': List[str]}
```

**Usage:**
```python
try:
    validate_required(email, 'email')
    if not validate_email(email):
        raise ValueError('Invalid email format')
except ValueError as error:
    print(str(error))

password_check = validate_password('myPassword123')
if not password_check['valid']:
    print('Password errors:', password_check['errors'])
```

### Helper Functions

```python
from datetime import datetime
from typing import Union, Callable, Any
from fastapi import Request, HTTPException

# Date helpers
def format_date(date: Union[datetime, str]) -> str
def is_valid_date(date: str) -> bool

# String helpers  
def sanitize_string(string: str) -> str
def generate_id() -> str

# FastAPI middleware helpers
def async_handler(fn: Callable) -> Callable
def require_service_auth(service_key: str) -> Callable
```

**Usage:**
```python
from datetime import datetime
from fastapi import FastAPI, Depends

# Date formatting
iso_date = format_date(datetime.now())  # "2024-01-01T12:00:00.000Z"

# Generate UUID
id = generate_id()  # "123e4567-e89b-12d3-a456-426614174000"

# FastAPI dependencies
app = FastAPI()

@app.get('/users', dependencies=[Depends(require_service_auth('nmc-internal-services-auth-key-phase1'))])
async def get_users():
    users = await get_users_from_database()
    return users
```

---

## 📋 Models Module (`/models`)

### Core Models

#### ApiResponse Model
```python
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
```

#### HealthStatus Model
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
from datetime import datetime

class HealthStatus(BaseModel):
    status: Literal['healthy', 'unhealthy', 'degraded']
    service: str
    version: Optional[str] = None
    uptime: Optional[int] = None
    dependencies: Optional[Dict[str, Literal['healthy', 'unhealthy']]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
```

#### User Model
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: str
    tenant_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

#### Tenant Model
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Tenant(BaseModel):
    id: str
    name: str
    domain: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

#### Call Model
```python
from pydantic import BaseModel, Field
from datetime import datetime

class Call(BaseModel):
    id: str
    tenant_id: str
    from_number: str
    to_number: str
    status: str
    duration: int
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

#### JwtPayload Model
```python
from pydantic import BaseModel
from typing import Optional

class JwtPayload(BaseModel):
    user_id: str
    tenant_id: str
    role: str
    email: str
    iat: Optional[int] = None
    exp: Optional[int] = None
```

### Exception Classes

```python
from typing import Optional

class ValidationError(Exception):
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field

class NotFoundError(Exception):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "Resource not found")

class UnauthorizedError(Exception):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "Unauthorized access")
```

### Response Helper Functions

```python
from typing import Any, Optional
from shared.models import ApiResponse

# Success response
def success_response(data: Any, message: Optional[str] = None) -> ApiResponse:
    return ApiResponse(success=True, data=data, message=message)

# Error response
def error_response(error: str, data: Optional[Any] = None) -> ApiResponse:
    return ApiResponse(success=False, error=error, data=data)
```

**Usage:**
```python
# In your API handlers
return success_response(user_data, 'User retrieved successfully')
return error_response('User not found')

# Error handling
try:
    validate_required(email, 'email')
except ValidationError as error:
    return error_response(f"Validation error: {str(error)}")
except Exception as error:
    return error_response(f"Internal error: {str(error)}")
```

---

## 🚀 Quick Start Examples

### Basic Service Setup

```python
from fastapi import FastAPI, HTTPException
from shared import init_database, get_common_config, logger, success_response, error_response, query

# Initialize service
app = FastAPI()
config = get_common_config()
db = init_database(config.database)
await db.connect()

logger.info('Service initialized')

# Simple API endpoint
@app.get('/users')
async def get_users(tenant_id: str):
    try:
        users = await query('SELECT * FROM users WHERE tenant_id = $1', [tenant_id])
        return success_response(users)
    except Exception as error:
        logger.error('Failed to get users', error=error)
        raise HTTPException(status_code=500, detail='Internal server error')
```

### Service-to-Service Communication

```python
from shared import ServiceClient, get_service_url
from shared.models import User

client = ServiceClient('nmc-internal-services-auth-key-phase1')
auth_service_url = get_service_url('auth-service')

# Call another service
user_response = await client.get(f'{auth_service_url}/internal/user/{user_id}')
if user_response.success:
    print('User:', user_response.data)
```

### Repository Pattern

```python
from shared.database import BaseRepository
from shared.models import User
from typing import List

class UsersRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__('users', User)
    
    async def find_by_tenant(self, tenant_id: str) -> List[User]:
        return await self.find_by_filters({'tenant_id': tenant_id, 'is_active': True})

# Usage
users_repo = UsersRepository()
users = await users_repo.find_by_tenant('tenant-123')
user = await users_repo.find_by_id('user-456')
```

---

## Environment Variables

The shared library uses these environment variables with sensible defaults:

```env
# Database
DATABASE_URL=postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall
DB_MAX_CONNECTIONS=5

# Authentication  
JWT_SECRET=e8a3b5c7d9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6
JWT_EXPIRES_IN=24h
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1

# Application
PYTHON_ENV=development
LOG_LEVEL=debug
```

---

## Migration Management

```python
# From any service directory
from shared.database.migrations import SimpleMigrationManager

migration_manager = SimpleMigrationManager()

# Check status
await migration_manager.get_status()

# Run migrations
await migration_manager.run_migrations()

# Create new migration
await migration_manager.create_migration('add_user_preferences')

# Or using Alembic directly
from alembic import command
from alembic.config import Config

alembic_cfg = Config('alembic.ini')
command.upgrade(alembic_cfg, 'head')
command.revision(alembic_cfg, autogenerate=True, message='add_user_preferences')
```

---

---

## Testing Framework

The shared library and all services use **unittest** (Python's built-in testing framework) for comprehensive test coverage:

```python
import unittest
from unittest.mock import AsyncMock, patch
from shared import init_database, success_response
from shared.models import User

class TestSharedDatabase(unittest.TestCase):
    
    async def test_database_connection(self):
        """Test database initialization and connection"""
        db = init_database({'url': 'postgresql://test'})
        self.assertIsNotNone(db)
    
    def test_success_response(self):
        """Test success response helper"""
        response = success_response({'id': '123'}, 'Test message')
        self.assertTrue(response.success)
        self.assertEqual(response.message, 'Test message')

if __name__ == '__main__':
    unittest.main()
```

### Running Tests
```bash
# Run all tests in a service
python -m unittest discover tests/

# Run with verbose output
python -m unittest discover tests/ -v

# Run specific test file
python -m unittest tests.test_database

# Run specific test method
python -m unittest tests.test_database.TestSharedDatabase.test_database_connection
```

---

This documentation covers all available functions, classes, and data models in the shared library. For specific implementation details, refer to the Python source files in the `/shared` directory.