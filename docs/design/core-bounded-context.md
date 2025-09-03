# Core Bounded Context Documentation — Minimal (2 contexts)

**Architecture stance (small project)**

* **Modular monolith** with **2 bounded contexts** and one relational DB (separate schemas): `conversation` and `fulfillment`.
* In-process domain events (no external broker). Direct function calls across modules for commands/queries.
* One external adapter at the edge for **CPaaSRef (SMS + missed-call webhooks)**; one for **Calendar provider** (Google/Jobber). Both live **inside** the owning context.
* Tenancy: simple `tenant_id` on all tables. Analytics deferred (append-only event table if needed).
* **Timekeeping**: All domain timestamps are persisted and serialized as **ISO-8601 UTC (`Z`)**; convert at edges.

---

## Visual (Mermaid)

```mermaid
flowchart LR
  subgraph Monolith
    A[Conversation & Comms]
    B[Fulfillment (Scheduling + Calendar)]
  end
  CPaaSRef[(CPaaSRef)] -->|webhooks| A
  A -->|send SMS| CPaaSRef
  A <-->|commands/queries| B
  B -->|provider API| CAL[(Calendar Provider)]
```

---

# 1) Conversation & Comms Context

### Aggregates

**Conversation (AR)**

* **Identity**: `(tenantId, conversationId)`

* **Invariants**:

  1. At most **one open** conversation per `(tenantId, callerNumber)` **at a time** (*open = state ≠ `Closed`*).
  2. Transitions are **state-machine bound**: `New → AwaitingReply → Escalated | Closed`.
  3. **Auto-reply budget**: composing + sending of the first SMS must start **≤ 5s** after `MissedCallDetected`.
  4. **Opt-out respected**: if caller is opted-out, block outbound SMS.

* **Consistency rules**: state changes and message creation are a **single transaction**; outbound SMS call happens after commit, with idempotency via `clientMessageId`.

* **Key business rules**: 60s human override timer; detect emergency keywords; throttle message bursts per tenant.

**Messaging Endpoint (AR)**

* **Identity**: `(tenantId, phoneNumber)`
* **Invariants**:

  1. Phone number must be assigned to a tenant before use.
  2. **Compliance** flags (10DLC brand/campaign) must be `Verified` to allow marketing/solicitation content; **policy enforcement occurs here** (the CPaaSRef adapter is transport only).
  3. **Opt-out list** is authoritative for blocking.

### Domain Events (in-process)

| Event                      | When emitted                         | Producer             | Consumers                                     |
| -------------------------- | ------------------------------------ | -------------------- | --------------------------------------------- |
| `MissedCallDetected`       | CPaaSRef webhook normalized             | Conversation service | Conversation service (self-trigger open)      |
| `ConversationOpened`       | First touch after missed call        | Conversation         | Analytics (optional)                          |
| `AutoReplySent`            | First outbound SMS accepted by CPaaSRef | Conversation         | Analytics (optional)                          |
| `MessageDeliveryUpdated`   | Delivery status callback from CPaaSRef  | Conversation         | None (internal update)                        |
| `ComplianceOptOutReceived` | Inbound STOP/UNSUBSCRIBE             | Messaging Endpoint    | Conversation (to close), Analytics (optional) |

**Event Schemas (JSON, v1)**
*All events support an optional `correlationId` that is **propagated unchanged end-to-end** when present.*

```json
{
  "MissedCallDetected": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "callId": "string",
    "from": "+15551234567",
    "to": "+15557654321",
    "startedAt": "ISO-8601 UTC (Z)",
    "endedAt": "ISO-8601 UTC (Z)"
  },
  "ConversationOpened": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "conversationId": "uuid",
    "caller": "+15551234567",
    "openedAt": "ISO-8601 UTC (Z)"
  },
  "AutoReplySent": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "conversationId": "uuid",
    "messageId": "uuid",
    "clientMessageId": "string",
    "to": "+15551234567",
    "acceptedAt": "ISO-8601 UTC (Z)",
    "cpaasRef": "string"
  },
  "MessageDeliveryUpdated": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "messageId": "uuid",
    "status": "QUEUED|SENT|DELIVERED|FAILED",
    "at": "ISO-8601 UTC (Z)",
    "cpaasRef": "string",
    "error": "string|null"
  },
  "ComplianceOptOutReceived": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "from": "+15551234567",
    "at": "ISO-8601 UTC (Z)"
  }
}
```

