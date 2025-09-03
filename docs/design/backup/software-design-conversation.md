# Software Design — Conversation & Messaging Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Conversation & Messaging

> Goal: Convert missed calls and inbound SMS into structured conversations, drive AI-led replies and booking flows, support rapid human takeover, and meet the **P95 ≤ 5s** first-response SLO. All cross-module effects go through the **Outbox**. Messaging is hard-gated by 10DLC compliance status.

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
  5. Persist `Message(out)` with `status='queued'` + write **Outbox** `ConversationStarted` and `MessageSent`.

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
* Update `conv_messages.status` to latest state; emit `MessageSent`/`DeliveryUpdated` events if changed.

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

* `first_sms_p95_seconds` (Conversation-only view; should be ≤ global SLO)
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
