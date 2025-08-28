# Use Case Flows and Sequence Diagrams

## Overview
This document provides detailed sequence diagrams for the key user scenarios in NeverMissCall. Each flow shows the step-by-step interaction between services, external APIs, and users.

## Core Use Cases

### 1. Missed Call to SMS Conversion Flow

**Primary Actor**: Customer calling business
**Scenario**: Customer calls business, call goes unanswered, SMS is automatically sent

```mermaid
sequenceDiagram
    participant Customer
    participant TwilioAPI as Twilio API
    participant TwilioServer as twilio-server
    participant CallService as as-call-service
    participant ConnectionService as as-connection-service
    participant WebUI as web-ui
    participant NMCAI as nmc-ai
    
    Customer->>TwilioAPI: Incoming call to business number
    TwilioAPI->>TwilioServer: Webhook: call.initiated
    TwilioServer->>CallService: POST /calls/incoming
    CallService->>ConnectionService: Notify: incoming_call
    ConnectionService->>WebUI: WebSocket: call_notification
    
    Note over WebUI: Business owner sees call notification
    Note over Customer,TwilioAPI: Call rings for 30 seconds
    
    TwilioAPI->>TwilioServer: Webhook: call.no-answer
    TwilioServer->>CallService: POST /calls/missed
    CallService->>CallService: Create conversation record
    CallService->>TwilioServer: POST /sms/send-initial
    TwilioServer->>TwilioAPI: Send SMS to customer
    TwilioAPI->>Customer: SMS: "Hi! Sorry we missed you at [Business]. We're helping another customer - how can we help you?"
    
    TwilioServer->>ConnectionService: Notify: sms_sent
    ConnectionService->>WebUI: WebSocket: conversation_started
    
    Note over WebUI: Business owner sees new conversation
```

### 2. Customer SMS Response and AI Handoff

**Primary Actor**: Customer responding to initial SMS
**Scenario**: Customer replies via SMS, AI takes over after 60 seconds if no human response

```mermaid
sequenceDiagram
    participant Customer
    participant TwilioAPI as Twilio API
    participant TwilioServer as twilio-server
    participant CallService as as-call-service
    participant ConnectionService as as-connection-service
    participant WebUI as web-ui
    participant NMCAI as nmc-ai
    participant OpenAI as OpenAI API
    
    Customer->>TwilioAPI: SMS reply: "I need plumbing help"
    TwilioAPI->>TwilioServer: Webhook: message.received
    TwilioServer->>CallService: POST /conversations/message
    CallService->>CallService: Store message, start 60s timer
    CallService->>ConnectionService: Notify: new_message
    ConnectionService->>WebUI: WebSocket: message_received
    
    Note over WebUI: Business owner has 60 seconds to respond
    
    alt Business owner responds within 60 seconds
        WebUI->>CallService: POST /conversations/reply
        CallService->>TwilioServer: POST /sms/send
        TwilioServer->>TwilioAPI: Send SMS
        TwilioAPI->>Customer: Human response
    else No response after 60 seconds
        CallService->>NMCAI: POST /conversations/takeover
        NMCAI->>CallService: GET /conversations/context
        CallService->>NMCAI: Return conversation history
        NMCAI->>OpenAI: Generate contextual response
        OpenAI->>NMCAI: AI response
        NMCAI->>CallService: POST /conversations/ai-reply
        CallService->>TwilioServer: POST /sms/send
        TwilioServer->>TwilioAPI: Send SMS
        TwilioAPI->>Customer: AI response: "I can help! What type of plumbing issue are you experiencing?"
        TwilioServer->>ConnectionService: Notify: ai_takeover
        ConnectionService->>WebUI: WebSocket: ai_active
    end
```

### 3. AI Appointment Scheduling Flow

**Primary Actor**: Customer requesting appointment through AI
**Scenario**: AI collects information and schedules appointment using calendar integration

