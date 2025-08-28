# Small-Team Documentation Six-Pack (Docs-as-Truth)

This template defines the minimum documentation needed for a small company to successfully use the **"documentation is truth"** approach.

---

## 0) Repo README (meta)
**Purpose:** Entry point for humans & AI.  
**Must include:**  
- Quickstart (3–5 commands)  
- Env vars table  
- How to run tests  
- How to deploy  
- System diagram thumbnail  
- Links to docs below  

**Owner:** Tech lead

---

## 1) Product Brief (1 page)
**Purpose:** Why this exists and what "done" means.  
**Sections:**  
- Problem  
- Goals (measurable)  
- Non-Goals  
- Primary Users  
- Success Metrics  
- Out-of-scope risks  

**Owner:** PM/founder

---

## 2) User Flows & Acceptance Criteria (1–2 pages)
**Purpose:** Executable truth for behavior.  
**Sections:**  
- 3–7 happy-path flows (sequence or screen flow)  
- Edge cases list  
- **Given/When/Then** acceptance criteria per flow  

**Owner:** PM + QA

---

## 3) Architecture Sheet + ADR Log (2 pages + log)
**Purpose:** How it's built and why.  
**Sections:**  
- Context diagram  
- Runtime components  
- Key integrations  
- Data flow  
- SLO targets (latency, uptime)  
- Scaling approach  

**ADR Log:** One-paragraph records of decisions. Example: *"Choose Postgres over MySQL – 2025-08-23"*  

**Owner:** Tech lead

---

## 4) API & Data Contract (source of truth; can be code)
**Purpose:** Zero-ambiguity interfaces.  
**Deliverables:**  
- **OpenAPI/Swagger** file for APIs  
- **DB schema** (DDL or migration file) + ERD  
- **Events/queues** contracts (topic, schema, retention)  
- **Repository Access Patterns** - Database service integration documentation (`/database-service/docs/repository-access/`)

**Owner:** Backend lead

---

## 5) Testing & Quality Documentation

### 5a) Integration Test Plan (1 page)
**Purpose:** Document component integration testing strategy with controlled mocking.  
**Sections:**  
- API endpoint coverage matrix  
- Mock vs. real component strategy  
- Business workflow scenarios  
- Error handling test cases  
- Performance benchmarks  
- Service interaction patterns  

### 5b) E2E Test Plan (1 page)  
**Purpose:** Document critical user journey validation with NO MOCKING or absolute minimum mocking.  
**Sections:**  
- Critical user journeys (CUJs) with real system flows  
- Test environment setup procedures (real databases, real services)  
- Test data management strategy (real data creation/cleanup)  
- Cross-service integration scenarios (real HTTP calls, real authentication)  
- System performance requirements (real infrastructure performance)  
- Real infrastructure dependencies (no mocked external services)  
- **Mocking Policy**: Document any unavoidable mocking with explicit justification  

### 5c) Test & Quality Checklist (1 page)
**Purpose:** Minimum bar before release with comprehensive three-tier testing.  
**Sections:**  
- **Three-Tier Testing Architecture** (mandatory for all microservices)
- Critical user journeys (CUJs) with test IDs  
- Perf budgets  
- Security checks (OWASP top 10 quick scan)  
- Accessibility level  
- Coverage targets  
- Exit criteria for release  

**Owner:** Dev/Eng

---

## 6) Ops Runbook (1–2 pages)
**Purpose:** Keep prod up without guesswork.  
**Sections:**  
- Environments matrix  
- Deploy steps/rollback  
- Feature flag policy  
- Monitoring dashboards & alerts  
- Common incidents & fixes  
- Secrets rotation  
- Backup/restore steps  
- DR objectives (RPO/RTO)  

**Owner:** DevOps/Eng

---

## 7) Changelog / Release Notes (meta)
**Purpose:** Traceability from intent → change → result.  
**Format:** One entry per release with links to PRs, migrations, and ADRs.  

**Owner:** Release manager

---

# Guardrails That Make This Work
- **Docs-as-code:** store docs in `/docs` folder in repo  
- **One-pager bias:** if it can't fit, cut scope or split component  
- **Owners & cadence:** each doc has named owner & review cadence  
- **Truth enforcement:**  
  - CI checks OpenAPI vs implementation  
  - CI checks schema vs migrations  
  - PR template asks: *Which doc did you update?*

