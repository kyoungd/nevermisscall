# NeverMissCall API

## Product Overview
Turn every missed call into a conversation—and every conversation into a customer.

Small local service pros (plumbers, electricians, HVAC, Locksmith, Garage Door Opener.) miss calls while on the job. 
Every unanswered ring sends prospects to competitors, bleeding revenue and wasting ad spend.

## Core Solution
- Instant text-back when calls go unanswered
- AI handles conversations until user takes over
- 60-second wait period before AI engagement
- One-tap takeover from notifications

## Workspace Configuration
**IMPORTANT**: This service uses npm with shared library integration for consistent patterns.

- **Package Manager**: npm (independent of workspace)
- **Testing Framework**: Jest with direct dependencies
- **TypeScript**: Not used (pure JavaScript implementation)
- **Build Tools**: Direct Node.js execution
- **Shared Library**: Uses `../shared` for database, config, logging, and utilities

## Shared Library Integration

This service integrates with the NeverMissCall shared library for consistent patterns:

### Configuration & Logging
```javascript
const { getCommonConfig, logger } = require('../shared');
const config = getCommonConfig();

// Structured logging instead of console.log
logger.info('Call webhook received', { callSid, from, to });
logger.error('Error sending SMS', error);
```

### Database Operations
```javascript
const { initDatabase, query } = require('../shared');
const db = initDatabase(config.database);

// Store call records
await query('INSERT INTO calls (call_sid, from_number, to_number) VALUES ($1, $2, $3)', 
  [callSid, from, to]);
```

### API Responses
```javascript
const { successResponse, errorResponse } = require('../shared');

// Consistent API responses
res.json(successResponse({ status: 'healthy' }));
res.status(400).json(errorResponse('Invalid webhook payload'));
```

### Service Communication
```javascript
const { ServiceClient, getServiceUrl } = require('../shared');
const callService = new ServiceClient(config.serviceAuth.key);

// Call other services
await callService.post(`${getServiceUrl('as-call-service')}/internal/calls/process`, {
  callSid, status: 'missed'
});
```

This service operates independently but follows shared patterns for consistency with other NeverMissCall services.

## Technical Architecture
- Custom API server (this project)
- Twilio for calls/SMS
- In-memory message queues
- GoHighLevel for CRM display
- AI integration for responses
- Postgresql for data storage

## MVP Features
[Include your MVP feature list from the original description]

# NeverMissCall Architecture Summary

## Core Concept
Turn missed calls into SMS conversations for local service pros with AI handling, seamless user takeover, and comprehensive conversation tracking.

## Architecture Decisions Made

### 1. **System Architecture**
- **Custom API Server** handles all business logic and complexity
- **GHL (GoHighLevel)** kept simple as data display/CRM layer only
- **Clean separation**: Your API = brain, GHL = presentation
- **In-memory message queue** for background processing (Phase 1 simplification)

### 2. **Data Flow**
```
Twilio → Custom API → Memory Queue → Background Worker
              ↓                         ↓
         GHL Sync                  AI Processing
              ↓                         ↓
         App/Web Display          Back to Twilio (SMS)
```

### 3. **Call & SMS Handling**
- **Call Forwarding**: Business number forwards to plumber's cell phone
- **Missed Call Detection**: Twilio `DialCallStatus` events trigger auto-response
- **Twilio Conversations API**: Automatic SMS threading per missed call
- **AI Dispatcher**: 60-second wait before AI takeover

### 4. **User Notification Strategy**
- **Primary**: Push notifications with deep links and takeover actions
- **Backup**: SMS to personal phone for critical/high-value leads
- **Conversation Summaries**: End-of-conversation outcome notifications
- **Daily Summaries**: Lead conversion and revenue tracking

### 5. **Conversation Lifecycle**
```
Missed Call → Auto-SMS → Customer Response → AI/User Handling → Conversation End → Summary Notification
```

## ✅ COMPLETED: Phase 1 Foundation - Webhook Handler