### Key Use Cases / Commands

**UC-1: Handle Missed Call → Auto-SMS**

* **Command**: `handleMissedCall(callPayload)`
* **Flow**: Normalize payload → find/open Conversation → persist `Message(draft)` → call CPaaSRef `sendSms` (idempotent) → update to `sent` → emit `AutoReplySent`.
* **Acceptance Criteria**:

  * P95 latency (call end → CPaaSRef POST) ≤ **5s**.
  * **Exactly one open Conversation** per `(tenantId, caller)`. If one exists, append to it; else open a new one and emit `ConversationOpened`.
  * On CPaaSRef failure (4xx/5xx/timeout), retry with backoff up to 2 times; if still failing, log `FAILED` and surface alert.

**UC-2: Inbound SMS → Route & Respond**

* **Command**: `handleInboundSms(inboundPayload)`
* **Flow**: Lookup active Conversation → append inbound Message → update state to `AwaitingReply` → optional AI reply → send via CPaaSRef.
* **Acceptance Criteria**:

  * If `STOP/UNSUBSCRIBE` → emit `ComplianceOptOutReceived` and mark conversation `Closed`.
  * Duplicate webhook deliveries are idempotent (via CPaaSRef message ID).

**UC-3: Human Takeover**

* **Command**: `requestHumanTakeover(conversationId)`
* **Flow**: Set state `Escalated`, pause AI, notify console.
* **Acceptance Criteria**:

  * No AI messages sent while `Escalated = true`.

**UC-4: Close Conversation**

* **Command**: `closeConversation(conversationId, reason)`
* **Flow**: Transition to `Closed`, clear timers.
* **Acceptance Criteria**:

  * No further outbound messages allowed once closed.

---

# 2) Fulfillment (Scheduling + Calendar) Context

### Aggregates

**Reservation (AR)**

* **Identity**: `(tenantId, reservationId)`
* **Invariants**:

  1. Holds exactly **one slot** `(resourceId, start, end)`.
  2. **TTL** enforced; auto-expires at `expiresAt` if not confirmed.

**Appointment (AR)**

* **Identity**: `(tenantId, appointmentId)`
* **Invariants**:

  1. **No double-booking** for `(resourceId, tstzrange(start,end))` using DB constraint `EXCLUDE USING GIST`.
  2. If created from a Reservation, the Reservation must be `Active` and is consumed atomically.
  3. Must have **externalSyncStatus** `PENDING|SYNCED|FAILED`.

**Availability (Projection)**

* **Materialized view** derived from existing appointments + business rules; read-only to other contexts.

* **Consistency rules**: All writes (Reservation/Appointment) are strongly consistent inside Fulfillment. Calendar sync happens **after commit**; failures do not violate invariants (we can be booked locally even if provider is temporarily down).

### Domain Events (in-process)

| Event                           | When emitted                             | Producer    | Consumers                                         |
| ------------------------------- | ---------------------------------------- | ----------- | ------------------------------------------------- |
| `SlotsProjected`                | On request, after computing availability | Fulfillment | Conversation (to propose options)                 |
| `ReservationCreated`            | After reserving a slot                   | Fulfillment | Conversation (to show hold + countdown)           |
| `ReservationExpired`            | TTL elapsed / manual release             | Fulfillment | Conversation (to refresh options)                 |
| `AppointmentBooked`             | Appointment persisted                    | Fulfillment | Conversation (confirmation), Analytics (optional) |
| `ExternalCalendarSyncSucceeded` | After provider accepts                   | Fulfillment | None (internal state update)                      |
| `ExternalCalendarSyncFailed`    | After provider rejects/fails             | Fulfillment | Conversation (optional notify)                    |

**Event Schemas (JSON, v1)**
*All events support an optional `correlationId` that is **propagated unchanged end-to-end** when present.*

