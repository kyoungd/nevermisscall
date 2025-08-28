# as-call-service Design Document

## Service Overview

**Service Name**: as-call-service  
**Port**: 3103  
**Phase**: 1 - Core Processing  
**Purpose**: Core business logic hub for call processing, conversation management, and AI coordination  

## Business Requirements

### Primary Functions
- Process missed call events from twilio-server
- Manage SMS conversation lifecycles
- Coordinate AI handoff and human takeover
- Track leads and appointment outcomes
- Validate service areas and business hours
- Store conversation history and analytics data

### Success Criteria
- Missed calls trigger SMS within 5 seconds
- Conversations are threaded correctly
- AI handoff occurs after 60 seconds of no response
- Human takeover is seamless and immediate
- All conversation data is preserved
- Service area validation prevents out-of-bounds leads

## Technical Specification

### Technology Stack
- **Runtime**: Node.js 18+ with TypeScript 5+
- **Framework**: Express.js 4+
- **Database**: PostgreSQL with Prisma ORM
- **Validation**: Zod for request/response validation
- **Real-time**: HTTP webhooks + WebSocket events

### Service Architecture

```mermaid
graph TB
    subgraph "as-call-service (Port 3103)"
        CallController[CallController]
        ConversationController[ConversationController]
        LeadController[LeadController]
        CallService[CallService]
        ConversationService[ConversationService]
        ValidationService[ValidationService]
        Database[(PostgreSQL<br/>nevermisscall)]
    end
    
    TwilioServer[twilio-server] --> CallController
    TwilioServer --> ConversationController
    DispatchAI[dispatch-bot-ai] --> ConversationController
    WebUI[web-ui] --> ConversationController
    ASConnection[as-connection-service] --> ConversationController
    
    CallController --> CallService
    ConversationController --> ConversationService
    CallService --> ValidationService
    ConversationService --> ValidationService
    
    CallService --> Database
    ConversationService --> Database
    
    CallService --> TSTenant[ts-tenant-service]
    ValidationService --> TSTenant
```

## API Endpoints

### Call Processing

#### POST /calls/incoming
**Purpose**: Process incoming call event from twilio-server  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "callSid": "CA1234567890abcdef",
  "from": "+12125551234",
  "to": "+13105551234",
  "tenantId": "tenant-uuid",
  "callStatus": "ringing",
  "direction": "inbound",
  "timestamp": "2024-01-01T10:00:00Z"
}
```
**Response (200)**:
```json
{
  "success": true,
  "call": {
    "id": "call-uuid",
    "callSid": "CA1234567890abcdef",
    "status": "processing",
    "tenantId": "tenant-uuid",
    "customerPhone": "+12125551234",
    "businessPhone": "+13105551234"
  }
}
```

#### POST /calls/missed
**Purpose**: Process missed call event and trigger SMS  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "callSid": "CA1234567890abcdef",
  "callStatus": "no-answer",
  "callDuration": 0,
  "endTime": "2024-01-01T10:00:30Z"
}
```
**Response (200)**:
```json
{
  "success": true,
  "call": {
    "id": "call-uuid",
    "status": "missed",
    "smsTriggered": true,
    "conversationId": "conversation-uuid",
    "autoResponseSent": true
  }
}
```

#### GET /calls/:callId
**Purpose**: Get call details  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "call": {
    "id": "call-uuid",
    "callSid": "CA1234567890abcdef",
    "tenantId": "tenant-uuid",
    "customerPhone": "+12125551234",
    "businessPhone": "+13105551234",
    "direction": "inbound",
    "status": "missed",
    "startTime": "2024-01-01T10:00:00Z",
    "endTime": "2024-01-01T10:00:30Z",
    "duration": 0,
    "conversationId": "conversation-uuid",
    "leadCreated": true
  }
}
```

### Conversation Management

#### POST /conversations/:conversationId/messages
**Purpose**: Process incoming SMS message  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "messageSid": "SM1234567890abcdef",
  "from": "+12125551234",
  "to": "+13105551234",
  "body": "I need help with a leaky faucet at 123 Main St",
  "timestamp": "2024-01-01T10:01:00Z"
}
```
**Response (200)**:
```json
{
  "success": true,
  "message": {
    "id": "message-uuid",
    "conversationId": "conversation-uuid",
    "direction": "inbound",
    "processed": true,
    "aiProcessingTriggered": true,
    "humanResponseWindow": 60
  }
}
```

