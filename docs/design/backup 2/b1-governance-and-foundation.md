# Architecture Decision Records (ADRs) — NeverMissCall MVP

**Date:** 2025-09-01 • **Owner:** Engineering • **Status:** Accepted

> These ADRs are the single source of truth for foundational decisions. Product or code that contradicts an ADR is wrong.

---

## ADR-0001: Tenant Model

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** SaaS MVP for ≤5,000 tenants. Each customer is exactly one business. We need isolation without operational overhead.
* **Decision:** Use a **single Postgres cluster**. All domain tables carry a **`tenant_id` column** (UUID). “Business” is a domain record 1:1 with tenant; engineering uses `tenant_id` everywhere. All unique constraints include `tenant_id`.
* **Consequences:** Simple migrations and joins; easy cross-module transactions. Must enforce tenant scoping in every query and index; risk of noisy neighbors if queries go rogue.
* **Alternatives:** Schema-per-tenant (more isolation, more ops), database-per-tenant (overkill).
* **References:** software-design-overview\.md §2, software-design-database.md §1–3.

---

## ADR-0002: Data Protection Posture (MVP)

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Auth and billing handled by third parties (Clerk, Stripe). We store phone numbers and SMS bodies (PII) but no payment secrets.
* **Decision:** **No field-level encryption** in MVP. Rely on Postgres **encryption-at-rest** and **TLS-in-transit**. PII minimization: only store what is needed for operations and KPIs. **Retention is governed centrally** (see *Glossary → Retention & Privacy*).
* **Consequences:** Lower complexity and latency. If requirements change (e.g., jurisdictional rules), we may add column-level crypto later. Keep types as `text` to permit future encryption.
* **Alternatives:** Application-layer crypto (higher complexity), KMS envelope encryption per field.
* **References:** software-design-overview\.md §2, security-and-compliance.md.

---

## ADR-0003: Outbox & Async Messaging

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Cross-module effects and projections require async notifications without introducing a broker now.
* **Decision:** Implement a **DB-backed Outbox** table with a background dispatcher (at-least-once). Worker selects with `FOR UPDATE SKIP LOCKED`, batch=100, concurrency=2.
* **Consequences:** Duplicate deliveries are possible; **consumers must be idempotent**. Operations are transparent and queryable. Adds a worker process.
* **Alternatives:** External broker (SQS/Kafka) — heavier ops now, easier scale later.
* **References:** software-design-overview\.md §3, software-design-database.md §2.7.

---

## ADR-0004: Event Versioning Policy

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Events evolve. We need stable contracts.
* **Decision:** Each event uses an envelope with `schema_version` (semantic). **Minor** = backward compatible additive changes; **major** = breaking (new name or side-by-side consumer). Payloads documented in `Event Catalog (this document)`.
* **Consequences:** Producers can add fields without breaking consumers. Breaking changes require dual-publishing or migration plan.
* **Alternatives:** No explicit versioning (guaranteed drift and breakage), timestamp-based versions.
* **References:** software-design-overview\.md §7, Event Catalog (this document).

---

## ADR-0005: Scheduling Strategy (Sync Sources)

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Need accurate availability vs Google/Jobber without hard dependency on webhooks.
* **Decision:** **Webhook-first** for calendar updates; **poll fallback** (Google 60s, Jobber 120s). Maintain `sched_ext_busy` shadow table.
* **Consequences:** Timely updates when webhooks work; eventual consistency bounded by poll intervals when they fail.
* **Alternatives:** Poll-only (slow), webhook-only (fragile).
* **References:** software-design-scheduling.md §5, software-design-database.md §6.

---

## ADR-0006: Scheduling Consistency (No Double-Booking)

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Preventing overlaps is critical and must be enforced in the database.
* **Decision:** Use Postgres **GiST exclusion constraint** on `(resource_id WITH =, timeslot WITH &&)` for `sched_appointments`. Booking is a single transaction: validate hold → insert appointment → delete hold → emit outbox.
* **Consequences:** Strong consistency with minimal app logic; requires `btree_gist` extension.
* **Alternatives:** Advisory locks (process-sided), app-level checks (race-prone).
* **References:** software-design-scheduling.md §6, software-design-database.md §2.3.

---

