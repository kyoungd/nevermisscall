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