#### POST /conversations/:conversationId/reply
**Purpose**: Send human response (owner takeover)  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "message": "Thanks for reaching out! I can help with that faucet. What's the best time to come by?",
  "takeOverFromAI": true
}
```
**Response (200)**:
```json
{
  "success": true,
  "message": {
    "id": "message-uuid",
    "conversationId": "conversation-uuid",
    "direction": "outbound",
    "sender": "human",
    "messageSid": "SM1234567890abcdef",
    "aiDeactivated": true,
    "sentAt": "2024-01-01T10:02:00Z"
  }
}
```

#### GET /conversations/:conversationId
**Purpose**: Get conversation details and message history  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "conversation": {
    "id": "conversation-uuid",
    "tenantId": "tenant-uuid",
    "customerPhone": "+12125551234",
    "businessPhone": "+13105551234",
    "status": "active",
    "aiActive": false,
    "humanTakeoverAt": "2024-01-01T10:02:00Z",
    "lastMessageAt": "2024-01-01T10:02:00Z",
    "messageCount": 4,
    "leadId": "lead-uuid",
    "createdAt": "2024-01-01T10:00:30Z"
  },
  "messages": [
    {
      "id": "message-1",
      "direction": "outbound",
      "body": "Hi! Sorry we missed your call at Smith Plumbing. How can we help?",
      "sender": "system",
      "timestamp": "2024-01-01T10:00:35Z"
    },
    {
      "id": "message-2", 
      "direction": "inbound",
      "body": "I need help with a leaky faucet at 123 Main St",
      "timestamp": "2024-01-01T10:01:00Z"
    },
    {
      "id": "message-3",
      "direction": "outbound", 
      "body": "I can help with that faucet repair! I'm available tomorrow between 9 AM and 3 PM. Would 10 AM work for you?",
      "sender": "ai",
      "timestamp": "2024-01-01T10:01:15Z"
    },
    {
      "id": "message-4",
      "direction": "outbound",
      "body": "Thanks for reaching out! I can help with that faucet. What's the best time to come by?",
      "sender": "human",
      "timestamp": "2024-01-01T10:02:00Z"
    }
  ]
}
```

#### GET /conversations/tenant/:tenantId/active
**Purpose**: Get all active conversations for a tenant  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "conversations": [
    {
      "id": "conversation-uuid",
      "customerPhone": "+12125551234",
      "status": "active",
      "aiActive": false,
      "lastMessage": "Thanks for reaching out! I can help with that faucet...",
      "lastMessageAt": "2024-01-01T10:02:00Z",
      "messageCount": 4,
      "leadStatus": "qualified"
    }
  ],
  "totalActive": 1,
  "aiHandledCount": 0,
  "humanHandledCount": 1
}
```

### Lead Management

#### GET /leads/:leadId
**Purpose**: Get lead information  
**Headers**: `Authorization: Bearer jwt-token`  
**Response (200)**:
```json
{
  "lead": {
    "id": "lead-uuid",
    "tenantId": "tenant-uuid",
    "conversationId": "conversation-uuid",
    "customerPhone": "+12125551234",
    "customerName": null,
    "customerAddress": "123 Main St, Los Angeles, CA",
    "problemDescription": "leaky faucet",
    "urgencyLevel": "normal",
    "jobType": "faucet_repair",
    "estimatedValue": 225.00,
    "status": "qualified",
    "aiAnalysis": {
      "confidence": 0.85,
      "jobClassification": "faucet_repair",
      "urgencyScore": 0.3,
      "serviceAreaValid": true
    },
    "createdAt": "2024-01-01T10:00:30Z"
  }
}
```

#### PUT /leads/:leadId/status
**Purpose**: Update lead status  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "status": "appointment_scheduled",
  "notes": "Scheduled for tomorrow 10 AM",
  "estimatedValue": 275.00
}
```
**Response (200)**:
```json
{
  "success": true,
  "lead": {
    "id": "lead-uuid",
    "status": "appointment_scheduled",
    "notes": "Scheduled for tomorrow 10 AM",
    "estimatedValue": 275.00,
    "updatedAt": "2024-01-01T10:05:00Z"
  }
}
```

### AI Integration