## ADR-0007: Webhook Idempotency (All Providers)

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Twilio/Stripe/Google/Jobber can deliver duplicate or out-of-order webhooks.
* **Decision:** Single table `webhook_events(provider, event_id, received_at, payload_hash)` with `UNIQUE(provider, event_id)` and **90-day** retention.
* **Consequences:** Simple dedupe across providers; easy auditing. Adds storage overhead (bounded by retention).
* **Alternatives:** Provider-specific tables; cache-based dedupe (volatile).
* **References:** software-design-database.md §2.7, integration-specs.md.

---

## ADR-0008: Retry & Backoff Policy

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** External calls fail transiently.
* **Decision:** **Exponential backoff with full jitter**: `delay = random(0, min(30s, 1s * 2^attempt))`, `max_attempts=6`; failures logged; DLQ = error row with last error.
* **Consequences:** Reduced thundering herd; bounded retry time. Some operations may remain failed and require manual intervention.
* **Alternatives:** Fixed intervals (worse congestion), no retries (worse UX).
* **References:** software-design-overview\.md §5, operational-runbook.md.

---

## ADR-0009: SLOs & Measurements

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Product promise requires a fast first response and snappy bookings.
* **Decision:** Primary SLO: **P95 ≤ 5s** from **Twilio inbound webhook** to **Twilio outbound “queued”** for the first SMS. Secondary: **Booking API P95 ≤ 500ms** (excluding third-party). Metrics and tracing are mandatory.
* **Consequences:** Engineering must budget latency per step; tests and dashboards enforce these budgets.
* **Alternatives:** Weaker SLOs (worse UX).
* **References:** software-design-overview\.md §8, observability.md.

---

## ADR-0010: Access & Authorization

* **Status:** Accepted • **Date:** 2025-09-01
* **Context:** Small teams, minimal roles.
* **Decision:** Roles: **OWNER**, **TECH** only. Authn via **Clerk JWT**. **No API keys** in MVP. All requests must be tenant-scoped; RBAC middleware enforces role checks.
* **Consequences:** Simple model that meets current needs. Future agent role/API keys can be added via new ADRs.
* **Alternatives:** Fine-grained permissions (overkill), API keys now (unnecessary surface).
* **References:** software-design-overview\.md §9, software-design-identity.md.





