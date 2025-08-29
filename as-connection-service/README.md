# as-connection-service

WebSocket management service for real-time dashboard updates and live communication in the NeverMissCall Phase 1 platform.

## Overview

The as-connection-service provides real-time WebSocket connectivity for the dashboard, enabling instant updates for calls, messages, and conversation status. It handles connection authentication, tenant isolation, and event broadcasting with Redis-backed state management.

## Key Features

- **WebSocket Management**: Real-time connections with Socket.IO
- **JWT Authentication**: Secure connection authentication via ts-auth-service
- **Tenant Isolation**: Room-based separation of tenant events
- **Redis State Management**: Reliable connection state and event queue storage
- **Event Broadcasting**: Real-time updates for calls, messages, and status changes
- **Connection Limits**: Configurable per-tenant connection limits
- **Rate Limiting**: Protection against connection flooding and spam

## Technology Stack

- **Runtime**: Python 3.10+
- **Framework**: FastAPI with python-socketio
- **Authentication**: JWT token validation with python-jose
- **Caching**: Redis for connection state and message queuing with aioredis
- **Event Broadcasting**: Socket.IO rooms for tenant isolation
- **ASGI Server**: uvicorn for production deployment

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit environment variables as needed
nano .env
```

## Configuration

Key environment variables:

```bash
# Service Configuration
PORT=3105
SERVICE_NAME=as-connection-service

# Redis Configuration
REDIS_URL=redis://localhost:6379
CONNECTION_REDIS_DB=1
EVENT_QUEUE_REDIS_DB=2

# Socket.IO Configuration
SOCKETIO_CORS_ORIGIN=http://localhost:3000
HEARTBEAT_INTERVAL_MS=30000

# Service Dependencies
TS_AUTH_SERVICE_URL=http://localhost:3301
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1
```

## Usage

### Development

```bash
# Run in development mode
python -m uvicorn src.as_connection_service.main:main_app --reload --host 0.0.0.0 --port 3105
```

### Production

```bash
# Run in production mode
python -m uvicorn src.as_connection_service.main:main_app --host 0.0.0.0 --port 3105
```

### Testing

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/unit/test_models.py -v

# Run with coverage
python -m pytest --cov=src/as_connection_service --cov-report=html
```

## WebSocket Events

### Client Connection

```javascript
const socket = io('http://localhost:3105', {
  auth: {
    token: 'jwt-token-here'
  }
});

socket.on('authenticated', (data) => {
  console.log('Connected:', data);
});
```

### Real-time Events

- `call_incoming` - New incoming call
- `call_missed` - Missed call with auto-response
- `message_received` - New SMS message from customer  
- `message_sent` - Outgoing SMS message sent
- `ai_activated` - AI has taken over conversation
- `dashboard_status` - Periodic dashboard status update

### User Actions

- `takeover_conversation` - Human takes over from AI
- `send_message` - Send manual message to customer
- `update_lead_status` - Update lead status from dashboard
- `subscribe_conversation` - Subscribe to conversation events
- `unsubscribe_conversation` - Unsubscribe from conversation events

## HTTP API Endpoints

### Connection Management

- `GET /connections/status` - Get connection service status
- `GET /connections/tenant/{tenant_id}` - Get active connections for tenant (internal)

### Event Broadcasting

- `POST /broadcast/` - Broadcast event to connected clients (internal)
- `POST /broadcast/tenant/{tenant_id}` - Broadcast to tenant (internal)
- `POST /broadcast/conversation/{conversation_id}` - Broadcast to conversation (internal)

### Health Checks

- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   web-ui        │────│ as-connection-   │────│   Redis         │
│   (Socket.IO    │    │ service          │    │   (State &      │
│    Client)      │    │ (FastAPI +       │    │    Events)      │
└─────────────────┘    │  python-socketio)│    └─────────────────┘
                       └──────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │                   │
            ┌───────────────┐  ┌──────────────┐
            │ ts-auth-      │  │ as-call-     │
            │ service       │  │ service      │
            │ (JWT Auth)    │  │ (Events)     │
            └───────────────┘  └──────────────┘
```

## Business Logic

### Connection Flow
1. Client connects with JWT token
2. Token validated with ts-auth-service
3. Connection added to tenant-specific Socket.IO room
4. Connection state stored in Redis
5. Authentication confirmation sent to client

### Event Broadcasting Flow
1. Service receives event via HTTP API
2. Event stored in Redis queue for reliability
3. Event broadcasted to appropriate Socket.IO rooms
4. Delivery tracked and failures retried

### Tenant Isolation
- Each tenant has isolated Socket.IO rooms
- Connection state separated by tenant ID in Redis
- Event filtering ensures tenant-scoped delivery
- Authorization checks prevent cross-tenant access

## Performance

- **Connection Establishment**: < 500ms for authentication
- **Event Delivery**: < 100ms from receipt to broadcast
- **Concurrent Connections**: 1000+ simultaneous connections
- **Event Throughput**: 10,000+ events/minute across all tenants

## Security

- JWT token validation for all WebSocket connections
- Service-to-service authentication for HTTP endpoints
- Tenant-scoped access control for all events
- Connection and rate limiting protection
- No sensitive data stored in connection state

## Monitoring

Health endpoints provide status of:
- Redis connection pools
- Active WebSocket connections
- Service dependencies
- Event queue status

## Development

### Project Structure

```
as-connection-service/
├── src/as_connection_service/
│   ├── config/           # Configuration settings
│   ├── models/           # Data models and schemas
│   ├── services/         # Business logic services
│   ├── controllers/      # HTTP API controllers
│   ├── utils/           # Utilities and helpers
│   └── main.py          # FastAPI application
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── requirements.txt     # Dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

### Adding New Events

1. Define event data model in `models/events.py`
2. Add broadcasting method to `EventBroadcaster`
3. Add HTTP endpoint in appropriate controller
4. Add Socket.IO handler if needed
5. Write unit tests for new functionality

## Phase 1 Integration

This service integrates with:

- **ts-auth-service** (Port 3301): JWT token validation
- **as-call-service** (Port 3104): Call and conversation events
- **twilio-server** (Port 3701): SMS and call status updates
- **web-ui** (Port 3000): Real-time dashboard client
- **Redis**: Connection state and event queue storage

## License

Part of the NeverMissCall Phase 1 platform.