#### POST /conversations/:conversationId/ai/process
**Purpose**: Trigger AI processing of conversation  
**Headers**: `X-Service-Key: internal-service-key`  
**Request Body**:
```json
{
  "messageContent": "I need help with a leaky faucet at 123 Main St",
  "conversationHistory": [
    "Hi! Sorry we missed your call at Smith Plumbing. How can we help?"
  ],
  "tenantContext": {
    "businessName": "Smith Plumbing",
    "serviceArea": 25,
    "businessHours": "07:00-18:00"
  }
}
```
**Response (200)**:
```json
{
  "success": true,
  "aiResponse": {
    "message": "I can help with that faucet repair! Let me check availability...",
    "confidence": 0.85,
    "intent": "schedule_service",
    "extractedInfo": {
      "jobType": "faucet_repair",
      "customerAddress": "123 Main St",
      "urgency": "normal"
    },
    "nextAction": "schedule_appointment"
  }
}
```

#### POST /conversations/:conversationId/ai/deactivate
**Purpose**: Deactivate AI for human takeover  
**Headers**: `Authorization: Bearer jwt-token`  
**Request Body**:
```json
{
  "reason": "human_takeover",
  "userId": "user-uuid"
}
```
**Response (200)**:
```json
{
  "success": true,
  "conversation": {
    "id": "conversation-uuid",
    "aiActive": false,
    "humanActive": true,
    "takeoverAt": "2024-01-01T10:02:00Z",
    "takeoverBy": "user-uuid"
  }
}
```

## Data Models

### Call Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class Call:
    id: str
    call_sid: str  # Twilio Call SID
    tenant_id: str
    
    # Call participants
    customer_phone: str
    business_phone: str
    
    # Call details
    direction: Literal['inbound', 'outbound']
    status: Literal['ringing', 'in-progress', 'completed', 'missed', 'failed']
    start_time: datetime
    duration: int  # seconds
    
    # Processing status
    processed: bool
    sms_triggered: bool
    conversation_created: bool
    lead_created: bool
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Optional fields
    end_time: Optional[datetime] = None
    conversation_id: Optional[str] = None
    lead_id: Optional[str] = None
    caller_city: Optional[str] = None
    caller_state: Optional[str] = None
    caller_country: Optional[str] = None
```

### Conversation Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class Conversation:
    id: str
    tenant_id: str
    call_id: str
    
    # Participants
    customer_phone: str
    business_phone: str
    
    # Conversation state
    status: Literal['active', 'completed', 'abandoned']
    ai_active: bool
    human_active: bool
    
    # Timing
    last_message_time: datetime
    
    # Metrics
    message_count: int
    ai_message_count: int
    human_message_count: int
    
    # Outcomes
    appointment_scheduled: bool
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Optional fields
    ai_handoff_time: Optional[datetime] = None
    human_takeover_time: Optional[datetime] = None
    last_human_response_time: Optional[datetime] = None
    outcome: Optional[Literal['appointment_scheduled', 'quote_provided', 'resolved', 'abandoned']] = None
    lead_id: Optional[str] = None
```

### Message Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

@dataclass
class Message:
    id: str
    conversation_id: str
    tenant_id: str
    
    # Message details
    direction: Literal['inbound', 'outbound']
    sender: Literal['customer', 'system', 'ai', 'human']
    body: str
    
    # Processing
    processed: bool
    ai_processed: bool
    
    # Delivery
    status: Literal['sent', 'delivered', 'undelivered', 'failed']
    
    # Timing
    sent_at: datetime
    created_at: datetime
    
    # Optional fields
    message_sid: Optional[str] = None  # Twilio Message SID
    confidence: Optional[float] = None
    intent: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None
```

### Lead Entity
```python
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any
from datetime import datetime

@dataclass
class AIAnalysis:
    confidence: float
    job_classification: str
    urgency_score: float
    service_area_valid: bool
    address_validated: bool

@dataclass
class Lead:
    id: str
    tenant_id: str
    conversation_id: str
    call_id: str
    
    # Customer information
    customer_phone: str
    
    # Lead details
    problem_description: str
    urgency_level: Literal['low', 'normal', 'high', 'emergency']
    
    # Lead status
    status: Literal['new', 'qualified', 'appointment_scheduled', 'completed', 'lost']
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Optional fields
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    job_type: Optional[str] = None
    estimated_value: Optional[float] = None
    status_notes: Optional[str] = None
    ai_analysis: Optional[AIAnalysis] = None
    appointment_id: Optional[str] = None
    conversion_value: Optional[float] = None
    lost_reason: Optional[str] = None
