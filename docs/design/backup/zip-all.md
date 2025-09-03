# Combined Design Docs

---

## decisions-adr.md

\n```markdown
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
* **Decision:** **No field-level encryption** in MVP. Rely on Postgres **encryption-at-rest** and **TLS-in-transit**. PII minimization: only store what is needed for operations and KPIs.
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
* **Decision:** Each event uses an envelope with `schema_version` (semantic). **Minor** = backward compatible additive changes; **major** = breaking (new name or side-by-side consumer). Payloads documented in `event-catalog.md`.
* **Consequences:** Producers can add fields without breaking consumers. Breaking changes require dual-publishing or migration plan.
* **Alternatives:** No explicit versioning (guaranteed drift and breakage), timestamp-based versions.
* **References:** software-design-overview\.md §7, event-catalog.md.

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

```

---

## event-catalog.md

\n```markdown
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

```

---

## glossary.md

\n```markdown
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
* **Dead Letter Queue (DLQ)** — Table for events that failed to dispatch after retries.

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
* **DLQ (Dead-Letter Queue)** — Table or log holding events that repeatedly fail processing. DLQ entries must still respect **Event Catalog schemas**.
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

```

---

## integration-specs.md

\n```markdown
# Integration Specs — NeverMissCall MVP

**Status:** Accepted • **Audience:** Engineering • **Scope:** MVP integrations with Twilio, Google Calendar, Jobber, Stripe, Clerk

> Principles: smallest viable contracts, **idempotent webhooks**, **retry with jitter**, observable failure paths, and strict **tenant scoping**. When providers wobble, we remain useful via fallbacks.

---

## 0) Cross-cutting Conventions

* **HTTP timeouts:** connect 2s, total 10s. Retries for 5xx/429 per policy below.
* **Retry policy:** exponential backoff with **full jitter** — `delay = random(0, min(30s, 1s * 2^attempt))`, `max_attempts=6`.
* **Idempotency (webhooks):** table `webhook_events(provider, event_id, received_at, payload_hash)` with `UNIQUE(provider, event_id)`; retain 90d.
    Once persisted, webhook events are processed into **domain events** (Outbox rows).
    The Event Catalog defines the canonical shapes; Outbox dispatch ensures consistency.
* **Tenant scoping:** all outbound calls include or resolve to a tenant configuration; never call a provider without a `tenant_id` context.
* **Secrets:** injected as environment variables; no secrets in code or Git.
* **Observability (labels):** `provider`, `tenant_id`, `endpoint`, `status_code`, `attempt`.
    Include `event_name` when outbound flows emit domain events, so logs/traces can be tied back
    to the **Event Catalog**.

---

## 1) Twilio (SMS & Voice)

### 1.1 Auth & Base

* **Auth:** Basic (Account SID / Auth Token) via SDK or HTTP basic auth.
* **Config:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_MESSAGING_SERVICE_SID`.

### 1.2 Outbound SMS

* **Endpoint:** `POST /2010-04-01/Accounts/{AccountSid}/Messages.json`
* **Payload (example):**

```json
{ "MessagingServiceSid": "${TWILIO_MESSAGING_SERVICE_SID}", "To": "+13105551212", "Body": "Hi! We got your call. Can you describe the issue?", "StatusCallback": "https://api.nmc.app/webhooks/twilio/sms-status" }
```

* **Idempotency:** we generate `client_dedup_key` per outbound message; webhook delivery is deduped by MessageSid.
* **Timeouts/Retry:** follow cross-cutting policy for transient errors; no retry on 4xx.

### 1.3 SMS Inbound Webhook

* **Endpoint:** `POST /webhooks/twilio/sms-inbound`
* **Headers:** `X-Twilio-Signature` (verify against raw body + URL).
* **Idempotency key:** `(provider='twilio', event_id=<MessageSid>)`.
* **Shape (example form-encoded):**

```
From=+13105551212&To=+13105550000&Body=My sink is clogged&MessageSid=SMxxxxxxxx&MessagingServiceSid=MGxxxx
```

* **Behavior:** open/create conversation; append inbound; trigger AI pipeline if allowed.

### 1.4 SMS Status Callback Webhook

* **Endpoint:** `POST /webhooks/twilio/sms-status`
* **Headers:** `X-Twilio-Signature` (verify).
* **Idempotency key:** `(provider='twilio', event_id=<MessageSid:MessageStatus>)`.
* **Shape (example):** `MessageSid=SMxxxx&MessageStatus=queued|sent|delivered|failed&ErrorCode=...`
* **Behavior:** update `conv_messages.status`; emit `DeliveryUpdated` as a **domain event**.
    Event schema is governed by the Event Catalog; consumers may not query `conv_messages` directly.

### 1.5 Voice (Missed Call) — Detection

* **Webhook:** `POST /webhooks/twilio/voice-status`
* **Trigger statuses:** `no-answer`, `busy`, `failed` → emit `CallDetected` (tenant-scoped), then first SMS flow.
* **Headers:** `X-Twilio-Signature` (verify). Idempotency uses `(provider='twilio', event_id=<CallSid:CallStatus>)`.

### 1.6 Signature Verification (pseudocode)

```python
sig = request.headers["X-Twilio-Signature"]
valid = twilio.validate_signature(sig, full_url, raw_body)
if not valid: return 401
```

### 1.7 Rate Limits & Errors

* **429/5xx:** retry per policy with jitter. Log into `observability` with labels.
* **STOP/HELP:** handle keywords; mark opt-out; do not send further messages.

---

## 2) Google Calendar

### 2.1 Auth & Scopes

* **Auth:** OAuth2 (per tenant). Store refresh tokens server-side.
* **Scopes:** `https://www.googleapis.com/auth/calendar.readonly` (MVP).
* **Config:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, OAuth redirect URL.

### 2.2 Sync Strategy

* **Primary:** **Push notifications** (watch channels) where available.
* **Fallback:** **Poll** every **60s** per connected calendar.
* **Shadow table:** `sched_ext_busy` tracks external busy blocks for conflict checks.

### 2.3 Push Webhook

* **Endpoint:** `POST /webhooks/google/calendar`
* **Headers (verify presence):** `X-Goog-Channel-ID`, `X-Goog-Resource-ID`, `X-Goog-Resource-State`.
* **Idempotency key:** `(provider='google', event_id=<X-Goog-Resource-ID:seq>)` (use concatenation with a counter if exposed; else hash payload).
* **Behavior:** mark calendar dirty; enqueue sync job.

### 2.4 Poll Flow (fallback)

* Free/busy or events list within the window; upsert `sched_ext_busy` for each block.
* Metric: `calendar_poll_conflicts_total` when local appts collide with remote busy.

### 2.5 Errors & Limits

* **401/403:** revoke tokens and notify tenant to re-auth.
* **429/5xx:** retry with jitter; backoff caps at 30s.

---

## 3) Jobber

### 3.1 Auth

* **Auth:** Server-to-server token or OAuth (tenant-provided). Config as `JOBBER_API_TOKEN` or equivalent.

### 3.2 Sync Strategy

* **Primary:** Use Jobber webhooks if tenant grants them; otherwise **poll** every **120s**.
* **Behavior:** treat Jobber busy blocks like Google; upsert into `sched_ext_busy`.

### 3.3 Errors & Limits

* Same retry policy. On auth failures, disable sync for tenant and surface an actionable banner in UI.

---

## 4) Stripe (Billing)

### 4.1 Auth & Base

* **Auth:** Bearer — `STRIPE_SECRET_KEY`. Use official SDK.
* **Config:** `STRIPE_PRICE_ID_*`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PORTAL_CONFIG_ID` (if used).

### 4.2 Checkout & Portal

* **Create Checkout Session:** include `client_reference_id=tenant_id` and `success/cancel` URLs.
* **Customer Portal:** generate portal link; restrict to subscription management.
* **Idempotency:** set `Idempotency-Key` header for POSTs originating from the app.

### 4.3 Webhooks

* **Endpoint:** `POST /webhooks/stripe`
* **Headers:** `Stripe-Signature` (verify with secret).
* **Idempotency key:** `(provider='stripe', event_id=<event.id>)`.
* **Events consumed:** `customer.subscription.created|updated|deleted`, `invoice.payment_failed`.
* **Behavior:** mirror subscription state to `bill_subscriptions`, then emit `SubscriptionUpdated`.

### 4.4 Example Verify (pseudocode)

```python
payload = request.data
sig = request.headers['Stripe-Signature']
event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
```

---

## 5) Clerk (Authn)

### 5.1 Verification

* **Flow:** verify Clerk JWT on every request. Extract `tenant_id` and role (`OWNER`/`TECH`).
* **Failure:** 401 if invalid; 403 if role not authorized for endpoint.

### 5.2 Config

* `CLERK_JWT_ISSUER`, `CLERK_JWT_AUDIENCE`, `CLERK_JWKS_URL`.

---

## 6) Error Taxonomy (normalized)

* **IntegrationError** (4xx non-retryable): bad auth, validation.
* **IntegrationRetryable** (5xx/429): retry per jitter policy.
* **IntegrationTimeout**: treat as retryable unless exceeding max attempts.
* **IntegrationSignatureError**: 401 on webhook; do not process body.
* **IntegrationIdempotentDuplicate**: 200 early exit; record dedupe hit metric.

Map to HTTP responses for webhooks: always return **2xx** after we persist dedupe record; never leak internal failures back to providers.

---

## 7) Metrics & Dashboards

* `integration_http_requests_total{provider,endpoint,status}`
* `integration_http_latency_ms{provider,endpoint}` (p50/p95)
* `webhook_dedupe_hits_total{provider}`
* `webhook_signature_failures_total{provider}`
* `retry_attempts_total{provider}`

---

## 8) Security & Compliance

* TLS everywhere; only accept provider webhooks on HTTPS.
* Validate signatures for Twilio and Stripe; validate Google headers; require allow-listed IPs if feasible (secondary).
* Outbound SMS **gated** by Compliance status (10DLC approved) — Conversation module enforces.

---

## 9) Operational Playbook (per provider)

* **Twilio:** if outbound failures spike → pause sends (feature flag), inspect ErrorCode patterns, open support ticket with correlation IDs.
* **Google/Jobber:** if webhooks silent → system auto-switches to polling; alert if `calendar_sync_errors_total` exceeds threshold.
* **Stripe:** if webhook signature failures rise → rotate webhook secret and re-deploy; replay events from Stripe dashboard.
* **Clerk:** monitor auth failures; verify JWKS reachability.

```

---

## observability.md

\n```markdown
# Observability — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/Ops • **Scope:** Metrics, Logs, Traces for Modular Monolith + Workers

> Principle: **you can’t manage what you can’t see**. We standardize metric names, logging fields, and trace context so on‑call can diagnose issues quickly and our SLOs aren’t theater.

---

## 1) SLOs & Golden Signals

* **SLO‑1 (Primary):** **P95 ≤ 5s** from **Twilio inbound** (CallDetected/InboundSmsReceived) to **Twilio outbound ‘queued’** (first SMS).
* **SLO‑2:** **P95 ≤ 500ms** for Booking API (excluding third‑party latency).

**Golden Signals**: latency, traffic, errors, saturation.

---

## 2) Metrics (canonical names)

### 2.1 Request/Handler Latency

* `http_request_duration_ms{route,method,status}`
* `webhook_handler_duration_ms{provider,endpoint,status}`
* `scheduling_search_duration_ms`
* `scheduling_book_duration_ms`
* `ai_pipeline_duration_ms`

### 2.2 SLO-focused

* `slo_first_sms_p95_seconds` (computed from Reporting’s first-response tracker)
* `booking_post_p95_ms`

### 2.3 Outbox & Projectors

* `outbox_dispatch_lag_seconds` — now − oldest `created_at` pending
* `outbox_dispatch_attempts_total{event_name}`
* `outbox_dispatch_failures_total{event_name}`
* `reporting_projector_lag_seconds`
* `reporting_projection_errors_total{projector}`

### 2.4 Integrations

* `integration_http_requests_total{provider,endpoint,status}`
* `integration_http_latency_ms{provider,endpoint}`
* `webhook_dedupe_hits_total{provider}`
* `webhook_signature_failures_total{provider}`

### 2.5 Scheduling Health

* `scheduling_hold_success_total`
* `scheduling_hold_conflict_total`
* `scheduling_book_conflict_total`
* `calendar_sync_errors_total`

### 2.6 Business KPIs (from Reporting)

* `kpi_calls_detected_total`
* `kpi_conversations_started_total`
* `kpi_appointments_booked_total`
* `kpi_attributed_revenue_cents_total`

### 2.7 Saturation

* `db_connections_in_use`
* `worker_queue_depth` (outbox pending rows)
* `cpu_utilization_percent`, `memory_utilization_percent`

---

## 3) Logging (structured)

### 3.1 Required Fields

* `timestamp`, `level`, `module` (telephony|conversation|scheduling|catalog|compliance|billing|reporting|infra)
* `tenant_id`, `correlation_id`, `causation_id?`
* HTTP: `method`, `route`, `status`, `latency_ms`
* Webhooks: `provider`, `event_id`
* Outbox: `event_name`, `outbox_id`, `attempts`
* Errors: `error_code`, `error_message`, `stack` (only in DEBUG/TRACE)

### 3.2 Redaction Rules

* Do **not** log full message bodies by default. If needed for debugging, log first 50 chars behind a feature flag.
* Mask emails and phone numbers to last 4 digits in INFO level logs; full values only in DEBUG with ephemeral retention.

---

## 4) Tracing

* **Trace boundaries:** webhook → outbox write → consumer handler → provider API call.
* **Propagation:** use `correlation_id` as a trace attribute and attach `event_id` for spans touching events.
* **Span naming:** `webhook.twilio.sms_inbound`, `outbox.dispatch`, `conversation.first_reply`, `scheduling.book`, etc.
* **Sampling:** head sampling 10% in prod; **100% for errors**.

---

## 5) Dashboards (panels)

1. **SLO Overview** — P95 first SMS, call volume, error rate.
2. **Outbox Health** — lag seconds, attempts, failures by event.
3. **Webhook Health** — dedupe hits, signature failures, per‑provider latency.
4. **Scheduling** — holds created vs conflicts, booking P95, calendar sync errors.
5. **Twilio Delivery** — queued→sent→delivered funnel, failure codes.
6. **DB & Workers** — connections, CPU/mem, queue depth.

---

## 6) Alerts (initial)

* First SMS SLO breach: `slo_first_sms_p95_seconds > 5` for 10m.
* Outbox lag: `outbox_dispatch_lag_seconds > 60` for 10m.
* Webhook signatures failing: `webhook_signature_failures_total > 10/min` for 5m.
* Calendar sync errors: `calendar_sync_errors_total > 0` for 15m.
* DB saturation: `db_connections_in_use > 0.8 * max` for 10m.

---

## 7) Implementation Notes

* Prefer **OpenTelemetry** for traces/metrics; export to your provider (Grafana/Prometheus/Datadog).
* Wrap HTTP clients (Twilio/Stripe/Google/Jobber) to emit metrics consistently and add request IDs to logs.
* Add a `/metrics` endpoint for scraping; protect with basic auth or IP allow‑list.

---

## 8) Validation & Tests

* Synthetic test: simulate inbound call → assert outbound queued in <5s across full path in staging.
* Unit tests for log redaction (no PII in INFO logs).
* Load tests to ensure P95 budgets under expected concurrency.

```