```json
{
  "SlotsProjected": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "requestId": "uuid",
    "criteria": {
      "serviceId": "uuid",
      "windowStart": "ISO-8601 UTC (Z)",
      "windowEnd": "ISO-8601 UTC (Z)",
      "locationId": "uuid|null"
    },
    "slots": [
      {"resourceId": "uuid", "start": "ISO-8601 UTC (Z)", "end": "ISO-8601 UTC (Z)"}
    ],
    "generatedAt": "ISO-8601 UTC (Z)"
  },
  "ReservationCreated": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "reservationId": "uuid",
    "slot": {"resourceId": "uuid", "start": "ISO-8601 UTC (Z)", "end": "ISO-8601 UTC (Z)"},
    "expiresAt": "ISO-8601 UTC (Z)"
  },
  "ReservationExpired": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "reservationId": "uuid"
  },
  "AppointmentBooked": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "appointmentId": "uuid",
    "slot": {"resourceId": "uuid", "start": "ISO-8601 UTC (Z)", "end": "ISO-8601 UTC (Z)"},
    "externalRefs": [{"provider": "google|jobber", "id": "string"}]
  },
  "ExternalCalendarSyncSucceeded": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "appointmentId": "uuid",
    "provider": "string",
    "providerRef": "string"
  },
  "ExternalCalendarSyncFailed": {
    "v": 1,
    "tenantId": "uuid",
    "correlationId": "string",
    "appointmentId": "uuid",
    "provider": "string",
    "error": "string"
  }
}
```

### Key Use Cases / Commands

**UC-5: Project Availability**

* **Query**: `projectAvailability(criteria)`
* **Flow**: Compute from appointments + business hours; return top N slots.
* **Acceptance Criteria**:

  * Response ≤ 300ms for typical criteria (in-memory/materialized read).
  * Returned slots do not intersect existing `appointments`.

**UC-6: Create Reservation**

* **Command**: `createReservation(slot)`
* **Flow**: Validate slot is still free → insert Reservation with `expiresAt(now+X)`.
* **Acceptance Criteria**:

  * Reservation visible to `projectAvailability` (hidden from list or marked `HELD`).
  * TTL expiry flips to `ReservationExpired` without manual cleanup.

**UC-7: Confirm Appointment**

* **Command**: `confirmAppointment(reservationId)`
* **Flow**: Atomically consume Reservation and insert Appointment (DB constraint prevents overlap) → enqueue calendar sync.
* **Acceptance Criteria**:

  * Two concurrent confirmations for overlapping slots: **exactly one** succeeds.
  * On provider sync failure, Appointment remains with `externalSyncStatus=FAILED` and retry policy; user is informed but booking stands.

**UC-8: Sync to Calendar Provider**

* **Command**: `syncAppointment(appointmentId)` (internal)
* **Flow**: Call provider API; map fields; set status.
* **Acceptance Criteria**:

  * Idempotent by `(tenantId, appointmentId, provider)`.
  * Retries with backoff on transient errors.

---

## Command/Query Responsibilities (cross-context)

* **Conversation → Fulfillment (commands)**: `createReservation`, `confirmAppointment`.
* **Conversation ← Fulfillment (queries)**: `projectAvailability` (read-optimized).
* **No shared tables**; each context uses its schema and repositories. No cross-schema joins.

---

## Acceptance Criteria Summary (SLIs/SLOs)

* **Auto-SMS**: P95 ≤ 5s from `MissedCallDetected` to CPaaSRef POST; P99 ≤ 8s.
* **Booking integrity**: 0% double-booking due to DB exclusion constraint.
* **Availability freshness**: ≤ 1s staleness tolerance after appointment creation or expiry.
* **CPaaSRef idempotency**: duplicate webhook deliveries produce no duplicate messages or state transitions.
* **Conversation uniqueness**: at most **one open conversation per tenant+caller**, enforced by a **partial unique index**.

---

## Minimal Data Model Hints (DDL sketches)

```sql
-- Fulfillment: prevent overlap
create extension if not exists btree_gist;
create table fulfillment.appointments (
  tenant_id uuid not null,
  appointment_id uuid primary key,
  resource_id uuid not null,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  external_sync_status text not null default 'PENDING',
  exclude using gist (
    tenant_id with =,
    resource_id with =,
    tstzrange(starts_at, ends_at, '[)') with &&
  )
);

create table fulfillment.reservations (
  tenant_id uuid not null,
  reservation_id uuid primary key,
  resource_id uuid not null,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  expires_at timestamptz not null
);

-- Conversation
create table conversation.conversations (
  tenant_id uuid not null,
  conversation_id uuid primary key,
  caller_e164 text not null,
  state text not null,
  opened_at timestamptz not null
);

-- Enforce: one open conversation per (tenant, caller)
create unique index conversation_uniq_open_per_caller
  on conversation.conversations (tenant_id, caller_e164)
  where state <> 'Closed';
```
