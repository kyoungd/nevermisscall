# Event Catalog — NeverMissCall MVP

**Status:** Accepted • **Audience:** Engineering • **Transport:** DB Outbox (at-least-once) • **Clock:** UTC

> Canonical list of **domain events**: envelope shape, versioning, and payloads. Producers/consumers must treat events as **immutable facts**. All examples use `schema_version: "1.0.0"` for MVP.

---

## 0) Envelope (canonical)

Every event persisted in `outbox_events` uses this envelope:

```json
{
  "event_id": "uuid",                 
  "event_name": "nmc.<domain>.<Event>",
  "schema_version": "semver",        
  "tenant_id": "uuid",              
  "occurred_at": "RFC3339-UTC",     
  "correlation_id": "uuid",         
  "causation_id": "uuid|null",      
  "payload": { /* event-specific */ }
}
```

**Conventions**

* `event_name`: dot-separated, domain-scoped (see names below).
* `correlation_id`: ties a user/business flow (e.g., one conversation thread and its booking).
* `causation_id`: the **event\_id** that immediately caused this event (may be `null`).
* **PII** in payloads: phone numbers allowed (E.164). No secrets.
* **Idempotency**: consumers must be idempotent (at-least-once delivery).

**Versioning**

* **Semantic** (ADR-0004): additive → minor; breaking → major (publish side-by-side or migrate consumers).

---

## 1) Telephony Domain

### 1.1 `nmc.telephony.CallDetected`

* **When**: We detect a missed/failed/busy inbound call worthy of SMS follow-up.
* **Producer**: Telephony Ingestion
* **Consumers**: Conversation, Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "call_id": "uuid",
    "from_phone": "+13105551212",
    "to_phone": "+13105550000",
    "reason": "no-answer|busy|failed",
    "provider_ref": "CAxxxxxxxx"
  }
}
```

### 1.2 `nmc.telephony.InboundSmsReceived`

* **When**: Twilio posts inbound SMS.
* **Producer**: Telephony Ingestion
* **Consumers**: Conversation
* **Schema `1.0.0`**

```json
{
  "payload": {
    "message_id": "uuid",
    "from_phone": "+13105551212",
    "to_phone": "+13105550000",
    "body": "My sink is clogged",
    "provider_ref": "SMxxxxxxxx"
  }
}
```

---

## 2) Conversation Domain

### 2.1 `nmc.conversation.ConversationStarted`

* **When**: We create or reopen an `open` conversation for a caller.
* **Producer**: Conversation
* **Consumers**: Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "conversation_id": "uuid",
    "caller_phone": "+13105551212"
  }
}
```

### 2.2 `nmc.conversation.MessageSent`

* **When**: We enqueue an outbound SMS (or record an inbound arrival).
* **Producer**: Conversation
* **Consumers**: Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "message_id": "uuid",
    "conversation_id": "uuid",
    "direction": "in|out",
    "status": "queued|sent|delivered|failed"
  }
}
```

### 2.3 `nmc.conversation.DeliveryUpdated`

* **When**: Twilio status callback advances message delivery state.
* **Producer**: Conversation
* **Consumers**: Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "message_id": "uuid",
    "status": "sent|delivered|failed",
    "provider_ref": "SMxxxxxxxx",
    "error_code": "string|null"
  }
}
```

### 2.4 `nmc.conversation.HumanTakeoverRequested`

* **When**: User clicks Takeover in UI.
* **Producer**: Conversation
* **Consumers**: Ops UI / Notifications
* **Schema `1.0.0`**

```json
{
  "payload": {
    "conversation_id": "uuid",
    "user_id": "uuid"
  }
}
```

---

## 3) Catalog Domain

### 3.1 `nmc.catalog.CatalogUpdated`