---

## operational-runbook.md

\n```markdown
# Operational Runbook — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/On‑call • **Scope:** Production ops for Modular Monolith (FastAPI + workers)

> Brutal summary: Managed PaaS (Heroku/Render) for the API + workers, Netlify/Vercel for the UI, single Postgres, DB Outbox + dispatcher, webhook-first with polling fallback. **Primary SLO:** first SMS **P95 ≤ 5s** (Twilio inbound → Twilio outbound queued).

---

## 1) System Topology

* **API (web)**: FastAPI app serving REST + webhooks (Twilio/Stripe/Google/Jobber).
* **Worker**: background process running:

  * **Outbox dispatcher** (batch=100, concurrency=2, at-least-once).
    Dispatches **domain events** defined in Event Catalog. This is not infra plumbing;
    these rows are business facts, and must remain aligned with catalog schemas.

  * **Hold GC** (deletes expired holds)
  * **Calendar pollers** (Google 60s, Jobber 120s per connected calendar)
* **DB**: Managed Postgres (primary only). Extensions: `btree_gist`.
* **Frontend**: Netlify/Vercel hosting Next.js.

---

## 2) Environments & Promotion

* **dev** → **staging** → **prod** (trunk-based; short-lived feature branches).
* Staging mirrors prod config with test credentials and a Twilio **test number**.
* Promotion is a **re-deploy** from a tagged commit; never hotfix on prod without a tag.

---

## 3) Configuration (Env Vars)

**Core**

* `DATABASE_URL`
* `SECRET_KEY`

**Twilio**

* `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_MESSAGING_SERVICE_SID`

**Stripe**

* `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

**Google**

* `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

**Clerk**

* `CLERK_JWT_ISSUER`, `CLERK_JWT_AUDIENCE`, `CLERK_JWKS_URL`

**Jobber**

* `JOBBER_API_TOKEN` (or OAuth credentials if applicable)

**Tuning / Feature Flags**

* `HOLD_TTL_MINUTES=15`
* `SEARCH_GRANULARITY_MINUTES=15`
* `POLL_INTERVAL_GOOGLE_SECONDS=60`
* `POLL_INTERVAL_JOBBER_SECONDS=120`
* `OUTBOX_BATCH_SIZE=100`
* `OUTBOX_CONCURRENCY=2`
* `TREAT_SHORT_COMPLETED_AS_MISSED=false`
* `SHORT_COMPLETED_MAX_SECONDS=10`
* `PAUSE_OUTBOUND_SMS=false` (ops kill-switch)

> Secrets live in platform config; never commit to Git.

---

## 4) Deploy Procedure (Zero‑downtime)

1. **Prepare**: Merge to `main`; CI green (tests + lint + migrations dry-run).
2. **Tag**: `vYYYY.MM.DD-x`.
3. **Run migrations** (release phase):

   * Additive first (nullable columns, new tables).
   * Deploy code that reads new fields.
   * Enforce non-null/constraints **later** after backfill.
4. **Deploy web + worker** images.
5. **Smoke**: /healthz (web), worker logs show dispatcher picking events.
6. **Verify SLO**: synthetic test (simulate inbound → expect outbound queued within budget on staging, spot-check prod).

**Rollback**

* Re-deploy previous tag for web + worker.
* Only roll back DB if the migration was destructive (avoid; use forward fixes where possible).

---

## 5) Observability

**Metrics (Prometheus-style names)**

* `slo_first_sms_p95_seconds` (alert if >5s for 10m)
* `booking_post_p95_ms` (alert if >500ms for 10m)
* `outbox_dispatch_lag_seconds` (alert if >60s for 10m)
* `webhook_dedupe_hits_total{provider}`
* `webhook_signature_failures_total{provider}` (alert if spike)
* `calendar_sync_errors_total` (alert if >0 for 15m)
* `scheduling_book_conflict_total` (watch trend)

**Logs (structured)**

* Include `tenant_id`, `module`, `event_name`, `correlation_id`, `http_status`.
* Log webhook **signature failures** at WARN with provider + headers (no secrets).

**Tracing**

* Correlation flows: webhook → outbox write → handler → provider API call. Use `correlation_id` + `causation_id` from the Event Catalog.

**Dashboards**

* SLO overview, Outbox health, Webhook health, Calendar sync, Scheduling conflicts, Provider error rates.

---

## 6) Alerts (initial thresholds)

* **SLO breach**: `slo_first_sms_p95_seconds > 5` for 10 minutes.
* **Outbox lag**: `outbox_dispatch_lag_seconds > 60` for 10 minutes.
    This alert is not only infra health — it also indicates that **domain events are delayed**,
    meaning projections, KPIs, and SLO measurements are stale.
* **Webhook signature failures**: `> 10/min` sustained 5 minutes.
* **Calendar sync errors**: any non-zero for 15 minutes.
* **DB saturation**: connections > 80% for 10 minutes; CPU > 80% for 10 minutes.

> Alerts page links to playbooks below.

---

## 7) On‑Call Playbooks

### 7.1 SLO Breach: First SMS > 5s (P95)

1. Check **Outbox health** (lag, attempts). If lag high → scale worker (`OUTBOX_CONCURRENCY`, dynos).
2. Inspect **Twilio latency** / 5xx rates; if high, set `PAUSE_OUTBOUND_SMS=true` only if Twilio is erroring to avoid floods.
3. Look for DB contention (long locks on `conv_*`/`sched_*`).
4. If calendar pollers are noisy, reduce poll frequency temporarily.

### 7.2 Outbox Stuck / Lagging

1. Query `outbox_events` where `dispatched_at IS NULL AND available_at < now()`.
2. If many rows with high `attempts`, inspect `last_error`.
3. Temporarily **increase** worker concurrency and **decrease** batch size to reduce lock times.
4. For poison messages, move rows to `outbox_events_errors` (manual table) and open a bug.
     **Do not bypass schema rules**: even DLQ entries must conform to Event Catalog contracts.

### 7.3 Twilio Failures (4xx/5xx spikes)

* 4xx (e.g., 21610 STOP): ensure opt-outs honored; investigate template content.
* 5xx/timeout: backoff with jitter kicks in. If sustained > 15m, notify Twilio support with correlation examples.

### 7.4 Calendar Webhooks Silent

* System should auto‑fallback to **polling**. Verify poll logs.
* If Google 401/403 → revoke tenant token and notify tenant to re‑auth.
* If Jobber token invalid → same re‑auth flow.

### 7.5 Stripe Webhook Signature Failures

* Rotate `STRIPE_WEBHOOK_SECRET`.
* Replay missed events from Stripe Dashboard.

### 7.6 DB Hotspots / Locking

* Check blocking queries (`pg_locks` joined to `pg_stat_activity`).
* Typical culprits: large `scheduling_search` or unbounded scans. Add/verify indexes.

### 7.7 Migration Gone Wrong

* If additive: revert app first. If destructive: apply compensating migration script.
* Document in postmortem; avoid destructive changes in the future.

---

## 8) Maintenance Tasks

* **Retention jobs**

  * Delete `conv_messages` older than **180 days** (after KPI aggregation).
  * Delete `webhook_events` older than **90 days**.
  * Delete `outbox_events` **30 days** after `dispatched_at`.
* **Secret rotation** quarterly (Twilio/Stripe/Google/Clerk/Jobber).
* **Restore drills** monthly: restore latest snapshot to staging and run smoke tests.

---

## 9) Backup & DR

* **Backups:** Daily snapshots + PITR (provider capability). Retain 7–14 days.
* **RPO:** ≤ 15 minutes. **RTO:** ≤ 2 hours.
* **Restore Steps:**

  1. Provision new Postgres instance from snapshot.
  2. Update `DATABASE_URL` in staging; run migrations if needed.
  3. Verify health + dashboards; then cut over prod if required.

---

## 10) Capacity & Scaling

* **Vertical** first (PaaS tiers), then **horizontal** (web/worker dynos).
* Scale worker when `outbox_dispatch_lag_seconds` trends up or pollers increase load (seasonal peaks).
* DB: monitor connections, IOPS; upgrade plan before exhaustion.

---

## 11) Run Commands (Heroku examples)

```bash
# Migrations (release phase)
heroku run -a nmc-prod alembic upgrade head

# Scale processes
heroku ps:scale web=2 worker=2 -a nmc-prod

# Tail logs
heroku logs -t -a nmc-prod

# Set flags
heroku config:set PAUSE_OUTBOUND_SMS=true -a nmc-prod

# Run SQL console
heroku pg:psql -a nmc-prod
```

---

## 12) SQL Cheatsheet

```sql
-- Outbox lag
SELECT now() - MIN(created_at) AS oldest, COUNT(*) AS pending
FROM outbox_events WHERE dispatched_at IS NULL;

-- Holds about to expire
SELECT id, resource_id, expires_at
FROM sched_holds WHERE expires_at < now() + interval '5 minutes'
ORDER BY expires_at;

-- Webhook dedupe volume by provider
SELECT provider, COUNT(*) FROM webhook_events
WHERE received_at > now() - interval '1 day'
GROUP BY provider;
```

---

## 13) Incident Postmortem Template

```
# Postmortem — <YYYY-MM-DD> <Title>
## Summary
## Timeline (UTC)
## Impact
## Root Cause
## Contributing Factors
## What Went Well / What Hurt
## Action Items (Owners, Dates)
```

---

## 14) Access & Security

* Principle of least privilege to PaaS accounts and DB.
* 2FA required for all dashboards and provider consoles.
* Rotate credentials on team changes; audit access quarterly.

```

---

## product-description.md

