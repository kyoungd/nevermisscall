# Software Design — Database (NeverMissCall MVP)

**Status:** Accepted • **Audience:** Engineering • **Scope:** MVP (≤ 5,000 tenants, ≤ 100 concurrent)

> Brutal summary: Single Postgres cluster. All rows carry **`tenant_id`** (UUID). ACID inside the app. **No field-level encryption** in MVP (rely on at-rest + TLS). **Outbox** and **Webhook Dedupe** live in DB. Booking consistency enforced with a **GiST exclusion constraint**.

---

## 1) Conventions

* **Timezone:** store timestamps as `timestamptz` (UTC). Convert at UI edges.
* **Tenant scoping:** every domain table includes `tenant_id UUID NOT NULL`. All unique constraints must include `tenant_id`.
* **Naming:** module prefixes — `conv_*`, `sched_*`, `catalog_*`, `id_*`, `comp_*`, `bill_*`, `rep_*`.
* **Soft deletes:** none in MVP. Use archival/retention policies instead.
* **Extensions:** `btree_gist`, `pgcrypto` (for UUID gen only, not crypto), `uuid-ossp` optional if preferred.

---

## 2) Core Tables (DDL excerpts)

### 2.1 Conversation

```sql
CREATE TABLE conv_conversations (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  caller_phone text NOT NULL,
  state text NOT NULL CHECK (state IN ('open','human','closed')),
  opened_at timestamptz NOT NULL DEFAULT now(),
  closed_at timestamptz,
  UNIQUE (tenant_id, caller_phone, state) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TABLE conv_messages (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  conversation_id uuid NOT NULL REFERENCES conv_conversations(id) ON DELETE CASCADE,
  direction text NOT NULL CHECK (direction IN ('in','out')),
  body text NOT NULL,
  provider_message_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  client_dedup_key text,
  UNIQUE (tenant_id, client_dedup_key)
);

CREATE INDEX conv_msgs_conv_idx ON conv_messages(conversation_id);
CREATE INDEX conv_msgs_tenant_created_idx ON conv_messages(tenant_id, created_at DESC);
```

### 2.2 Job Catalog & Pricing (aligned with product-specification.md)

```sql
-- Base job definitions per tenant
CREATE TABLE catalog_jobs (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  title text NOT NULL,
  short_description text,
  base_duration_min int NOT NULL CHECK (base_duration_min > 0 AND base_duration_min <= 8*60),
  base_price_cents int NOT NULL CHECK (base_price_cents >= 0),
  currency char(3) NOT NULL DEFAULT 'USD',
  active boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, title)
);

-- Job variants (additional options)
CREATE TABLE catalog_job_variants (
  id uuid PRIMARY KEY,
  job_id uuid NOT NULL REFERENCES catalog_jobs(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  addl_duration_min int NOT NULL DEFAULT 0,
  addl_price_cents int NOT NULL DEFAULT 0,
  UNIQUE (job_id, name)
);

-- Job add-ons (additional services)
CREATE TABLE catalog_job_addons (
  id uuid PRIMARY KEY,
  job_id uuid NOT NULL REFERENCES catalog_jobs(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  duration_delta_min int NOT NULL DEFAULT 0,
  price_delta_cents int NOT NULL DEFAULT 0,
  UNIQUE (job_id, name)
);
```

### 2.3 Scheduling (Appointments & Holds)

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE sched_calendars (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,            -- e.g., technician or shared team calendar
  provider text NOT NULL CHECK (provider IN ('google','jobber','internal')),
  provider_ref text NOT NULL,           -- calendar id, etc.
  active boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, provider, provider_ref)
);

CREATE TABLE sched_holds (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  created_by uuid, -- user id optional
  CHECK (lower(timeslot) < upper(timeslot))
);
CREATE INDEX sched_holds_resource_idx ON sched_holds(resource_id, expires_at);
CREATE INDEX sched_holds_timeslot_idx ON sched_holds USING gist (resource_id, timeslot);

CREATE TABLE sched_appointments (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  timeslot tstzrange NOT NULL,
  job_id uuid REFERENCES catalog_jobs(id),
  customer_phone text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  CHECK (lower(timeslot) < upper(timeslot))
);
CREATE INDEX sched_appt_resource_idx ON sched_appointments(resource_id);
CREATE INDEX sched_appt_timeslot_idx ON sched_appointments USING gist (resource_id, timeslot);
ALTER TABLE sched_appointments
  ADD CONSTRAINT sched_no_overlap
  EXCLUDE USING gist (resource_id WITH =, timeslot WITH &&);
```

**Hold TTL:** default 15 minutes enforced by worker that deletes expired holds.

**Booking transaction (pseudo-SQL):**

```sql
BEGIN;
  -- ensure hold exists and not expired
  SELECT 1 FROM sched_holds
   WHERE id = :hold_id AND expires_at > now() AND tenant_id = :tenant_id
   FOR UPDATE;

  -- create appointment (constraint guarantees no overlap)
  INSERT INTO sched_appointments(id, tenant_id, resource_id, timeslot, job_id, customer_phone)
  VALUES (:id, :tenant_id, :resource_id, :timeslot, :job_id, :phone);

  -- delete hold
  DELETE FROM sched_holds WHERE id = :hold_id;

  -- write outbox event
  INSERT INTO outbox_events(...);
