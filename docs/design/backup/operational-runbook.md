# Operational Runbook — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/On‑call • **Scope:** Production ops for Modular Monolith (FastAPI + workers)

> Brutal summary: Managed PaaS (Heroku/Render) for the API + workers, Netlify/Vercel for the UI, single Postgres, DB Outbox + dispatcher, webhook-first with polling fallback. **Primary SLO:** first SMS **P95 ≤ 5s** (Twilio inbound → Twilio outbound queued).

---

## 1) System Topology

* **API (web)**: FastAPI app serving REST + webhooks (Twilio/Stripe/Google/Jobber).
* **Worker**: background process running:

  * **Outbox dispatcher** (batch=100, concurrency=2, at-least-once).
    Dispatches **domain events** defined in Event Catalog. This is not infra plumbing;
    these rows are business facts, and must remain aligned with catalog schemas.

  * **Hold GC** (deletes expired holds)
  * **Calendar pollers** (Google 60s, Jobber 120s per connected calendar)
* **DB**: Managed Postgres (primary only). Extensions: `btree_gist`.
* **Frontend**: Netlify/Vercel hosting Next.js.

---

## 2) Environments & Promotion

* **dev** → **staging** → **prod** (trunk-based; short-lived feature branches).
* Staging mirrors prod config with test credentials and a Twilio **test number**.
* Promotion is a **re-deploy** from a tagged commit; never hotfix on prod without a tag.

---

## 3) Configuration (Env Vars)

**Core**

* `DATABASE_URL`
* `SECRET_KEY`

**Twilio**

* `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_MESSAGING_SERVICE_SID`

**Stripe**

* `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

**Google**

* `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

**Clerk**

* `CLERK_JWT_ISSUER`, `CLERK_JWT_AUDIENCE`, `CLERK_JWKS_URL`

**Jobber**

* `JOBBER_API_TOKEN` (or OAuth credentials if applicable)

**Tuning / Feature Flags**

* `HOLD_TTL_MINUTES=15`
* `SEARCH_GRANULARITY_MINUTES=15`
* `POLL_INTERVAL_GOOGLE_SECONDS=60`
* `POLL_INTERVAL_JOBBER_SECONDS=120`
* `OUTBOX_BATCH_SIZE=100`
* `OUTBOX_CONCURRENCY=2`
* `TREAT_SHORT_COMPLETED_AS_MISSED=false`
* `SHORT_COMPLETED_MAX_SECONDS=10`
* `PAUSE_OUTBOUND_SMS=false` (ops kill-switch)

> Secrets live in platform config; never commit to Git.

---

## 4) Deploy Procedure (Zero‑downtime)

1. **Prepare**: Merge to `main`; CI green (tests + lint + migrations dry-run).
2. **Tag**: `vYYYY.MM.DD-x`.
3. **Run migrations** (release phase):

   * Additive first (nullable columns, new tables).
   * Deploy code that reads new fields.
   * Enforce non-null/constraints **later** after backfill.
4. **Deploy web + worker** images.
5. **Smoke**: /healthz (web), worker logs show dispatcher picking events.
6. **Verify SLO**: synthetic test (simulate inbound → expect outbound queued within budget on staging, spot-check prod).

**Rollback**

* Re-deploy previous tag for web + worker.
* Only roll back DB if the migration was destructive (avoid; use forward fixes where possible).

---

## 5) Observability

**Metrics (Prometheus-style names)**

* `slo_first_sms_p95_seconds` (alert if >5s for 10m)
* `booking_post_p95_ms` (alert if >500ms for 10m)
* `outbox_dispatch_lag_seconds` (alert if >60s for 10m)
* `webhook_dedupe_hits_total{provider}`
* `webhook_signature_failures_total{provider}` (alert if spike)
* `calendar_sync_errors_total` (alert if >0 for 15m)
* `scheduling_book_conflict_total` (watch trend)

**Logs (structured)**

* Include `tenant_id`, `module`, `event_name`, `correlation_id`, `http_status`.
* Log webhook **signature failures** at WARN with provider + headers (no secrets).

**Tracing**

* Correlation flows: webhook → outbox write → handler → provider API call. Use `correlation_id` + `causation_id` from the Event Catalog.

**Dashboards**

* SLO overview, Outbox health, Webhook health, Calendar sync, Scheduling conflicts, Provider error rates.

---

## 6) Alerts (initial thresholds)

* **SLO breach**: `slo_first_sms_p95_seconds > 5` for 10 minutes.
* **Outbox lag**: `outbox_dispatch_lag_seconds > 60` for 10 minutes.
    This alert is not only infra health — it also indicates that **domain events are delayed**,
    meaning projections, KPIs, and SLO measurements are stale.
* **Webhook signature failures**: `> 10/min` sustained 5 minutes.
* **Calendar sync errors**: any non-zero for 15 minutes.
* **DB saturation**: connections > 80% for 10 minutes; CPU > 80% for 10 minutes.