\n```markdown
# NeverMissCall — Product Description

## Product Overview

**NeverMissCall** is a specialized call management platform designed exclusively for blue-collar service businesses whose workers are physically unable to answer phones during work hours. The platform automatically converts missed calls into SMS conversations with AI assistance, capturing revenue that would otherwise be completely lost to competitors who happen to be available when customers call.

### Core Value Proposition

* **Capture Revenue While Working**: Never lose jobs because your hands are dirty, you're in a crawl space, or using loud tools
* **Instant Customer Response**: Customers get immediate SMS replies when you physically can't answer the phone
* **AI Handles Initial Screening**: Qualify leads, assess urgency, and book appointments automatically
* **Work-Focused Design**: Built specifically for trades where physical work prevents phone access

---

## Key Features

### 📞 **Automated Missed Call Recovery**

* Instant SMS response to missed calls (≤5 seconds)
* Intelligent call detection and customer identification
* Customizable greeting templates per business

### 🤖 **AI Conversation Management**

* Context-aware AI responses using business-specific information
* Lead qualification and customer needs assessment
* 60-second response timer with human override capability
* Natural conversation flow with appointment scheduling capabilities

### 👥 **Human-AI Collaboration**

* One-click takeover from AI to human agents
* Conversation history preserved during handoffs
* Real-time conversation monitoring and intervention
* Role-based access for different team members

### 📅 **Intelligent Job Catalog & Scheduling**

* **Job Catalog Database**: Business-specific list of services with custom pricing and duration
* **Instant Price Quotes**: AI provides immediate cost estimates during customer conversations
* **Smart Scheduling**: Books appointments with correct time blocks based on job complexity
* **Calendar Integration**: Direct sync with Jobber and Google Calendar
* **Real-time Availability**: Checks actual calendar availability before offering appointment slots

### 📊 **Business Intelligence**

* Lead tracking and conversion analytics
* Conversation performance metrics
* Revenue attribution from missed calls
* Basic reporting and insights (advanced analytics deferred)

### 🛡️ **Compliance & Security**

* Full 10DLC compliance for business messaging
* STOP/HELP keyword handling
* Data retention policies and privacy controls
* Encrypted customer data storage

---

## Target Users

### Primary Users - Blue-Collar Service Businesses

**The Problem**: These professionals are physically unable to answer phones during work hours when most customers call:

* **Plumbers**: Hands dirty, under sinks, in crawl spaces, using loud pipe tools
* **Electricians**: In attics/basements, working with live wires, safety requires focus
* **HVAC Technicians**: On rooftops, in tight spaces, handling heavy equipment
* **Handymen**: On ladders, both hands occupied, working with power tools
* **Auto Mechanics**: Under cars, hands covered in grease, using pneumatic tools
* **Cleaning Services**: Wearing gloves, using chemicals, focused on detail work

**Business Profile**: 1-5 employees, local service area (LA/SF metro), immediate-need customer base

### User Roles (for 1-5 employee businesses)

* **Business Owner**: Full platform access, job catalog setup, billing, compliance management
* **Worker/Technician**: View appointments, basic conversation access (optional for larger teams)

*Note: Most small businesses will use only the Owner role initially*

---

## Use Cases

### 1. **Emergency Service Provider**
**Scenario**: A plumbing company receives calls outside business hours for emergency repairs.

**User Journey**:
1. Customer calls after hours with a burst pipe emergency
2. Call goes to voicemail, triggers NeverMissCall
3. Immediate SMS sent: "Hi! Thanks for calling [Business]. We received your call about plumbing services. Is this an emergency?"
4. Customer responds: "Yes! Burst pipe flooding my kitchen!"
5. AI escalates to human agent immediately due to emergency keywords
6. Agent responds within minutes, schedules emergency visit
7. Customer receives confirmation with technician details and arrival time

**Outcome**: Emergency captured, customer served, revenue generated instead of lost to competitor.

### 2. **Solo Handyman Business**
**Scenario**: A one-person handyman operation in LA handles home repairs but is often on job sites during peak call times.

**User Journey**:
1. Homeowner calls about kitchen cabinet repair while handyman is installing flooring at another job
2. AI responds: "Hi! Thanks for calling Mike's Handyman Services. I see you called about home repair. What kind of work do you need done?"
3. Customer: "My kitchen cabinet door fell off and I need it fixed this week"
4. AI checks job catalog and calendar: "Cabinet door repair takes 2 hours and costs $95. I have availability Tuesday at 10 AM or Wednesday at 1 PM - both slots have the full 2 hours available. Which works better for you?"
5. Customer chooses Tuesday morning and accepts the price range
6. AI books 2-hour appointment with pricing estimate directly in Google Calendar
7. Handyman receives notification with customer details and repair description
8. Customer gets confirmation SMS with Mike's photo and arrival time

**Outcome**: Job booked automatically while handyman stays focused on current work, no calls missed.

### 3. **HVAC Contractor During Peak Season**
**Scenario**: LA HVAC company gets overwhelmed with AC repair calls during summer heat waves.

**User Journey**:
1. Customer calls about broken AC on 95-degree day when all technicians are booked
2. AI responds immediately: "Thanks for calling Cool Air HVAC! I understand you need AC service. Is this an emergency or can we schedule for tomorrow?"
3. Customer: "It's 90 degrees in my house! This is definitely an emergency"
4. AI escalates: "I'm connecting you with our emergency dispatcher right now. Please hold."
5. Business owner receives priority notification and responds within minutes
6. Emergency service scheduled for same day with premium pricing
7. Customer receives tech details, arrival window, and service cost upfront

**Outcome**: Emergency captured at premium rates, customer expectations managed, revenue maximized during peak season.

### 4. **Electrician with Google Ads**
**Scenario**: SF electrician runs Google Ads for "emergency electrical repairs" but misses calls while working in basements/attics with poor cell service.

**User Journey**:
1. Customer clicks Google Ad and calls about flickering lights (potential fire hazard)
2. Call goes straight to AI: "Thanks for calling Bay Area Electric! I see you're calling about electrical issues. Can you describe what's happening?"
3. Customer: "My living room lights keep flickering and I smell something burning"
4. AI recognizes safety keywords and immediately flags for human takeover
5. Business owner gets urgent SMS alert and calls back within 10 minutes
6. Emergency service visit scheduled for same day
7. Customer receives safety tips via SMS while waiting

**Outcome**: High-value emergency lead captured from paid advertising, safety issue addressed immediately, ad spend ROI maximized.

### 5. **Husband-Wife Cleaning Service**
**Scenario**: Two-person cleaning service in LA wants to grow but can't answer phones while cleaning clients' homes.

**User Journey**:
1. Potential customer calls for weekly house cleaning quote during active cleaning job
2. AI responds: "Hello! Thanks for calling Sparkle Clean Services. I'd love to help you get a cleaning quote. What size is your home?"
3. Customer: "It's a 3-bedroom, 2-bathroom house in Venice"
4. AI checks job catalog and availability: "For a 3-bedroom home, our weekly cleaning takes 3 hours and costs $120. I have two 3-hour slots available: Friday at 10 AM-1 PM or Monday at 2 PM-5 PM. Which works better?"
5. Customer books Friday at 10 AM
6. AI automatically blocks the calendar time and sends customer onboarding checklist
7. Cleaning team receives new client notification with home details and special instructions

**Outcome**: New recurring client acquired automatically, service priced correctly from catalog, no interruption to current work.

### 6. **Mobile Auto Mechanic**
**Scenario**: Mobile mechanic serves LA/SF markets but needs to stay focused on repairs while customers call for service.

**User Journey**:
1. Driver calls about car breakdown while mechanic is under another car
2. AI responds: "Thanks for calling Mobile Mech LA! I can help you with your car trouble. Where are you located and what's the problem?"
3. Customer: "I'm in Santa Monica, my car won't start after I got groceries"
4. AI checks service radius: "I can get a mechanic to you today. It sounds like a battery or starter issue. Are you in a safe location?"
5. Customer confirms safety, AI schedules emergency visit
6. AI provides arrival estimate and sends customer prep checklist (keys ready, hood access, etc.)
7. Mechanic gets full briefing between current job and pickup

**Outcome**: Roadside emergency captured, customer kept safe with clear communication, mechanic arrives prepared with proper tools.

---

## Business Benefits

### Revenue Impact

* **Recover 100% Lost Revenue**: Capture calls that currently go to zero because you can't physically answer
* **Premium Pricing Opportunities**: Book urgent jobs same-day when available
* **Maximize Marketing ROI**: Every Google Ad click and referral gets immediate response
* **No Staffing Overhead**: Grow revenue without hiring office staff or answering services

### Operational Efficiency

* **Stay Focused on Work**: No interruptions from phone calls during jobs
* **Automatic Job Qualification**: AI screens serious inquiries from price shoppers with upfront pricing
* **Work-Safe Communication**: No need to handle phone with dirty/gloved hands

### Customer Experience

* **No More Voicemail**: Customers get instant, helpful responses instead of "leave a message"
* **Immediate Scheduling**: Book appointments without waiting for callbacks
* **Professional Image**: Consistent, reliable communication even when you're unavailable

---

## Technical Requirements

### Job Catalog & Pricing Engine

* **Business-Specific Job Catalog**: Each business configures their own services with custom pricing and duration
* **Duration-Based Scheduling**: AI matches job duration with available calendar slots before making offers
* **Smart Availability Matching**: Only offers appointment slots that can accommodate the full job duration
* **Custom Rate Setting**: Business owners set their own prices - AI never invents pricing
* **Time Block Validation**: Enforced with Postgres `tstzrange` and GiST exclusion constraints to guarantee **No Double-Booking** (ADR-0006).


**How It Works:**

1. Business pre-configures job catalog (e.g., "Sink Clog: 1 hour, \$175")
2. Customer describes problem: "My kitchen sink is completely clogged"
3. AI matches description to catalog entry and checks calendar availability
4. AI only offers slots with 1+ hour availability: "I can fix that sink clog today at 2 PM or tomorrow at 9 AM. It typically takes 1 hour and costs \$175."
5. AI books appointment with correct time block reserved

**Example Business-Specific Catalogs:**

*Joe's Plumbing (Premium Service):*

* Sink Clog: 1 hour, \$175
* Shower Leak Repair: 2 hours, \$285
* Toilet Installation: 3 hours, \$420

*Budget Plumbing Co:*

* Sink Clog: 1 hour, \$125
* Shower Leak Repair: 2 hours, \$210
* Toilet Installation: 3 hours, \$315

### Integration Capabilities

* **Existing Phone Systems**: Works with current business phone numbers
* **Calendar Systems**: Direct integration with Jobber and Google Calendar (Microsoft Office planned for Phase 2)
* **CRM Systems**: Lead data export and integration capabilities
* **Payment Processing**: Stripe integration for subscription billing

### Compliance & Security

* **10DLC Compliance**: Manual brand/campaign registration in Phase 1, automated compliance gates for message sending
* **Data Privacy**: GDPR/CCPA compliant data handling
* **Data Retention**: Messages retained 180 days, metadata 13 months, webhook dedupe 90 days, outbox events 30 days after dispatch (per Glossary + ADRs).
* **Message Security**: Encrypted at-rest and TLS-in-transit (no field-level crypto in MVP, ADR-0002).
* **Audit Trail**: Complete conversation and action logging

### Scalability

* **Low Volume Processing**: 5,000 users max total, less than 100 simultaneous connections at max.
* **Multi-Tenant Architecture**: Modular Monolith with `tenant_id` column model (single Postgres cluster, tenant-scoped tables per ADR-0001).
* **Performance SLOs**: Auto-SMS ≤5s P95, Booking API responses ≤500ms P95 (excluding 3rd party latency), UI freshness ≤2.5s P95
* **Reliability**: 99.9% uptime target with managed cloud services

---

## Getting Started

### Onboarding Process

1. **Account Setup**: Business registration via Clerk and user authentication
2. **Billing Setup**: Stripe subscription activation and billing shadow creation
3. **Job Catalog Setup**: Configure your services with custom pricing and durations
4. **Phone Integration**: Connect existing business phone number  
5. **Calendar Connection**: Link scheduling system (Jobber or Google)
6. **AI Configuration**: Customize greeting templates and response flows
7. **Compliance Registration**: Complete KYC form, ops registers 10DLC brand/campaign manually
8. **Go Live**: SMS enabled after compliance approval, begin capturing missed calls

### Pricing Model

* **Subscription-based only**: Monthly recurring revenue model
* **Compliance Included**: 10DLC registration and maintenance included
* **Transparent Billing**: Clear pricing with no hidden fees

---

## Success Metrics

### Key Performance Indicators

* **Missed Call Capture Rate**: Percentage of missed calls converted to conversations
* **Response Time**: Time from missed call to first customer interaction
* **Conversation Conversion Rate**: Percentage of conversations resulting in appointments/sales
* **Customer Satisfaction**: Rating of AI and human interaction quality
* **Revenue Attribution**: Tracked revenue from NeverMissCall-generated leads

### Expected Outcomes for Blue-Collar Businesses

* **Recover \$2,000-\$5,000/month** in previously lost revenue from missed calls
* **3-5 additional jobs per week** booked automatically during work hours
* **Eliminate customer frustration** with instant SMS responses vs. voicemail
* **5-10x ROI** within first 3 months (typical service call value \$200-\$500)

---

## Development & Deployment Constraints

### Design Philosophy

* **SaaS Service**: Use existing services like Clerk.dev or Stripe (with customer and billing services).
* **AI Development**: Modules divided by domain (conversation, scheduling, compliance), keeping the **modular monolith** simple and maintainable.

### Deployment & Infrastructure

* **Hosting Model**: Managed cloud services (Heroku/Netlify) preferred to minimize operational burden
* **Geographic Scope**: Los Angeles first, San Francisco second (10DLC compliance complexity)
* **Database Strategy**: Modular Monolith with single Postgres cluster, tenant-scoped tables via `tenant_id` column (ADR-0001). Modules are isolated in code, but share one schema for MVP.


### Development Constraints

* **Technology Stack**: Python/FastAPI backend, Next.js frontend (tailwind/shadcn) - no polyglot complexity
* **Integration Approach**: API-first design, avoid deep integrations that create maintenance burden
* **Third-party Dependencies**: Minimize vendor lock-in, prefer services with clear migration paths

### Business Model Constraints

* **Target Market**: SMBs (1-5 employees) - no enterprise features that complicate the product
* **Pricing Simplicity**: Transparent subscription model only
* **Support Model**: Self-service onboarding with email support, not white-glove service

### Risk Management

* **Compliance-First**: No SMS without 10DLC approval - hard gates prevent legal issues
* **Data Retention**: Clear policies (180 days for messages, 13 months metadata) to limit liability
* **Vendor Dependencies**: Twilio (messaging), Clerk (auth), Stripe (billing) - establish fallback plans

### Quality Gates

* **AI Code Generation**: All services must follow documentation-first development from `/docs/services/phase-1/`
* **Testing Philosophy**: Three-tier testing (unit/integration/e2e) with real business scenario validation
* **Performance Budgets**: Auto-SMS ≤5s P95, Booking API responses ≤500ms P95 (excluding 3rd party latency), UI freshness ≤2.5s P95, zero double-bookings

### Things that are complete

* **Twilio Server** Already complete.
* **Conversation AI** Already complete.
* **Scheduling** This is done, but getting and setting data from calendar is not complete.
* **10DLC Compliance** Manual in Phase 1.


# NeverMissCall — Product Description

*(Full specification preserved as before)*

---


## Addendum 1: Domain-Driven Design & Architectural Approach

### Architectural Style

NeverMissCall is a **DDD-driven Modular Monolith** with clear bounded contexts (ADR-0001..0010). Modules are strongly isolated in code and schema (tenant_id enforced), but run in a single deployable unit. This gives us low operational overhead for MVP scale (≤5,000 tenants) while preserving future **service extraction paths** if growth demands.

### Bounded Contexts (Modules)

1. **Telephony** – Handles Twilio webhooks, missed-call detection, caller identity, message forwarding.
2. **Conversation** – AI-driven SMS threads, human takeover, 60s timers, conversation state machines.
3. **Scheduling** – Job catalog, appointment booking, calendar integration (Jobber/Google), conflict prevention with Postgres `tstzrange` + GiST.
4. **Catalog** – Service item catalog, pricing, duration, and availability data.
5. **Compliance** – 10DLC brand/campaign, opt-outs, outbound message gates.
6. **Billing** – Stripe subscription mirror, subscription state events.
7. **Identity** – Tenant accounts, roles (OWNER/TECH), Clerk JWT enforcement.
8. **Reporting** – Cross-domain **read-model/projection** module for analytics and SLO tracking (not a transactional bounded context).

### Data & Consistency

* **Single PostgreSQL instance**, single schema, all tables tenant-scoped by `tenant_id` (ADR-0001).
* ACID transactions within modules (especially Scheduling to prevent double-booking).
* **Outbox pattern** used for domain events → projections and async flows.
* CQRS-lite: transactional writes, denormalized read models for performance.

### Integration Patterns

* **Idempotency keys** for Twilio/Stripe/Jobber/Google integrations.
* **Adapters** abstract external services to keep the core domain independent.
* **Contract tests** between modules enforce boundaries.

### Scalability & Growth Path

* Modular Monolith sufficient for target scale (≤5,000 users, ≤100 concurrent).
* If future scale demands, likely extractions are: Telephony Ingestion, Compliance workflows, Analytics pipeline.

---

**Summary:** This project is a **DDD-driven Modular Monolith**, optimized for SMB-focused MVP delivery. Modules enforce strong domain boundaries, enabling rapid development today and optional microservice extraction tomorrow.

```