### Status: MVP Call Processing Complete & Tested
**Implementation Date**: January 2025

**What Was Built:**
- ✅ **Express Server**: Full webhook handler with Twilio integration
- ✅ **Call Forwarding**: Routes incoming calls to user phone (20-second timeout)
- ✅ **Missed Call Detection**: Detects no-answer/busy/failed call statuses
- ✅ **Auto SMS Response**: Sends "test 1" message when calls are missed
- ✅ **Comprehensive Test Suite**: 9 passing tests with mocked Twilio
- ✅ **Production Config**: Environment setup, health endpoints, error handling

**Files Created:**
- `index.js` - Main server with webhook endpoints
- `package.json` - Dependencies and scripts
- `tests/webhooks.test.js` - Unit tests for webhook handlers
- `tests/integration.test.js` - End-to-end flow testing
- `tests/setup.js` - Test configuration and mocks
- `.env.example` - Environment configuration template

**Key Endpoints Implemented:**
- `POST /webhooks/twilio/call` - Handles incoming calls and forwards them
- `POST /webhooks/twilio/call/status/:callSid` - Detects missed calls and sends SMS
- `GET /health` - Health check endpoint

**Testing Setup Verified:**
- ✅ **Twilio Integration**: Webhook configuration working
- ✅ **Call Flow**: Google Voice → Twilio Number → User Phone → Auto SMS
- ✅ **ngrok Setup**: Public webhook URL working with Twilio
- ✅ **End-to-End Test**: Complete flow tested and functioning

**Current Functionality:**
```
Incoming Call → Forward to User → No Answer → Auto SMS "test 1"
```

**Next Implementation Priority:**
Move to Phase 2: SMS conversation handling and AI dispatcher logic.

## Next Steps
Ready to implement SMS conversation management and AI handoff logic.

## Phase 1: Foundation Components (Week 1-2)

### 1. WebhookEvent Handler
**Priority: Critical**
- **Purpose**: Single entry point for all external events (Twilio calls and SMS)
- **Core Functions**:
  - Receive and validate webhook payloads
  - Route events to appropriate handlers
  - Implement retry logic for failed processing
  - Log all events for debugging
- **Key Endpoints**:
  - `POST /webhooks/twilio/call` - Missed call events
  - `POST /webhooks/twilio/sms` - Incoming/outgoing SMS
  - `POST /webhooks/ghl/contact` - Contact updates
  - `POST /webhooks/ghl/opportunity` - Lead status changes
- **Dependencies**: None (foundation component)

### 2. User & Settings Management
**Priority: Critical**
- **Purpose**: Core user data and configuration management
- **Core Functions**:
  - User status tracking (Available/Busy/Offline/Vacation)
  - Settings CRUD operations
  - Business hours validation
  - Auto-response template management
- **Key Components**:
  - User authentication/authorization
  - Settings validation and defaults
  - Status change notifications
- **Dependencies**: Database setup

**API**: oauth2 access and global calendar access.

**General Endpoints:**
- `GET /` → `302 redirect to /oauth-demo.html`
- `GET /oauth-demo.html` → `200 HTML` (demo interface)
- `GET /health` → `200 { status: "healthy", database: "connected", providers: {...} }`

**OAuth Authentication:**
- `GET /auth/:provider/start?user_id=string` → `200 { auth_url: string, state: string, provider: string }`
- `GET /auth/:provider/callback?code=string&state=string` → `200 { success: true, message: "Connected successfully" }` or `302 redirect`
- `POST /auth/:provider/token/refresh { user_id: string }` → `200 { access_token: string, expires_at: string }` or `401 error`
- `GET /auth/:provider/status?user_id=string` → `200 { connected: boolean, expires_at?: string, scopes?: string[] }`
- `DELETE /auth/:provider/disconnect { user_id: string }` → `200 { success: true, message: "Disconnected successfully" }`

