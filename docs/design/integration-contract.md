# Integration Contracts — Minimal (Small Project)

**Architecture baseline**: Modular monolith, **2 contexts** — `Conversation & Comms` and `Fulfillment`. Contracts below are the **minimum** needed to keep boundaries honest while staying simple.

**Notation**: JSON payloads with types; times are ISO-8601 UTC (`Z`). E.164 for phone numbers.

---

## 1) Internal Context Boundary (In-Process APIs)

> Function contracts between **Conversation** (caller) and **Fulfillment** (callee). Keep pure; no side effects besides their own data.

### 1.1 `projectAvailability(criteria) → AvailabilityResponse`

**Request**

```json
{
  "v": 1,
  "tenantId": "uuid",
  "criteria": {
    "serviceId": "uuid",
    "windowStart": "2025-09-02T00:00:00Z",
    "windowEnd": "2025-09-09T00:00:00Z",
    "locationId": "uuid|null",
    "maxOptions": 5
  }
}
```

**Response**

```json
{
  "v": 1,
  "tenantId": "uuid",
  "generatedAt": "2025-09-02T12:00:00Z",
  "slots": [
    {"resourceId": "uuid", "start": "2025-09-03T16:00:00Z", "end": "2025-09-03T18:00:00Z"}
  ]
}
```

**Errors**: none (empty `slots` if none). Budget: ≤300ms.

### 1.2 `createReservation(slot) → ReservationCreated`

**Request**

```json
{
  "v": 1,
  "tenantId": "uuid",
  "slot": {"resourceId": "uuid", "start": "2025-09-03T16:00:00Z", "end": "2025-09-03T18:00:00Z"},
  "ttlSeconds": 600
}
```

**Response**

```json
{
  "v": 1,
  "tenantId": "uuid",
  "reservationId": "uuid",
  "slot": {"resourceId": "uuid", "start": "2025-09-03T16:00:00Z", "end": "2025-09-03T18:00:00Z"},
  "expiresAt": "2025-09-03T16:10:00Z"
}
```

**Errors**

```json
{"code":"SLOT_UNAVAILABLE","message":"Slot is no longer free."}
```

### 1.3 `confirmAppointment(reservationId) → AppointmentBooked`

**Request**

```json
{"v":1,"tenantId":"uuid","reservationId":"uuid"}
```

**Response**

```json
{
  "v": 1,
  "tenantId": "uuid",
  "appointmentId": "uuid",
  "slot": {"resourceId": "uuid", "start": "2025-09-03T16:00:00Z", "end": "2025-09-03T18:00:00Z"},
  "externalRefs": []
}
```

**Errors**

```json
{"code":"RESERVATION_EXPIRED","message":"Reservation is no longer active."}
```

---

## 2) External Edge Contracts (HTTP)

### 2.1 CPaaSRef Webhooks → Conversation

**Auth**: HMAC header `X-Signature` (shared secret); reject if invalid.
**Correlation**: Optional `correlationId` may be included by CPaaSRef; if present, we propagate it **unchanged end-to-end**.

**Missed Call** — `POST /webhooks/cpaasRef/missed-call`

```json
{
  "v": 1,
  "tenantId": "uuid",
  "correlationId": "string",
  "callId": "string",
  "from": "+15551234567",
  "to": "+15557654321",
  "startedAt": "2025-09-02T11:59:55Z",
  "endedAt": "2025-09-02T12:00:05Z"
}
```

**Inbound SMS** — `POST /webhooks/cpaasRef/inbound-sms`

```json
{
  "v": 1,
  "tenantId": "uuid",
  "correlationId": "string",
  "messageId": "string",
  "from": "+15551234567",
  "to": "+15557654321",
  "body": "text",
  "receivedAt": "2025-09-02T12:01:00Z"
}
```

**Delivery Status** — `POST /webhooks/cpaasRef/delivery-status`

```json
{
  "v": 1,
  "tenantId": "uuid",
  "correlationId": "string",
  "messageId": "string",
  "status": "QUEUED|SENT|DELIVERED|FAILED",
  "at": "2025-09-02T12:01:03Z",
  "cpaasRef": "string",
  "error": "string|null"
}
```

**Responses**: `204 No Content` if accepted; `401` on bad signature.

### 2.2 Outbound SMS (internal → CPaaSRef via Comms adapter)

**Function**: `sendSms(clientMessageId, to, body) → { messageId, acceptedAt, cpaasRef }`

* **Idempotency**: `clientMessageId` prevents duplicates.
* **Timeout**: 2s; 2 retries with jitter; give up and record `FAILED`.