COMMIT;
```

### 2.4 Identity & Access

```sql
CREATE TABLE id_tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE id_users (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  email text NOT NULL,
  role text NOT NULL CHECK (role IN ('OWNER','TECH')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
```

### 2.5 Compliance (Manual 10DLC)

```sql
CREATE TABLE comp_campaigns (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('pending','approved','rejected')),
  provider_ref text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE comp_phone_numbers (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  e164 text NOT NULL,
  campaign_id uuid REFERENCES comp_campaigns(id),
  UNIQUE (tenant_id, e164)
);
```

### 2.6 Billing (Stripe Mirror)

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

### 2.7 Outbox & Webhook Dedupe

```sql
CREATE TABLE outbox_events (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  event_name text NOT NULL,
  schema_version text NOT NULL,
  payload_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  available_at timestamptz NOT NULL DEFAULT now(),
  attempts int NOT NULL DEFAULT 0,
  last_error text,
  dispatched_at timestamptz
);
CREATE INDEX outbox_available_idx ON outbox_events(available_at);

-- Idempotency for inbound webhooks from all providers
CREATE TABLE webhook_events (
  id bigserial PRIMARY KEY,
  provider text NOT NULL,       -- 'twilio','stripe','google','jobber'
  event_id text NOT NULL,       -- provider-specific unique id
  received_at timestamptz NOT NULL DEFAULT now(),
  payload_hash text NOT NULL,
  UNIQUE (provider, event_id)
);
```

**Dispatcher query (worker):**

```sql
SELECT id, tenant_id, event_name, schema_version, payload_json
FROM outbox_events
WHERE dispatched_at IS NULL AND available_at <= now()
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 100;
```

---

## 3) Indexing & Performance

* **Hot paths**

  * `conv_messages(tenant_id, created_at DESC)` for timeline queries.
  * `sched_appointments USING gist(resource_id, timeslot)` for overlaps.
  * `catalog_jobs(tenant_id, title)` for AI quoting.
* **Partial indexes** where applicable (e.g., `WHERE state='open'`).
* **Avoid LIKE** on phone numbers; store **E.164** and index exact match.

---

## 4) Retention & Archival

* `conv_messages`: **180 days** (hard delete via nightly job). Aggregate counts persisted to `rep_kpis_*` before deletion.
* Conversation metadata: **13 months**.
* `webhook_events`: **90 days** (delete old rows).
* `outbox_events`: delete **30 days** after `dispatched_at` IS NOT NULL.

---

## 5) Migrations Policy

* Tooling: Alembic (Python). One migration per PR per module when possible.
* Naming: `mod_<module>__<change>__YYYYMMDD.sql` (e.g., `mod_sched__add-holds__20250901.sql`).
* Zero-downtime rules: add columns with defaults **NULL**, backfill in code, then enforce constraints.
* Rollback: write down reversible steps; avoid destructive DDL in same deploy as code relying on it.

---

## 6) Data Integrity Rules (selected)

* All FKs must include `ON DELETE RESTRICT` or `CASCADE` intentionally (no defaults).
* All unique business keys include `tenant_id`.
* Check constraints for money/duration already defined (non-negative, bounded).
* Conversation single-active rule enforced at service layer (state machine), validated with partial unique if needed.

Example partial unique to prevent 2 open conversations per caller:

```sql
CREATE UNIQUE INDEX conv_single_open_per_caller
  ON conv_conversations(tenant_id, caller_phone)
  WHERE state = 'open';
```

---

## 7) Backup & DR

* Daily snapshot with 7-day point-in-time recovery (provider capability).
* Verify restores monthly in a staging environment.
* Store schema dumps of critical tables (`sched_*`, `conv_*`) for quick diff.

---

## 8) Example Queries

* **Find next available slots for 120 minutes:**

```sql
-- Simplified: fetch holds and appointments, compute gaps in app code
SELECT resource_id, timeslot FROM sched_appointments WHERE tenant_id = :t
UNION ALL
SELECT resource_id, timeslot FROM sched_holds WHERE tenant_id = :t AND expires_at > now();
```

* **Messages timeline for a caller:**

```sql
SELECT m.* FROM conv_messages m
JOIN conv_conversations c ON c.id = m.conversation_id
WHERE c.tenant_id = :t AND c.caller_phone = :phone
ORDER BY m.created_at DESC
LIMIT 200;
```

---

## 9) Future Considerations

* Table partitioning by month for `conv_messages` if volume grows.
* Materialized views for daily KPIs.
* Field-level encryption for PII if compliance demands change (keep columns `text` to ease later crypto).
