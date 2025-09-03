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
