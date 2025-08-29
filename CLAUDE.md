# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **NeverMissCall Phase 1** implementation - a focused call management system that turns missed calls into SMS conversations with AI assistance and seamless human handoff. Phase 1 delivers a complete, working system for small market deployment.

## Phase 1 Scope

**Current Focus**: Building the core working system (4-6 weeks)
- Business onboarding and phone number provisioning
- Missed call to SMS conversion with AI processing  
- Real-time dashboard with conversation management
- Manual takeover from AI conversations
- Basic lead tracking and appointment scheduling

**Excluded from Phase 1**: Advanced analytics, business intelligence, multi-user support, billing systems, phone number compliance features

## Development Philosophy

Our market is small, so we prioritize simplicity and working functionality over complex optimizations:

- **Clean, Readable Code** - Prioritize clarity and maintainability
- **Coding Best Practices** - Strict adherence to best practice standards
- **Easy Implementation** - Simple setup for end users
- **Straightforward Architecture** - Avoid over-engineering
- **Functionality First** - Focus on working features over performance optimization
- **Documentation-Driven** - All implementation follows detailed specifications

## CRITICAL: AI Code Generation Standards

**MANDATORY READING**: All AI-generated code MUST follow the comprehensive guidelines in `/documentation-requirement.md`.

### Key AI Development Requirements:
- **Honest Failure Over Eager Passing**: Tests must validate actual behavior, not just pass
- **Business Logic Focus**: Code must solve real business problems with proper error handling
- **Three-Tier Testing**: Unit, Integration, and E2E tests with meaningful validation
- **Domain Knowledge Integration**: Code must understand and enforce business rules
- **Self-Documenting Code**: Clear business context and purpose in all implementations

### Before Writing Any Code:
1. **Always check the /docs folder first** - Review all relevant documentation in docs/architecture/, docs/services/phase-1/, and docs/overview/ before implementing anything
2. **Read existing patterns** in the codebase and follow them exactly
3. **Ask: "What real bug would this catch?"** for all tests and validations
4. **Include error conditions and edge cases** in all implementations
5. **Write domain-specific, testable code** that integrates with business workflows
6. **Document business context** and integration points clearly

**Reference Documents:**
- `/documentation-requirement.md` - Core development and testing standards
- `/documentation-prerelease.md` - Performance and security requirements for production

This ensures AI-generated code provides genuine business value rather than just passing tests.

## MANDATORY: Shared Library Usage

**CRITICAL REQUIREMENT**: All NeverMissCall microservices MUST use the shared library (`/shared/`) for common functionality. This is the foundation of our architecture and ensures consistency, maintainability, and code reuse across the platform.

### Shared Library Components

The shared library (`/shared/`) provides standardized implementations for:

✅ **Database Operations**: Connection pooling, queries, health checks via `shared.init_database()`, `shared.query()`  
✅ **Configuration Management**: Environment variables, service ports via `shared.get_common_config()`  
✅ **Authentication**: Service-to-service API keys via `shared.require_service_auth()`  
✅ **API Responses**: Standardized success/error formats via `shared.success_response()`, `shared.error_response()`  
✅ **Logging**: Structured JSON logging with context via `shared.logger`  
✅ **Validation**: Common validation functions via `shared.validate_*()` functions  
✅ **Models**: Pydantic models for User, Tenant, Call, etc. via `shared.models`  
✅ **Utilities**: Helper functions, service client, formatting via `shared.utils`  

### Integration Requirements

**Every microservice implementation MUST:**

1. **Import from shared library first**:
```python
from shared import (
    init_database, query, health_check,
    get_common_config, logger,
    success_response, error_response,
    require_service_auth
)
```

2. **Use shared database operations** instead of custom database code
3. **Use shared authentication** for service-to-service communication  
4. **Use shared configuration** for environment variables and service ports
5. **Use shared API responses** for consistent client experience
6. **Use shared logging** for structured monitoring and debugging
7. **Use shared validation** for consistent error handling

### Benefits of Shared Library Architecture

🔒 **Consistency**: Identical patterns across all services for database, auth, logging  
🛠️ **Maintainability**: Infrastructure changes happen in one place  
🚀 **Development Speed**: Services focus on business logic, not infrastructure  
🔍 **Debugging**: Consistent logging and error handling  
📈 **Reliability**: Shared, tested infrastructure code  
⚡ **Performance**: Optimized database connection pooling and async operations  

### Example Service Structure

```python
# ✅ CORRECT: Using shared library
from shared import (
    init_database, query, logger, 
    get_common_config, success_response,
    require_service_auth
)

@app.on_event("startup")
async def startup_event():
    config = get_common_config()
    await init_database(config.database)
    logger.info("Service started using shared library")

@app.post("/internal/resource")  
async def create_resource(
    data: ResourceCreate,
    _: bool = Depends(require_service_auth)
):
    result = await query("INSERT INTO ...", params)
    return success_response(result, "Resource created")
```

**❌ INCORRECT: Custom implementations that duplicate shared library functionality**

### Documentation Reference

