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