---

# Minimal File Layout
```
/README.md
/CLAUDE.md                      # Main project guidance
/documentation-requirement.md   # This document
/migrate.py                     # Database migration CLI
/migrations/                    # Schema migration files
  001_initial_schema.sql
/shared/                        # Shared library for all services
  database/
    __init__.py                 # Database connection & queries
    migrations.py               # Migration management
  config/
    __init__.py                 # Common configuration
  models/
    __init__.py                 # Shared Pydantic models
  utils/
    __init__.py                 # Common utilities
  __init__.py                   # Main exports
  README.md                     # Shared library docs
/docs/
  product-brief.md
  flows-acceptance.md
  architecture.md
  adrs/ADR-0001-title.md
  api/
    openapi.yaml
    events/
  data/
    schema.sql
    erd.png
  testing/
    integration-test-plan.md
    e2e-test-plan.md
  quality-checklist.md
  ops-runbook.md
  CHANGELOG.md
```

---

# Mandatory Three-Tier Testing Architecture

**REQUIREMENT:** All microservices MUST implement a three-tier testing architecture to ensure comprehensive validation while maintaining fast development feedback loops.

## Testing Philosophy: Honest Failure Over Eager Passing

**CRITICAL PRINCIPLE**: All tests across all tiers must prioritize meaningful validation over passing status.

### Core Testing Values
- **Honest Failures Are Preferable**: A test that fails and reveals a real bug is infinitely more valuable than a test that passes but validates nothing meaningful
- **Validate Business Logic, Not Mock Setup**: Tests should verify actual behavior, edge cases, and error conditions - not just that mocks were called correctly
- **Test What Matters**: Focus on critical business logic, data integrity, error handling, and user-facing behavior
- **Catch Real Problems**: Tests should be designed to catch the types of bugs that actually occur in production

### Red Flags in Testing (Avoid These Patterns)
- **Mock-Heavy Tests**: Tests that primarily verify mock function calls rather than business logic
- **Happy Path Only**: Tests that only cover success scenarios without edge cases or error conditions
- **Shallow Validation**: Tests that check structure but not actual data processing or transformations
- **Coverage Gaming**: Writing tests solely to increase coverage percentages without meaningful validation
- **Brittle Mocking**: Over-mocked tests that break on implementation changes rather than behavior changes

### What Good Tests Look Like
- **Behavior-Focused**: Test outcomes and side effects, not implementation details
- **Edge Case Coverage**: Include boundary conditions, invalid inputs, and error scenarios
- **State Verification**: Verify actual data transformations and system state changes
- **Error Path Testing**: Ensure error handling works correctly and provides useful information
- **Integration Reality**: Test how components actually work together, not just isolated units

### Testing Quality Self-Assessment Questions
Before marking any test as "complete," ask:
1. **Would this test catch a real bug?** If the implementation had a logic error, would this test fail?
2. **Does this test validate behavior or implementation?** Tests should pass/fail based on what the system does, not how it does it
3. **What would happen if I removed the mocks?** Could this test work with real dependencies, or is it purely testing mock interactions?
4. **Does this test cover failure scenarios?** Error conditions are often where the most critical bugs hide
5. **Would a new developer understand the expected behavior from this test?** Tests should serve as living documentation of system behavior

## Testing Tier Requirements

### Tier 1: Unit Tests (Fast, Isolated)
- **Purpose**: Test individual functions, methods, and components in complete isolation
- **Mocking**: Heavily mocked - ALL external dependencies, database calls, and service interactions
- **Speed**: Very fast execution (< 5 seconds for complete suite)
- **Coverage Target**: 80%+ overall, 90%+ for repositories and business logic
- **Location**: `tests/unit/`
- **Focus**: Pure logic, validation, transformations, business rules
- **Quality Gate**: Tests must validate actual behavior, not just mock interactions

### Tier 2: Integration Tests (Component Integration)  
- **Purpose**: Test how multiple components work together while controlling external dependencies
- **Mocking**: Selective mocking - mock external services but test real component interactions
- **Speed**: Moderate execution (10-30 seconds)
- **Scope**: API endpoints, service-to-repository interactions, business workflows
- **Location**: `tests/integration/`
- **Focus**: Request/response validation, workflow orchestration, error handling
- **Quality Gate**: Tests must verify real component interactions and system behavior