```

## Database Schema

### Calls Table
```sql
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(100) UNIQUE NOT NULL,
    tenant_id UUID NOT NULL,
    
    -- Call participants
    customer_phone VARCHAR(20) NOT NULL,
    business_phone VARCHAR(20) NOT NULL,
    
    -- Call details
    direction VARCHAR(20) DEFAULT 'inbound',
    status VARCHAR(50) DEFAULT 'ringing',
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER DEFAULT 0,
    
    -- Processing status
    processed BOOLEAN DEFAULT false,
    sms_triggered BOOLEAN DEFAULT false,
    conversation_created BOOLEAN DEFAULT false,
    lead_created BOOLEAN DEFAULT false,
    
    -- Related entities
    conversation_id UUID,
    lead_id UUID,
    
    -- Geographic data
    caller_city VARCHAR(100),
    caller_state VARCHAR(50),
    caller_country VARCHAR(3) DEFAULT 'US',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_calls_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_calls_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_calls_lead FOREIGN KEY (lead_id) REFERENCES leads(id)
);
```

### Conversations Table
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    call_id UUID NOT NULL,
    
    -- Participants
    customer_phone VARCHAR(20) NOT NULL,
    business_phone VARCHAR(20) NOT NULL,
    
    -- Conversation state
    status VARCHAR(50) DEFAULT 'active',
    ai_active BOOLEAN DEFAULT false,
    human_active BOOLEAN DEFAULT false,
    
    -- Timing
    ai_handoff_time TIMESTAMP,
    human_takeover_time TIMESTAMP,
    last_message_time TIMESTAMP DEFAULT NOW(),
    last_human_response_time TIMESTAMP,
    
    -- Metrics
    message_count INTEGER DEFAULT 0,
    ai_message_count INTEGER DEFAULT 0,
    human_message_count INTEGER DEFAULT 0,
    
    -- Outcomes
    outcome VARCHAR(50),
    appointment_scheduled BOOLEAN DEFAULT false,
    
    -- Related entities
    lead_id UUID,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_conversations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_conversations_call FOREIGN KEY (call_id) REFERENCES calls(id),
    CONSTRAINT fk_conversations_lead FOREIGN KEY (lead_id) REFERENCES leads(id)
);
```

### Messages Table
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    
    -- Message details
    message_sid VARCHAR(100),
    direction VARCHAR(20) NOT NULL,
    sender VARCHAR(20) NOT NULL,
    body TEXT NOT NULL,
    
    -- Processing
    processed BOOLEAN DEFAULT false,
    ai_processed BOOLEAN DEFAULT false,
    confidence DECIMAL(3,2),
    intent VARCHAR(100),
    
    -- Delivery
    status VARCHAR(50) DEFAULT 'sent',
    error_code INTEGER,
    error_message TEXT,
    
    -- Timing
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_messages_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_messages_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

### Leads Table
```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    call_id UUID NOT NULL,
    
    -- Customer information
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_address TEXT,
    
    -- Lead details
    problem_description TEXT NOT NULL,
    job_type VARCHAR(100),
    urgency_level VARCHAR(20) DEFAULT 'normal',
    estimated_value DECIMAL(10,2),
    
    -- Lead status
    status VARCHAR(50) DEFAULT 'new',
    status_notes TEXT,
    
    -- AI analysis (stored as JSONB)
    ai_analysis JSONB,
    
    -- Outcomes
    appointment_id UUID,
    conversion_value DECIMAL(10,2),
    lost_reason TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_leads_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_leads_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_leads_call FOREIGN KEY (call_id) REFERENCES calls(id)
);
```

### Performance Indexes
```sql
-- Critical performance indexes
CREATE INDEX idx_calls_tenant_status ON calls (tenant_id, status);
CREATE INDEX idx_calls_customer_phone ON calls (customer_phone);
CREATE INDEX idx_calls_start_time ON calls (start_time DESC);
CREATE INDEX idx_calls_call_sid ON calls (call_sid); -- Added for Twilio webhook lookups

CREATE INDEX idx_conversations_tenant_status ON conversations (tenant_id, status);
CREATE INDEX idx_conversations_customer_phone ON conversations (customer_phone);
CREATE INDEX idx_conversations_ai_active ON conversations (ai_active, status);

CREATE INDEX idx_messages_conversation ON messages (conversation_id, created_at DESC);
CREATE INDEX idx_messages_tenant_direction ON messages (tenant_id, direction);
CREATE INDEX idx_messages_message_sid ON messages (message_sid); -- Added for Twilio webhook lookups

CREATE INDEX idx_leads_tenant_status ON leads (tenant_id, status);
CREATE INDEX idx_leads_customer_phone ON leads (customer_phone);
CREATE INDEX idx_leads_created_at ON leads (created_at DESC);
```

## Business Logic