```markdown
# Glossary — NeverMissCall (MVP)

> Canonical, unambiguous terms used across product and engineering. If code or docs conflict with this glossary, the glossary wins.

---

## Core Entities

* **Tenant** — A customer account in our SaaS. One tenant = one business. Primary scope key in DB (`tenant_id`).
* **Business** — Domain synonym for Tenant; 1:1 mapping. Engineering uses `tenant_id` everywhere.
* **Caller / Customer** — The person contacting the tenant via phone/SMS (identified by **E.164** phone number).
* **Conversation** — A thread of messages with a caller. States: `open` (AI-controlled), `human` (tenant operator has taken over via **HumanTakeoverRequested**), `closed` (finished), `blocked` (compliance or opt-out).
* **Message** — One SMS unit in or out. Attributes: `direction` (`in`|`out`), outbound statuses: `queued`, `sent`, `delivered`, `failed`.
* **Participant** — Actor in a conversation: `caller` or `tenant` (human or AI).

## Catalog & Scheduling

* **Service Item** — Bookable job with `name`, **Duration**, and **Money** (price). Must be `active` to quote.
* **Catalog** — Per-tenant collection of Service Items plus optional aliases used for matching.
* **Resource** — A calendar-owning worker/team that can be booked.
* **Resource Calendar** — Calendar associated with a Resource (Google/Jobber/internal).
* **Hold** — Temporary reservation of a **Timeslot** for a Resource; expires after **Hold TTL**.
* **Appointment** — Confirmed booking occupying a Timeslot for a Resource.
* **Timeslot** — A `tstzrange` (UTC) representing `[start, end)`.
* **External Busy (Shadow)** — Denormalized busy blocks from Google/Jobber stored in a local **shadow table**.

## Compliance & Identity

* **10DLC** — US A2P messaging registration regime (brand/campaign/number).
* **Brand** — Legal/business identity used for 10DLC registration.
* **Campaign** — Messaging use-case registration. Status: `pending`, `approved`, `rejected`. Outbound SMS is blocked unless `campaign=approved` (hard compliance gate).
* **Opt-out** — STOP from a caller; we block future messages and log in `comp_opt_outs`.
* **OWNER / TECH** — RBAC roles. OWNER manages users/billing/compliance; TECH operates conversations/scheduling.
* **JWT** — Auth token issued by Clerk for app users; verified on every request.
* **Feature Gates** — Access control flags determined by subscription state. Identity module enforces gates based on Billing’s `SubscriptionUpdated` events.

## Telephony & Integrations

* **E.164** — International phone number format (e.g., `+13105551212`).
* **Provider Ref** — External identifier (Twilio `MessageSid`/`CallSid`, Stripe `event.id`, etc.). Present in events where the provider is source of truth (telephony, billing, calendar).
* **Webhook** — Provider → NMC HTTP callback. All webhooks are idempotent and signature-verified where supported.
* **Idempotency** — Handling the same event multiple times safely (via `webhook_events` or client keys).
* **Outbound (queued)** — Twilio accepted the send request and queued the SMS; used in the first-response SLO.

## Events & Consistency

* **Domain Event** — Immutable fact, published via DB Outbox. Namespaced `nmc.<domain>.<EventName>`.
* **Event Envelope** — Standard wrapper: `event_id`, `event_name`, `schema_version`, `tenant_id`, `occurred_at`, `correlation_id`, `causation_id`, `payload`.
* **Outbox** — DB table for async event delivery. Worker dispatches with at-least-once semantics. **Not infra plumbing** — this is the backbone of cross-module contracts.
* **Dead Letter Queue (DLQ)** — Canonical store for events that failed to dispatch after max retries. DLQ entries retain full envelope and last error; **consumers must still respect Event Catalog schemas**.

## Scheduling Guarantees

* **No Double-Booking** — Enforced by Postgres `EXCLUDE USING gist (resource_id WITH =, timeslot WITH &&)`.
* **Hold TTL** — Default 15 minutes before a hold expires automatically.

## Performance & SLO

* **SLA vs SLO** — SLA: contractual promise (we do **not** publish one). SLO: internal target. Primary SLO is **P95 ≤ 5s** first SMS.
* **P95** — 95th percentile latency (95% of requests are at or faster than this time).

## Ops & Resilience

* **Outbox Dispatcher** — Worker that drains `outbox_events` with `FOR UPDATE SKIP LOCKED`. Ops monitors lag/health, but events remain **domain contracts**.
* **Polling vs Webhook** — Fallback strategy: webhook-first; poll on provider failure.
* **Backoff with Jitter** — Retry delay: `random(0, min(30s, 1s*2^attempt))`, attempts ≤ 6.
* **DLQ (Dead-Letter Queue)** — *See Events & Consistency → Dead Letter Queue (DLQ)*.
* **Shadow Table** — Local mirror of external state (e.g., external busy blocks) used in availability computation.
* **DR** — Disaster Recovery procedures (backups, restores, cutovers).
* **RPO / RTO** — Recovery Point/Time Objectives. MVP target: RPO ≤ 15m, RTO ≤ 2h.
* **PITR** — Point-in-Time Recovery for Postgres.

## Data Types & Constraints

* **Money** — `{ amount_cents:int, currency:char(3) }` (MVP currency = USD).
* **Duration** — Minutes (int). Upper bound 480 in MVP.
* **GiST** — Generalized Search Tree index type enabling range exclusion for overlaps.
* **tstzrange** — Postgres range type for UTC timestamp intervals.

## Retention & Privacy

* **PII** — Personally Identifiable Information (phone numbers, message bodies). Stored without field-level encryption in MVP; protected by at-rest encryption and TLS.
* **Retention** — Messages 180 days; metadata 13 months; webhook dedupe 90 days; outbox 30 days after dispatch.

## Naming Conventions

* **Event names** — `nmc.<domain>.<EventName>` (e.g., `nmc.scheduling.AppointmentBooked`).
* **Tables** — Prefixed by module: `conv_*`, `sched_*`, `catalog_*`, `id_*`, `comp_*`, `bill_*`, `rep_*`.
* **Env vars** — Upper snake case: `OUTBOX_BATCH_SIZE`, `HOLD_TTL_MINUTES`.
* **IDs** — UUIDs unless provider requires strings.

---

# Notes

NeverMissCall is intentionally a **modular monolith** at MVP scale (≤5,000 tenants, ≤100 concurrent). Modules are isolated in code but share a single Postgres schema. Design favors clarity and future extraction over premature distribution. Eventing is async but not real-time; Outbox + retry workers are acceptable at this scale. **Culturally enforced rule:** Event Catalog is the source of truth. Outbox rows are business facts, not infra jobs.
```





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