```mermaid
sequenceDiagram
    participant Customer
    participant TwilioAPI as Twilio API
    participant TwilioServer as twilio-server
    participant CallService as as-call-service
    participant NMCAI as nmc-ai
    participant OpenAI as OpenAI API
    participant UniversalCal as universal-calendar
    participant GoogleCal as Google Calendar
    participant ConnectionService as as-connection-service
    participant WebUI as web-ui
    
    Customer->>TwilioAPI: SMS: "I need an appointment tomorrow"
    TwilioAPI->>TwilioServer: Webhook: message.received
    TwilioServer->>CallService: POST /conversations/message
    CallService->>NMCAI: POST /process-message
    
    NMCAI->>OpenAI: Analyze intent: appointment request
    OpenAI->>NMCAI: Intent: schedule_appointment
    
    NMCAI->>UniversalCal: GET /availability?date=tomorrow
    UniversalCal->>GoogleCal: Check business calendar
    GoogleCal->>UniversalCal: Available slots
    UniversalCal->>NMCAI: Available: 10am, 2pm, 4pm
    
    NMCAI->>OpenAI: Generate response with options
    OpenAI->>NMCAI: "I can schedule you for tomorrow at 10am, 2pm, or 4pm. Which works best?"
    
    NMCAI->>CallService: POST /conversations/ai-reply
    CallService->>TwilioServer: POST /sms/send
    TwilioServer->>TwilioAPI: Send SMS
    TwilioAPI->>Customer: Time slot options
    
    Customer->>TwilioAPI: SMS: "2pm works"
    TwilioAPI->>TwilioServer: Webhook: message.received
    TwilioServer->>CallService: POST /conversations/message
    CallService->>NMCAI: POST /process-message
    
    NMCAI->>OpenAI: Confirm appointment details
    OpenAI->>NMCAI: Extract: time=2pm, date=tomorrow
    
    NMCAI->>UniversalCal: POST /appointments/create
    UniversalCal->>GoogleCal: Create calendar event
    GoogleCal->>UniversalCal: Event created
    UniversalCal->>NMCAI: Appointment confirmed
    
    NMCAI->>OpenAI: Generate confirmation message
    OpenAI->>NMCAI: "Perfect! I've scheduled you for tomorrow at 2pm. You'll receive a confirmation shortly."
    
    NMCAI->>CallService: POST /conversations/ai-reply
    CallService->>TwilioServer: POST /sms/send
    TwilioServer->>TwilioAPI: Send SMS
    TwilioAPI->>Customer: Confirmation message
    
    CallService->>ConnectionService: Notify: appointment_scheduled
    ConnectionService->>WebUI: WebSocket: new_appointment
    
    Note over WebUI: Business owner sees new appointment in dashboard
```

### 4. Business Owner Dashboard Login Flow

**Primary Actor**: Business Owner
**Scenario**: Owner logs into dashboard to view conversations and analytics

```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant WebUI as web-ui
    participant ASAuth as as-auth-service
    participant TSAuth as ts-auth-service
    participant TSTenant as ts-tenant-service
    participant TSUser as ts-user-service
    participant Dashboard as as-dashboard-service
    participant Analytics as as-analytics-core-service
    participant Connection as as-connection-service
    
    Owner->>WebUI: Navigate to dashboard
    WebUI->>ASAuth: Check existing session
    ASAuth->>TSAuth: Validate JWT token
    
    alt No valid session
        TSAuth->>ASAuth: Token invalid/expired
        ASAuth->>WebUI: Redirect to login
        WebUI->>Owner: Show login form
        
        Owner->>WebUI: Submit credentials
        WebUI->>ASAuth: POST /auth/login
        ASAuth->>TSAuth: POST /auth/authenticate
        TSAuth->>TSTenant: Validate tenant status
        TSTenant->>TSAuth: Tenant active
        TSAuth->>TSUser: Validate user credentials
        TSUser->>TSAuth: User valid
        TSAuth->>ASAuth: Return JWT token
        ASAuth->>WebUI: Authentication successful
    else Valid session exists
        TSAuth->>ASAuth: Token valid
        ASAuth->>WebUI: Authentication confirmed
    end
    
    WebUI->>Dashboard: GET /dashboard (with JWT)
    Dashboard->>TSAuth: Validate request token
    TSAuth->>Dashboard: Token valid
    Dashboard->>Analytics: GET /analytics/summary
    Analytics->>Dashboard: Return metrics data
    Dashboard->>WebUI: Dashboard layout + data
    
    WebUI->>Connection: Establish WebSocket connection
    Connection->>TSAuth: Validate WebSocket token
    TSAuth->>Connection: Token valid
    Connection->>WebUI: WebSocket connected
    
    WebUI->>Owner: Display dashboard with live data
    
    Note over Owner: Real-time updates flow through WebSocket
```

### 5. Phone Number Provisioning Flow

**Primary Actor**: Business Owner setting up new number
**Scenario**: Owner provisions new phone number with 10DLC compliance