### Tier 3: End-to-End Tests (Full System)
- **Purpose**: Test complete user journeys and system workflows with real infrastructure
- **Mocking**: **NO MOCKING** - real database, real HTTP requests, real data persistence, real external services  
- **Speed**: Slower execution (30-120 seconds)
- **Scope**: Full user workflows, cross-service communication, data integrity
- **Location**: `tests/e2e/`
- **Focus**: Complete user journeys, real data persistence, system integration
- **Critical Requirement**: Use real infrastructure only - any mocking must be explicitly justified and documented

## Required Test Structure

```
tests/
├── unit/                    # Tier 1: Unit tests with heavy mocking
│   ├── repositories/        # Repository method testing
│   ├── services/            # Service logic testing
│   ├── middleware/          # Auth, validation, error handling
│   ├── utils/               # Helper functions and utilities
│   └── conftest.py          # Unit test fixtures and configuration
├── integration/             # Tier 2: Integration tests with selective mocking
│   ├── api/                 # API endpoint testing
│   ├── services/            # Service interaction testing
│   ├── workflows/           # Business workflow testing
│   └── conftest.py          # Integration test fixtures and configuration
├── e2e/                     # Tier 3: End-to-end tests with no mocking
│   ├── workflows/           # Complete user journey testing
│   ├── database/            # Real database operation testing
│   ├── fixtures/            # Test data and scenarios
│   └── conftest.py          # E2E test database and environment setup
└── shared/                  # Shared test utilities and helpers
    ├── test_data.py         # Common test data factories
    ├── assertions.py        # Custom assertion helpers
    └── mocks/               # Reusable mock implementations
```

## Required Python Testing Scripts

```python
# unittest.cfg - unittest configuration
[unittest]
start_dir = tests
pattern = test_*.py
verbosity = 2

# test_config.py - Custom unittest configuration
import unittest
import os

class TestConfig:
    # Test directories
    UNIT_TESTS_DIR = "tests/unit"
    INTEGRATION_TESTS_DIR = "tests/integration" 
    E2E_TESTS_DIR = "tests/e2e"
    
    # Test patterns
    TEST_PATTERN = "test_*.py"
    
    @classmethod
    def get_test_suite(cls, test_type="all"):
        loader = unittest.TestLoader()
        if test_type == "unit":
            return loader.discover(cls.UNIT_TESTS_DIR, pattern=cls.TEST_PATTERN)
        elif test_type == "integration":
            return loader.discover(cls.INTEGRATION_TESTS_DIR, pattern=cls.TEST_PATTERN)
        elif test_type == "e2e":
            return loader.discover(cls.E2E_TESTS_DIR, pattern=cls.TEST_PATTERN)
        else:
            return loader.discover("tests", pattern=cls.TEST_PATTERN)

# Makefile or scripts
test: test-unit test-integration test-e2e
test-unit:
	python -m unittest discover tests/unit -v
test-integration:
	python -m unittest discover tests/integration -v
test-e2e:
	python -m unittest discover tests/e2e -v
test-coverage:
	coverage run -m unittest discover tests/ && coverage report && coverage html
test-watch:
	python -m unittest discover tests/unit -v --locals
test-debug:
	python -m unittest discover tests/ -v -s
```

## Development Workflow Integration

### Fast Development Loop
```bash
# Primary development feedback (< 5 seconds)
python -m unittest discover tests/unit -v

# Pre-commit validation (< 30 seconds)  
python -m unittest discover tests/integration

# Pre-deployment validation (< 2 minutes)
python -m unittest discover tests/e2e
```

### CI/CD Pipeline Requirements
```bash
# Stage 1: Fast feedback (< 10 seconds)
python -m unittest discover tests/unit

# Stage 2: Integration validation (< 60 seconds) 
python -m unittest discover tests/integration

# Stage 3: System validation (< 300 seconds)
python -m unittest discover tests/e2e

# Final: Coverage and quality gates
coverage run -m unittest discover tests/ && coverage html
```

## Service-Specific Testing Focus

### Repository Services (Database Access)
- **Unit**: Repository methods, validation logic, transformations
- **Integration**: API endpoints, transaction handling, business workflows  
- **E2E**: Real database operations, data persistence, cascade operations