* **When**: A tenant changes service items (name, price, duration, active flag).
* **Producer**: Catalog
* **Consumers**: Conversation (cache invalidation), Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "updated_item_ids": ["uuid"],
    "full_refresh": false
  }
}
```

---

## 4) Scheduling Domain

### 4.1 `nmc.scheduling.AppointmentHeld`

* **When**: A temporary reservation is created.
* **Producer**: Scheduling
* **Consumers**: Conversation (to message the user)
* **Schema `1.0.0`**

```json
{
  "payload": {
    "hold_id": "uuid",
    "resource_id": "uuid",
    "start": "2025-09-01T17:00:00Z",
    "end": "2025-09-01T19:00:00Z"
  }
}
```

### 4.2 `nmc.scheduling.AppointmentBooked`

* **When**: A hold is converted into a confirmed appointment.
* **Producer**: Scheduling
* **Consumers**: Reporting, Calendar Sync
* **Schema `1.0.0`**

```json
{
  "payload": {
    "appointment_id": "uuid",
    "resource_id": "uuid",
    "start": "2025-09-01T17:00:00Z",
    "end": "2025-09-01T19:00:00Z",
    "service_item_id": "uuid",
    "customer_phone": "+13105551212"
  }
}
```

### 4.3 `nmc.scheduling.AppointmentReleased`

* **When**: A hold expires or is explicitly released.
* **Producer**: Scheduling
* **Consumers**: Conversation
* **Schema `1.0.0`**

```json
{
  "payload": {
    "hold_id": "uuid",
    "resource_id": "uuid",
    "start": "2025-09-01T17:00:00Z",
    "end": "2025-09-01T19:00:00Z"
  }
}
```

### 4.4 `nmc.scheduling.AppointmentCancelled`

* **When**: A confirmed appointment is canceled.
* **Producer**: Scheduling
* **Consumers**: Reporting, Conversation
* **Schema `1.0.0`**

```json
{
  "payload": {
    "appointment_id": "uuid",
    "resource_id": "uuid",
    "start": "2025-09-01T17:00:00Z",
    "end": "2025-09-01T19:00:00Z",
    "cancelled_reason": "user|tenant|system|conflict"
  }
}
```

---

## 5) Compliance Domain

### 5.1 `nmc.compliance.ComplianceStatusChanged`

* **When**: 10DLC campaign state changes.
* **Producer**: Compliance
* **Consumers**: Conversation (gate outbound messaging)
* **Schema `1.0.0`**

```json
{
  "payload": {
    "campaign_id": "uuid",
    "status": "pending|approved|rejected"
  }
}
```

---

## 6) Billing Domain

### 6.1 `nmc.billing.SubscriptionUpdated`

* **When**: Stripe notifies us of a subscription lifecycle change.
* **Producer**: Billing
* **Consumers**: Identity/Feature Gates
* **Schema `1.0.0`**

```json
{
  "payload": {
    "stripe_customer_id": "cus_xxx",
    "stripe_subscription_id": "sub_xxx",
    "plan": "basic|pro",
    "status": "active|past_due|canceled|trialing",
    "current_period_end": "2025-09-30T23:59:59Z"
  }
}
```

---

## 7) Naming & Topics

* **Pattern:** `nmc.<domain>.<EventName>`; domains: `telephony`, `conversation`, `catalog`, `scheduling`, `compliance`, `billing`.
* **Outbox storage:** `event_name` column stores the canonical name; consumers filter by prefix.

---

## 8) Ordering & Delivery Semantics

* **At-least-once** delivery; global ordering is **not guaranteed**. Consumers must handle replays and reordering.
* For per-conversation ordering, use `correlation_id`. If strict ordering is required within a conversation, consumer should **serialize** processing by `(tenant_id, conversation_id)`.

---

## 9) Error Handling & Retries

* Consumers that fail should log the error with `event_id`, increment a failure metric, and either **retry** (transient) or **dead-letter** to an error table with context. Use jitter policy from ADR-0008.

---

## 10) Examples (full envelopes)

### 10.1 `nmc.telephony.CallDetected`

```json
{
  "event_id": "0b0f3b9a-0d1e-4c1b-9f1b-7a0a7b8c3d10",
  "event_name": "nmc.telephony.CallDetected",
  "schema_version": "1.0.0",
  "tenant_id": "a7b1d0ee-d0a8-4b3a-9a6c-1a2b3c4d5e6f",
  "occurred_at": "2025-09-01T18:22:03Z",
  "correlation_id": "2f1a3c4b-8a9d-4a8e-9c22-bf0a1c9d22aa",
  "causation_id": null,
  "payload": {
    "call_id": "7f0d8e2c-9e65-4a1a-a7f4-6f3f8b9c0a11",
    "from_phone": "+13105551212",
    "to_phone": "+13105550000",
    "reason": "no-answer",
    "provider_ref": "CA1234567890"
  }
}
```

### 10.2 `nmc.scheduling.AppointmentBooked`

```json
{
  "event_id": "5c6d7e8f-1111-4222-8333-944445555666",
  "event_name": "nmc.scheduling.AppointmentBooked",
  "schema_version": "1.0.0",
  "tenant_id": "a7b1d0ee-d0a8-4b3a-9a6c-1a2b3c4d5e6f",
  "occurred_at": "2025-09-01T19:00:00Z",
  "correlation_id": "2f1a3c4b-8a9d-4a8e-9c22-bf0a1c9d22aa",
  "causation_id": "0b0f3b9a-0d1e-4c1b-9f1b-7a0a7b8c3d10",
  "payload": {
    "appointment_id": "3f9f4e4b-6cbd-4c0a-9c6a-1c7c0d6f2a4e",
    "resource_id": "8e8bd1b6-1c7e-4fb8-9ef2-b3f47428a1d9",
    "start": "2025-09-02T17:00:00Z",
    "end": "2025-09-02T19:00:00Z",
    "service_item_id": "b3a1f9d6-7e2c-4a5a-b1c5-ada2d0f1e8c6",
    "customer_phone": "+13105551212"
  }
}
```

---

## 11) Change Management

* Update `schema_version` when fields change; keep consumers backward compatible for one minor version span when possible.
* Document changes here first; then implement.
