# as-infrastructure-service

Health monitoring and service discovery for NeverMissCall Phase 1.

## Overview

The as-infrastructure-service provides comprehensive health monitoring, service discovery, and basic infrastructure management for the NeverMissCall platform. It monitors all Phase 1 services, provides real-time health status, collects performance metrics, and manages alerting for system reliability.

## Features

- **Health Monitoring**: Continuous health checks for all registered services
- **Service Discovery**: Dynamic service registry with health status
- **Metrics Collection**: Performance metrics and system analytics
- **Alert Management**: Threshold-based alerting for service issues
- **Dashboard API**: Real-time status data for web UI
- **Critical Path Monitoring**: Special handling for mission-critical services

## Technology Stack

- **Runtime**: Python 3.10+
- **Framework**: FastAPI with asyncio
- **Monitoring**: aiohttp for async health checks
- **Storage**: aioredis for metrics caching
- **Scheduling**: APScheduler for background tasks
- **Authentication**: Internal service key validation

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m src.as_infrastructure_service.main
```

### Development

```bash
# Run in development mode
uvicorn src.as_infrastructure_service.main:app --reload --port 3106

# Run tests
python simple_test.py
python run_tests.py
```

## Service Configuration

### Monitored Services

The service monitors all Phase 1 services:

- **Identity Services**: ts-auth-service, ts-tenant-service, ts-user-service
- **Core Services**: as-call-service, as-connection-service
- **External Services**: twilio-server, dispatch-bot-ai, pns-provisioning-service
- **Frontend**: web-ui

### Health Check Configuration

```python
# Default check intervals
DEFAULT_CHECK_INTERVAL = 30 seconds
CRITICAL_SERVICE_CHECK_INTERVAL = 15 seconds

# Alert thresholds
RESPONSE_TIME_WARNING = 1000ms
RESPONSE_TIME_CRITICAL = 3000ms
ERROR_RATE_WARNING = 1%
ERROR_RATE_CRITICAL = 5%
```

## API Endpoints

### Health Monitoring

- `GET /health` - Overall infrastructure health
- `GET /health/services` - Detailed service health status
- `GET /health/service/{name}` - Specific service details

### Service Discovery

- `GET /services` - Service registry with health status
- `GET /services/dependencies` - Service dependency graph

### Metrics & Monitoring

- `GET /metrics` - System and service metrics
- `GET /metrics/service/{name}` - Service-specific metrics

### System Status

- `GET /status/critical` - Critical system status for alerts
- `GET /status/dashboard` - Dashboard data for web UI

## Environment Configuration

```bash
# Service Configuration
PORT=3106
SERVICE_NAME=as-infrastructure-service
LOG_LEVEL=info
ENVIRONMENT=development

# Redis Configuration
REDIS_URL=redis://localhost:6379
METRICS_REDIS_DB=3
HEALTH_DATA_TTL_SECONDS=86400

# Health Check Configuration
DEFAULT_CHECK_INTERVAL_MS=30000
CRITICAL_SERVICE_CHECK_INTERVAL_MS=15000
HEALTH_CHECK_TIMEOUT_MS=5000

# Authentication
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1
```

## Architecture

### Service Components

```
┌─────────────────────────────────────┐
│           FastAPI Application       │
├─────────────────────────────────────┤
│  Health Controller  │  API Routes   │
├─────────────────────────────────────┤
│  HealthChecker     │ MetricsCollector│
├─────────────────────────────────────┤
│           Redis Client              │
└─────────────────────────────────────┘
```

### Health Check Workflow

1. **Scheduled Checks**: Timer triggers health check for each service
2. **HTTP Request**: Send GET request to service `/health` endpoint  
3. **Response Analysis**: Parse response and measure timing
4. **Status Classification**: Classify as healthy/degraded/unhealthy
5. **Storage**: Store result in Redis with timestamp
6. **Alert Evaluation**: Check if alert thresholds are crossed
7. **Metrics Update**: Update running averages and counters

### Service Status Classification

- **Healthy**: HTTP 2xx, response time < 1000ms
- **Degraded**: HTTP 4xx or response time 1000-3000ms
- **Unhealthy**: HTTP 5xx, timeout, or response time > 3000ms

## Testing

### Unit Tests

```bash
# Run simple core tests (no external dependencies)
python simple_test.py

# Run full test suite
python run_tests.py
```

### Test Coverage

- ✅ **Data Models**: Pydantic model validation and structure
- ✅ **Configuration**: Settings loading and environment handling  
- ✅ **Business Logic**: Health checking and status determination
- ✅ **Metrics**: Performance calculation and aggregation
- ✅ **API Models**: Response formatting and error handling

## Monitoring & Alerts

### Alert Types

- **Service Down**: Consecutive health check failures
- **High Response Time**: Response time exceeds thresholds
- **High Error Rate**: Error rate exceeds configured limits  
- **Dependency Failure**: Critical service dependencies failing

### Critical Path Services

Services marked as critical path (failure impacts core functionality):

- `twilio-server` - Call processing
- `as-call-service` - Business logic hub
- `as-connection-service` - Real-time updates  
- `web-ui` - User interface

### Metrics Collection

- **Response Time**: Current, average, P95, P99 percentiles
- **Availability**: Uptime percentage, MTBF, MTTR
- **Request Volume**: Total requests, requests per minute
- **Error Tracking**: Error count, error rate, consecutive failures

## Integration

### Service-to-Service Authentication

All internal endpoints require the shared service key:

```bash
x-service-key: nmc-internal-services-auth-key-phase1
```

### Redis Storage

- **Health Data**: Service status and check history
- **Metrics**: Performance metrics and aggregations
- **Alerts**: Active alert state and history
- **TTL**: 24-hour expiration for cleanup

## Production Deployment

### Health Check Requirements

- Health check response time < 100ms per service
- Dashboard updates < 500ms for status page load  
- Alert detection < 30 seconds for service outages
- Concurrent monitoring of all 9+ services

### Scaling Considerations

- Redis clustering for high availability
- Multiple instance deployment with load balancing
- Alert rate limiting and cooldown periods
- Metrics aggregation and historical data management

## Development Guidelines

### Adding New Services

1. Add service configuration to `SERVICE_REGISTRY`
2. Define dependencies in `SERVICE_DEPENDENCIES`  
3. Set critical path status if needed
4. Configure appropriate check intervals

### Custom Metrics

1. Extend `ServiceMetrics` model for new data points
2. Update `MetricsCollector` collection logic
3. Add corresponding API endpoints
4. Update Redis storage schema

## Phase 1 Compliance

This service implements the complete health monitoring requirements for NeverMissCall Phase 1:

- ✅ **All Service Monitoring**: Tracks health of all 9+ Phase 1 services
- ✅ **Real-time Updates**: Sub-30-second outage detection  
- ✅ **Dashboard Integration**: Provides data for web-ui status displays
- ✅ **Alert Management**: Threshold-based alerting with proper escalation
- ✅ **Dependency Tracking**: Service dependency validation and critical path analysis
- ✅ **Performance Metrics**: Response time, availability, and request volume tracking

The infrastructure service ensures system reliability and provides visibility into platform health for both operators and automated systems.