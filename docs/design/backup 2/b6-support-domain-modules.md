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
   From **Twilio inbound** (`CallDetected` or `InboundSmsReceived`) to **first outbound enqueue** (`OutboundQueued`).

   * Measured in **milliseconds** per `correlation_id` (first pair only).
   * Note: use `MessageRecorded` for inbound/outbound **persistence counts**; use `OutboundQueued` for **first-response timing**.

3. **Conversation Conversion Rate**
   `conversation_to_booking = appointments_booked / conversations_started`

   * `appointments_booked` = count of `nmc.scheduling.AppointmentBooked` where a conversation exists under the same `correlation_id` (if available) or same `caller_phone` on the same day (fallback).

4. **Attributed Revenue**
   Sum of `price_cents` for `AppointmentBooked` (single‑touch attribution to the originating conversation if known). Currency assumed **USD** in MVP.

---

## 3) Events Consumed

* Telephony: `nmc.telephony.CallDetected`, `nmc.telephony.InboundSmsReceived`
* Conversation: `nmc.conversation.ConversationStarted`, `nmc.conversation.MessageRecorded`, `nmc.conversation.OutboundQueued`
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
  outbound_event_id uuid,             -- first OutboundQueued
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
* On `OutboundQueued`: if **no** `outbound_event_id` exists for the `correlation_id`, set it and compute `first_response_ms = outbound_occurred_at - inbound_occurred_at`.


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
