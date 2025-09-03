```markdown
# Ubiquitous Language Glossary — Minimal (Small Project)

**Purpose**: One small team, one language. These definitions are **canonical** for code and domain docs. UI may use limited synonyms **only when explicitly listed for that term below**. If a term you need isn’t here, **add it to this glossary before you ship**.


**Scope**: Two contexts only — **Conversation & Comms** and **Fulfillment (Scheduling + Calendar)**.

**Rules of use**

1. Use the **canonical term** exactly as written (case and singular/plural).
2. Each term lists allowed business rules and examples.
3. “Terms to avoid” are banned words in code, UI, and tickets.

---

## People & Tenancy

### Tenant

* **Definition**: A business account that owns phone numbers, settings, and calendars. Primary partition key.
* **Business rules**: Every persisted row has a `tenantId`. Data never crosses tenants.
* **Examples**:

  * “Create reservation for **tenant** T with slot S.”
  * “Resolve **tenant** context before sending SMS.”
* **Do NOT say**: *Account*, *Org*, *Workspace* (pick **Tenant** only).

### Caller

* **Definition**: The phone number (E.164) that placed the call or sent SMS before identity is known.
* **Business rules**: Unverified until explicitly linked to a Customer; may be opted-out.
* **Examples**:

  * “Open conversation for **caller** +15551234567.”
  * “Block SMS if **caller** is opted out.”
* **Do NOT say**: *Lead*, *Contact* (unless promoted per below).

### Customer

* **Definition**: A recognized person or company (optionally derived from Caller) with stored profile.
* **Business rules**: A **Caller** is **not** a **Customer** until linked or created.
* **Examples**:

  * “Promote caller to **customer** after booking.”
* **Do NOT say**: *Client*, *User* (user = staff).

---

## Conversation & Comms (Context: Conversation & Comms)

### Conversation

* **Definition**: The aggregate representing a messaging thread between a Tenant and a Caller over a rolling window.
* **Business rules**: Exactly **one Open** conversation per `(tenant, caller)` **at a time**; state machine governs transitions.
* **Examples**:

  * “When missed call arrives, **open a conversation**.”
  * “Close **conversation** after booking.”
* **Do NOT say**: *Thread*, *Chat*, *Ticket*.

### Message

* **Definition**: A single inbound or outbound SMS belonging to a Conversation.
* **Business rules**: Outbound must respect opt-out; stored idempotently via `clientMessageId`.
* **Examples**:

  * “Append inbound **message** and update state.”
* **Do NOT say**: *Text* (UI can show ‘text’, code/docs say **Message**).

### Auto-Reply

* **Definition**: The first outbound message sent automatically after a missed call.
* **Business rules**: Must be sent **≤ 5s** from call end; uses Tenant policy template.
* **Examples**:

  * “Send **auto-reply** within SLA.”
* **Do NOT say**: *Bot message*, *Auto-text*.

### Human Takeover

* **Definition**: Operator intervention that pauses automated replies for a Conversation.
* **Business rules**: While active, automation is disabled; audit action.
* **Examples**:

  * “Escalate to **human takeover** on ‘EMERGENCY’ keyword.”
* **Do NOT say**: *Manual mode*, *Agent mode*.

### Opt-Out

* **Definition**: Caller’s choice to stop receiving messages (e.g., STOP).
* **Business rules**: Global per Caller × Tenant; any outbound is blocked until explicit opt-in. Must honor HELP/STOP language.
* **Examples**:

  * “Record **opt-out** and close conversation.”
* **Do NOT say**: *Blacklist*, *DNC* (use **Opt-Out**).

### Messaging Endpoint

* **Definition**: A Tenant-owned phone number and associated compliance state with the CPaaSRef.
* **Business rules**: Must be **Verified** to send non-transactional messages. **Enforces compliance policy** (brand/campaign/opt-in & opt-out, throughput); delivery adapters/gateways only forward and record outcomes.
* **Examples**:

  * “Rotate **messaging endpoint** on throughput issues.”
* **Do NOT say**: *Line*, *Twilio number* (vendor-neutral).

### Policy Snapshot

* **Definition**: An immutable capture of the **effective messaging/compliance policy** (templates, brand/campaign IDs, opt-in/opt-out state, disclaimers) applied to a specific outbound Message at the time it was sent.
* **Business rules**: Attached to each outbound Message for audit; never edited after send; used to explain enforcement and provider responses.
* **Examples**:

  * “Persist **policy snapshot** with the outbound message for audit.”
* **Do NOT say**: *Policy state now*, *Live config* (snapshot is historical, immutable).

---

## Scheduling & Calendar (Context: Fulfillment)

### Availability

* **Definition**: A read model of free time for resources derived from existing Appointments and business hours.
* **Business rules**: Never shows overlaps with existing Appointments or active Reservations.
* **Examples**:

  * “Compute **availability** for next 7 days.”
* **Do NOT say**: *Openings*, *Free time*.

### Slot

* **Definition**: A concrete `(resource, start, end)` candidate offered for booking.
* **Business rules**: A **Slot** is **not held** until a Reservation exists.
* **Examples**:

  * “Offer three **slots** to the caller.”
* **Do NOT say**: *Time*, *Timeslot* (use **Slot**).

### Reservation

* **Definition**: A temporary hold on a Slot that expires at `expiresAt`.
* **Business rules**: One Slot per Reservation; TTL enforced; not visible as Appointment until confirmed.
* **Examples**:

  * “Create a **reservation** for slot S, TTL 10 minutes.”
* **Do NOT say**: *Hold*, *Pencil-in*.

### Appointment

* **Definition**: A confirmed booking for a Slot.
* **Business rules**: **No overlaps** per `(tenant, resource, time range)` guaranteed by DB exclusion constraint; has external sync status.
* **Examples**:

  * “Write **appointment**, then sync to Google.”
* **Do NOT say**: *Booking* (UI text may show “booking”, but domain term is **Appointment**).

### External Sync

* **Definition**: The act of reflecting an Appointment to a calendar provider.
* **Business rules**: Best-effort; Appointment remains valid even if sync fails; retries apply.
* **Examples**:

  * “Mark **external sync** FAILED; keep appointment.”
* **Do NOT say**: *Push to calendar* (too vague).

---

## Pricing (kept minimal inside Conversation)

### Service Item

* **Definition**: A billable unit the Tenant offers (e.g., “Basic Clean, 2h”).
* **Business rules**: Has currency, base price, and duration rule.
* **Examples**:

  * “Use **service item** duration to choose slots.”
* **Do NOT say**: *Sku*, *Product*.

### Quote

* **Definition**: A computed price/duration proposal for one or more Service Items.
* **Business rules**: A **Quote** is an ephemeral read model; not a contract. **Canonical term is _Quote_; “Pricing” may appear in UI labels only.**
* **Examples**:

  * “Send **quote** with three options.”
* **Do NOT say**: *Estimate* (too loaded), *Invoice* (different lifecycle).

---

## Events (names are stable; payloads versioned)

* **MissedCallDetected** — normalized signal that starts the flow.
* **ConversationOpened** — first domain state.
* **AutoReplySent** — CPaaSRef accepted first outbound.
* **MessageDeliveryUpdated** — delivery state change.
* **ComplianceOptOutReceived** — STOP received and applied.
* **SlotsProjected** — availability computed for criteria.
* **ReservationCreated / ReservationExpired** — hold lifecycle.
* **AppointmentBooked** — invariant secured; triggers external sync.
* **ExternalCalendarSyncSucceeded/Failed** — provider outcomes.

> **Rule**: Event names are **not** synonyms for commands. Do not use event names in the imperative (“`AppointmentBooked` the slot”). Use commands like `confirmAppointment`.
>
> **Timestamps**: All event timestamps are **ISO-8601 UTC (`Z`)**. Persist UTC; convert at edges.

---

## Global Terms to Avoid (and why)

* **Lead** — implies CRM lifecycle we don’t implement. Use **Caller** or **Customer**.
* **Ticket** — suggests helpdesk workflow. Use **Conversation**.
* **Job** — conflicts with Jobber’s domain. Use **Appointment**.
* **Chat** — implies web chat; our channel is SMS. Use **Conversation**/**Message**.
* **Text** — colloquial. UI may say “text” but domain uses **Message**.
* **Event** (in UI) — ambiguous between calendar and domain events. Use **Appointment** or **Domain Event** explicitly.
* **Participant** — ambiguous role. Use **Caller** (external) or **User** (staff) instead.

---

## Example: Correct Usage in a Single Flow

> “For **tenant** T, we received **MissedCallDetected** from +1555… . We **open a conversation** and send an **auto-reply**. The caller picks a **slot**; we create a **reservation** with TTL 10m. They confirm; we write an **appointment** (no overlap) and attempt **external sync** to Google. Delivery updates do not change the **appointment**.”

---

## Maintenance

* Any new term must include: Definition, Business rules, Example, Do-not-say.
* PRs changing terms must tag `@domain-owners` and run a UI copy sweep.
```
