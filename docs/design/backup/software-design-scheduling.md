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