---

## software-design-billing.md

\n```markdown
# Software Design — Billing Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Billing (Stripe Mirror)

> Goal: Mirror **subscription state from Stripe** and expose it to the rest of the system for **feature gating**. Subscription‑only pricing (no usage billing). Stripe is the **source of truth**; our DB is a cache.

---

## 1) Responsibilities

* Create and manage **Stripe Checkout** sessions for tenants.
* Expose **Customer Portal** links for self‑service management.
* Consume **Stripe webhooks** to mirror subscription state into `bill_subscriptions`.
* Emit `SubscriptionUpdated` events for other modules (e.g., Identity/feature gates, UI banners).
* Provide read APIs for current plan/status per tenant.

**Out of scope:** invoicing UI, taxes, coupons, proration logic (all handled by Stripe).

---

## 2) Domain Model

### Aggregates / Entities

* **Subscription**

  * Fields: `id`, `tenant_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan`, `status`, `current_period_end`, `updated_at`.
  * Invariants:

    1. Exactly **one active** subscription per tenant in MVP.
    2. `status ∈ {active, past_due, canceled, trialing}`.
    3. Plan is subscription‑only; no usage add‑ons.

### Value Objects

* **Plan**: string key (e.g., `basic`). MVP can start with a **single plan**.

---

## 3) Public API (internal HTTP)

* `POST /billing/checkout-session` → creates a Stripe Checkout session for the tenant.

  * Request: `{ success_url, cancel_url }`
  * Response: `{ url }` (redirect URL)
* `POST /billing/customer-portal` → returns Stripe Customer Portal link.

  * Request: `{ return_url }`
  * Response: `{ url }`
* `GET /billing/subscription` → current subscription mirror for the tenant.

**AuthZ:** OWNER only for POST endpoints; OWNER/TECH can `GET` subscription.

---

## 4) Stripe Integration

### 4.1 Checkout

* Create Checkout Session with:

  * `mode='subscription'`
  * `line_items=[{ price: STRIPE_PRICE_ID, quantity: 1 }]`
  * `client_reference_id = tenant_id`
  * `success_url`, `cancel_url`
* On completion, Stripe will emit `customer.subscription.created` and `...updated`.

### 4.2 Customer Portal

* Generate a portal session scoped to the tenant's `stripe_customer_id`.
* Allow cancel/pause/change plan per Stripe settings; we reflect changes via webhooks.

### 4.3 Webhooks

* Endpoint: `POST /webhooks/stripe`
* Verify signature with `STRIPE_WEBHOOK_SECRET`.
* **Idempotency:** `(provider='stripe', event_id)` in `webhook_events` table.
* **Events consumed** (minimum):

  * `customer.subscription.created`
  * `customer.subscription.updated`
  * `customer.subscription.deleted`
  * `invoice.payment_failed` (optional; for banner/notifications)

**Handler behavior**

1. Resolve `tenant_id` via `client_reference_id` (Checkout) or by looking up `stripe_customer_id` / `subscription_id` in `bill_subscriptions`.
2. Upsert `bill_subscriptions` with latest `status`, `plan`, `current_period_end`.
3. Emit `nmc.billing.SubscriptionUpdated { stripe_customer_id, stripe_subscription_id, plan, status, current_period_end }` to Outbox.
4. Return **200**.

---

## 5) Feature Gates (consumers of subscription state)

* **Conversation** & **Telephony**: no hard gate on send for MVP (compliance is the hard gate). However, if `status in {'canceled','past_due'}` for > grace period, UI should show banners and we may **soft‑limit** non‑critical actions (configurable, default off).
* **Admin UI**: show current plan and renewal date; surface `past_due` and `canceled` prominently.

> Explicit **no usage caps** in MVP. This module is only about subscription presence and status.

---

## 6) Data Model (restate from DB doc)

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

**Lookups**

* By `tenant_id` (most common).
* By `stripe_customer_id` / `stripe_subscription_id` (webhooks).

---

## 7) Events

**Produced** (schema\_version `1.0.0`)

* `nmc.billing.SubscriptionUpdated { stripe_customer_id, stripe_subscription_id, plan, status, current_period_end }`

**Consumed**

* None required; optional `Identity` can listen to raise UI banners or toggle access.

---

## 8) Failure Modes & Policies

* **Webhook verification failure** → 401; do not process.
* **Duplicate events** → dedup via `webhook_events`; return 200.
* **Unknown customer/subscription** → attempt to resolve via Stripe API; if still unknown, log WARN and 200 (so Stripe doesn’t retry endlessly) and open manual task.
* **API rate/5xx** → retry with jitter (base=1s, cap=30s, max\_attempts=6).

Grace period (configurable, default **7 days**) before any soft‑limit is enacted for `past_due`.

---

## 9) Observability

**Metrics**

* `billing_webhook_events_total{type}`
* `billing_subscription_state{status}` (gauge per tenant, optional)
* `billing_checkout_sessions_created_total`
* `billing_portal_sessions_created_total`

**Logs**

* Include `tenant_id`, `stripe_customer_id`, `stripe_subscription_id`, `event_type`, transition `old_status → new_status`.

---

## 10) Testing Strategy

* **Webhook idempotency**: replay same event id → single DB update and single outbox emit.
* **State transitions**: created → active, active → past\_due → active, active → canceled.
* **Checkout flow**: simulate completion and ensure mirror row created.
* **Portal**: smoke to ensure URL generated for existing customer id.

---

## 11) Config & Defaults

* `STRIPE_PRICE_ID` (single plan)
* `BILLING_PAST_DUE_GRACE_DAYS = 7`
* `BILLING_ENABLE_SOFT_LIMITS = false`

---

## 12) Open Questions (non‑blocking)

* Will we support **multiple plan tiers** later (e.g., Pro)? If yes, document gate matrix.
* Do we want proactive email notifications for `past_due`? (Out of MVP.)

```

---

## software-design-catalog.md

\n```markdown
# Software Design — Catalog & Pricing Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Catalog & Pricing

> Goal: Provide a **truthful, tenant-scoped catalog** of service items with fixed prices and durations. Guarantee that AI never invents prices by exposing read APIs used for quoting and slot computation.

---

## 1) Responsibilities

* Maintain per-tenant **Service Items** (name, duration, price, currency, active flag).
* Provide **read-optimized** APIs for quoting and Conversation flows.
* Emit `CatalogUpdated` events for cache invalidation and reporting.
* Expose a lightweight **matching** endpoint so AI can map user text → catalog item using tenant-defined aliases (no ML needed in MVP).

Out of scope: discounts, taxes, bundles/combos, cost accounting.

---

## 2) Domain Model

### Aggregates / Entities

* **ServiceItem**

  * Fields: `id`, `tenant_id`, `name`, `duration_minutes`, `price_cents`, `currency`, `active`.
  * Invariants:

    1. `duration_minutes` ∈ (0, 480].
    2. `price_cents` ≥ 0; `currency` is ISO-4217 (MVP default `USD`).
    3. `name` **unique** per tenant; `active=true` required to quote.

* **ServiceItemAlias** (optional helper, not a separate aggregate)

  * Fields: `id`, `tenant_id`, `service_item_id`, `alias_text` (lowercased), `priority`.
  * Used for string matching from the AI/Conversation module.

### Value Objects

* **Money**: (`amount_cents`, `currency`).
* **Duration**: integer minutes.

---

## 3) Public API (internal HTTP)

### 3.1 CRUD (Admin)

* `GET   /catalog/items?active=true` → list items
* `GET   /catalog/items/{id}` → item details
* `POST  /catalog/items` → create item `{ name, duration_minutes, price_cents, currency? }`
* `PUT   /catalog/items/{id}` → update fields (partial)
* `DELETE /catalog/items/{id}` → **soft-delete via `active=false`** (MVP)

### 3.2 Quoting & Matching (Runtime)

* `GET  /catalog/quote/{id}` → `{ service_item_id, name, duration_minutes, price_cents, currency }`
* `POST /catalog/match` → `{ text: "clogged kitchen sink" }` → `{ service_item_id, confidence, matched_alias? }`

  * Matching algorithm (MVP): normalize, tokenize, exact/substring match over `name` and `aliases`. Return highest `priority`/longest-match first.

**AuthZ:** OWNER can CRUD; OWNER/TECH can read/quote/match. All endpoints require `tenant_id`.

---

## 4) Events (Produced & Consumed)

**Produced**

* `nmc.catalog.CatalogUpdated { updated_item_ids: [uuid], full_refresh: boolean }` (schema\_version `1.0.0`)

**Consumers**

* **Conversation**: cache invalidation to avoid stale quotes; reads detail on-demand.
* **Reporting**: track price/duration evolution over time (future).

---

## 5) Data Model (adds to DB doc)

```sql
-- already defined in database doc; repeated here for context
CREATE TABLE catalog_service_items (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  duration_minutes int NOT NULL CHECK (duration_minutes > 0 AND duration_minutes <= 8*60),
  price_cents int NOT NULL CHECK (price_cents >= 0),
  currency char(3) NOT NULL DEFAULT 'USD',
  active boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, name)
);

-- simple alias table for text matching
CREATE TABLE catalog_item_aliases (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  service_item_id uuid NOT NULL REFERENCES catalog_service_items(id) ON DELETE CASCADE,
  alias_text text NOT NULL,      -- store lowercased
  priority int NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, service_item_id, alias_text)
);
CREATE INDEX catalog_alias_lookup ON catalog_item_aliases(tenant_id, alias_text);
```

---

## 6) Matching Algorithm (MVP)

1. Lowercase input `text`; strip punctuation; tokenize (split on whitespace).
2. Construct candidate phrases (n-grams up to length 4).
3. Search for substring matches against `catalog_service_items.name` and `catalog_item_aliases.alias_text` (both lowercased) within the same `tenant_id`.
4. Rank: (a) longer match > shorter, (b) alias `priority` desc, (c) exact name match > alias.
5. Return top candidate with a heuristic `confidence` ∈ \[0.0, 1.0]. If no match, return 404 with `{ reason: 'no-match' }`.

**Notes**

* We intentionally avoid ML; deterministic behavior is easier to test and explain.
* Conversation can still apply AI to pre-normalize text but must rely on this endpoint for the **final** item id and price.

---

## 7) Failure Modes & Policies

* **Inactive item**: `GET /quote/{id}` returns 410 Gone.
* **No match**: 404 with `{ reason: 'no-match' }` — Conversation falls back to human or a generic response.
* **Currency mismatch**: MVP only supports one currency per tenant (default USD). Validate on create; reject mixed currencies per tenant.
* **Race on rename**: enforce `UNIQUE(tenant_id, name)`; return 409 on conflict.

Retry policy for transient DB errors: standard jitter (base=1s, cap=30s, max\_attempts=6).

---

## 8) Observability

**Metrics**

* `catalog_match_requests_total{outcome}` (hit|no-match)
* `catalog_match_latency_ms` (p50/p95)
* `catalog_quote_latency_ms`
* `catalog_events_published_total`

**Logs**

* Include `tenant_id`, `service_item_id`, `matched_alias`, `confidence` for `/match`.

---

## 9) Testing Strategy

* **CRUD tests**: invariants (duration, money, unique name).
* **Matching tests**: aliases, tie-breakers (priority/length), non-English/accents basic coverage.
* **Quoting tests**: inactive items blocked; prices/durations consistent with DB.
* **Event tests**: `CatalogUpdated` emitted correctly on create/update/delete.

---

## 10) Config & Defaults

* `DEFAULT_CURRENCY = 'USD'`
* `ALIAS_MAX_LEN = 120`
* `MATCH_MAX_NGRAM = 4`
* `MATCH_MIN_CONFIDENCE = 0.5` (advisory; Conversation can decide UX)

---

## 11) Example Flows

**Create item** → emits `CatalogUpdated`.

**User says:** “toilet install this week” → Conversation calls `/catalog/match` → returns `ServiceItem(id='toilet-installation', duration=180, price=$420)` → Conversation calls Scheduling `/search` with `duration_minutes=180` → offers slots → hold → book.

---

## 12) Open Questions (non-blocking)

* Should we support **variants** (e.g., travel fee) as separate items or surcharges? (Defer.)
* Do we need **categories** for UI grouping? (Defer.)
* Multi-currency per tenant? (Out of MVP.)

```

---

## software-design-compliance.md