### Missed Call Processing Workflow
1. **Receive Call Event**: twilio-server sends call initiation
2. **Store Call Record**: Create call entry with "ringing" status
3. **Wait for Completion**: Monitor for call completion events
4. **Process Missed Call**: If no-answer/busy, trigger SMS workflow
5. **Create Conversation**: Initialize conversation thread
6. **Send Auto-Response**: Trigger initial SMS via twilio-server
7. **Create Lead**: Generate lead record from call
8. **Start AI Timer**: Begin 60-second countdown for AI activation

### Conversation State Management
```python
from enum import Enum

class ConversationState(Enum):
    WAITING_FOR_CUSTOMER = 'waiting_for_customer'  # After auto-response sent
    WAITING_FOR_HUMAN = 'waiting_for_human'        # Customer replied, waiting for owner
    AI_ACTIVE = 'ai_active'                        # AI is handling conversation
    HUMAN_ACTIVE = 'human_active'                  # Human has taken over
    COMPLETED = 'completed'                        # Conversation ended
    ABANDONED = 'abandoned'                        # No response after timeout
```

### AI Coordination Logic
1. **Message Receipt**: Customer sends SMS reply
2. **Human Response Window**: Start 60-second countdown
3. **AI Activation**: If no human response, activate AI via dispatch-bot-ai
4. **AI Response Processing**: Store AI response and continue monitoring
5. **Human Takeover**: Immediate deactivation of AI when human responds
6. **State Persistence**: Maintain conversation state across all interactions

### Service Area Validation
1. **Extract Address**: Parse customer message for address information
2. **Validate with Tenant Service**: Check if address is within service area
3. **Update Lead**: Mark lead with service area validation results
4. **Auto-Reject**: If out of area, send polite rejection message

## Security Considerations

### Authentication & Authorization
- Internal service endpoints use API key authentication
- User-facing endpoints require JWT token validation
- Tenant-scoped access control enforced at service level
- All database queries include tenant_id filtering

### Data Protection
- Customer phone numbers encrypted at rest
- Message content encrypted with tenant-specific keys
- Audit logging for all conversation access
- Automatic PII redaction in logs

### Input Validation
- Phone number format validation (E.164)
- Message content length limits (1600 characters)
- SQL injection prevention with parameterized queries
- XSS protection for message display

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "Conversation not found or access denied",
    "details": {
      "conversationId": "invalid-uuid",
      "tenantId": "tenant-uuid"
    }
  }
}
```

### Common Error Codes
- `CALL_PROCESSING_FAILED`: Error processing call event
- `CONVERSATION_NOT_FOUND`: Invalid conversation ID
- `MESSAGE_SEND_FAILED`: SMS delivery failure
- `AI_PROCESSING_ERROR`: AI service communication error
- `SERVICE_AREA_VALIDATION_FAILED`: Address validation error
- `LEAD_CREATION_FAILED`: Lead generation error

## Testing Strategy

### Unit Tests
- Call processing workflow logic
- Conversation state management
- Message threading and ordering
- Lead creation and status updates
- Service area validation logic

### Integration Tests
- twilio-server webhook integration
- dispatch-bot-ai coordination
- Database operations and transactions
- Real-time event broadcasting

### End-to-End Tests
- Complete missed call to SMS flow
- AI handoff and human takeover
- Multi-message conversation handling
- Lead lifecycle management

## Performance Requirements

- **Call Processing**: < 2 seconds from webhook to SMS trigger
- **Message Processing**: < 500ms for message storage and forwarding
- **Conversation Queries**: < 300ms for active conversation lists
- **AI Coordination**: < 1 second for AI activation/deactivation
- **Concurrent Load**: Support 100+ simultaneous conversations

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nevermisscall

# Service Dependencies
TWILIO_SERVER_URL=http://localhost:3701
DISPATCH_AI_URL=http://localhost:3801
TS_TENANT_SERVICE_URL=http://localhost:3302
AS_CONNECTION_SERVICE_URL=http://localhost:3105

# Service Authentication
INTERNAL_SERVICE_KEY=shared-secret-key-for-phase-1

# Business Logic
AI_TAKEOVER_DELAY_SECONDS=60
MESSAGE_TIMEOUT_MINUTES=30
MAX_CONVERSATION_MESSAGES=1000
SERVICE_AREA_VALIDATION_ENABLED=true

# Service Configuration
PORT=3103
SERVICE_NAME=as-call-service
```

This call service acts as the central business logic hub for Phase 1, coordinating all aspects of the missed call to conversation workflow while maintaining clean integration points with all other services.