**Calendar Operations:**
- `GET /calendar/:provider/events?user_id=string&start_date=ISO&end_date=ISO&limit=number` 
    → `200 
    { 
        events: CalendarEvent[], 
        next_page_token?: string 
    }`
- `POST /calendar/:provider/events 
    { 
        user_id: string, 
        title: string, 
        start: ISO, 
        end: ISO, 
        description?: string, 
        location?: 
        string, 
        attendees?: string[],
        customData?: object
    }` 
    → 
    `201 
    { 
        id: string, 
        title: string, 
        start: ISO, 
        end: ISO, 
        ... 
    }`
- `PUT /calendar/:provider/events/:id 
    { 
        user_id: string, 
        title?: string, 
        start?: ISO, 
        end?: ISO, 
        description?: string, 
        location?: string 
    }` 
    → `200 
    { 
        id: string, 
        title: string, 
        start: ISO, 
        end: ISO, 
        ... 
    }`
- `DELETE /calendar/:provider/events/:id?user_id=string 
    → `204
        (no content)`
- `GET /calendar/:provider/availability?user_id=string&date=ISO&duration=minutes
    → `200 
    { 
        available_slots: { 
            start: ISO, 
            end: ISO 
        }[] 
    }`


custom_data:
{

}
**Error Responses (all endpoints):**
- `400` → `{ error: "invalid_request", message: string }`
- `401` → `{ error: "token_expired", message: string, reconnect_url?: string }`
- `404` → `{ error: "not_found", message: string }`
- `429` → `{ error: "rate_limited", message: string, retry_after: number }`
- `500` → `{ error: "server_error", message: string }`


### 3. Database Schema & Migrations
**Priority: Critical**
- **Purpose**: Persistent storage for all entities
- **Tables to Create**:
  - `users` - Service pro accounts
  - `settings` - User configurations
  - `calls` - Call event records
  - `conversations` - SMS thread containers
  - `messages` - Individual SMS records
  - `leads` - Customer opportunities
  - `webhook_events` - Event audit log
  - `notifications` - User alerts
- **Indexes**: Optimize for real-time queries
- **Dependencies**: Database platform selection

## Phase 2: Core Processing Engine (Week 2-3)

### 4. Call Processing Engine
**Priority: High**
- **Purpose**: Handle missed call events and trigger auto-responses
- **Core Functions**:
  - Process missed call webhooks
  - Create conversation records
  - Generate initial auto-response SMS
  - Link calls to existing or new leads
  - Trigger user notifications
- **Key Logic**:
  - Check user availability status
  - Apply business hours rules
  - Handle voicemail transcription
  - Deduplicate rapid successive calls
- **Dependencies**: WebhookEvent Handler, User Management

### 5. SMS Conversation Manager
**Priority: High**
- **Purpose**: Manage SMS thread lifecycle and message routing
- **Core Functions**:
  - Route incoming SMS to correct conversation
  - Track conversation state and ownership
  - Handle message persistence
  - Manage user/AI handoff states
- **Key Components**:
  - Message validation and filtering
  - Conversation thread grouping
  - Real-time message delivery
  - Read/unread status tracking
- **Dependencies**: Call Processing Engine

### 6. State Management System
**Priority: High**
- **Purpose**: Centralized state tracking for conversations and users
- **Core Functions**:
  - Track conversation ownership (AI vs User)
  - Manage user availability states
  - Handle state transitions
  - Provide real-time state queries
- **Key States**:
  - User: Available, Busy, Offline, Vacation
  - Conversation: Active, AI_Handling, User_Handling, Completed
  - Message: Pending, Sent, Delivered, Read
- **Dependencies**: Database, User Management

## Phase 3: Intelligence Layer (Week 3-4)

### 7. AIDispatcher Logic
**Priority: High**
- **Purpose**: Manage 60-second wait period and AI takeover decisions
- **Core Functions**:
  - Start countdown timer on new conversations
  - Monitor for user response within 60 seconds
  - Trigger AI takeover when appropriate
  - Handle user manual takeover
  - Generate AI responses via external service