\n```markdown
# Software Design — Compliance Module (10DLC, Manual Phase)

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Compliance (Messaging Eligibility)

> Goal: Enforce **10DLC compliance** for US A2P messaging. In MVP, registration is **manual**. Outbound SMS is **blocked** until a tenant’s campaign is **approved**. The module owns the phone‑number↔tenant mapping used by Telephony.

---

## 1) Responsibilities

* Track **brand/campaign/number** state per tenant.
* Provide a simple **submission** flow that collects tenant details for manual registration.
* Gate outbound messaging (Conversation/Twilio send) until status is `approved`.
* Maintain mapping from **receiving phone numbers (E.164)** → `tenant_id` for webhook routing.
* Emit `ComplianceStatusChanged` events for other modules.

Out of scope: automated TCR/10DLC API integration (Phase 2), international sender regulations.

---

## 2) Invariants

1. A tenant cannot send outbound SMS until there is a **campaign with `status='approved'`**.
2. All inbound webhooks must map `To` number to exactly **one** `tenant_id` owned number.
3. STOP/HELP keywords must be handled (Conversation executes behavior; Compliance retains an **opt‑out ledger** for audit).

---

## 3) Public API (internal HTTP)

### 3.1 Submit for Compliance (manual)

`POST /compliance/submit`

```json
{
  "business_name": "Joe's Plumbing, LLC",
  "ein_last4": "1234",
  "website": "https://joesplumbing.example",
  "contact_name": "Joe Smith",
  "contact_email": "owner@joesplumbing.example",
  "contact_phone": "+13105550000"
}
```

**Behavior**: creates/updates a **brand** record (pending), creates a **campaign** with `status='pending'`, opens an internal support task.

### 3.2 Status

`GET /compliance/status` → `{ status: 'pending'|'approved'|'rejected', campaign_id, phone_numbers: ["+1..."] }`

### 3.3 Assign / Verify Receiving Number

`POST /compliance/numbers`

```json
{ "e164": "+13105550000" }
```

Registers a receiving number under the tenant; must be unique under the tenant.

### 3.4 Admin (internal only)

* `POST /admin/compliance/{tenant_id}/approve` → mark campaign `approved` and emit event.
* `POST /admin/compliance/{tenant_id}/reject` → mark `rejected` with `reason`.

**AuthZ:** OWNER for submit/status/numbers. Admin endpoints restricted to ops.

---

## 4) Events

**Produced** (schema\_version `1.0.0`)

* `nmc.compliance.ComplianceStatusChanged { campaign_id, status }`

**Consumers**

* **Conversation**: blocks or unblocks outbound SMS according to status.
* **Telephony**: uses number mapping for webhook tenant resolution.

---

## 5) Data Model (adds to DB doc)

```sql
-- Brand (tenant identity for 10DLC). MVP keeps minimal fields required for manual registration
CREATE TABLE comp_brands (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL UNIQUE,
  name text NOT NULL,
  ein_last4 char(4),
  website text,
  contact_name text,
  contact_email text,
  contact_phone text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Campaign state machine (manual)
CREATE TABLE comp_campaigns (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('pending','approved','rejected')),
  provider_ref text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Numbers owned by tenant (receiving and/or outbound); used to resolve webhooks to tenant
CREATE TABLE comp_phone_numbers (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  e164 text NOT NULL,
  campaign_id uuid REFERENCES comp_campaigns(id),
  is_receiving boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, e164)
);

-- Opt-out ledger for audit (Conversation enforces behavior; we store facts)
CREATE TABLE comp_opt_outs (
  tenant_id uuid NOT NULL,
  phone_e164 text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, phone_e164)
);
```

**Notes**

* `comp_phone_numbers.is_receiving` flags which numbers expect inbound webhooks.
* We keep **one campaign per tenant** in MVP. Multiple numbers can point to the same campaign.

---

## 6) Enforcement (integration with Conversation)

* Conversation must call `compliance.can_send(tenant_id)` before enqueueing an outbound SMS.
* If **not approved** → set conversation state `blocked`, 403 on send, and show an in‑app banner with re‑submission link.
* When an inbound `STOP` is detected: insert into `comp_opt_outs` and **close** the conversation.

**Pseudocode**

```python
def can_send(tenant_id: UUID) -> bool:
    return db.fetchval("SELECT status='approved' FROM comp_campaigns WHERE tenant_id=$1", tenant_id) or False
```

---

## 7) Operational Workflow (manual 10DLC)

1. **Tenant submits** brand details via `/compliance/submit`.
2. **Ops agent** uses Twilio Console/TCR to create brand + register A2P campaign (manual).
3. **Ops updates** `comp_campaigns.status` → `approved` or `rejected` via admin endpoint.
4. **Ops assigns** phone numbers to the tenant via `/compliance/numbers` (or migration script).
5. **System emits** `ComplianceStatusChanged` and unblocks outbound if `approved`.

**Artifacts** (optional storage): ops can upload PDFs/screenshots to internal storage; we store references in `comp_brands` (future).

---

## 8) Observability

**Metrics**

* `compliance_status_total{status}` (gauge or counters per tenant)
* `compliance_blocked_outbound_total` (denied attempts)
* `compliance_numbers_registered_total`

**Logs**

* Status transitions with `tenant_id`, `old→new`, `reason` if rejected.
* Opt‑out events recorded with `tenant_id`, `phone_e164`.

---

## 9) Failure Modes & Policies

* **Duplicate numbers**: 409 on `UNIQUE (tenant_id, e164)`.
* **Unmapped inbound number**: Telephony returns 200 no‑op, logs WARN with number seen.
* **Ops delay**: tenants remain `pending`; UI shows banner and instructions. No outbound until approval.

Retry policy for admin-side provider calls: exponential backoff with jitter (base=1s, cap=30s, max\_attempts=6).

---

## 10) Testing Strategy

* **Gate enforcement**: send blocked when pending; unblocked after approval event.
* **Webhook routing**: map inbound `To` to tenant correctly; unknown numbers no‑op.
* **STOP/HELP**: STOP inserts into `comp_opt_outs` and prevents future sends; HELP renders template.

---

## 11) Open Questions (non‑blocking)

* Multi‑campaign per tenant (marketing vs transactional) later?
* Automated campaign provisioning via API (Phase 2) — when?
* Do we need per‑number **use roles** (marketing vs customer care) in MVP? (Likely not.)

```

---

## software-design-conversation.md

\n```markdown
# Software Design — Conversation & Messaging Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Conversation & Messaging

> Goal: Convert missed calls and inbound SMS into structured conversations, drive AI-led replies and booking flows, support rapid human takeover, and meet the **P95 ≤ 5s** first-response SLO. All cross-module effects go through the **Outbox**. Messaging is hard-gated by 10DLC compliance status.

---

## 1) Responsibilities

* Maintain tenant-scoped **conversations** and **messages** with a clear state machine.
* Orchestrate AI replies using tenant context (catalog, availability) without fabricating prices.
* Enforce **compliance gates** (no outbound SMS unless approved).
* Support **human takeover** and return to AI control.
* Handle Twilio send & delivery callbacks with **idempotency**.
* Emit domain events for Reporting and other modules.

Out of scope: pricing definition (Catalog owns), bookings invariant (Scheduling owns), identity management.

---

## 2) Domain Model

### Aggregates / Entities

* **Conversation**: life-cycle of an interaction with a caller.

  * Fields: `id`, `tenant_id`, `caller_phone`, `state` (`open` | `human` | `closed` | `blocked`), `opened_at`, `closed_at`, `last_activity_at`.
  * Invariants:

    1. At most **one** `open` or `human` conversation per `(tenant_id, caller_phone)`.
    2. Outbound messages require `compliance_status = 'approved'`.
    3. State transitions are explicit (see state machine).
* **Message**: units of communication (SMS in/out).

  * Fields: `id`, `tenant_id`, `conversation_id`, `direction` (`in`|`out`), `body`, `provider_message_id?`, `status` (`queued`|`sent`|`delivered`|`failed`), `client_dedup_key?`, `created_at`.
  * Invariants:

    1. Outbound `Message` is created **once** per `client_dedup_key`.
    2. Delivery status updates are idempotent per `provider_message_id`.

### Value Objects

* **PhoneNumber**: E.164 string.
* **Template**: `key`, `body`, optional variables (MVP: stored per tenant).

---

## 3) State Machine

```
           +---------+     human takeover     +--------+
 inbound → |  open   | --------------------→ | human  |
  SMS/Call |         | ←----------- release  |        |
           +----+----+                       +----+---+
                |   close (inactivity/user)       |
                |---------------------------------|
                              ↓                   |
                            +---------------------+
                            |       closed        |
                            +---------------------+

 compliance not approved → state becomes `blocked` (no outbound). When compliance approved → transition back to `open`.
```

**Transitions**

* `open → human`: `POST /conversations/:id/takeover`.
* `human → open`: `POST /conversations/:id/release`.
* `open|human → closed`: auto-close after inactivity threshold or explicit close.
* `* → blocked`: if compliance becomes unapproved; outbound sends are denied.
* `blocked → open`: upon `ComplianceStatusChanged(approved)`.

**Single-open constraint (SQL)**

```sql
CREATE UNIQUE INDEX conv_single_open_per_caller
  ON conv_conversations(tenant_id, caller_phone)
  WHERE state IN ('open','human');
```

---

## 4) Public API (internal HTTP)

### Send human message

`POST /conversations/{id}/messages`

```json
{ "body": "Got it. Tuesday 10am works.", "client_dedup_key": "ui-8f2a..." }
```

* Returns 403 if `blocked` or compliance not approved.
* Returns 409 if duplicate `client_dedup_key`.

### Takeover / Release / Close

* `POST /conversations/{id}/takeover` → state `human`.
* `POST /conversations/{id}/release` → state `open`.
* `POST /conversations/{id}/close` → state `closed`.

### Templates (tenant-scoped)

* `GET /templates`
* `PUT /templates/{key}` with body text (no variables beyond simple `{name}` placeholders in MVP).

### Query

* `GET /conversations?caller_phone=+13105551212&state=open`
* `GET /conversations/{id}/messages?limit=200`

AuthZ: `OWNER` and `TECH` only; all routes require `tenant_id` scoping.

---

## 5) AI Orchestration (server-side policy)

**First message (SLO-critical):**

* Trigger: `CallDetected` or `InboundSmsReceived`.
* Steps (max budget \~3.5s inside our app; Twilio network budget \~1.5s):

  1. Check **compliance gate** → if not approved, create conversation with state `blocked`, enqueue an ops task, **do not send** SMS.
  2. Load **tenant settings** + **templates**.
  3. Create or fetch `open` conversation (enforce unique index).
  4. Compose greeting reply (template) and send via Twilio.
  5. Persist `Message(out)` with `status='queued'` + write **Outbox** `ConversationStarted` and `MessageSent`.

**Subsequent messages:**

* AI policy obeys **60s human override window** *when state=human*. When state=open, AI may reply immediately.
* AI must:

  * Never invent price; fetch from `catalog_service_items`.
  * For scheduling offers: call Scheduling `/search` with `duration_minutes` and propose slots; place **hold** only after customer picks a slot.

**Safety & Keyword filters**

* STOP/UNSUBSCRIBE: mark participant opted-out; close conversation.
* HELP: send help template.

---

## 6) Twilio Integration

### Outbound Send (SMS)

* Generate `client_dedup_key` if not provided.
* POST to Twilio Messages API; store `provider_message_id`.
* On success: `status='queued'` or `sent` depending on callback arrival.

### Delivery Callbacks (Webhook)

* Endpoint: `/webhooks/twilio/sms-status`.
* Idempotency: dedupe using `(provider='twilio', event_id=<MessageSid:Status>)` in `webhook_events`.
* Update `conv_messages.status` to latest state; emit `MessageSent`/`DeliveryUpdated` events if changed.

**Inbound SMS**

* Endpoint: `/webhooks/twilio/sms-inbound`.
* Dedupe via `(provider='twilio', event_id=<MessageSid>)`.
* Create/open conversation; append inbound message; trigger AI pipeline if `state=open`.

---

## 7) Events (Produced & Consumed)

**Produced** (all include `schema_version`, `tenant_id`, `occurred_at`, `correlation_id`):

* `ConversationStarted { conversation_id, caller_phone }`
* `MessageSent { conversation_id, message_id, direction, status }`
* `DeliveryUpdated { message_id, status }`
* `HumanTakeoverRequested { conversation_id, user_id }`

**Consumed**

* `CallDetected` (from Telephony) → start conversation + first SMS.
* `InboundSmsReceived` (from Telephony) → append message; maybe reply.
* `AppointmentHeld|Booked|Released` (from Scheduling) → inform user in-thread.
* `CatalogUpdated` → refresh cached durations/prices.
* `ComplianceStatusChanged` → unblock outbound messaging if approved.

Versioning: **semantic** via `schema_version`.

---

## 8) Data Model (adds to the DB doc)

```sql
-- Templates (per-tenant greeting and help/stop)
CREATE TABLE conv_templates (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  key text NOT NULL,         -- e.g., 'greeting', 'help', 'fallback'
  body text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, key)
);

-- Add status to messages
ALTER TABLE conv_messages
  ADD COLUMN status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','sent','delivered','failed'));
```

**Denormalized read model (optional MVP)**

```sql
CREATE MATERIALIZED VIEW conv_threads AS
SELECT c.tenant_id, c.id AS conversation_id, c.caller_phone,
       c.state, c.last_activity_at,
       (SELECT body FROM conv_messages m WHERE m.conversation_id=c.id AND m.direction='in' ORDER BY m.created_at DESC LIMIT 1) AS last_inbound,
       (SELECT body FROM conv_messages m WHERE m.conversation_id=c.id AND m.direction='out' ORDER BY m.created_at DESC LIMIT 1) AS last_outbound