```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant WebUI as web-ui
    participant ASAuth as as-auth-service
    participant PNSProv as pns-provisioning-service
    participant PNSSec as pns-security-service
    participant PNSBrand as pns-10dlc-brand-service
    participant PNSCampaign as pns-10dlc-campaign-service
    participant TwilioAPI as Twilio API
    participant AWSKMS as AWS KMS
    
    Owner->>WebUI: Request new phone number
    WebUI->>ASAuth: Validate session
    ASAuth->>WebUI: Session valid
    
    WebUI->>PNSProv: POST /phone-numbers/provision
    PNSProv->>ASAuth: Validate request token
    ASAuth->>PNSProv: Token valid
    
    PNSProv->>TwilioAPI: Search available numbers
    TwilioAPI->>PNSProv: Available numbers list
    PNSProv->>WebUI: Return number options
    
    WebUI->>Owner: Display number choices
    Owner->>WebUI: Select preferred number
    
    WebUI->>PNSProv: POST /phone-numbers/reserve
    PNSProv->>TwilioAPI: Reserve selected number
    TwilioAPI->>PNSProv: Number reserved
    
    PNSProv->>PNSBrand: GET /brands/tenant/{tenantId}
    
    alt Brand registration exists
        PNSBrand->>PNSProv: Return brand info
    else No brand registration
        PNSProv->>PNSBrand: POST /brands/register
        PNSBrand->>PNSSec: GET /encryption/tenant-key
        PNSSec->>AWSKMS: Retrieve DEK
        AWSKMS->>PNSSec: Return key
        PNSSec->>PNSBrand: Encryption key
        PNSBrand->>TwilioAPI: Submit brand registration
        TwilioAPI->>PNSBrand: Brand registration pending
        PNSBrand->>PNSProv: Brand submitted
    end
    
    PNSProv->>PNSCampaign: POST /campaigns/create
    PNSCampaign->>TwilioAPI: Create 10DLC campaign
    TwilioAPI->>PNSCampaign: Campaign created
    PNSCampaign->>PNSProv: Campaign ready
    
    PNSProv->>TwilioAPI: Purchase and configure number
    TwilioAPI->>PNSProv: Number activated
    
    PNSProv->>PNSSec: POST /storage/encrypt-profile
    PNSSec->>AWSKMS: Encrypt number profile
    AWSKMS->>PNSSec: Encrypted data
    PNSSec->>PNSProv: Profile encrypted
    
    PNSProv->>WebUI: Number provisioned successfully
    WebUI->>Owner: Confirmation + number details
```

### 6. Real-time Conversation Monitoring

**Primary Actor**: Business Owner monitoring active conversations
**Scenario**: Owner watches live conversations and can take over from AI

```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant WebUI as web-ui
    participant Connection as as-connection-service
    participant CallService as as-call-service
    participant NMCAI as nmc-ai
    participant TwilioServer as twilio-server
    participant Customer
    
    Note over Owner: Owner is logged into dashboard
    
    Connection->>WebUI: WebSocket: active_conversations_update
    WebUI->>Owner: Display live conversation list
    
    Owner->>WebUI: Click on conversation to monitor
    WebUI->>CallService: GET /conversations/{id}/messages
    CallService->>WebUI: Return message history
    WebUI->>Owner: Display conversation thread
    
    Note over Customer,NMCAI: AI is actively conversing with customer
    
    Customer->>TwilioServer: New SMS message
    TwilioServer->>CallService: POST /conversations/message
    CallService->>Connection: Notify: new_message
    Connection->>WebUI: WebSocket: message_update
    WebUI->>Owner: Display new message in real-time
    
    NMCAI->>CallService: POST /conversations/ai-reply
    CallService->>TwilioServer: POST /sms/send
    CallService->>Connection: Notify: ai_response
    Connection->>WebUI: WebSocket: ai_message
    WebUI->>Owner: Show AI response in real-time
    
    alt Owner decides to take over
        Owner->>WebUI: Click "Take Over Conversation"
        WebUI->>CallService: POST /conversations/human-takeover
        CallService->>NMCAI: POST /conversations/deactivate-ai
        NMCAI->>CallService: AI deactivated
        CallService->>Connection: Notify: human_active
        Connection->>WebUI: WebSocket: takeover_confirmed
        WebUI->>Owner: Show "You are now active" indicator
        
        Owner->>WebUI: Type and send message
        WebUI->>CallService: POST /conversations/reply
        CallService->>TwilioServer: POST /sms/send
        TwilioServer->>Customer: Human response
        
        Note over Owner: Owner continues conversation manually
    else Owner continues monitoring
        Note over Owner: AI continues handling conversation
        Connection->>WebUI: WebSocket: ongoing updates
        WebUI->>Owner: Continue showing live updates
    end
```

### 7. Analytics and Reporting Dashboard

**Primary Actor**: Business Owner reviewing performance
**Scenario**: Owner views analytics dashboard with real-time metrics

