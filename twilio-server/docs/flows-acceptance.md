# Twilio Server - Flows & Acceptance Criteria

## Overview

This document provides "executable truth for behavior" with Given/When/Then acceptance criteria for all Twilio webhook handling and TwiML response flows in the Twilio-Server. These flows define the behavioral contracts for call processing, SMS handling, and integration with the NeverMissCall platform services.

## Flow 1: Incoming Call Webhook Processing Flow (FLOW_TWILIO_001)

### Description
Complete incoming call webhook processing with TwiML response generation and service notification.

```
[Twilio] --> [POST /webhooks/twilio/call] --> [Parse Webhook] --> [Lookup Tenant] --> [Generate TwiML] --> [Notify Services]
```

### Happy Path Acceptance Criteria

**AC-001.1: Incoming ringing call processing**
- **Given**: An incoming call with status "ringing" from Twilio
- **When**: POST /webhooks/twilio/call is called with valid webhook data
- **Then**:
  - Webhook data is validated and parsed successfully
  - Phone number is looked up to determine tenant association
  - TwiML response with dial command is generated
  - Response includes timeout and status callback URL
  - as-call-service is notified of incoming call
  - TwiML XML is returned with status 200

**AC-001.2: Call completion processing**
- **Given**: A call status update with "completed" status
- **When**: POST /webhooks/twilio/call is called with completion data
- **Then**:
  - Call duration and status are recorded
  - as-call-service is notified of call completion
  - Empty TwiML response is returned
  - Call metrics are updated

**AC-001.3: Call forwarding with business owner number**
- **Given**: An incoming call to provisioned business number
- **When**: Call webhook is processed with "ringing" status
- **Then**:
  - Business owner's forwarding number is retrieved from configuration
  - TwiML dial command targets owner's personal number
  - Dial timeout is set appropriately (20 seconds)
  - Action URL points to status callback endpoint

### Edge Cases
- Invalid webhook data format from Twilio
- Phone number not associated with any tenant
- Missing business owner forwarding number
- Twilio account validation failures
- Service notification failures to as-call-service
- Network timeouts during webhook processing

## Flow 2: Call Status Webhook Processing Flow (FLOW_TWILIO_002)

### Description
Call status updates from dial attempts with missed call detection and notification.

```
[Twilio Dial] --> [POST /webhooks/twilio/call/status/{callSid}] --> [Process Status] --> [Handle Missed Call] --> [Trigger SMS]
```

### Happy Path Acceptance Criteria

**AC-002.1: Call answered successfully**
- **Given**: A dial status webhook with "answered" status
- **When**: POST /webhooks/twilio/call/status/{callSid} is called
- **Then**:
  - Call status is processed and recorded
  - as-call-service is notified of successful connection
  - Call duration is tracked and stored
  - Empty TwiML response is returned
  - Analytics are updated with successful call metrics

**AC-002.2: Missed call detection and SMS trigger**
- **Given**: A dial status webhook with "no-answer" status
- **When**: Call status webhook is processed
- **Then**:
  - Call is marked as missed in the system
  - as-call-service is notified of missed call
  - SMS auto-response workflow is triggered
  - Customer information is prepared for SMS greeting
  - Conversation tracking is initialized

**AC-002.3: Busy or failed call handling**
- **Given**: A dial status with "busy" or "failed" status
- **When**: Call status webhook is processed
- **Then**:
  - Call failure reason is recorded
  - as-call-service is notified of call failure
  - Alternative handling workflow may be triggered
  - Error metrics are updated

### Edge Cases
- Invalid call SID in webhook URL
- Duplicate status webhooks for same call
- Status webhooks for non-existent calls
- Network failures during status processing
- Service notification failures for missed calls

## Flow 3: SMS Webhook Processing Flow (FLOW_TWILIO_003)

### Description
Incoming SMS message processing with conversation routing and AI integration.

```
[Twilio SMS] --> [POST /webhooks/twilio/sms] --> [Parse Message] --> [Route to Conversation] --> [Trigger AI Response]
```

### Happy Path Acceptance Criteria

