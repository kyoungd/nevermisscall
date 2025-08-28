# NeverMissCall Platform

Turn every missed call into a conversation—and every conversation into a customer.

## Quickstart

**IMPORTANT**: Services are now managed as independent npm packages. Each service must be set up individually.

### Prerequisites

**1. Database Setup (REQUIRED FIRST)**
```bash
# Create PostgreSQL database
createdb nevermisscall

# Run core database migration (CRITICAL - creates foundational tables)
psql -d nevermisscall -f database/migrations/001_create_core_tables.sql

# Verify core tables were created
psql -d nevermisscall -c "\dt"
# Should show: tenants, users, user_sessions, phone_numbers, and other core tables
```

**2. Service Setup**
```bash
# Set environment variables (shared across services)
export DATABASE_URL=postgresql://localhost:5432/nevermisscall
export JWT_SECRET=e8a3b5c7d9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6

# Set up services IN DEPENDENCY ORDER (start each in separate terminal)

# 1. Authentication service (no dependencies)
cd ts-auth-service && npm install && npm run dev

# 2. Tenant service (requires auth service)  
cd ts-tenant-service && npm install && npm run dev

# 3. User service (requires auth + tenant services)
cd ts-user-service && npm install && npm run dev

# 4. Call service (requires all above services)
cd as-call-service && npm install && npm run dev

# ... repeat for each service in dependency order
```

**CRITICAL**: Services depend on each other and on core database tables. Starting services out of order or without the core migration will cause startup failures.

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| DATABASE_URL | PostgreSQL connection string | Yes | - |
| JWT_SECRET | JWT signing secret | Yes | - |
| REDIS_URL | Redis connection string | No | redis://localhost:6379 |
| NODE_ENV | Environment mode | No | development |

## Tests

```bash
# Run tests for individual services
cd ts-auth-service
npm test

# Test multiple services with a loop
for service in ts-* as-* pns-*; do
  if [ -d "$service" ] && [ -f "$service/package.json" ]; then
    echo "Testing $service..."
    cd "$service"
    npm test
    cd ..
  fi
done

# Run E2E tests (if configured)
cd tests/e2e && npm test
```

## Deployment

```bash
# Build all services individually
for service in ts-* as-* pns-*; do
  if [ -d "$service" ] && [ -f "$service/package.json" ]; then
    echo "Building $service..."
    cd "$service"
    npm run build
    cd ..
  fi
done

# Start services for production
# Each service needs to be started individually
cd ts-auth-service && npm start &
cd ../ts-tenant-service && npm start &
# ... repeat for each service
```

## Architecture

![System Architecture](./docs/architecture/system-diagram-thumbnail.png)

Call management platform for local service professionals with 14+ microservices:

- **Analytics Services (AS)**: Real-time analytics and business intelligence
- **Tenant Services (TS)**: Multi-tenant management and authentication  
- **Communication**: Twilio integration, AI conversation handling
- **Integration**: Calendar sync, phone number provisioning, web interface

**Key Components:**
- PostgreSQL shared database for consistent data storage
- Redis for caching and session management
- JWT-based authentication across all services
- Real-time WebSocket connections for live updates
- E2E testing coverage with UC-001 through UC-010 test suites

## Documentation

**Six-Pack Documentation Standard** - Complete documentation for each service:

### Service Documentation
Each service includes standardized documentation in `{service}/docs/`:
- **product-brief.md** - Purpose, goals, and success metrics
- **architecture.md** - System design and technical decisions
- **flows-acceptance.md** - Given/When/Then acceptance criteria
- **api/openapi.yaml** - Complete OpenAPI 3.0 specifications
- **quality-checklist.md** - Testing and release criteria
- **ops-runbook.md** - Deployment and operational procedures
- **CHANGELOG.md** - Version history and migration notes

### System Documentation
- **[System Architecture](./docs/architecture/)** - Overall platform design
- **[API Documentation](./docs/api/)** - Complete API reference
- **[Testing Strategy](./docs/testing/)** - E2E and integration testing
- **[Deployment Guide](./docs/deployment/)** - Single-server deployment

### Key Services
- **[ts-auth-service](./ts-auth-service/README.md)** - Authentication and authorization
- **[ts-tenant-service](./ts-tenant-service/README.md)** - Business registration and management
- **[twilio-server](./twilio-server/README.md)** - Call/SMS processing and AI integration
- **[as-analytics-core-service](./as-analytics-core-service/README.md)** - Core analytics engine
- **[universal-calendar](./universal-calendar/README.md)** - Calendar integration


## Development

**ARCHITECTURE CHANGE**: This project no longer uses pnpm workspace. Each service is now an **independent npm package** with its own dependencies.

### Service Dependency Order

**CRITICAL**: Services must be started in dependency order to function correctly.

```bash
# 1. Database Prerequisites (FIRST)
psql -d nevermisscall -f database/migrations/001_create_core_tables.sql

# 2. Core Infrastructure Services
Terminal 1: cd ts-auth-service && npm install && npm run dev       # Port 3301
Terminal 2: cd ts-tenant-service && npm install && npm run dev     # Port 3302 
Terminal 3: cd ts-user-service && npm install && npm run dev       # Port 3303

# 3. Phone Number Provisioning  
Terminal 4: cd pns-provisioning-service && npm install && npm run dev # Port 3501

# 4. Analytics and Processing Services
Terminal 5: cd as-call-service && npm install && npm run dev       # Port 3304
Terminal 6: cd as-connection-service && npm install && npm run dev # Port 3305
Terminal 7: cd as-infrastructure-service && npm install && npm run dev # Port 3306

# 5. External Integration Services
Terminal 8: cd twilio-server && npm install && npm run dev         # Port 3701
Terminal 9: cd dispatch-bot-ai && npm install && npm run dev       # Port 3801

# 6. Frontend Application (requires all services)
Terminal 10: cd web-ui && npm install && npm run dev               # Port 3000
```

### Development Workflow (Per Service)
```bash
cd {service-name}              # Navigate to specific service
npm install                    # Install service dependencies  
npm run dev                    # Start in development mode
npm test                       # Run service tests
npm run build                  # Build service
```

**Dependencies Between Services**: Each service validates that its dependencies are running before starting. Check the service's CLAUDE.md file for specific dependency requirements.

## Production Deployment

**Single Server Architecture** - All services deployed independently on one server:

```bash
# Build each service for production
for service in ts-* as-* pns-*; do
  if [ -d "$service" ]; then
    cd "$service"
    npm install --production
    npm run build
    cd ..
  fi
done

# Start services (use process manager like PM2)
npm install -g pm2
cd ts-auth-service && pm2 start npm --name "auth-service" -- start
cd ../ts-tenant-service && pm2 start npm --name "tenant-service" -- start
# ... repeat for each service

# Service management
pm2 list          # View all services
pm2 restart all   # Restart all services
pm2 stop all      # Stop all services
```

**Monitoring & Health Checks:**
- Health endpoints: `GET /{service}/health`
- Metrics: Prometheus + Grafana dashboards
- Logging: Centralized with Winston + ELK stack
- Alerting: Critical service alerts via email/SMS

---

**📖 Complete documentation:** [Six-Pack Documentation Standard](./documentation-requirement.md)