- **Shared Library Documentation**: `/shared/README.md`
- **API Integration Patterns**: `/docs/services/phase-1/api-integration-patterns.md`
- **Authentication Standards**: `/docs/services/phase-1/authentication-standards.md`

**Remember**: The shared library exists to eliminate code duplication and ensure platform consistency. Always use it instead of implementing custom solutions for common functionality.

## Phase 1 Service Architecture

**Total Services**: 13+ services (comprehensive NeverMissCall platform)

### Group 1: Identity & Onboarding Services
Core authentication and tenant management:
- `ts-auth-service` ✅ - User authentication, registration, JWT management  
- `ts-tenant-service` ✅ - Business onboarding, configuration management
- `ts-user-service` ✅ - User profiles, preferences, status management  
- `ts-config-service` ✅ - Configuration management and business settings

### Group 2: Phone Number & Communication Services  
Phone number provisioning and Twilio integration:
- `pns-provisioning-service` ✅ - Phone number provisioning via Twilio
- `twilio-server` ✅ - Twilio integration and webhook handling

### Group 3: Core Business Logic & Processing
Call processing and AI conversation management:
- `as-call-service` ✅ - Core business logic hub for call/conversation processing
- `dispatch-bot-ai` ✅ - AI conversation processing with OpenAI

### Group 4: Analytics & Data Services
Analytics processing and data management:
- `as-analytics-core-service` ✅ - Analytics processing, KPI calculation, and metrics
- `as-alerts-service` ✅ - Alert management and notification delivery
- `shared/` ✅ - Shared database, config, and utilities library

### Group 5: Real-time & Infrastructure Services
Dashboard connectivity and system monitoring:
- `as-connection-service` ✅ - WebSocket management for real-time updates
- `as-infrastructure-service` ✅ - Health monitoring and service status

### Group 6: Frontend & Calendar Integration
User interface and external integrations:
- `web-ui` ✅ - Next.js dashboard application with real-time features
- `universal-calendar` ✅ - Calendar integration (Google, Microsoft, etc.)

### Service Communication Pattern
```
Customer Call → twilio-server → as-call-service → dispatch-bot-ai
                      ↓              ↓                ↓
                  web-ui ← as-connection-service ← Real-time Events
                      ↓              ↓                ↓
            ts-auth-service ← Authentication    as-analytics-core-service
                      ↓              ↓                ↓
            ts-tenant-service ← Business Config  as-alerts-service ← Monitoring
                      ↓              ↓                ↓
            ts-user-service ← User Data         as-infrastructure-service
                      ↓              ↓                ↓
            ts-config-service ← Settings       universal-calendar ← Scheduling
                      ↓              ↓
            pns-provisioning-service ← Phone Setup
                      ↓
                database-service ← Data Layer
```

### Service Dependencies & Communication Flow:
- **Authentication Flow**: ts-auth-service → ts-tenant-service → ts-user-service
- **Business Logic**: as-call-service ↔ dispatch-bot-ai ↔ universal-calendar
- **Real-time Updates**: as-connection-service ← all services (events)
- **Analytics Pipeline**: as-analytics-core-service ← as-call-service ← as-alerts-service
- **Infrastructure**: as-infrastructure-service monitors all services
- **Data Layer**: database-service provides repository patterns for all services

### Service-to-Service Authentication

**Fixed API Key Authentication**: All internal service-to-service communication uses a shared API key for authentication.

- **Header**: `x-service-key: nmc-internal-services-auth-key-phase1`
- **Environment Variable**: `INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1`
- **Usage**: Required for all internal endpoints (`/internal/*`)
- **Security**: Services validate this key before processing internal requests

## Phase 1 Technology Stack

### Backend Services
- **Runtime**: Python 3.11+
- **Framework**: FastAPI with Pydantic for API validation
- **Database**: PostgreSQL with asyncpg/SQLAlchemy
- **Testing**: unittest with comprehensive test coverage
- **Package Manager**: pip with requirements.txt (individual service dependencies)
- **Authentication**: JWT tokens with bcrypt
- **HTTP Client**: httpx for service-to-service communication

### Service Organization
- **Service Location**: All microservices are located in the **root folder** as independent Python packages
- **Package Management**: Each service has its own `requirements.txt` with local dependencies
- **Testing Integration**: Each service has its own unittest test suite
- **Build System**: Services are run and tested independently using Python/pip commands

### Frontend Application  
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript 5+
- **Styling**: Tailwind CSS with custom design system
- **HTTP Client**: Axios for API communication
- **Real-time**: Socket.IO client for WebSocket connections  
- **State Management**: Zustand + React Query
- **Forms**: React Hook Form + Zod validation

### External Integrations
- **Twilio**: Voice calls, SMS, phone number provisioning
- **OpenAI**: AI conversation processing  
- **Google Maps**: Address validation and geocoding

## Service Port Allocation

### Identity & Onboarding Services (330x range)
- `ts-auth-service`: **3301** - User authentication and JWT management
- `ts-tenant-service`: **3302** - Business registration and tenant management  
- `ts-user-service`: **3303** - User profiles and status management
- `ts-config-service`: **3304** - Configuration and business settings

