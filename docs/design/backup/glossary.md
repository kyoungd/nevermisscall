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
