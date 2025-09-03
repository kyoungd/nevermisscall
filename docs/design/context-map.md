# Minimal Context Map v0.2 — Small Project

**Goal**: Ship value with the least moving parts. Modular monolith with **2 contexts** and **one process**. No service mesh, no Kafka. We keep boundaries in code and DB schemas so we can split later without regret.

**Date**: 2025-09-02

---

## Visual (Mermaid)

```mermaid
flowchart LR
  subgraph EXT[External]
    CARRIER[(Telephony Carrier/PBX)]
    CPaaSRef[(SMS Aggregator/CPaaSRef)]
    GOOGLE[(Google Calendar)]
    JOBBER[(Jobber API)]
  end

  subgraph APP[Modular Monolith]
    subgraph CC[Conversation & Comms (Conversations + Quote)]
      CC_CORE[Conversation & Comms Core]
      COMMS[Comms Adapter (Telephony/SMS)]
    end
    subgraph FULF[Fulfillment Core (Scheduling + Booking)]
      FULF_CORE[Fulfillment Core]
      INTEG[Integrations Adapter (Calendar)]
    end
  end

  %% External intake
  CARRIER -->|Webhook: missed call| COMMS

  %% Conversation loop
  CC -.->|sendSMS| COMMS
  COMMS -->|inbound SMS / delivery| CC

  %% Quote & offers (in-process reads)
  CC -->|Request slots & hold| FULF
  FULF -->|Slots/Quote projections| CC

  %% Calendar sync
  FULF -->|Sync appointment| INTEG
  INTEG -->|ACL| GOOGLE
  INTEG -->|ACL| JOBBER

  %% CPaaSRef
  COMMS -->|Conformist| CPaaSRef
```

**Legend**:

* *Conformist*: we adapt to vendor models (no illusion of control)
* *ACL*: Anti-corruption Layer (we translate vendors to our language)
* Dashed arrows = synchronous in-process calls; solid arrows = webhooks/API calls

---

## Contexts (smallest viable set)

### 1) Conversation & Comms (Conversations + Quote)

**Purpose**: Own the conversation state machine and the ≤5s auto-SMS promise. Compute quotes using local rules/read-models.
**Owns**: `Conversation`, `Message`, `MessagingEndpoint`, `Policy Snapshot`, `Quote` (read model).
**APIs (internal)**: `sendAutoReply(call)`, `handleInboundSms(msg)`, `proposeOptions(criteria)`.
**Integration**: Calls **Comms Adapter** for SMS. Reads **Fulfillment** projections; issues `createReservation()` and `confirmAppointment()` commands.

### 2) Fulfillment Core (Scheduling + Booking)

**Purpose**: Availability projection, short-lived reservations, booking, and calendar sync requests.
**Owns**: `Availability`, `Reservation(TTL)`, `Appointment`.
**APIs**: `projectAvailability(criteria)`, `createReservation(slot)`, `confirmAppointment(reservationId)`.
**Integration**: Calls **Integrations Adapter** to push to Google/Jobber. Provides read models to **Conversation & Comms**.

### Adapter: Comms (Telephony/SMS)

**Purpose**: Single adapter to the CPaaSRef and telephony webhooks. Centralize rate limiting. **Compliance decisions are enforced by `MessagingEndpoint` in the domain; the adapter records deliveries & signatures.**
**Persists**: `MessageDelivery` (idempotent send records, delivery receipts), webhook envelopes.
**APIs**: `sendSms(clientMessageId, to, body) → messageId` (idempotent). Webhook handlers for missed calls & inbound SMS.
**Integration**: Conformist to CPaaSRef; forwards inbound events to **Conversation & Comms**.

### (Internal Adapter) Integrations (Calendar)

**Purpose**: Normalize Google/Jobber behaviors; isolate failures.
**Persists**: `ProviderConnection`, `SyncJob`, mapping tables.
**Integration**: ACL to vendors.

> **Deferred**: Separate Identity/Tenancy and Analytics contexts. For now, tenant context is a library + table; analytics is off the hot path via append-only event log.

---

## Integration Patterns (minimal)

* **In-process domain events** inside the monolith (no external broker). Outbox only if/when we add async consumers.
* **Open Host Service** only at the edges: Comms webhook endpoints and (optionally) a thin public API for booking.
* **ACL** solely for calendar vendors. Everything else talks native domain.

---

## Data Boundaries (single DB, separate schemas)

* `conversation.*` — conversations, messages, **messaging\_endpoints**, **message\_deliveries**, quotes (read models)
* `fulfillment.*` — availability, reservations, appointments, **provider\_connections**, **sync\_jobs**

**Rule**: No cross-schema joins from application code; repositories only. Enforced via lints/tests.

**Double-booking guard (simple)**: Postgres `EXCLUDE USING GIST (tenant_id WITH =, resource_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)`.

---

## Team Ownership (small project)

* **One team** owns the monolith. Clear code ownership per module:

  * Conversation & Comms: Feature PM + 1 dev
  * Adapters (Comms/Integrations): 1 dev
  * Fulfillment: 1 dev

> When the team grows, split by context: (1) Conversation & Comms, (2) Fulfillment, (3) Adapters.

---

## Operational Minimalism

* **SLI**: P95 auto-SMS ≤ 5s (call end → SMS POST). Keep hot path: Carrier → **Comms Adapter** → **Conversation & Comms** → **Comms Adapter** → CPaaSRef.
* **Resilience**: Library-level retries/timeouts; no mesh. Idempotency keys for SMS send & booking.
* **Observability**: One tracer; correlationId on every call; 3 dashboards (auto-SMS latency, booking success rate, delivery failures).

---

## Not Now (explicitly out)

* No microservices / service mesh
* No Kafka / event bus
* No complex IAM; tenant context via simple `tenant_id`
* No custom analytics pipeline; append events to a table for later ETL

---

## Split Triggers (when to increase complexity)

* CPaaSRef throughput/compliance becomes a bottleneck → split **Comms Adapter**.
* Calendar sync errors/backlog impact bookings → split **Integrations Adapter**.
* Conversation experiments cause deploy friction → split **Conversation & Comms**.

## Conversation & Comms (incl. Comms adapter)” and “Fulfillment (incl. Integrations adapter)”.