- **Key Logic**:
  - Respect user status (don't wait if offline)
  - Handle multiple simultaneous conversations
  - Graceful AI→User handoff
  - Context preservation across handoffs
- **Dependencies**: State Management, SMS Manager, AI Service Integration

### 8. Notification Service
**Priority: Medium**
- **Purpose**: Real-time alerts to users via push/SMS with deep linking
- **Core Functions**:
  - Send instant win notifications with app deep links
  - Push missed call alerts with takeover actions
  - SMS backup notifications with conversation links
  - End-of-conversation summaries with outcomes
  - Delivery status tracking
- **Notification Types**:
  - **New Lead Alerts**: "New $5K kitchen remodel - AI responding" [Take Over] [Let AI Continue]
  - **Conversation Summaries**: Appointment made/follow-up needed/lost with quick actions
  - **Daily Summaries**: End-of-day lead conversion recap
  - **AI Engagement**: Status updates when AI is actively chatting
- **Deep Link Integration**:
  - Push notifications → Direct to conversation in app
  - SMS links → Web app conversation takeover
  - One-tap takeover from notifications
- **Dependencies**: User Management, Push Service Setup, Twilio Conversations API

## Phase 4: Integration & Polish (Week 4-5)

### 9. GHL Integration Layer
**Priority: Medium**
- **Purpose**: Bi-directional sync with GoHighLevel platform
- **Core Functions**:
  - Sync conversations to GHL inbox
  - Update opportunity records
  - Push contact information
  - Handle GHL webhook events
- **Key Features**:
  - Real-time conversation mirroring
  - Lead status synchronization
  - Custom field mapping
  - Bulk data sync for onboarding
- **Dependencies**: All core components

### 10. Analytics & Reporting
**Priority: Low**
- **Purpose**: Track performance metrics and generate insights
- **Core Metrics**:
  - Call capture rate
  - Response time averages
  - Lead conversion rates
  - Revenue attribution
- **Reports**:
  - Daily win summaries
  - Weekly performance trends
  - Monthly business insights
- **Dependencies**: All data-generating components

### 11. Database Design Considerations:
Core Tables for Your Entities:

users - Service pros with phone numbers and settings
calls - Call events with Twilio CallSid and status
conversations - Twilio ConversationSid threading
messages - SMS content and metadata
leads - Customer opportunities and status
webhook_events - Audit log for debugging

Key Relationships:
sqlcalls → conversations (1:1)
conversations → messages (1:many)
users → calls (1:many)
conversations → leads (1:1)
Important Indexes:

Phone numbers (frequent lookups)
Twilio SIDs (webhook processing)
Conversation status (active conversation queries)
Timestamps (time-based queries)

## Implementation Guidelines

### Development Priorities
1. **Build for reliability first** - Handle failures gracefully
2. **Design for scale** - Assume rapid user growth
3. **Keep it simple** - Avoid over-engineering early features
4. **Test thoroughly** - Each component must work in isolation

### Quality Gates
- [ ] Each component has comprehensive unit tests
- [ ] End-to-end testing of critical paths
- [ ] Performance testing under load
- [ ] Security audit of webhook endpoints
- [ ] Documentation for each component

### Success Metrics
- **Week 2**: Process missed calls and send auto-responses
- **Week 3**: Handle full SMS conversations with AI handoff
- **Week 4**: Complete user takeover and notification flow
- **Week 5**: Full GHL integration and basic analytics

## Risk Mitigation

### Technical Risks
- **Webhook reliability**: Implement retry logic and dead letter queues
- **Race conditions**: Use proper locking for state transitions
- **AI service downtime**: Fallback to template responses
- **Scale bottlenecks**: Design for horizontal scaling from start

### Business Risks
- **User adoption**: Keep setup under 5 minutes
- **Feature creep**: Stick to MVP scope until backbone is solid
- **Performance issues**: Monitor response times from day one

