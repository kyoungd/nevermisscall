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