**AC-003.1: Customer SMS message processing**
- **Given**: An incoming SMS from customer to business number
- **When**: POST /webhooks/twilio/sms is called with message data
- **Then**:
  - SMS content and metadata are parsed
  - Customer phone number is identified
  - Message is routed to appropriate conversation thread
  - as-call-service is notified of new message
  - Conversation context is maintained

**AC-003.2: AI conversation routing**
- **Given**: An SMS message requiring AI processing
- **When**: SMS webhook is processed
- **Then**:
  - Message content is forwarded to dispatch-bot-ai
  - Conversation history is maintained
  - AI response generation is triggered
  - Response timing is tracked for analytics

**AC-003.3: Media message handling**
- **Given**: An SMS with media attachments (images, etc.)
- **When**: SMS webhook contains NumMedia > 0
- **Then**:
  - Media attachments are identified and processed
  - Media URLs are extracted and validated
  - Message with media is routed appropriately
  - Media content is made available to conversation handlers

### Edge Cases
- Empty SMS message bodies
- Messages with invalid characters or encoding
- Media messages with unsupported formats
- Messages from blocked or invalid phone numbers
- SMS webhook replay attacks
- Network failures during message processing

## Flow 4: Tenant Phone Number Resolution Flow (FLOW_TWILIO_004)

### Description
Phone number lookup and tenant association for incoming communications.

```
[Phone Number] --> [Lookup in Database] --> [Retrieve Tenant Info] --> [Get Business Configuration] --> [Return Context]
```

### Happy Path Acceptance Criteria

**AC-004.1: Business phone number lookup**
- **Given**: An incoming call/SMS to provisioned business number
- **When**: Phone number lookup is performed
- **Then**:
  - Phone number is found in tenant configuration
  - Tenant ID and business details are retrieved
  - Business owner contact information is available
  - Business hours and preferences are loaded
  - Service area information is accessible

**AC-004.2: Multiple phone number handling**
- **Given**: A tenant with multiple provisioned phone numbers
- **When**: Lookup is performed for any associated number
- **Then**:
  - Correct tenant association is established
  - Primary vs secondary number designation is identified
  - Routing preferences are applied appropriately
  - All numbers route to same business configuration

### Edge Cases
- Phone numbers not found in tenant database
- Inactive or suspended tenant accounts
- Phone numbers in transition or provisioning state
- Database connection failures during lookup
- Cached vs fresh data consistency issues

## Flow 5: TwiML Response Generation Flow (FLOW_TWILIO_005)

### Description
Dynamic TwiML response generation based on call status and business configuration.

```
[Call Context] --> [Load Configuration] --> [Generate TwiML] --> [Include Callbacks] --> [Return XML Response]
```

### Happy Path Acceptance Criteria

**AC-005.1: Dial command TwiML generation**
- **Given**: A ringing call requiring forwarding
- **When**: TwiML response is generated
- **Then**:
  - Valid XML structure is created with proper encoding
  - Dial command includes target phone number
  - Timeout value is set based on business preferences
  - Action URL includes correct callback endpoint with call SID
  - Method is set to POST for status updates

**AC-005.2: Empty response for completed calls**
- **Given**: A call status that doesn't require further action
- **When**: TwiML response is requested
- **Then**:
  - Empty but valid TwiML Response element is returned
  - XML is properly formatted with encoding declaration
  - No additional commands or actions are included

**AC-005.3: Complex TwiML with multiple instructions**
- **Given**: A scenario requiring multiple TwiML commands
- **When**: Advanced call handling is needed
- **Then**:
  - Multiple TwiML verbs are properly sequenced
  - Conditional logic is applied based on business hours
  - Proper XML escaping is applied to dynamic content
  - All callback URLs are correctly formatted

### Edge Cases
- XML encoding issues with special characters
- Invalid phone number formats in dial commands
- Missing or malformed callback URLs
- TwiML size limits and complex instruction sets
- Business configuration data corruption

## Flow 6: Service Integration and Notification Flow (FLOW_TWILIO_006)

### Description
Integration with NeverMissCall platform services for event notification and data synchronization.