### Business Logic Services
- **Unit**: Core business rules, calculations, validations
- **Integration**: Service orchestration, external API interactions
- **E2E**: Complete business processes, real external service integration

### Communication Services (Email, SMS, Webhooks)
- **Unit**: Message formatting, template processing, validation
- **Integration**: Delivery logic, retry mechanisms, error handling
- **E2E**: Real message delivery, external service integration

## Shared Library Requirements

**MANDATORY:** All microservices MUST use the standardized shared library to eliminate code duplication and ensure consistent patterns across services.

### Shared Library Architecture (Required for All Services)
- **Purpose**: Centralize database, configuration, utilities, and type definitions
- **Location**: `shared/` directory with direct imports
- **Benefits**: Single source of truth, consistent patterns, simplified maintenance
- **Implementation**: Replace all duplicated code with shared library imports

**Implementation Requirements:**
```python
# REQUIRED: Shared library usage
from shared import init_database, query, health_check, get_common_config, logger, success_response
import os

# BEFORE (Duplicated in every service): ❌
import psycopg2
from psycopg2 import pool
import logging

connection_pool = psycopg2.pool.SimpleConnectionPool(
    1, 5,
    host=os.getenv('DATABASE_HOST', 'localhost'),
    database=os.getenv('DATABASE_NAME', 'nevermisscall'),
    user=os.getenv('DATABASE_USER'),
    password=os.getenv('DATABASE_PASSWORD')
)
print('Service started')

# AFTER (Shared library pattern): ✅
config = get_common_config()
db = init_database(config.database)
await db.connect()
logger.info('Service started')
users = await query('SELECT * FROM users WHERE tenant_id = %s', [tenant_id])
return success_response(users)
```

**Shared Library Requirements:**

### Database Module (`shared/database/`)
- **Connection Management**: Simple PostgreSQL connection and pooling using asyncpg
- **Migration System**: File-based schema migrations with `python migrate.py`
- **Query Helpers**: Basic async query functions with connection management
- **Health Checking**: Database health validation for monitoring

### Configuration Module (`shared/config/`)
- **Common Config**: Standardized environment variable handling using Pydantic Settings
- **Service Discovery**: Port mappings and service URL generation
- **JWT Settings**: Shared authentication configuration
- **Service Auth**: Internal service-to-service authentication keys

### Models Module (`shared/models/`)
- **API Responses**: Standardized success/error response formats using Pydantic
- **Domain Models**: User, Tenant, Call, and other shared Pydantic models
- **Error Types**: Common exception classes and validation types
- **Helper Functions**: Response formatting utilities

### Utils Module (`shared/utils/`)
- **Logging**: Structured logger using Python logging with JSON formatting
- **Validation**: Common validation functions (email, phone, UUID) using Pydantic
- **HTTP Client**: Service-to-service communication helpers using httpx
- **Middleware**: FastAPI middleware for authentication and error handling

**Quality Gates (All Services Must Pass):**
- [ ] Shared library imported using `from shared import ...`
- [ ] All database connections use `init_database()` and `query()` functions
- [ ] All services use `get_common_config()` for configuration
- [ ] All API responses use `success_response()` and `error_response()`
- [ ] All logging uses shared `logger` instead of print statements
- [ ] Zero duplicate database connection code across services
- [ ] Schema migrations managed centrally with `python migrate.py`

## Compliance and Quality Assurance

### Pre-Release Checklist
- [ ] All three test tiers implemented and passing
- [ ] Unit test coverage meets 80%+ requirement  
- [ ] Integration tests cover all API endpoints
- [ ] E2E tests validate critical user journeys
- [ ] Test execution times meet performance targets
- [ ] Test databases properly isolated and cleaned
- [ ] CI/CD pipeline validates all test tiers

### Documentation Requirements
Each service MUST document:
- Test strategy and architecture in service README
- How to run each test tier
- Test data setup and cleanup procedures  
- Coverage reports and quality metrics
- Known test limitations or exclusions

This three-tier testing architecture ensures comprehensive validation while maintaining fast development feedback loops and reliable system quality assurance across all microservices in the platform.

---

# AI Code Generation Standards

**PURPOSE**: Ensure AI-generated code prioritizes correctness and meaningful validation over quick completion and passing tests.

## AI Code Quality Requirements