FROM conv_conversations c;
```

---

## 9) Failure Modes & Policies

* **Compliance blocked**: state=`blocked`, 403 on send; ops task created.
* **Duplicate webhooks**: dedup via `webhook_events`; updates idempotent.
* **SMS send failure**: mark message `failed`, retry policy with jitter for transient errors.
* **AI timeout**: fall back to template-based reply; log `ai_timeout_total`.
* **Template missing**: use default baked-in fallback template.

Retry policy: exponential backoff with jitter (base=1s, cap=30s, max\_attempts=6).

---

## 10) Observability

**Metrics**

* `first_sms_p95_seconds` (Conversation-only view; should be ≤ global SLO)
* `ai_pipeline_duration_ms` (compose + integrations)
* `sms_outbound_failures_total`, `sms_delivery_failures_total`
* `human_takeover_rate`
* `stop_optout_total`

**Tracing**

* Correlate: `twilio_message_sid` ↔ `message_id` ↔ `conversation_id` ↔ `hold_id/appointment_id`.

**Logs**

* Structured logs include `tenant_id`, `conversation_id`, `message_id`, `correlation_id`.

---

## 11) Testing Strategy

* **State machine tests**: all transitions and guards (blocked, human takeover, close on inactivity).
* **Idempotency tests**: duplicate inbound/outbound webhook events do not duplicate messages.
* **SLO tests**: inject fake Twilio client to simulate latency; ensure P95 budget.
* **Template rendering tests**: no missing variables (fail fast).
* **Compliance gate tests**: outbound blocked until approved.

---

## 12) Config & Defaults

* `AI_HUMAN_OVERRIDE_WINDOW_SECONDS = 60` (only when state=`human`)
* `CONVERSATION_INACTIVITY_AUTO_CLOSE_HOURS = 72`
* `FIRST_SMS_SLO_P95_SECONDS = 5`

---

## 13) Pseudocode — First Reply Flow

```python
@twilio_inbound_call_or_sms_webhook
@idempotent(provider='twilio', event_id=payload["MessageSid"])
def handle_incoming(payload, tenant_id):
    if not compliance.is_approved(tenant_id):
        conv = conversations.open_or_blocked(caller=payload["From"], state='blocked')
        ops.notify("compliance_blocked", conv.id)
        return 202

    conv = conversations.get_or_create_open(tenant_id, caller=payload["From"])  # unique open/human enforced
    msg_in = messages.append_inbound(conv.id, body=payload["Body"])  # returns message_id

    # Compose AI reply (catalog-aware, no invented prices)
    reply_text = ai.compose_reply(tenant_id, conv, msg_in)

    # Send via Twilio (with client dedup)
    client_key = uuid4()
    msg_out = messages.append_outbound(conv.id, body=reply_text, client_dedup_key=client_key)
    twilio_sid = twilio.send_sms(to=conv.caller_phone, body=reply_text, status_callback=STATUS_URL)
    messages.attach_provider_id(msg_out.id, twilio_sid)

    outbox.emit("ConversationStarted", {...})
    outbox.emit("MessageSent", {...})
    return 202
```

---

## 14) Open Questions (non-blocking)

* Multi-language templates per tenant? (MVP: English only.)
* Quiet hours per tenant? (Throttle AI at night.)
* Attachments/MMS? (Out of MVP.)

```

---

## software-design-database.md

\n```markdown
# Software Design — Database (NeverMissCall MVP)

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

```

---

## software-design-identity.md

\n```markdown
# Software Design — Identity & Access Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Identity & Access (AuthN/AuthZ)

> Goal: Authenticate users with **Clerk (JWT)**, enforce **tenant-scoped RBAC** with roles `OWNER` and `TECH`, and ensure every request carries a **valid `tenant_id`**. No API keys in MVP. Webhooks (Twilio/Stripe/Google/Jobber) are **unauthenticated** but deduped and mapped to tenants by provider-specific identifiers.

---

## 1) Responsibilities

* Authenticate app users via **Clerk JWT**.
* Authorize requests via **RBAC** (roles: `OWNER`, `TECH`).
* Bind every request to a **single tenant** (multi-tenancy via `tenant_id` column).
* Manage tenant/users lifecycle (invite, role assignment, deactivation).
* Provide helpers for modules to retrieve **current tenant context** safely.

**Out of scope:** SSO providers config (handled by Clerk), fine-grained permissions beyond two roles, API key issuance (deferred).

---

## 2) Domain Model

### Aggregates / Entities

* **Tenant** (`id`, `name`, `created_at`)
* **User** (`id`, `tenant_id`, `email`, `role`, `created_at`)

  * `role ∈ {OWNER, TECH}`
  * Each user belongs to **one tenant** (1 business per tenant per product decision).

### Invariants

1. Every request in app code has **exactly one** `tenant_id` in context.
2. Only `OWNER` may manage users, billing, compliance.
3. `TECH` has read/write to operational features (conversations, scheduling) **within the tenant**.
4. Users cannot switch tenants (MVP); changing tenant requires re-invite and data migration.

---

## 3) Authentication (Clerk)

* **Token type:** JWT (access token) attached as `Authorization: Bearer <token>` on API requests.
* **Verification:**

  * Validate issuer (`CLERK_JWT_ISSUER`), audience (`CLERK_JWT_AUDIENCE`), and signature via JWKS (`CLERK_JWKS_URL`).
  * Cache JWKS for 15 minutes; refresh on `kid` miss.
  * Accept only tokens issued for our API audience.
* **Claims mapping (expected)**

  * `sub` → `user_id`
  * `email` → preferred email
  * `org_id` or custom claim → **`tenant_id`** (we will configure Clerk to embed `tenant_id` in a custom claim `nmc_tenant_id`).
  * `role` or custom metadata → `OWNER` or `TECH` (custom claim `nmc_role`).

**Failure handling**

* Missing/invalid token → 401.
* Token valid but missing `nmc_tenant_id` or `nmc_role` → 403 and log misconfiguration.

---

## 4) Authorization (RBAC)

### Roles

* **OWNER**: manage users, billing, compliance, catalogs, all runtime ops.
* **TECH**: runtime ops (conversations, scheduling), limited settings view, no billing/compliance/user management.

### Enforcement

* Implement a FastAPI **dependency** `require_role(*roles)` that:

  1. Validates JWT.
  2. Extracts `tenant_id`, `user_id`, `role`.
  3. Asserts role ∈ allowed roles.
  4. Populates request-scoped `Context(tenant_id, user_id, role, correlation_id)`.

**Pseudocode**

```python
from fastapi import Depends, HTTPException

class RequestContext(BaseModel):
    tenant_id: UUID
    user_id: UUID
    role: Literal['OWNER','TECH']
    correlation_id: UUID

_jwks_cache = JWKSCache(ttl=900)

def auth_dependency(allowed_roles: set[str]):
    def _inner(request: Request) -> RequestContext:
        token = extract_bearer(request.headers)
        claims = verify_with_jwks(token, issuer=ISS, audience=AUD, jwks=_jwks_cache)
        tenant_id = claims.get('nmc_tenant_id')
        role = claims.get('nmc_role')
        if tenant_id is None or role not in allowed_roles:
            raise HTTPException(status_code=403)
        ctx = RequestContext(
            tenant_id=UUID(tenant_id),
            user_id=UUID(claims['sub']),
            role=role,
            correlation_id=uuid4(),
        )
        request.state.ctx = ctx
        return ctx
    return _inner

# Usage
@app.post('/scheduling/book')
async def book(..., ctx: RequestContext = Depends(auth_dependency({'OWNER','TECH'}))):
    ...
```

---

## 5) Public API (Identity endpoints)

* `GET /me` → returns user & tenant context (id, email, role, tenant\_id).
* `POST /users/invite` (OWNER) → sends Clerk invite; on accept, we create `id_users` row.
* `POST /users/{id}/role` (OWNER) → change role (`OWNER` or `TECH`).
* `DELETE /users/{id}` (OWNER) → deactivate user (soft delete: flag or revoke in Clerk + local disable).

**AuthZ**: All endpoints require JWT; only OWNER can modify.

---

## 6) Data Model (adds/clarifies)

```sql
CREATE TABLE id_tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE id_users (
  id uuid PRIMARY KEY,         -- matches Clerk user id
  tenant_id uuid NOT NULL REFERENCES id_tenants(id) ON DELETE RESTRICT,
  email text NOT NULL,
  role text NOT NULL CHECK (role IN ('OWNER','TECH')),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
```

**Notes**

* We mirror minimal user data locally for RBAC and auditing; Clerk remains the source of truth for authn.
* We do **not** store passwords.

---

## 7) Context Ingestion (Unauthenticated Webhooks)

Not all inbound requests have JWTs. We establish `tenant_id` via deterministic mapping:

* **Twilio** (Telephony): map `To` number (E.164) → `tenant_id` via provisioned numbers table (Compliance owns). If not found, no-op 200.
* **Stripe** (Billing): parse event, extract `customer` or `subscription` id, look up in `bill_subscriptions` to resolve `tenant_id`.
* **Google/Jobber** (Scheduling): webhook includes calendar/account id; look up by provider ref under a single tenant.

If mapping fails: log WARN with provider refs; return **2xx** to avoid provider retries; create a manual investigation task.

---

## 8) Failure Modes & Policies

* **Role downgrade mid-session**: role checked per request; no long-lived sessions on server; next request reflects new role.
* **User removed**: set `active=false`; 403 on subsequent requests (even if token still valid) by checking local `id_users` state.
* **Missing tenant claim**: treat as configuration error; 403 and log.
* **Clock skew**: rely on JWT `exp`/`nbf`; require NTP on servers.

Retry policy for Clerk admin calls: jitter (base=1s, cap=30s, max\_attempts=6).

---

## 9) Observability

**Metrics**

* `auth_jwt_verify_failures_total{reason}` (signature, audience, issuer, expired)
* `auth_forbidden_total{endpoint}`
* `auth_user_deactivated_total`

**Logs**

* Include `tenant_id` (if resolved), `user_id`, `role`, `endpoint`, `decision` (allow|deny), `reason`.

**Tracing**

* Attach `user_id` and `tenant_id` as span attributes on entry spans.

---

## 10) Testing Strategy

* **JWT verification**: valid/invalid tokens, wrong audience/issuer, expired/nbf.
* **RBAC**: OWNER vs TECH coverage per endpoint.
* **Tenant scoping**: ensure all queries require `tenant_id`; add unit tests that reject empty scope.
* **Webhook resolution**: provider → tenant mapping happy/edge paths.

---

## 11) Config & Defaults

* `CLERK_JWT_CACHE_TTL_SECONDS = 900`
* `AUTH_REQUIRED_ROUTES = true`
* `ALLOW_ANONYMOUS = false` (except webhooks)

---

## 12) Security Notes

* Enforce HTTPS only; HSTS on frontends.
* Strict CORS origins for API.
* Principle of least privilege on DB and platform accounts.
* Log redaction for emails and tokens in error messages.

---

## 13) Open Questions (non-blocking)

* Do we need an **AGENT** role later (non-owner human responders)? (Deferred.)
* Should we allow **multiple tenants per user** (contractors)? (Out of MVP.)
* Self-service domain mapping for SMS numbers vs. manual provisioning? (Compliance doc.)

```

---

## software-design-overview.md

\n```markdown
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
* **Emits:** `ConversationStarted`, `MessageSent`, `HumanTakeoverRequested`

### Catalog & Pricing

* **Commands:** `GET/POST /catalog/items`
* **Emits:** `CatalogUpdated`

### Scheduling

* **Commands:** `POST /scheduling/search`, `POST /scheduling/holds`, `POST /scheduling/book`
* **Emits:** `AppointmentHeld`, `AppointmentBooked`, `AppointmentReleased`

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
| `MessageSent`             | Conversation | Reporting                   |
| `HumanTakeoverRequested`  | Conversation | Ops UI                      |
| `CatalogUpdated`          | Catalog      | Conversation, Reporting     |
| `AppointmentHeld`         | Scheduling   | Conversation                |
| `AppointmentBooked`       | Scheduling   | Reporting, Calendar Sync    |
| `AppointmentReleased`     | Scheduling   | Conversation                |
| `ComplianceStatusChanged` | Compliance   | Conversation (gate sending) |
| `SubscriptionUpdated`     | Billing      | Identity/Feature Gates      |

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
* `calendar_poll_conflicts_total`

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

```

---

## software-design-reporting.md

\n```markdown
# Software Design — Reporting Module (Basic KPIs)

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Reporting (Read Models & KPIs)

> Goal: Provide **basic business KPIs** with event‑driven read models. Zero writes to core domains. Everything is derived from **domain events** via the **DB Outbox** (at‑least‑once). Idempotent, tenant‑scoped, and cheap to query.

---

## 1) Responsibilities

* Maintain **denormalized read models** for tenant KPIs.
* Compute latency and conversion metrics needed by the UI and Ops.
* Persist **revenue attribution** for booked appointments.
* Stay resilient to event replays / reordering.

Out of scope: heavy analytics, multi‑touch attribution, cohort analysis.

---

## 2) KPIs (canonical definitions)

All KPIs are **per tenant** and commonly **per day (UTC)** unless specified.

1. **Missed Call Capture Rate**
   `capture_rate = conversations_started / calls_detected`

   * `calls_detected` = count of `nmc.telephony.CallDetected`.
   * `conversations_started` = count of `nmc.conversation.ConversationStarted` *caused by* a call or inbound SMS on that day (via `correlation_id`).

2. **First Response Time (P50 / P95)**
   From **Twilio inbound** (`CallDetected` or `InboundSmsReceived`) to **first outbound** (`MessageSent(direction='out', status∈{'queued','sent','delivered'})`).

   * Measured in **milliseconds** per `correlation_id` (first pair only).

3. **Conversation Conversion Rate**
   `conversation_to_booking = appointments_booked / conversations_started`

   * `appointments_booked` = count of `nmc.scheduling.AppointmentBooked` where a conversation exists under the same `correlation_id` (if available) or same `caller_phone` on the same day (fallback).

4. **Attributed Revenue**
   Sum of `price_cents` for `AppointmentBooked` (single‑touch attribution to the originating conversation if known). Currency assumed **USD** in MVP.

---

## 3) Events Consumed

* Telephony: `nmc.telephony.CallDetected`, `nmc.telephony.InboundSmsReceived`
* Conversation: `nmc.conversation.ConversationStarted`, `nmc.conversation.MessageSent`
* Scheduling: `nmc.scheduling.AppointmentBooked`, `nmc.scheduling.AppointmentCancelled`
* Catalog (optional for cache): `nmc.catalog.CatalogUpdated`

**Delivery:** via **Outbox** table polling. Ordering is not guaranteed; projections must be idempotent.

---

## 4) Read Models (DDL excerpts)

```sql
-- Tracks the first reply latency per correlation
CREATE TABLE rep_first_responses (
  tenant_id uuid NOT NULL,
  correlation_id uuid NOT NULL,
  inbound_event_id uuid NOT NULL,     -- CallDetected or InboundSmsReceived
  outbound_event_id uuid,             -- first MessageSent(out)
  inbound_occurred_at timestamptz NOT NULL,
  outbound_occurred_at timestamptz,
  first_response_ms int,              -- computed when outbound arrives
  PRIMARY KEY (tenant_id, correlation_id)
);
CREATE INDEX rep_first_resp_tenant_inbound ON rep_first_responses(tenant_id, inbound_occurred_at);

-- Daily rollups per tenant
CREATE TABLE rep_kpi_tenant_daily (
  tenant_id uuid NOT NULL,
  day date NOT NULL,
  calls_detected int NOT NULL DEFAULT 0,
  conversations_started int NOT NULL DEFAULT 0,
  first_resp_p50_ms int,
  first_resp_p95_ms int,
  appointments_booked int NOT NULL DEFAULT 0,
  revenue_cents int NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, day)
);