```
[Webhook Event] --> [Validate Event] --> [Prepare Notification] --> [Call Service APIs] --> [Handle Responses]
```

### Happy Path Acceptance Criteria

**AC-006.1: as-call-service notification for incoming calls**
- **Given**: A new incoming call event
- **When**: Service notification is triggered
- **Then**:
  - HTTP POST request is sent to as-call-service
  - Request includes call SID, phone numbers, tenant ID
  - Call status and direction are included
  - Timestamp is provided in ISO 8601 format
  - Success response is received and validated

**AC-006.2: Missed call notification workflow**
- **Given**: A call that goes unanswered
- **When**: Missed call is detected from status webhook
- **Then**:
  - Missed call notification is sent to as-call-service
  - Call duration (0) and end time are included
  - SMS auto-response workflow is initiated
  - Customer contact information is provided
  - Response tracking is established

**AC-006.3: SMS conversation routing**
- **Given**: An incoming SMS message
- **When**: Message routing is required
- **Then**:
  - Message content and metadata are sent to as-call-service
  - Conversation thread association is maintained
  - Customer identity and history are preserved
  - AI processing flags are set appropriately

### Edge Cases
- Service endpoints unavailable during notification
- Authentication failures with platform services
- Network timeouts during service calls
- Partial notification failures requiring retry
- Service response validation failures

## Security & Performance Considerations

### Security Measures
- **Webhook Validation**: Twilio webhook signatures are validated
- **Request Origin**: Only legitimate Twilio requests are processed
- **Data Sanitization**: All incoming data is sanitized and validated
- **Phone Number Validation**: E.164 format validation for all numbers
- **Rate Limiting**: Protection against webhook replay attacks

### Performance Expectations
- **Webhook Processing**: < 2000ms for call webhook processing
- **TwiML Generation**: < 500ms for response generation
- **Service Notifications**: < 1000ms for platform service calls
- **SMS Processing**: < 1500ms for message routing and AI trigger
- **Database Lookups**: < 300ms for tenant resolution

### Error Handling Standards
- **Webhook Failures**: Return appropriate HTTP status codes
- **Service Failures**: Graceful degradation with fallback responses
- **Invalid Data**: Clear validation error messages
- **Network Issues**: Retry logic for service communications
- **TwiML Errors**: Valid XML even in error conditions

## Integration Dependencies

### Required External Services
- **Twilio Platform**: Webhook source and TwiML response target
- **AS-Call-Service**: Call event processing and conversation management
- **PNS-Provisioning-Service**: Phone number and tenant lookup
- **Dispatch-Bot-AI**: SMS conversation processing and AI responses

### Webhook Security
- **Request Validation**: Twilio signature verification for all webhooks
- **Origin Verification**: Ensure requests originate from Twilio infrastructure
- **Rate Limiting**: Prevent abuse and replay attacks
- **Data Validation**: Strict validation of all incoming webhook parameters

## TwiML Response Standards

### Call Handling TwiML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial timeout="20" action="/webhooks/twilio/call/status/CA123" method="POST">
    +1987654321
  </Dial>
</Response>
```

### SMS Handling TwiML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
</Response>
```

### Error Response TwiML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Hangup/>
</Response>
```

## Webhook Data Validation Rules

### Call Webhook Validation
- **CallStatus**: Must be from valid enum [ringing, in-progress, completed, busy, no-answer, failed, canceled]
- **Phone Numbers**: Must be valid E.164 format (+1234567890)
- **CallSid**: Must be valid Twilio call identifier format
- **Direction**: Must be from [inbound, outbound-api, outbound-dial]

### SMS Webhook Validation
- **MessageSid**: Must be valid Twilio message identifier
- **Phone Numbers**: Must be valid E.164 format
- **Body**: Maximum 1600 characters for SMS content
- **NumMedia**: Must be valid integer for media count

### Status Webhook Validation
- **DialCallStatus**: Must be from [answered, no-answer, busy, failed, canceled]
- **CallDuration**: Must be valid integer representing seconds
- **CallSid**: Must match existing call identifier