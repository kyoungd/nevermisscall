# AS Call Service

Core business logic hub for NeverMissCall - handles call processing, conversation management, and AI coordination.

## Overview

The AS Call Service is a Python/FastAPI microservice that serves as the central hub for:

- **Call Processing**: Handle incoming and missed call events from Twilio
- **Conversation Management**: Manage SMS conversations with AI and human handoff
- **Lead Management**: Track and manage leads generated from calls
- **AI Coordination**: Integrate with dispatch-bot-ai for intelligent responses
- **Validation**: Service area and business rules validation

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Access to shared library (`../shared/`)

### Installation

1. **Clone and setup**:
   ```bash
   cd as-call-service
   pip install -r requirements.txt
   ```

2. **Environment setup**:
   ```bash
   python run_dev.py setup
   # Edit .env with your configuration
   ```

3. **Run development server**:
   ```bash
   python run_dev.py dev
   ```

4. **Run tests**:
   ```bash
   python run_tests.py
   ```

## Configuration

Key environment variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# Service Dependencies
TWILIO_SERVER_URL=http://localhost:3701
DISPATCH_AI_URL=http://localhost:3801
TS_TENANT_SERVICE_URL=http://localhost:3302
AS_CONNECTION_SERVICE_URL=http://localhost:3105

# Authentication
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1

# Business Logic
AI_TAKEOVER_DELAY_SECONDS=60
SERVICE_AREA_VALIDATION_ENABLED=true
```

## API Endpoints

### Call Processing
- `POST /calls/incoming` - Process incoming call events
- `POST /calls/missed` - Process missed call events  
- `GET /calls/{callId}` - Get call details

### Conversation Management
- `POST /conversations/{id}/messages` - Process incoming SMS messages
- `POST /conversations/{id}/reply` - Send human reply (takeover from AI)
- `GET /conversations/{id}` - Get conversation history
- `GET /conversations/tenant/{tenantId}/active` - Get active conversations

### Lead Management
- `GET /leads/{leadId}` - Get lead details
- `PUT /leads/{leadId}/status` - Update lead status
- `GET /leads/tenant/{tenantId}` - Get leads for tenant

### Health & Monitoring
- `GET /health` - Service health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   twilio-server │───▶│  as-call-service │───▶│  dispatch-bot-ai │
│     (3701)      │    │     (3104)      │    │     (3801)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   (nevermisscall)│
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │as-connection-   │
                       │service (3105)   │
                       └─────────────────┘
```

## Service Integration

### Incoming Call Flow
1. **twilio-server** sends webhook to `/calls/incoming`
2. **as-call-service** creates call record
3. If missed call, triggers SMS via **twilio-server**
4. Creates conversation and lead records
5. Broadcasts real-time events via **as-connection-service**

### Message Processing Flow
1. **twilio-server** sends SMS to `/conversations/{id}/messages`
2. **as-call-service** stores message and starts AI timer
3. After 60 seconds, activates **dispatch-bot-ai** if no human response
4. **dispatch-bot-ai** processes conversation and returns response
5. **as-call-service** sends response via **twilio-server**

### Human Takeover Flow
1. User sends reply via `/conversations/{id}/reply`
2. **as-call-service** deactivates AI immediately
3. Sends human message via **twilio-server**
4. Broadcasts takeover event via **as-connection-service**

## Development

### Project Structure
```
as-call-service/
├── src/as_call_service/
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic services
│   ├── controllers/     # FastAPI route handlers
│   ├── utils/           # Utilities and shared integrations
│   ├── config/          # Configuration management
│   └── main.py          # FastAPI application
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── run_dev.py           # Development server
├── run_tests.py         # Test runner
└── requirements.txt     # Dependencies
```

### Running Tests

```bash
# All tests with coverage
python run_tests.py

# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# All quality checks
python run_tests.py checks
```

### Development Commands

```bash
# Start development server
python run_dev.py dev

# Check dependencies
python run_dev.py check

# Setup environment
python run_dev.py setup

# Run quick smoke test
python run_dev.py test
```

## Business Logic

### AI Takeover Timer
- Customer messages start 60-second countdown
- Human response cancels AI activation
- AI activates automatically if no human response
- AI can be deactivated instantly by human reply

### Service Area Validation
- Validates customer addresses against business service area
- Uses **ts-tenant-service** for validation
- Can be disabled via `SERVICE_AREA_VALIDATION_ENABLED=false`

### Lead Classification
- Creates leads automatically from missed calls
- AI analysis updates lead details (job type, urgency, etc.)
- Status tracking: new → qualified → appointment_scheduled → completed

### Conversation States
- `active` - Ongoing conversation
- `completed` - Successfully concluded
- `abandoned` - No response timeout

## Error Handling

### Common Error Codes
- `CALL_PROCESSING_FAILED` - Error processing call event
- `CONVERSATION_NOT_FOUND` - Invalid conversation ID
- `MESSAGE_SEND_FAILED` - SMS delivery failure
- `AI_PROCESSING_ERROR` - AI service communication error
- `SERVICE_AREA_VALIDATION_FAILED` - Address validation error

### Graceful Degradation
- Service area validation failures don't block calls
- AI failures fallback to manual processing
- External service errors logged but don't crash service

## Performance

### Requirements
- Call processing: < 2 seconds from webhook to SMS
- Message processing: < 500ms for storage and forwarding
- AI coordination: < 1 second for activation/deactivation
- Support 100+ concurrent conversations

### Monitoring
- Health checks at `/health`, `/health/ready`, `/health/live`
- Structured JSON logging
- Real-time event broadcasting
- Database query performance tracking

## Security

### Authentication
- Internal service endpoints use `x-service-key` header
- User endpoints require JWT token validation
- Tenant-scoped access control on all operations

### Data Protection
- Phone numbers validated with E.164 format
- Message content sanitization
- SQL injection prevention
- Input validation on all endpoints

## Deployment

### Docker Support
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 3104
CMD ["uvicorn", "as_call_service.main:app", "--host", "0.0.0.0", "--port", "3104"]
```

### Production Checklist
- [ ] Set `DEBUG=false`
- [ ] Configure production database URL
- [ ] Set secure JWT secret
- [ ] Configure service URLs
- [ ] Enable service area validation
- [ ] Set up monitoring and logging
- [ ] Configure proper CORS origins

## Troubleshooting

### Common Issues

**Service won't start:**
- Check database connection in `.env`
- Verify all required environment variables
- Run `python run_dev.py check` for dependency issues

**Tests failing:**
- Ensure test database is accessible
- Check shared library path in `sys.path`
- Run `python run_tests.py unit` for faster feedback

**API authentication errors:**
- Verify `INTERNAL_SERVICE_KEY` matches other services
- Check JWT secret configuration
- Ensure service-to-service headers are correct

### Development Tips
- Use `/docs` endpoint for API testing when `DEBUG=true`
- Check logs in console for detailed error information
- Use `python run_tests.py checks` before committing code
- Monitor real-time events via **as-connection-service** WebSocket

## Contributing

1. Follow existing code patterns and structure
2. Add tests for new functionality
3. Run full test suite before submitting changes
4. Update documentation for API changes
5. Follow Python PEP 8 style guidelines