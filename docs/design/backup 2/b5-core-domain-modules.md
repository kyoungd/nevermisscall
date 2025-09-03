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





# Software Design — Conversation & Messaging Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Conversation & Messaging

> Goal: Convert missed calls and inbound SMS into structured conversations, drive AI-led replies and booking flows, support rapid human takeover, and meet the **P95 ≤ 5s** first-response SLO. All cross-module effects go through the **Outbox**. Messaging is hard-gated by 10DLC compliance status.
**See also:** Compliance Module → *Enforcement* (gating rules) and ADR-0004/Event Catalog for event naming/versioning.

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
  5. Persist `Message(out)` with `status='queued'` + write **Outbox** `ConversationStarted`, `MessageRecorded`, and `OutboundQueued`.

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
* Update `conv_messages.status` to latest state; emit `MessageRecorded`/`DeliveryUpdated` events if changed.

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

* `slo_first_sms_p95_seconds` (Conversation-only view; should be ≤ global SLO)
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

All emitted events **must** follow the **Event Catalog** envelope and versioning policy (ADR-0004), with `schema_version` **`1.0.0`** for MVP.

* `nmc.telephony.CallDetected`

  * `payload`: `{ call_id, from_phone, to_phone, reason: 'no-answer'|'busy'|'failed', provider_ref }`
  * **Consumers**: Conversation (first reply), Reporting

* `nmc.telephony.InboundSmsReceived`

  * `payload`: `{ message_id, from_phone, to_phone, body, provider_ref }`
  * **Consumers**: Conversation

**Correlation:**

* Create a **`correlation_id` per call** (UUID). For subsequent inbound SMS from the same `from_phone` within a short window (e.g., 10 minutes), reuse the correlation if available; otherwise generate a new one. Conversation will carry the correlation forward.

---

## 6) Mapping Numbers → Tenants

* Maintain a configuration map: `tenant_id ↔ receiving_phone_e164` (from Compliance/Provisioning).
* On webhook, resolve `To` to a **single** `tenant_id`. If unknown, **200 with no-op** (prevent provider retries) and WARN log.
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
* **Missed-call classification**: table-driven tests for statuses; no short-call special-case.
* **Number-to-tenant mapping**: unknown numbers, multiple numbers per tenant.
* **Performance**: ensure webhook handler p95 < 50ms server-side (excluding network) to protect the 5s SLO budget.

---

## 11) Config & Defaults

* `MISSED_CALL_STATUSES = ['no-answer','busy','failed']`
* `CORRELATION_REUSE_WINDOW_MINUTES = 10`

---

## 12) Open Questions (non-blocking)

* Do we want **Answering Machine Detection (AMD)** to refine missed vs voicemail? (Costs/latency trade-off.)
* Multiple receiving numbers per tenant? (Likely yes later; mapping already supports 1\:N.)
* Spam detection for inbound SMS? (Defer to later.)





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
* `AppointmentCancelled { schema_version, appointment_id, resource_id, timeslot, cancelled_reason }`

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