### Core Business Logic Services (330x range)
- `as-call-service`: **3304** - Call processing and conversation management

### Analytics Services (310x range)  
- `as-analytics-core-service`: **3102** - Analytics processing and KPI calculation
- `as-alerts-service`: **3101** - Alert management and notifications

### Infrastructure Services (310x range)
- `as-connection-service`: **3105** - WebSocket real-time connections
- `as-infrastructure-service`: **3106** - Health monitoring and service registry

### Phone & Communication Services (350x range)
- `pns-provisioning-service`: **3501** - Phone number provisioning

### External Integration Services (370x+ range)
- `twilio-server`: **3701** - Twilio webhook processing
- `dispatch-bot-ai`: **3801** - AI conversation processing (Python)
- `universal-calendar`: **3901** - Calendar integration service

### Frontend Application
- `web-ui`: **3000** - Next.js dashboard application

### Database Services
- `database-service`: **PostgreSQL** - Centralized database and repository patterns
- **PostgreSQL Database**: Port 5432 (standard)

## Database Architecture

### Database Design
**Single PostgreSQL Database**: `nevermisscall` - Centralized data storage for all services

**Key Tables**:
- **Core Tables**: `tenants`, `users`, `user_sessions`, `business_settings`
- **Call Processing**: `calls`, `conversations`, `call_participants`, `call_metadata`
- **Phone Numbers**: `phone_numbers`, `twilio_phone_numbers`
- **Analytics**: `metrics`, `kpis`, `analytics_reports`
- **Alerts**: `alert_rules`, `alerts`, `notifications`, `alert_history`
- **Calendar**: `calendar_integrations`, `appointments`, `availability`

### Shared Library Architecture
- **Shared Database Access**: All services use the shared `shared/database` library
- **Simple Connection Pool**: Single connection pool managed by shared library
- **Schema Migrations**: File-based migrations managed via `node migrate.js` command
- **Multi-tenant Support**: Basic tenant isolation in shared queries

### Data Flow
```
Services → shared/database → PostgreSQL
Services → shared/config → Common Configuration
Services → shared/utils → Common Utilities
```

**Benefits**:
- Simple file-based sharing (no published packages)
- Consistent database access patterns
- Shared configuration and utilities
- Easy schema migrations and updates

## Shared Library Usage

### Database Operations
```python
from shared import init_database, query, health_check
import os

# Initialize database connection
db = init_database(url=os.getenv('DATABASE_URL'))
await db.connect()

# Simple queries
users = await query('SELECT * FROM users WHERE tenant_id = %s', [tenant_id])
is_healthy = await health_check()
```

### Configuration
```python
from shared import get_common_config, SERVICE_PORTS, get_service_url

config = get_common_config()
auth_service_url = get_service_url('ts-auth-service')
```

### Common Types & Utilities
```python
from shared import ApiResponse, success_response, error_response, logger, validate_required

# API responses
return success_response(user_data, 'User retrieved successfully')

# Logging
logger.info('Service started', extra={'port': config.port})

# Validation
validate_required(email, 'email')
```

### Database Migrations
```bash
# Check migration status
node migrate.js status

# Run pending migrations  
node migrate.js migrate

# Create new migration
node migrate.js create "add user preferences table"
```

## Phase 1 Implementation Guidelines

### Core Development Principles

1. **Documentation-First Development**
   - All services have complete design specifications in `docs/services/phase-1/`
   - API endpoints, database schemas, and business logic fully documented
   - Implementation must strictly follow design documents

2. **Working System Focus**  
   - Each service group delivers working functionality
   - Weekly milestones with testable outcomes
   - Complete user journey: Registration → Onboarding → Live Conversations

3. **Simple & Reliable**
   - Clear service boundaries with single responsibilities
   - Direct service-to-service communication
   - Basic error handling with proper logging
   - No premature optimization

4. **Test-Driven Quality**
   - Unit tests for business logic
   - Integration tests for API endpoints
   - End-to-end tests for critical user flows

### Standard Development Commands

#### Database Management
```bash
# Check migration status
python migrate.py status

# Run pending migrations
python migrate.py migrate

# Create new migration
python migrate.py create "add user preferences table"
```

#### Service Development
```bash
# Each service directory
pip install -r requirements.txt  # Install dependencies
python -m uvicorn main:app --reload --port 3801  # Development mode
python main.py        # Production mode
python -m unittest discover tests/  # Run unit tests
python -m unittest discover tests/ -v  # Run unit tests with verbose output
```

#### Shared Library Integration
All services must use the shared library:
```python
from shared import init_database, get_common_config, logger, success_response
```

**Next Phases**: After Phase 1 completion, expand to advanced analytics (Phase 2) and enterprise features (Phase 3) based on market feedback and business requirements.

**Development Focus**: Build Phase 1 completely before considering Phase 2 features. Each service must be production-ready with proper testing, monitoring, and documentation.


## check root/documentation-requirement.md for additional documentation and development information.