### 2.2 `nmc.conversation.Recorded`

* **When**: Any inbound or outbound message is persisted (content recorded).
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

### 2.3 `nmc.conversation.OutboundQueued`

* **When**: An outbound message is enqueued to the provider.
* **Producer**: Conversation
* **Consumers**: Reporting
* **Schema `1.0.0`**

```json
{
  "payload": {
    "message_id": "uuid",
    "conversation_id": "uuid"
  }
}
```

### 2.4 `nmc.conversation.DeliveryUpdated`

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

### 2.5 `nmc.conversation.HumanTakeoverRequested`

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
    "timeslot": "[2025-09-01T17:00:00Z,2025-09-01T19:00:00Z)",
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
    "timeslot": "[2025-09-01T17:00:00Z,2025-09-01T19:00:00Z)"
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
    "timeslot": "[2025-09-01T17:00:00Z,2025-09-01T19:00:00Z)",
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
    "plan": "standard",
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





# Software Design Overview — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering • **Scope:** MVP (≤ 5,000 tenants, ≤ 100 concurrent)

> Brutal summary: We are building a **DDD Modular Monolith** with crisp module seams, a single Postgres DB using a **`tenant_id` column** for multi-tenancy, and an **Outbox** for async events. First SMS response **P95 ≤ 5s** from Twilio webhook receipt to Twilio outbound "queued" status.

---

## 1) Architecture Rationale

### Why **Modular Monolith** (not microservices)

* Scale is small; strong ACID needs around booking and message state.
* Fewer deployables and simpler debugging versus distributed monolith risk.
* Clear DDD seams let us peel off services later (ingest, analytics) without chaos.

### Bounded Contexts → Modules (single repo)

1. **Telephony Ingestion** — Twilio webhooks, missed-call detection, caller normalization.
2. **Conversation & Messaging** — AI-led SMS threads, 60s human override, delivery callbacks.
3. **Job Catalog & Pricing** — Per-tenant catalog, duration + price rules.
4. **Scheduling & Availability** — Slot search, holds, bookings, calendar sync.
5. **Identity & Access** — Tenants, users, RBAC (OWNER/TECH).
6. **Compliance** — 10DLC tracking (manual in Phase 1), messaging gates.
7. **Billing** — Stripe subscription mirroring.
8. **Reporting (Basic)** — Projections for KPIs; no heavy analytics.

> Extraction candidates later: Telephony Ingestion, Compliance workflows, Analytics pipeline.

---

## 2) Tenancy & Data

* **Model:** single Postgres cluster; all domain tables carry **`tenant_id`**. One business per tenant.
* **PII stance:** rely on Postgres encryption-at-rest + TLS-in-transit. No field-level crypto in MVP.
* **Retention:** messages 180d; metadata 13m; webhook dedupe 90d; outbox events 30d after dispatch.
* **Naming:** tables prefixed by module (e.g., `conv_messages`, `sched_appointments`).

### Core Tables (overview)

* `conv_conversations`, `conv_messages`, `conv_participants`
* `catalog_service_items`
* `sched_calendars`, `sched_holds`, `sched_appointments`
* `id_users`, `id_role_assignments`, `id_tenants`
* `comp_campaigns`, `comp_phone_numbers`
* `bill_subscriptions`
* `rep_kpis_*` (denormalized)
* Infra: `outbox_events`, `webhook_events`

---

## 3) Consistency & Transactions

* **ACID within module writes** (same DB, same transaction).
* **Outbox pattern** for cross-module effects and projections (at-least-once). Fields: `id, tenant_id, event_name, schema_version, payload_json, created_at, available_at, attempts, last_error, dispatched_at`.
* **CQRS-lite**: transactional writes → async projections into read models for Reporting.
* Idempotency: per-provider IDs in `webhook_events` (unique `(provider, event_id)`).

---

## 4) Scheduling: Holds & No Double-Booking