```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant WebUI as web-ui
    participant Dashboard as as-dashboard-service
    participant Analytics as as-analytics-core-service
    participant CallService as as-call-service
    participant Connection as as-connection-service
    participant BSFinancial as bs-financial-analytics-service
    participant BSUsage as bs-usage-tracking-service
    
    Owner->>WebUI: Navigate to Analytics tab
    WebUI->>Dashboard: GET /dashboard?layout=analytics
    
    Dashboard->>Analytics: GET /analytics/call-volume?range=today
    Analytics->>CallService: GET /calls/metrics
    CallService->>Analytics: Return call data
    Analytics->>Dashboard: Call volume metrics
    
    Dashboard->>Analytics: GET /analytics/response-times
    Analytics->>Dashboard: Response time data
    
    Dashboard->>BSFinancial: GET /financial/revenue?period=month
    BSFinancial->>Analytics: GET /analytics/revenue-data
    Analytics->>BSFinancial: Revenue metrics
    BSFinancial->>Dashboard: Financial analytics
    
    Dashboard->>BSUsage: GET /usage/feature-adoption
    BSUsage->>CallService: GET /calls/ai-usage
    CallService->>BSUsage: AI usage statistics
    BSUsage->>Dashboard: Usage analytics
    
    Dashboard->>WebUI: Complete dashboard data
    WebUI->>Owner: Display analytics dashboard
    
    Note over Owner: Real-time updates begin
    
    loop Every 30 seconds
        Dashboard->>Analytics: GET /analytics/realtime-metrics
        Analytics->>Dashboard: Updated metrics
        Dashboard->>Connection: Notify: dashboard_update
        Connection->>WebUI: WebSocket: metrics_update
        WebUI->>Owner: Update charts and metrics in real-time
    end
    
    alt Owner requests data export
        Owner->>WebUI: Click "Export Report"
        WebUI->>Dashboard: POST /dashboard/export
        Dashboard->>Analytics: GET /analytics/export-data
        Analytics->>Dashboard: Raw data for export
        Dashboard->>Dashboard: Generate CSV/PDF
        Dashboard->>WebUI: Download link
        WebUI->>Owner: Provide download
    end
```

## Error Handling Flows

### 1. Service Unavailable Fallback

```mermaid
sequenceDiagram
    participant WebUI as web-ui
    participant Dashboard as as-dashboard-service
    participant Analytics as as-analytics-core-service
    
    WebUI->>Dashboard: GET /dashboard
    Dashboard->>Analytics: GET /analytics/metrics
    
    Note over Analytics: Service is down
    
    Analytics-->>Dashboard: Connection timeout
    Dashboard->>Dashboard: Generate fallback data
    Dashboard->>WebUI: Dashboard with mock data + warning
    WebUI->>WebUI: Display "Live data unavailable" notice
```

### 2. External API Failure Handling

```mermaid
sequenceDiagram
    participant Customer
    participant TwilioServer as twilio-server
    participant NMCAI as nmc-ai
    participant OpenAI as OpenAI API
    
    Customer->>TwilioServer: SMS message
    TwilioServer->>NMCAI: Process message
    NMCAI->>OpenAI: Generate response
    
    Note over OpenAI: OpenAI API is down
    
    OpenAI-->>NMCAI: API Error 503
    NMCAI->>NMCAI: Switch to fallback templates
    NMCAI->>TwilioServer: Template response: "Thanks for your message. A team member will respond soon."
    TwilioServer->>Customer: Fallback response
```

## Performance Optimization Patterns

### 1. Caching Strategy Flow

```mermaid
sequenceDiagram
    participant WebUI as web-ui
    participant Dashboard as as-dashboard-service
    participant Cache as Redis Cache
    participant Analytics as as-analytics-core-service
    
    WebUI->>Dashboard: GET /widgets/data
    Dashboard->>Cache: Check cached data
    
    alt Cache hit
        Cache->>Dashboard: Return cached data
        Dashboard->>WebUI: Fast response (< 50ms)
    else Cache miss
        Dashboard->>Analytics: GET /analytics/fresh-data
        Analytics->>Dashboard: Fresh data
        Dashboard->>Cache: Store data (TTL: 2min)
        Dashboard->>WebUI: Response with fresh data
    end
```

### 2. WebSocket Connection Management

```mermaid
sequenceDiagram
    participant WebUI as web-ui
    participant Connection as as-connection-service
    participant Redis as Redis Store
    
    WebUI->>Connection: Establish WebSocket
    Connection->>Connection: Authenticate connection
    Connection->>Redis: Store connection state
    
    loop Heartbeat every 30s
        Connection->>WebUI: Ping
        WebUI->>Connection: Pong
    end
    
    alt Connection lost
        Connection->>Redis: Mark connection as disconnected
        Connection->>Connection: Cleanup resources
    else Normal disconnect
        WebUI->>Connection: Close connection
        Connection->>Redis: Remove connection state
    end
```

These use case flows provide a comprehensive view of how all the NeverMissCall services interact to deliver the core functionality of converting missed calls into SMS conversations with AI assistance and human handoff capabilities.