### Before Writing Any Code, AI Must:
- [ ] **Read existing codebase patterns** and follow them exactly
- [ ] **Identify actual business logic** that needs testing/implementation
- [ ] **Ask: "What real bug would this code/test catch?"**
- [ ] **Verify integration points** and error boundaries
- [ ] **Understand the domain context** before generating solutions

### Prohibited AI Behaviors
- ❌ **Writing tests that only verify mock function calls** without business logic validation
- ❌ **Creating "happy path only" implementations** without error handling
- ❌ **Generating boilerplate without understanding context** or domain requirements
- ❌ **Prioritizing code completion over code correctness** and meaningful validation
- ❌ **Copy-pasting patterns without adapting to specific business requirements**

### Required AI Behaviors
- ✅ **Test actual behavior and business rules** rather than implementation details
- ✅ **Include error conditions, edge cases, and boundary testing** in all implementations
- ✅ **Follow established codebase conventions** for naming, structure, and patterns
- ✅ **Write self-documenting code** with clear intent and business context
- ✅ **Validate assumptions** about data, dependencies, and system behavior

## Documentation Standards for AI-Generated Code

### Code Documentation Requirements
- **Function/Method Documentation**: Every function must include purpose, parameters, return values, and potential errors
- **Business Logic Comments**: Complex business rules must be documented with context and reasoning
- **Integration Points**: Document dependencies, external service calls, and error handling strategies
- **Error Scenarios**: Document expected error conditions and recovery mechanisms

### Self-Documenting Code Standards
```python
# GOOD: Self-documenting with business context
from typing import Literal
from shared.models import Result

async def validate_alert_threshold(
    metric_value: float, 
    threshold: float, 
    operator: Literal['greater_than', 'less_than']
) -> Result[bool]:
    """
    Validate if a metric value violates the alert threshold.
    
    Business rule: Alert triggers when metric violates threshold
    based on the specified operator condition.
    
    Args:
        metric_value: Current metric measurement
        threshold: Business-defined threshold value
        operator: Comparison operation for threshold validation
        
    Returns:
        Result containing True if threshold is violated, False otherwise
    """
    if operator == 'greater_than' and metric_value > threshold:
        return Result.ok(True)
    if operator == 'less_than' and metric_value < threshold:
        return Result.ok(True)
    return Result.ok(False)

# BAD: Unclear purpose and no business context
def check(a: float, b: float, op: str) -> bool:
    return a > b if op == 'gt' else a < b
```

### Documentation Quality Gates
- [ ] **Purpose Clear**: Every function's business purpose is obvious from name and documentation
- [ ] **Parameters Documented**: All parameters have clear types and business meaning
- [ ] **Error Conditions**: All failure modes are documented with examples
- [ ] **Business Context**: Domain-specific logic includes business reasoning
- [ ] **Integration Notes**: Dependencies and side effects are clearly documented

## Refactoring Guidelines for AI-Generated Code

### When to Refactor AI Code
- **Code Duplication**: More than 3 similar functions/patterns should be consolidated
- **Complex Functions**: Functions longer than 50 lines should be broken down
- **Poor Naming**: Generic names (data, result, item) should be made domain-specific
- **Missing Error Handling**: Functions without proper error boundaries need refactoring
- **Hard-to-Test Code**: Code that requires excessive mocking needs structural improvement

### Refactoring Standards
```python
# BEFORE: Hard to test, unclear purpose
from typing import Any, Dict
import logging

async def process_data(data: Any) -> Any:
    try:
        result = await some_service.call(data)
        if result.ok:
            await database.save(result.data)
            logging.info('Success')
            return {'success': True}
        else:
            logging.error('Failed')
            raise Exception('Processing failed')
    except Exception as error:
        raise error

# AFTER: Clear purpose, testable, proper error handling
from shared.models import CreateAlertRequest, Alert, AsyncResult, Result
from shared import logger

async def create_alert_from_metrics(
    alert_data: CreateAlertRequest
) -> AsyncResult[Alert]:
    """
    Create a new alert from metric data with proper business validation.
    
    Validates business rules before processing and maintains audit trail.
    """
    # Validate business rules before processing
    validation = validate_alert_data(alert_data)
    if validation.is_error():
        return validation

    # Create alert with proper error boundary
    try:
        alert = await alerts_repository.create(alert_data)
        await alert_history_repository.record_creation(alert.id)
        
        logger.info('Alert created successfully', extra={'alert_id': alert.id})
        return Result.ok(alert)
    except Exception as error:
        message = f'Failed to create alert: {str(error)}'
        logger.error(message, extra={'alert_data': alert_data.dict(), 'error': str(error)})
        return Result.error(message, 'ALERT_CREATION_FAILED')
```