* **Holds:** temporary reservation rows with TTL (default **15 minutes**). Expire via background job.
* **Booking transaction:** hold → confirm appointment atomically.
* **Constraint:** prevent overlaps per resource using Postgres exclusion constraint:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE sched_appointments (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  ...
);
CREATE INDEX ON sched_appointments USING gist (resource_id, timeslot);
ALTER TABLE sched_appointments
  ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (resource_id WITH =, timeslot WITH &&);
```

---

## 5) Integrations & Reliability

* **Providers:** Twilio (SMS/Voice), Google Calendar, Jobber, Stripe, Clerk.
* **Webhook idempotency:** `webhook_events(provider, event_id, received_at, payload_hash)` with `UNIQUE(provider, event_id)`; retain 90d.
* **Retries:** exponential backoff **with jitter**:

  * `delay = random(0, min(30s, 1s * 2^attempt))`, `max_attempts=6`; failures logged and visible via ops dashboard.
* **Calendar sync:** webhook-first; **poll fallback** (GCal 60s, Jobber 120s) to reconcile.

---

## 6) Domain Interfaces (high-level)

### Telephony Ingestion

* **Inbound:** `POST /webhooks/twilio/*` (voice status, missed call, SMS inbound)
* **Emits:** `CallDetected`, `InboundSmsReceived`

### Conversation & Messaging

* **Commands:** `POST /conversations/:id/messages`, `POST /conversations/:id/takeover`
* **Emits:** `ConversationStarted`, `OutboundQueued`, `HumanTakeoverRequested`

### Catalog & Pricing

* **Commands:** `GET/POST /catalog/items`, `POST /catalog/match`
* **Emits:** `CatalogUpdated`

### Scheduling

* **Commands:** `POST /scheduling/search`, `POST /scheduling/holds`, `POST /scheduling/book`
* **Emits:** `AppointmentHeld`, `AppointmentBooked`, `AppointmentReleased`, `AppointmentCancelled`

### Compliance / Billing / Identity

* Compliance: `POST /compliance/submit`, `GET /compliance/status`; emits `ComplianceStatusChanged`.
* Billing: Stripe webhooks `/webhooks/stripe`; emits `SubscriptionUpdated`.
* Identity: Clerk-authenticated endpoints; tenant-scoped.

---

## 7) Domain Events (canonical)

All events include: `event_id`, `tenant_id`, `occurred_at`, **`schema_version`**, `payload`.

| Event                     | Producer     | Consumers                   |
| ------------------------- | ------------ | --------------------------- |
| `CallDetected`            | Telephony    | Conversation, Reporting     |
| `InboundSmsReceived`      | Telephony    | Conversation                |
| `ConversationStarted`     | Conversation | Reporting                   |
| `DeliveryUpdated`         | Conversation | Reporting                   |
| `HumanTakeoverRequested`  | Conversation | Ops UI                      |
| `CatalogUpdated`          | Catalog      | Conversation, Reporting     |
| `AppointmentHeld`         | Scheduling   | Conversation                |
| `AppointmentBooked`       | Scheduling   | Reporting, Calendar Sync    |
| `AppointmentReleased`     | Scheduling   | Conversation                |
| `AppointmentCancelled`    | Scheduling   | Conversation, Reporting     |
| `ComplianceStatusChanged` | Compliance   | Conversation (gate sending) |
| `SubscriptionUpdated`     | Billing      | Identity/Feature Gates      |
| `OutboundQueued`          | Conversation | Conversation                |

Versioning policy: **semantic** — add fields → minor; remove/rename → major.

---

## 8) SLOs, Observability & Alerts

* **Primary SLO:** first SMS **P95 ≤ 5s** (Twilio inbound → Twilio outbound queued).
* **Secondary:** booking API **P95 ≤ 500ms** (excluding third-party latency).

**Key Metrics**

* `slo_first_sms_p95_seconds`
* `booking_post_p95_ms`
* `outbox_dispatch_lag_seconds`
* `webhook_dedupe_hits_total`
* `calendar_poll_conflicts_total` (poller reconciliation conflicts)

**Tracing**

* Propagate correlation IDs across: webhook → outbox write → handler → provider API call.

**Logging**

* Structured logs with `tenant_id`, `module`, `event_name`, `correlation_id`.

---

## 9) Security & Access

* **Roles:** `OWNER`, `TECH` only (RBAC middleware; tenant-scoped).
* **Authn:** Clerk (JWT). **No API keys** in MVP.
* **Messaging gates:** outbound SMS **blocked** until compliance status is approved.
* **Secrets:** platform-managed (e.g., Heroku config vars). No secrets in repo.

---

## 10) Deployment & Runtime

* **Runtime:** single app (FastAPI) + background workers (outbox dispatcher, schedulers).
* **Hosting:** managed PaaS (Heroku/Render) + managed Postgres; frontend on Netlify/Vercel.
* **Workers:** outbox batch=100, concurrency=2 per dyno; pollers for calendars per tenant.
* **Migrations:** per-module namespaces; zero-downtime strategy.

---

## 11) Risks & Mitigations

* **Provider flakiness** → retries w/ jitter, DLQ table, ops dashboard.
* **Calendar drift** → webhook+poll reconciliation; holds TTL; conflict detection metric.
* **Scope creep** → basic reporting only; analytics deferred.
* **Cross-module coupling** → contract tests; no cross-module SQL; all cross-effects via events.

---

## 12) References (canonical ADRs)

* ADR-0001 Tenant Model — `tenant_id` column; 1 business per tenant.
* ADR-0002 Data Protection — no field-level crypto in MVP; rely on at-rest/TLS.
* ADR-0003 Outbox & Async — DB outbox + dispatcher; at-least-once.
* ADR-0004 Event Versioning — semantic `schema_version` policy.
* ADR-0005 Scheduling Strategy — webhook-first; poll fallback; holds TTL 15m.
* ADR-0006 Scheduling Consistency — PG `EXCLUDE` constraint.
* ADR-0007 Webhook Idempotency — unified `webhook_events` table, 90d retention.
* ADR-0008 Retry Policy — exponential backoff with jitter.
* ADR-0009 SLOs — P95 ≤ 5s first-SMS; booking P95 ≤ 500ms.
* ADR-0010 Access & AuthZ — roles OWNER/TECH; no API keys.





# Software Design — Database (NeverMissCall MVP)

## 0) Table Ownership Map (canonical)
+
+| Module        | Tables (prefix)                                         | Notes |
+|---------------|----------------------------------------------------------|-------|
+| Conversation  | `conv_*`                                                | Outbound gating depends on Compliance status |
+| Telephony     | `tel_*`, `webhook_events`                                | `webhook_events` is shared infra but **owned** by Telephony for ingestion flows (ADR-0007) |
+| Scheduling    | `sched_*`                                                | GiST exclusion on `sched_appointments` (ADR-0006) |
+| Catalog       | `catalog_*`                                              | Price/duration source of truth |
+| Compliance    | `comp_*`                                                 | Number ↔ tenant mapping; opt-out ledger |
+| Billing       | `bill_*`                                                 | Stripe mirror; emits `SubscriptionUpdated` |
+| Reporting     | `rep_*`                                                  | Read models only; fed by Outbox |

**Status:** Accepted • **Audience:** Engineering • **Scope:** MVP (≤ 5,000 tenants, ≤ 100 concurrent)

> Brutal summary: Single Postgres cluster. All rows carry **`tenant_id`** (UUID). ACID inside the app. **No field-level encryption** in MVP (rely on at-rest + TLS). **Outbox** and **Webhook Dedupe** live in DB. Booking consistency enforced with a **GiST exclusion constraint**.

---

## 1) Conventions

* **Timezone:** store timestamps as `timestamptz` (UTC). Convert at UI edges.
* **Tenant scoping:** every domain table includes `tenant_id UUID NOT NULL`. All unique constraints must include `tenant_id`.
* **Naming:** module prefixes — `conv_*`, `sched_*`, `catalog_*`, `id_*`, `comp_*`, `bill_*`, `rep_*`.
* **Soft deletes:** none in MVP. Use archival/retention policies instead.
* **Extensions:** `btree_gist`, `pgcrypto` (for UUID gen only, not crypto), `uuid-ossp` optional if preferred.

---

## 2) Core Tables (DDL excerpts)

### 2.1 Conversation

```sql
CREATE TABLE conv_conversations (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  caller_phone text NOT NULL,
  state text NOT NULL CHECK (state IN ('open','human','closed')),
  opened_at timestamptz NOT NULL DEFAULT now(),
  closed_at timestamptz,
  UNIQUE (tenant_id, caller_phone, state) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TABLE conv_messages (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  conversation_id uuid NOT NULL REFERENCES conv_conversations(id) ON DELETE CASCADE,
  direction text NOT NULL CHECK (direction IN ('in','out')),
  body text NOT NULL,
  provider_message_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  client_dedup_key text,
  UNIQUE (tenant_id, client_dedup_key)
);

CREATE INDEX conv_msgs_conv_idx ON conv_messages(conversation_id);
CREATE INDEX conv_msgs_tenant_created_idx ON conv_messages(tenant_id, created_at DESC);
```

### 2.2 Job Catalog & Pricing (aligned with product-specification.md)

```sql
-- Base job definitions per tenant
CREATE TABLE catalog_jobs (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  title text NOT NULL,
  short_description text,
  base_duration_min int NOT NULL CHECK (base_duration_min > 0 AND base_duration_min <= 8*60),
  base_price_cents int NOT NULL CHECK (base_price_cents >= 0),
  currency char(3) NOT NULL DEFAULT 'USD',
  active boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, title)
);

-- Job variants (additional options)
CREATE TABLE catalog_job_variants (
  id uuid PRIMARY KEY,
  job_id uuid NOT NULL REFERENCES catalog_jobs(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  addl_duration_min int NOT NULL DEFAULT 0,
  addl_price_cents int NOT NULL DEFAULT 0,
  UNIQUE (job_id, name)
);

-- Job add-ons (additional services)
CREATE TABLE catalog_job_addons (
  id uuid PRIMARY KEY,
  job_id uuid NOT NULL REFERENCES catalog_jobs(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  duration_delta_min int NOT NULL DEFAULT 0,
  price_delta_cents int NOT NULL DEFAULT 0,
  UNIQUE (job_id, name)
);
```

### 2.3 Scheduling (Appointments & Holds)

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE sched_calendars (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,            -- e.g., technician or shared team calendar
  provider text NOT NULL CHECK (provider IN ('google','jobber','internal')),
  provider_ref text NOT NULL,           -- calendar id, etc.
  active boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, provider, provider_ref)
);

CREATE TABLE sched_holds (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  created_by uuid, -- user id optional
  CHECK (lower(timeslot) < upper(timeslot))
);
CREATE INDEX sched_holds_resource_idx ON sched_holds(resource_id, expires_at);
CREATE INDEX sched_holds_timeslot_idx ON sched_holds USING gist (resource_id, timeslot);

CREATE TABLE sched_appointments (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  job_id uuid REFERENCES catalog_jobs(id),
  customer_phone text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  CHECK (lower(timeslot) < upper(timeslot))
);
CREATE INDEX sched_appt_resource_idx ON sched_appointments(resource_id);
CREATE INDEX sched_appt_timeslot_idx ON sched_appointments USING gist (resource_id, timeslot);
ALTER TABLE sched_appointments
  ADD CONSTRAINT sched_no_overlap
  EXCLUDE USING gist (resource_id WITH =, timeslot WITH &&);
```

**Hold TTL:** default 15 minutes enforced by worker that deletes expired holds.

**Booking transaction (pseudo-SQL):**

```sql
BEGIN;
  -- ensure hold exists and not expired
  SELECT 1 FROM sched_holds
   WHERE id = :hold_id AND expires_at > now() AND tenant_id = :tenant_id
   FOR UPDATE;

  -- create appointment (constraint guarantees no overlap)
  INSERT INTO sched_appointments(id, tenant_id, resource_id, timeslot, job_id, customer_phone)
  VALUES (:id, :tenant_id, :resource_id, :timeslot, :job_id, :phone);

  -- delete hold
  DELETE FROM sched_holds WHERE id = :hold_id;

  -- write outbox event
  INSERT INTO outbox_events(...);
COMMIT;
```

### 2.4 Identity & Access

```sql
CREATE TABLE id_tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE id_users (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  email text NOT NULL,
  role text NOT NULL CHECK (role IN ('OWNER','TECH')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
```

### 2.5 Compliance (Manual 10DLC)

```sql
CREATE TABLE comp_campaigns (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('pending','approved','rejected')),
  provider_ref text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE comp_phone_numbers (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  e164 text NOT NULL,
  campaign_id uuid REFERENCES comp_campaigns(id),
  UNIQUE (tenant_id, e164)
);
```

### 2.6 Billing (Stripe Mirror)

```sql
CREATE TABLE bill_subscriptions (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  stripe_customer_id text NOT NULL,
  stripe_subscription_id text NOT NULL,
  plan text NOT NULL,
  status text NOT NULL CHECK (status IN ('active','past_due','canceled','trialing')),
  current_period_end timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, stripe_subscription_id)
);
```

### 2.7 Outbox & Webhook Dedupe

```sql
CREATE TABLE outbox_events (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  event_name text NOT NULL,
  schema_version text NOT NULL,
  payload_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  available_at timestamptz NOT NULL DEFAULT now(),
  attempts int NOT NULL DEFAULT 0,
  last_error text,
  dispatched_at timestamptz
);
CREATE INDEX outbox_available_idx ON outbox_events(available_at);

-- Idempotency for inbound webhooks from all providers
CREATE TABLE webhook_events (
  id bigserial PRIMARY KEY,
  provider text NOT NULL,       -- 'twilio','stripe','google','jobber'
  event_id text NOT NULL,       -- provider-specific unique id
  received_at timestamptz NOT NULL DEFAULT now(),
  payload_hash text NOT NULL,
  UNIQUE (provider, event_id)
);
```

**Dispatcher query (worker):**

```sql
SELECT id, tenant_id, event_name, schema_version, payload_json
FROM outbox_events
WHERE dispatched_at IS NULL AND available_at <= now()
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 100;
```

---

## 3) Indexing & Performance

* **Hot paths**

  * `conv_messages(tenant_id, created_at DESC)` for timeline queries.
  * `sched_appointments USING gist(resource_id, timeslot)` for overlaps.
  * `catalog_jobs(tenant_id, title)` for AI quoting.
* **Partial indexes** where applicable (e.g., `WHERE state='open'`).
* **Avoid LIKE** on phone numbers; store **E.164** and index exact match.

---

## 4) Retention & Archival

* `conv_messages`: **180 days** (hard delete via nightly job). Aggregate counts persisted to `rep_kpis_*` before deletion.
* Conversation metadata: **13 months**.
* `webhook_events`: **90 days** (delete old rows).
* `outbox_events`: delete **30 days** after `dispatched_at` IS NOT NULL.

---

## 5) Migrations Policy

* Tooling: Alembic (Python). One migration per PR per module when possible.
* Naming: `mod_<module>__<change>__YYYYMMDD.sql` (e.g., `mod_sched__add-holds__20250901.sql`).
* Zero-downtime rules: add columns with defaults **NULL**, backfill in code, then enforce constraints.
* Rollback: write down reversible steps; avoid destructive DDL in same deploy as code relying on it.

---

## 6) Data Integrity Rules (selected)

* All FKs must include `ON DELETE RESTRICT` or `CASCADE` intentionally (no defaults).
* All unique business keys include `tenant_id`.
* Check constraints for money/duration already defined (non-negative, bounded).
* Conversation single-active rule enforced at service layer (state machine), validated with partial unique if needed.

Example partial unique to prevent 2 open conversations per caller:

```sql
CREATE UNIQUE INDEX conv_single_open_per_caller
  ON conv_conversations(tenant_id, caller_phone)
  WHERE state = 'open';
```

---

## 7) Backup & DR

* Daily snapshot with 7-day point-in-time recovery (provider capability).
* Verify restores monthly in a staging environment.
* Store schema dumps of critical tables (`sched_*`, `conv_*`) for quick diff.

---

## 8) Example Queries

* **Find next available slots for 120 minutes:**

```sql
-- Simplified: fetch holds and appointments, compute gaps in app code
SELECT resource_id, timeslot FROM sched_appointments WHERE tenant_id = :t
UNION ALL
SELECT resource_id, timeslot FROM sched_holds WHERE tenant_id = :t AND expires_at > now();
```

* **Messages timeline for a caller:**

```sql
SELECT m.* FROM conv_messages m
JOIN conv_conversations c ON c.id = m.conversation_id
WHERE c.tenant_id = :t AND c.caller_phone = :phone
ORDER BY m.created_at DESC
LIMIT 200;
```

---

## 9) Future Considerations

* Table partitioning by month for `conv_messages` if volume grows.
* Materialized views for daily KPIs.
* Field-level encryption for PII if compliance demands change (keep columns `text` to ease later crypto).
