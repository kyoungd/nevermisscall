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