-- Revenue attribution at booking time
CREATE TABLE rep_revenue_attribution (
  tenant_id uuid NOT NULL,
  appointment_id uuid PRIMARY KEY,
  conversation_id uuid,
  correlation_id uuid,
  service_item_id uuid,
  price_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  booked_at timestamptz NOT NULL
);

-- Projector bookkeeping
CREATE TABLE rep_projector_cursors (
  projector_name text PRIMARY KEY,
  last_event_created_at timestamptz NOT NULL,
  last_seen_outbox_id uuid
);

CREATE TABLE rep_projection_errors (
  id bigserial PRIMARY KEY,
  projector_name text NOT NULL,
  event_id uuid,
  error text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
```

**Notes**

* We persist **first response per correlation** (not per conversation id) to cover the call→SMS flow cleanly.
* Daily rollups are recomputed incrementally; latency percentiles computed from recent `rep_first_responses` entries per day.

---

## 5) Projection Logic (idempotent)

### 5.1 First Response Tracker

* On `CallDetected|InboundSmsReceived`: upsert `(tenant_id, correlation_id, inbound_event_id, inbound_occurred_at)` if not exists.
* On `MessageSent(direction='out')`: if **no** `outbound_event_id` for the `correlation_id`, set it and compute `first_response_ms = outbound_occurred_at - inbound_occurred_at`.

### 5.2 Daily Rollup

For each event’s `occurred_at::date` → `day`:

* `CallDetected` → `calls_detected += 1`.
* `ConversationStarted` → `conversations_started += 1`.
* `AppointmentBooked` → `appointments_booked += 1`, `revenue_cents += price_cents` (from attribution, see below).
* **Latency percentiles**: recompute p50/p95 for `first_response_ms` where `inbound_occurred_at::date = day`.

### 5.3 Revenue Attribution

* On `AppointmentBooked`:

  * Determine **price**. MVP chooses the **catalog price at time of booking** by reading `catalog_service_items` (or a cached snapshot).
  * Insert into `rep_revenue_attribution` with `conversation_id`/`correlation_id` if available.
* On `AppointmentCancelled`:

  * Optional MVP: subtract price if canceled same day; otherwise leave revenue as booked (simplify for now).

**Late/out‑of‑order events** are handled because updates are **UPSERT** and rollups are **recomputed** from atomic facts.

---

## 6) APIs (read‑only)

* `GET /reporting/kpi/daily?from=2025-09-01&to=2025-09-30` → list of `rep_kpi_tenant_daily` rows.
* `GET /reporting/first-response?since=2025-09-01` → recent `rep_first_responses` (for SLO panels).
* `GET /reporting/revenue?from=...&to=...` → aggregated sum of `rep_revenue_attribution`.

All endpoints require `tenant_id` and role `OWNER` or `TECH`.

---

## 7) Observability

**Metrics**

* `reporting_projector_lag_seconds` (now − newest processed outbox `created_at`)
* `reporting_projection_errors_total{projector}`
* `reporting_rollup_duration_ms{projector}`

**Logs**

* Projector start/stop, batch sizes, cursor positions. Log and continue on per‑event failures.

---

## 8) Performance & Retention

* Index `rep_first_responses(tenant_id, inbound_occurred_at)` for time‑range queries.
* Daily table is tiny (one row per tenant per day). Reads are cheap.
* Retain `rep_first_responses` **13 months** (align with metadata). `rep_revenue_attribution` retained indefinitely (accounting).

---

## 9) Testing Strategy

* **Idempotency**: replay each event 5x → identical read models.
* **Reordering**: deliver outbound before inbound (should not compute latency until inbound exists); then deliver inbound; ensure computation is correct after both.
* **Percentiles**: verify p50/p95 with deterministic datasets.
* **Attribution**: confirm price comes from catalog snapshot at booking time.

---

## 10) Open Questions (non‑blocking)

* Do we need multi‑currency support soon? (If yes, partition revenue by currency and avoid summing across.)
* Should cancellations decrement revenue? (MVP treats revenue at booking time; finance rules can evolve.)

```

---

## software-design-scheduling.md

\n```markdown
# Software Design — Scheduling Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Scheduling & Availability

> Goal: Offer only truly available appointment slots (duration-aware), prevent double-booking with database constraints, and keep calendars in sync using webhook-first with polling fallback. Emits domain events for downstream consumers.

---

## 1) Responsibilities

* Maintain resource calendars (per technician or team).
* Compute availability windows for requested **durations**.
* Manage **holds** (temporary reservations with TTL) and convert to **appointments** atomically.
* Synchronize with external calendars (Google, Jobber): webhook-first, poll fallback.
* Publish domain events: `AppointmentHeld`, `AppointmentBooked`, `AppointmentReleased`.

Out of scope: pricing logic, conversation UX, identity, billing.

---

## 2) Domain Model

### Aggregates / Entities

* **ResourceCalendar** (`resource_id`, provider, provider\_ref, active)
* **Hold** (`id`, `tenant_id`, `resource_id`, `timeslot[tstzrange]`, `expires_at`, `created_by`)
* **Appointment** (`id`, `tenant_id`, `resource_id`, `timeslot[tstzrange]`, `service_item_id`, `customer_phone`)

### Value Objects

* **TimeSlot**: `tstzrange` (UTC)
* **Duration**: minutes (int > 0)

### Invariants

1. No overlapping `appointments` for the same `resource_id`.
2. Holds expire after **15 minutes** (configurable); expired holds do not block booking.
3. Offers must match **full service duration** from the catalog.
4. All writes must include `tenant_id`.

---

## 3) Public API (internal HTTP)

### Search Availability

`POST /scheduling/search`

```json
{
  "resource_ids": ["<uuid>"],
  "duration_minutes": 120,
  "window_start": "2025-09-01T09:00:00Z",
  "window_end": "2025-09-02T09:00:00Z",
  "granularity_minutes": 15
}
```

**Response**

```json
{
  "slots": [
    {"resource_id": "<uuid>", "start": "2025-09-01T17:00:00Z", "end": "2025-09-01T19:00:00Z"},
    {"resource_id": "<uuid>", "start": "2025-09-01T20:00:00Z", "end": "2025-09-01T22:00:00Z"}
  ]
}
```

### Create Hold

`POST /scheduling/holds`

```json
{ "resource_id": "<uuid>", "start": "2025-09-01T17:00:00Z", "end": "2025-09-01T19:00:00Z" }
```

**Response**

```json
{ "hold_id": "<uuid>", "expires_at": "2025-09-01T17:15:00Z" }
```

### Book Appointment

`POST /scheduling/book`

```json
{
  "hold_id": "<uuid>",
  "service_item_id": "<uuid>",
  "customer_phone": "+13105551212"
}
```

**Response**

```json
{ "appointment_id": "<uuid>" }
```

### Cancel Appointment

`POST /scheduling/cancel`

```json
{ "appointment_id": "<uuid>" }
```

**Response**

```json
{ "ok": true }
```

---

## 4) Algorithms

### 4.1 Availability Computation (duration-aware)

1. Pull **busy events** = confirmed `sched_appointments` + non-expired `sched_holds`.
2. Merge overlapping busy ranges by `resource_id`.
3. Compute free ranges within `[window_start, window_end]`.
4. Slide a window of size `duration_minutes` with step `granularity_minutes` (default 15) to generate candidate slots.
5. Optionally respect business hours (future enhancement, not MVP).

### 4.2 Hold Creation

* Validate the requested slot is still free (no overlap with `appointments` or non-expired `holds`).
* Insert `sched_holds` row with `expires_at = now() + 15 minutes`.
* Emit `AppointmentHeld` via outbox with payload `{ hold_id, resource_id, timeslot }`.

### 4.3 Booking Transaction

* `SELECT ... FOR UPDATE` the hold (not expired, correct `tenant_id`).
* Insert `sched_appointments` (GiST constraint enforces no overlap).
* Delete the hold.
* Emit `AppointmentBooked` via outbox with payload `{ appointment_id, resource_id, timeslot, service_item_id }`.

### 4.4 Release

* Expiration job deletes stale holds and emits `AppointmentReleased`.

---

## 5) External Sync (Google/Jobber)

### Webhook-first

* Google/Jobber webhooks → mark affected `resource_id` dirty; enqueue sync task.
* Sync task fetches authoritative busy ranges and upserts a **shadow table** `sched_ext_busy(resource_id, timeslot)`.

### Poll fallback

* Poll every **60s (Google)** / **120s (Jobber)** per connected calendar.
* Diff remote busy blocks vs local `sched_ext_busy`; update if changed; record metric `calendar_poll_conflicts_total` when conflicts detected.

### Conflict Resolution

* External busy entry overlapping a local appointment triggers an ops alert (should be rare if we own the bookings).

---

## 6) Data Model (selected DDL)

```sql
CREATE TABLE sched_ext_busy (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  source text NOT NULL CHECK (source IN ('google','jobber')),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sched_ext_busy_idx ON sched_ext_busy USING gist (resource_id, timeslot);
```

**Important indexes**

* `sched_appointments USING gist(resource_id, timeslot)`
* `sched_holds USING gist(resource_id, timeslot)`
* `sched_ext_busy USING gist(resource_id, timeslot)`

---

## 7) Events (Produced & Consumed)

**Produced**

* `AppointmentHeld { schema_version, hold_id, resource_id, timeslot }`
* `AppointmentBooked { schema_version, appointment_id, resource_id, timeslot, service_item_id }`
* `AppointmentReleased { schema_version, hold_id, resource_id, timeslot }`

**Consumed**

* `CatalogUpdated` (optional) — for duration lookup caching.
* `ComplianceStatusChanged` (read-only) — no impact, but sending confirmations may be gated elsewhere.

Versioning: semantic `schema_version` per event.

---

## 8) Failure Modes & Policies

* **Concurrent booking race** → DB exclusion constraint guarantees consistency; return 409 and instruct caller to re-search.
* **Hold expired** → 410 Gone.
* **Calendar downstream failure** → appointment still books locally; sync retries with jitter.
* **Clock skew** → use DB `now()` only; never trust client timestamps for invariants.
* **Large windows** → enforce max search span (e.g., 14 days) to cap compute cost.

Retry policy: exponential backoff with jitter (base=1s, cap=30s, max\_attempts=6).

---

## 9) Observability

**Metrics**

* `scheduling_search_p95_ms`
* `scheduling_hold_success_total`, `scheduling_hold_conflict_total`
* `scheduling_book_p95_ms`, `scheduling_book_conflict_total`
* `calendar_sync_errors_total`, `calendar_poll_conflicts_total`

**Tracing**

* Correlate `conversation_id` → `hold_id` → `appointment_id` through event metadata.

**Logs**

* Structured with `tenant_id`, `resource_id`, `timeslot`, `correlation_id`.

---

## 10) Testing Strategy

* **Property tests**: generate random busy blocks, assert no overlaps post-booking.
* **Contract tests**: API shapes (`search`, `holds`, `book`) and event payloads.
* **Idempotency tests**: duplicate `book` with same `hold_id` yields single appointment.
* **Time-based tests**: hold expiration, DST transitions.

---

## 11) Config & Defaults

* `HOLD_TTL_MINUTES = 15`
* `SEARCH_GRANULARITY_MINUTES = 15`
* `POLL_INTERVAL_GOOGLE_SECONDS = 60`
* `POLL_INTERVAL_JOBBER_SECONDS = 120`

---

## 12) Security & Access

* Only `OWNER` and `TECH` roles may create holds/bookings, scoped by `tenant_id`.
* No cross-tenant access; all queries filter by `tenant_id`.

---

## 13) Open Questions (none blocking MVP)

* Business hours / blackout windows per tenant.
* Resource skills/tags to filter which technician can perform a service item.
* Buffer times between appointments.

```

---

## software-design-telephony.md

\n```markdown
# Software Design — Telephony Ingestion Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Telephony Ingestion

> Goal: Reliably ingest Twilio webhooks (Voice status + SMS inbound), detect **missed calls**, and emit domain events (`CallDetected`, `InboundSmsReceived`) with strict idempotency and signature verification. Keep the path to first SMS **fast** by minimizing logic here and handing off to Conversation.

---

## 1) Responsibilities

* Verify and ingest **Twilio** webhooks (voice status, inbound SMS) with signature validation.
* Detect **missed calls** suitable for SMS follow-up.
* Normalize phone numbers to **E.164**; attach `tenant_id` context.
* Emit domain events to **Outbox**: `nmc.telephony.CallDetected`, `nmc.telephony.InboundSmsReceived`.
* Maintain minimal call/message ingest logs for observability and audits.

**Non-goals:** composing replies, quoting, scheduling, or compliance gating (handled by Conversation/Compliance modules).

---

## 2) Invariants & Guarantees

1. **Idempotency:** Every webhook is deduped by `(provider='twilio', event_id)` in `webhook_events`.
2. **Signature:** `X-Twilio-Signature` must validate; otherwise **401** and drop.
3. **Tenant scoping:** All emitted events include `tenant_id`; inbound phone numbers are mapped to tenant by our phone-number configuration (per-tenant receiving numbers).
4. **Latency:** Minimal processing; heavy logic belongs in consumers to meet global **P95 ≤ 5s** SLO for first SMS.

---

## 3) Data Model (adds)

```sql
CREATE TABLE tel_calls (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  from_phone text NOT NULL,
  to_phone text NOT NULL,
  status text NOT NULL,          -- no-answer|busy|failed|completed|...
  provider_ref text NOT NULL,    -- CallSid
  duration_seconds int,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX tel_calls_tenant_created_idx ON tel_calls(tenant_id, created_at DESC);

CREATE TABLE tel_inbound_sms (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  from_phone text NOT NULL,
  to_phone text NOT NULL,
  provider_ref text NOT NULL,    -- MessageSid
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

> Note: These are **ingest logs** for ops/forensics; the source of truth for user-visible messages is in `conv_messages`.

---

## 4) Public Endpoints (Webhooks)

### 4.1 Voice Status — Missed Call Detection

`POST /webhooks/twilio/voice-status`

* **Verify** `X-Twilio-Signature`.
* **Idempotency key**: `(provider='twilio', event_id=<CallSid:CallStatus>)`.
* **Parse** form-encoded fields (examples):

  * `CallSid`, `From`, `To`, `CallStatus` in `{no-answer,busy,failed,completed,...}`
  * Optional: `CallDuration`, `AnsweredBy` (if AMD enabled)

**Missed-call rule (MVP):**

* If `CallStatus ∈ { 'no-answer','busy','failed' }` → **missed**.
* Optional enhancement (config flag): if `CallStatus='completed'` AND `CallDuration < 10s` AND `AnsweredBy NOT IN ('human')` → treat as missed (voicemail/short ring).

**Actions:**

1. Persist `tel_calls` row.
2. Emit `nmc.telephony.CallDetected` to Outbox with payload `{ call_id, from_phone, to_phone, reason, provider_ref }`.
3. Return **200**.

### 4.2 SMS Inbound

`POST /webhooks/twilio/sms-inbound`

* **Verify** `X-Twilio-Signature`.
* **Idempotency key**: `(provider='twilio', event_id=<MessageSid>)`.
* **Parse**: `From`, `To`, `Body`, `MessageSid`, `MessagingServiceSid`.

**Actions:**

1. Persist `tel_inbound_sms` row.
2. Emit `nmc.telephony.InboundSmsReceived` with payload `{ message_id, from_phone, to_phone, body, provider_ref }`.
3. Return **200**.

---

## 5) Event Emissions (Outbox)

All emitted events follow the **Event Catalog** envelope with `schema_version` **`1.0.0`**.

* `nmc.telephony.CallDetected`

  * `payload`: `{ call_id, from_phone, to_phone, reason: 'no-answer'|'busy'|'failed'|'short-complete', provider_ref }`
  * **Consumers**: Conversation (first reply), Reporting

* `nmc.telephony.InboundSmsReceived`

  * `payload`: `{ message_id, from_phone, to_phone, body, provider_ref }`
  * **Consumers**: Conversation

**Correlation:**

* Create a **`correlation_id` per call** (UUID). For subsequent inbound SMS from the same `from_phone` within a short window (e.g., 10 minutes), reuse the correlation if available; otherwise generate a new one. Conversation will carry the correlation forward.

---

## 6) Mapping Numbers → Tenants

* Maintain a configuration map: `tenant_id ↔ receiving_phone_e164` (from Compliance/Provisioning).
* On webhook, resolve `To` to a **single** `tenant_id`. If unknown, 404 (or 200 with no-op, configurable).

---

## 7) Security & Verification

* **Twilio signature**: validate using account auth token over the **full URL** and **raw body**.
* **HTTPS only**; reject plain HTTP.
* **Rate limiting**: per-IP/per-tenant basic throttle to absorb bursts; do not throttle below provider expectations.

**Pseudocode:**

```python
sig = request.headers["X-Twilio-Signature"]
full_url = request.url  # include query
raw = request.body
if not twilio_validate(sig, full_url, raw):
    return 401

# dedupe
key = ("twilio", f"{payload['MessageSid']}:{payload.get('MessageStatus','')}")
if webhook_dedupe.exists(key):
    return 200
webhook_dedupe.save(key, hash(raw))

# emit event
outbox.emit(...)
return 200
```

---

## 8) Observability

**Metrics**

* `telephony_webhook_requests_total{endpoint,status}`
* `telephony_webhook_verify_failures_total`
* `telephony_missed_calls_total{reason}`
* `telephony_inbound_sms_total`
* `webhook_dedupe_hits_total{provider='twilio'}`

**Logs**

* Include `tenant_id`, `provider_ref (CallSid|MessageSid)`, `from`, `to`, `event`.

**Tracing**

* New `correlation_id` for each call; propagate to Conversation. Use `causation_id` to link `InboundSmsReceived` if it follows a call.

---

## 9) Error Handling

* **Signature invalid** → 401, do not write dedupe, no event.
* **Duplicate webhook** → write dedupe hit metric and return 200.
* **Unknown tenant number** → 200 with no-op (to avoid Twilio retries), warn log with details.
* **DB transient error** → retry with jitter (max attempts 6). If still failing, write to error log table and return 200 to Twilio (we will reconcile via ops).

---

## 10) Testing Strategy

* **Signature verification**: known-good and tampered payloads.
* **Idempotency**: replay same webhook 5x → single ingest row and single Outbox event.
* **Missed-call classification**: table-driven tests for statuses and optional short-complete rule.
* **Number-to-tenant mapping**: unknown numbers, multiple numbers per tenant.
* **Performance**: ensure webhook handler p95 < 50ms server-side (excluding network) to protect the 5s SLO budget.

---

## 11) Config & Defaults

* `MISSED_CALL_STATUSES = ['no-answer','busy','failed']`
* `TREAT_SHORT_COMPLETED_AS_MISSED = false` (MVP)
* `SHORT_COMPLETED_MAX_SECONDS = 10`
* `CORRELATION_REUSE_WINDOW_MINUTES = 10`

---

## 12) Open Questions (non-blocking)

* Do we want **Answering Machine Detection (AMD)** to refine missed vs voicemail? (Costs/latency trade-off.)
* Multiple receiving numbers per tenant? (Likely yes later; mapping already supports 1\:N.)
* Spam detection for inbound SMS? (Defer to later.)

```

---

## testing-strategy.md

\n```markdown
# Testing Strategy — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/QA • **Scope:** Modular Monolith (FastAPI + workers), Next.js UI, single Postgres, DB‑backed Outbox

> Brutal principle: ship only what we can test. Primary SLO is **P95 ≤ 5s** first SMS. All tests are tenant‑scoped. All integrations are idempotent.

---

## 1) Test Pyramid & Tools

* **Unit tests** (fast, isolated): **pytest** for Python, **vitest/jest** for frontend utilities.
* **Integration tests** (module + DB): **pytest + Testcontainers** (Postgres) — no mocks for DB; use real migrations.
* **Contract tests** (between modules & external providers): **schemathesis** (OpenAPI) for HTTP, sample webhook payloads for providers.
* **End‑to‑End (E2E)** (user flows): **Playwright** for UI + API; run against ephemeral DB.
* **Performance/SLO**: **locust/k6** synthetic flow; SLO check in staging pipeline.

**General rules**

* Deterministic tests: freeze time where needed (`freezegun`).
* Every test provides `tenant_id`; cross‑tenant access is a failure.
* No network in unit tests; external HTTP is faked.

---

## 2) Coverage Targets & Gates (CI)

* **Backend line coverage** ≥ **85%**, **branches** ≥ **75%**; critical paths (Conversation, Scheduling) **90%+**.
* **Contract tests** must pass for public/internal APIs (OpenAPI).
* **Migrations**: apply and rollback successfully on a pristine DB in CI.
* **Lint/type**: ruff/flake8 + mypy for backend; eslint/types for UI.
* **SLO pre‑flight** (staging nightly): synthetic call→SMS flow P95 ≤ 5s.

PRs blocked unless all gates are green.

---

## 3) Test Data & Fixtures

* **Factories/builders** per aggregate (e.g., `make_conversation`, `make_service_item`).
* **Tenant fixture** provides `tenant_id`, default OWNER/TECH users.
* **Phone numbers** in **E.164**; aliases lowercased.
* **Clock** fixture for `now()`; use DB time in integration tests.
* **Webhooks**: golden samples for Twilio/Stripe/Google/Jobber with valid signatures.

---

## 4) Module‑Specific Test Plans

### 4.1 Telephony Ingestion

* **Signature verification**: valid vs tampered payloads → 200 vs 401.
* **Idempotency**: replay the same webhook 5× → one `webhook_events` row and one Outbox event.
* **Missed call classification**: table‑driven for `no-answer|busy|failed` (+ optional short‑complete rule off by default).
* **Number→tenant mapping**: unknown number → 200 no‑op + WARN.

### 4.2 Conversation & Messaging

* **State machine**: `open ↔ human`, `* → blocked`, auto‑close.
* **Compliance gate**: outbound denied when not approved → 403; unblocks on `ComplianceStatusChanged(approved)`.
* **First reply flow**: inbound → first outbound within budget (mock Twilio client latency to 0ms in unit; integration measures our server time only).
* **Idempotent delivery updates**: multiple status callbacks update once.
* **Template rendering**: missing variables fail fast with clear error.

### 4.3 Scheduling & Availability

* **No double‑booking**: property tests generate random busy blocks; assertion: DB constraint denies overlap.
* **Hold TTL**: expires at 15m; booking after expiry → 410.
* **Booking transaction**: hold → appointment → outbox emitted; idempotent on retries.
* **External sync**: webhook then poll; shadow table updated with minimal drift.

### 4.4 Catalog & Pricing

* **CRUD invariants**: unique name per tenant; price/duration bounds.
* **Matching**: aliases, ranking (length > priority > exact name).
* **Quoting**: inactive item → 410; values match DB.

### 4.5 Identity & Access

* **JWT verification**: issuer/audience/exp/nbf; bad token → 401.
* **RBAC**: OWNER vs TECH route access; tenant scoping enforced.
* **User deactivation**: active=false → 403 even if JWT valid.

### 4.6 Compliance

* **Submission**: creates brand/campaign pending.
* **Gating**: blocked before approval; event on approve/reject.
* **Phone mapping**: unique per tenant; webhook routing respects mapping.
* **STOP/HELP**: opt‑out ledger updated; no further sends.

### 4.7 Billing

* **Checkout**: session created with `client_reference_id=tenant_id`.
* **Webhooks**: idempotent mirror to `bill_subscriptions`; events emitted.
* **State transitions**: created→active, active→past\_due→active, active→canceled.

### 4.8 Reporting

* **First response tracker**: outbound before inbound → no latency until both present; then computed.
* **Daily rollups**: p50/p95 recompute with new data; UPSERT semantics.
* **Revenue attribution**: price snapshot at booking time.

---

## 5) Contract Tests (APIs & Events)

* **HTTP APIs**: generate tests from OpenAPI (schemathesis) covering edge cases (missing tenant header, bad role, invalid payloads).
* **Module boundaries**: provider/consumer tests for Conversation↔Scheduling↔Catalog. Example: Conversation consumes `AppointmentHeld` and sends a message; Scheduling consumes `CatalogUpdated` cache invalidation.
* **Event schemas**: validate `schema_version` and payload shape against `event-catalog.md` JSON Schemas.

---

## 6) E2E Flows (Playwright)

1. **Missed Call → First SMS**

   * Simulate Twilio voice status webhook → assert outbound queued within budget (mock Twilio status to success).
2. **Quote & Book**

   * Inbound SMS describes job → `/catalog/match` → show 2–3 slot offers → hold → book → confirmation.
3. **Human Takeover**

   * UI takeover → AI paused → human message sent.
4. **Compliance Block**

   * Tenant pending → outbound blocked; approve → unblocked.
5. **Billing**

   * Checkout session link visible; webhook updates plan; banner reflects state.

Each E2E run seeds an **ephemeral tenant** and tears it down.

---

## 7) Performance & SLO Tests

* **Synthetic SLO** (staging, nightly): end‑to‑end missed call → first SMS; collect 100 samples; assert **P95 ≤ 5s**.
* **Load test**: 50 concurrent missed calls/minute for 10 minutes; verify outbox lag < 60s and DB CPU < 80%.
* **Scheduling search**: p95 under 300ms for typical windows.

---

## 8) Resilience & Chaos

* **Provider 5xx/timeout**: simulate Twilio/Google/Jobber failures; verify retry with jitter and no duplicate side effects.
* **Outbox worker crash**: kill worker mid‑batch; ensure `FOR UPDATE SKIP LOCKED` prevents lost work.
* **Clock skew**: ensure DB `now()` is used for invariants (holds, booking, SLO trackers).

---

## 9) CI/CD Integration

* **Stages**: unit → integration (with Testcontainers) → contract → e2e (headless) → package → deploy → staging SLO job (nightly).
* **Artifacts**: coverage HTML, junit XML, cucumber JSON (Playwright), DB migration logs.
* **Flakes**: tests using backoff/jitter must stub RNG to deterministic sequence.

---

## 10) Test Utilities & Fakes

* **HTTP fakes** for Twilio/Stripe/Google/Jobber with recorded responses.
* **Signature helpers** to generate valid webhook signatures for tests.
* **Event bus helper** to insert into `outbox_events` and drain synchronously in tests.
* **Phone assertions** to check E.164 formatting and masking in logs.

---

## 11) Definition of Done (per PR)

* New logic covered by unit + integration tests.
* If an API or event changed: contract tests updated; **schema\_version** bump evaluated.
* Migrations added with rollback notes; CI migration test passes.
* Observability: new metrics/logs/traces added as specified; dashboards updated if needed.

---

## 12) Open Questions (non‑blocking)

* Do we need browser visual regression tests now (Playwright snapshots)? (Probably later.)
* Should we include canary deployments with SLO probes before full rollout? (Future.)

```