> Alerts page links to playbooks below.

---

## 7) On‑Call Playbooks

### 7.1 SLO Breach: First SMS > 5s (P95)

1. Check **Outbox health** (lag, attempts). If lag high → scale worker (`OUTBOX_CONCURRENCY`, dynos).
2. Inspect **Twilio latency** / 5xx rates; if high, set `PAUSE_OUTBOUND_SMS=true` only if Twilio is erroring to avoid floods.
3. Look for DB contention (long locks on `conv_*`/`sched_*`).
4. If calendar pollers are noisy, reduce poll frequency temporarily.

### 7.2 Outbox Stuck / Lagging

1. Query `outbox_events` where `dispatched_at IS NULL AND available_at < now()`.
2. If many rows with high `attempts`, inspect `last_error`.
3. Temporarily **increase** worker concurrency and **decrease** batch size to reduce lock times.
4. For poison messages, move rows to `outbox_events_errors` (manual table) and open a bug.
     **Do not bypass schema rules**: even DLQ entries must conform to Event Catalog contracts.

### 7.3 Twilio Failures (4xx/5xx spikes)

* 4xx (e.g., 21610 STOP): ensure opt-outs honored; investigate template content.
* 5xx/timeout: backoff with jitter kicks in. If sustained > 15m, notify Twilio support with correlation examples.

### 7.4 Calendar Webhooks Silent

* System should auto‑fallback to **polling**. Verify poll logs.
* If Google 401/403 → revoke tenant token and notify tenant to re‑auth.
* If Jobber token invalid → same re‑auth flow.

### 7.5 Stripe Webhook Signature Failures

* Rotate `STRIPE_WEBHOOK_SECRET`.
* Replay missed events from Stripe Dashboard.

### 7.6 DB Hotspots / Locking

* Check blocking queries (`pg_locks` joined to `pg_stat_activity`).
* Typical culprits: large `scheduling_search` or unbounded scans. Add/verify indexes.

### 7.7 Migration Gone Wrong

* If additive: revert app first. If destructive: apply compensating migration script.
* Document in postmortem; avoid destructive changes in the future.

---

## 8) Maintenance Tasks

* **Retention jobs**

  * Delete `conv_messages` older than **180 days** (after KPI aggregation).
  * Delete `webhook_events` older than **90 days**.
  * Delete `outbox_events` **30 days** after `dispatched_at`.
* **Secret rotation** quarterly (Twilio/Stripe/Google/Clerk/Jobber).
* **Restore drills** monthly: restore latest snapshot to staging and run smoke tests.

---

## 9) Backup & DR

* **Backups:** Daily snapshots + PITR (provider capability). Retain 7–14 days.
* **RPO:** ≤ 15 minutes. **RTO:** ≤ 2 hours.
* **Restore Steps:**

  1. Provision new Postgres instance from snapshot.
  2. Update `DATABASE_URL` in staging; run migrations if needed.
  3. Verify health + dashboards; then cut over prod if required.

---

## 10) Capacity & Scaling

* **Vertical** first (PaaS tiers), then **horizontal** (web/worker dynos).
* Scale worker when `outbox_dispatch_lag_seconds` trends up or pollers increase load (seasonal peaks).
* DB: monitor connections, IOPS; upgrade plan before exhaustion.

---

## 11) Run Commands (Heroku examples)

```bash
# Migrations (release phase)
heroku run -a nmc-prod alembic upgrade head

# Scale processes
heroku ps:scale web=2 worker=2 -a nmc-prod

# Tail logs
heroku logs -t -a nmc-prod

# Set flags
heroku config:set PAUSE_OUTBOUND_SMS=true -a nmc-prod

# Run SQL console
heroku pg:psql -a nmc-prod
```

---

## 12) SQL Cheatsheet

```sql
-- Outbox lag
SELECT now() - MIN(created_at) AS oldest, COUNT(*) AS pending
FROM outbox_events WHERE dispatched_at IS NULL;

-- Holds about to expire
SELECT id, resource_id, expires_at
FROM sched_holds WHERE expires_at < now() + interval '5 minutes'
ORDER BY expires_at;

-- Webhook dedupe volume by provider
SELECT provider, COUNT(*) FROM webhook_events
WHERE received_at > now() - interval '1 day'
GROUP BY provider;
```

---

## 13) Incident Postmortem Template

```
# Postmortem — <YYYY-MM-DD> <Title>
## Summary
## Timeline (UTC)
## Impact
## Root Cause
## Contributing Factors
## What Went Well / What Hurt
## Action Items (Owners, Dates)
```

---

## 14) Access & Security

* Principle of least privilege to PaaS accounts and DB.
* 2FA required for all dashboards and provider consoles.
* Rotate credentials on team changes; audit access quarterly.