### 2.3 Calendar Sync (Fulfillment → Provider)

**POST /provider/events** (abstracted by ACL)

```json
{
  "summary": "Appointment",
  "start": {"dateTime": "2025-09-03T16:00:00Z"},
  "end": {"dateTime": "2025-09-03T18:00:00Z"},
  "extendedProperties": {"private": {"tenantId": "uuid", "appointmentId": "uuid"}}
}
```

**Response**

```json
{"id": "provider-event-id", "status": "confirmed"}
```

---

## 3) Domain Events (In-Process Catalog)

> Emitted after successful commits. Versioned; consumers must be tolerant to additive fields. All events include an **optional** `"correlationId": "string"` which is **propagated unchanged end-to-end**.

```json
{
  "MissedCallDetected": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "callId": "string", "from": "+1555…", "to": "+1555…", "startedAt": "ISO", "endedAt": "ISO"
  },
  "ConversationOpened": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "conversationId": "uuid", "caller": "+1555…", "openedAt": "ISO"
  },
  "AutoReplySent": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "conversationId": "uuid", "messageId": "uuid", "clientMessageId": "string", "to": "+1555…", "acceptedAt": "ISO", "cpaasRef": "string"
  },
  "MessageDeliveryUpdated": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "messageId": "uuid", "status": "QUEUED|SENT|DELIVERED|FAILED", "at": "ISO", "cpaasRef": "string", "error": "string|null"
  },
  "ComplianceOptOutReceived": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "from": "+1555…", "at": "ISO"
  },
  "SlotsProjected": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "requestId": "uuid", "criteria": {}, "slots": [{"resourceId":"uuid","start":"ISO","end":"ISO"}], "generatedAt": "ISO"
  },
  "ReservationCreated": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "reservationId": "uuid", "slot": {"resourceId":"uuid","start":"ISO","end":"ISO"}, "expiresAt": "ISO"
  },
  "ReservationExpired": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "reservationId": "uuid"
  },
  "AppointmentBooked": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "appointmentId": "uuid", "slot": {"resourceId":"uuid","start":"ISO","end":"ISO"}, "externalRefs": []
  },
  "ExternalCalendarSyncSucceeded": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "appointmentId": "uuid", "provider": "string", "providerRef": "string"
  },
  "ExternalCalendarSyncFailed": {
    "v": 1, "tenantId": "uuid", "correlationId": "string", "appointmentId": "uuid", "provider": "string", "error": "string"
  }
}
```

**Triggers & Consumers (minimal)**

* `MissedCallDetected` → Conversation opens.
* `AutoReplySent` → Analytics (optional).
* `SlotsProjected` → Conversation proposes options.
* `ReservationCreated`/`Expired` → Conversation updates UI copy.
* `AppointmentBooked` → Conversation confirms; triggers calendar sync.

---

## 4) Data Transformation Rules (Slim, Enforceable)

### 4.1 Telephony/SMS Normalization

* Phone numbers → **E.164**; reject non-E.164 at boundaries.
* Collapse whitespace; trim message bodies; cap at 1600 chars; store original + normalized.
* Map CPaaSRef delivery states → internal: `queued→QUEUED`, `sent→SENT`, `delivered→DELIVERED`, `failed→FAILED`.

### 4.2 Time & Timezone

* Store everything in **UTC**; convert UI inputs to UTC at the edge.
* For provider sync, send UTC and let provider display per calendar settings.

### 4.3 Idempotency Keys

* Outbound SMS: `clientMessageId = sha256(tenantId, conversationId, body, first160Chars)`.
* Booking: `(tenantId, reservationId)` unique.
* Calendar sync: `(tenantId, appointmentId, provider)`.

### 4.4 Availability & Reservations

* `projectAvailability` excludes ranges overlapping existing Appointments **and** active Reservations.
* On `ReservationExpired`, slot becomes visible again immediately.

### 4.5 Opt-Out Semantics

* Normalize STOP keywords to a boolean `isOptedOut` at `(tenantId, from)`.
* Any attempt to send while opted-out → hard fail `HTTP 403` (edge) or `ERROR: OPTED_OUT` (internal), no side effects.

---

## 5) Versioning & Evolution (Keep It Boring)

* All payloads include `v` (integer). Only **add** fields for minor changes.
* Breaking change → bump `v` and support both for one release.
* Event consumers must ignore unknown fields.

---

*This is the smallest viable contract set. Anything missing means scope creep; bring evidence before expanding.*
