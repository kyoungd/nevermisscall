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