### Refactoring Quality Gates
- [ ] **Single Responsibility**: Each function has one clear business purpose
- [ ] **Testability**: Functions can be tested without excessive mocking
- [ ] **Error Boundaries**: All external calls have proper error handling
- [ ] **Domain Language**: Code uses business terminology consistently
- [ ] **Maintainability**: Code structure supports future changes and extensions

## Domain Knowledge Integration

### Business Context Requirements
AI must integrate domain knowledge into all code generation:

- **Alert Management Domain**:
  - Alerts have lifecycles: triggered → acknowledged → resolved
  - Thresholds define business-critical boundaries
  - Escalation follows business hierarchy and timing rules
  - Notifications must respect user preferences and delivery constraints

- **Tenant Management Domain**:
  - Multi-tenancy requires strict data isolation
  - Business settings control service behavior per tenant
  - User roles define access and operation permissions
  - Configuration changes must maintain system consistency

- **Service Integration Domain**:
  - Service calls must handle failures gracefully
  - Authentication propagates through service chains
  - Data consistency across services requires transaction boundaries
  - Real-time updates require event-driven architecture

### Domain Validation Requirements
```python
# GOOD: Domain-aware validation
from typing import Optional
from shared.models import Result, BusinessHours
from shared.utils import is_valid_time_format, is_valid_timezone

def validate_business_hours(
    start_time: str, 
    end_time: str, 
    timezone: str
) -> Result[BusinessHours]:
    """
    Validate business operating hours for geographical operations.
    
    Enforces business rules for time format, logical ordering,
    and timezone validity for customer service operations.
    """
    # Business rule: Must be valid 24-hour format
    if not is_valid_time_format(start_time) or not is_valid_time_format(end_time):
        return Result.validation_error('Business hours must be in HH:MM format')
    
    # Business rule: End time must be after start time
    if start_time >= end_time:
        return Result.validation_error('Business end time must be after start time')
    
    # Business rule: Must be valid timezone for geographical operations
    if not is_valid_timezone(timezone):
        return Result.validation_error('Invalid timezone for business location')
    
    return Result.ok(BusinessHours(
        start_time=start_time, 
        end_time=end_time, 
        timezone=timezone
    ))
```

### Domain Integration Quality Gates
- [ ] **Business Rules Enforced**: All domain constraints are validated in code
- [ ] **Domain Language Used**: Code terminology matches business vocabulary
- [ ] **Workflow Awareness**: Code understands business process flows
- [ ] **Data Relationships**: Code respects business entity relationships
- [ ] **Compliance Requirements**: Code enforces business compliance rules

## AI Code Review Checklist

### Mandatory Review Points
Before accepting any AI-generated code:

1. **Business Logic Validation**
   - [ ] Does this solve the actual business problem?
   - [ ] Are all business rules properly enforced?
   - [ ] Does this integrate correctly with existing workflows?

2. **Error Handling Review**
   - [ ] Are all error conditions properly handled?
   - [ ] Do error messages provide actionable information?
   - [ ] Are error boundaries appropriate for the business context?

3. **Testing Quality Review**
   - [ ] Do tests validate behavior, not implementation?
   - [ ] Are edge cases and boundary conditions covered?
   - [ ] Would removing mocks break tests (good) or not (bad)?

4. **Integration Review**
   - [ ] Does this work with real data/dependencies?
   - [ ] Are service boundaries respected?
   - [ ] Is data flow and state management correct?

5. **Documentation Review**
   - [ ] Is the business purpose clear?
   - [ ] Are integration points documented?
   - [ ] Can a new developer understand the intent?

This ensures AI-generated code meets the same quality standards as human-written code while leveraging AI's efficiency for implementation details.

---

# AISO-X Extras (for AI visibility)
- Stable headings & front matter  
- Glossary of terms and IDs  
- Example-first (every API endpoint has request + response example)  
- Absolute paths in links  
- Change stamps: `Updated: YYYY-MM-DD`  