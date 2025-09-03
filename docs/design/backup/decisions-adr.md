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
