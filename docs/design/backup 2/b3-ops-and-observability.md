# Observability — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/Ops • **Scope:** Metrics, Logs, Traces for Modular Monolith + Workers

> Principle: **you can’t manage what you can’t see**. We standardize metric names, logging fields, and trace context so on‑call can diagnose issues quickly and our SLOs aren’t theater.

---

## 1) SLOs & Golden Signals

* **SLO‑1 (Primary):** **P95 ≤ 5s** from **Twilio inbound** (CallDetected/InboundSmsReceived) to **Twilio outbound ‘queued’** (first SMS).
* **SLO‑2:** P95 ≤ 500ms for Booking API (end-to-end handler latency, including third-party calls).

**Golden Signals**: latency, traffic, errors, saturation.

---

## 2) Metrics (canonical names)

### RUM (Web) Metrics

* `ui_first_contentful_paint_p95_seconds`
  * Source: RUM (web SDK). SLO: P95 ≤ 2.5s.
* `ui_input_latency_p95_ms`
  * Source: RUM. Track typing/send latencies in Conversation UI.

### 2.1 Request/Handler Latency

* `http_request_duration_ms{route,method,status}`
* `webhook_handler_duration_ms{provider,endpoint,status}`
* `scheduling_search_duration_ms`
* `scheduling_book_duration_ms`
* `ai_pipeline_duration_ms`

### 2.2 SLO-focused

* `slo_first_sms_p95_seconds` (computed from Reporting’s first-response tracker)
* `booking_post_p95_ms`

### 2.3 Outbox & Projectors

* `outbox_dispatch_lag_seconds` — now − oldest `created_at` pending
* `outbox_dispatch_attempts_total{event_name}`
* `outbox_dispatch_failures_total{event_name}`
* `reporting_projector_lag_seconds`
* `reporting_projection_errors_total{projector}`

### 2.4 Integrations

* `integration_http_requests_total{provider,endpoint,status}`
* `integration_http_latency_ms{provider,endpoint}`
* `webhook_dedupe_hits_total{provider}`
* `webhook_signature_failures_total{provider}`

### 2.5 Scheduling Health

* `scheduling_hold_success_total`
* `scheduling_hold_conflict_total`
* `scheduling_book_conflict_total`
* `calendar_sync_errors_total`

### 2.6 Business KPIs (from Reporting)

* `kpi_calls_detected_total`
* `kpi_conversations_started_total`
* `kpi_appointments_booked_total`
* `kpi_attributed_revenue_cents_total`

### 2.7 Saturation

* `db_connections_in_use`
* `worker_queue_depth` (outbox pending rows)
* `cpu_utilization_percent`, `memory_utilization_percent`

---

## 3) Logging (structured)

### 3.1 Required Fields

* `timestamp`, `level`, `module` (telephony|conversation|scheduling|catalog|compliance|billing|reporting|infra)
* `tenant_id`, `correlation_id`, `causation_id?`
* HTTP: `method`, `route`, `status`, `latency_ms`
* Webhooks: `provider`, `event_id`
* Outbox: `event_name`, `outbox_id`, `attempts`
* Errors: `error_code`, `error_message`, `stack` (only in DEBUG/TRACE)

### 3.2 Redaction Rules

* Do **not** log full message bodies by default. If needed for debugging, log first 50 chars behind a feature flag.
* Mask emails and phone numbers to last 4 digits in INFO level logs; full values only in DEBUG with ephemeral retention.

---

## 4) Tracing

* **Trace boundaries:** webhook → outbox write → consumer handler → provider API call.
* **Propagation:** use `correlation_id` as a trace attribute and attach `event_id` for spans touching events.
* **Span naming:** `webhook.twilio.sms_inbound`, `outbox.dispatch`, `conversation.first_reply`, `scheduling.book`, etc.
* **Sampling:**head sampling 10% in prod; **collector tail rules** keep **100%** of traces with span.status=ERROR or HTTP status>=500; otherwise 10%.

---

## 5) Dashboards (panels)

1. **SLO Overview** — P95 first SMS, call volume, error rate.
2. **Outbox Health** — lag seconds, attempts, failures by event.
3. **Webhook Health** — dedupe hits, signature failures, per‑provider latency.
4. **Scheduling** — holds created vs conflicts, booking P95, calendar sync errors.
5. **Twilio Delivery** — queued→sent→delivered funnel, failure codes.
6. **DB & Workers** — connections, CPU/mem, queue depth.

---

## 6) Alerts (initial)

* First SMS SLO breach: `slo_first_sms_p95_seconds > 5` for 10m.
* Outbox lag: `outbox_dispatch_lag_seconds > 60` for 10m.
* Webhook signatures failing: `webhook_signature_failures_total > 10/min` for 5m.
* Calendar sync errors: `calendar_sync_errors_total > 0` for 15m.
* DB saturation: `db_connections_in_use > 0.8 * max` for 10m.

---

## 7) Implementation Notes

* Prefer **OpenTelemetry** for traces/metrics; export to your provider (Grafana/Prometheus/Datadog).
* Wrap HTTP clients (Twilio/Stripe/Google/Jobber) to emit metrics consistently and add request IDs to logs.
* Add a `/metrics` endpoint for scraping; protect with basic auth or IP allow‑list.

---

## 8) Validation & Tests

* Synthetic test: simulate inbound call → assert outbound queued in <5s across full path in staging.
* Unit tests for log redaction (no PII in INFO logs).
* Load tests to ensure P95 budgets under expected concurrency.





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

### Circuit Breakers (External Providers)

* **Twilio SMS/Voice**
  * Open if 5xx rate > 2% over 3m **or** P95 send latency > 3× baseline for 5m.
  * Half-open after 2m; allow 10% traffic; close when error rate < 1% for 5m.
* **Google Calendar / Jobber**
  * Open if 429/5xx > 1% over 5m or average response time > 2× baseline for 10m.
  * When open: pause non-critical syncs; continue token refresh and health checks.
* **Stripe**
  * Open if 5xx > 1% over 3m.

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





# Testing Strategy — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/QA • **Scope:** Modular Monolith (FastAPI + workers), Next.js UI, single Postgres, DB‑backed Outbox

> Brutal principle: ship only what we can test. Primary SLO is **P95 ≤ 5s** first SMS. All tests are tenant‑scoped. All integrations are idempotent.

---

## 1) Test Pyramid & Tools

* **Unit tests** (fast, isolated): **pytest** for Python, **vitest/jest** for frontend utilities.
* **Integration tests** (module + DB): **pytest + Testcontainers** (Postgres) — no mocks for DB; use real migrations.
* **Contract tests** (between modules & external providers): **schemathesis** (OpenAPI) for HTTP, sample webhook payloads for providers.
* **End‑to‑End (E2E)** (user flows): **Playwright** for UI + API; run against ephemeral DB.
* **Performance/SLO**: **locust/k6** synthetic flow; SLO check in staging pipeline.

**General rules**

* Deterministic tests: freeze time where needed (`freezegun`).
* Every test provides `tenant_id`; cross‑tenant access is a failure.
* No network in unit tests; external HTTP is faked.

---

## 2) Coverage Targets & Gates (CI)

* **Backend line coverage** ≥ **85%**, **branches** ≥ **75%**; critical paths (Conversation, Scheduling) **90%+**.
* **Contract tests** must pass for public/internal APIs (OpenAPI).
* **Migrations**: apply and rollback successfully on a pristine DB in CI.
* **Lint/type**: ruff/flake8 + mypy for backend; eslint/types for UI.
* **SLO pre‑flight** (staging nightly): synthetic call→SMS flow P95 ≤ 5s.

PRs blocked unless all gates are green.

---

## 3) Test Data & Fixtures

* **Factories/builders** per aggregate (e.g., `make_conversation`, `make_service_item`).
* **Tenant fixture** provides `tenant_id`, default OWNER/TECH users.
* **Phone numbers** in **E.164**; aliases lowercased.
* **Clock** fixture for `now()`; use DB time in integration tests.
* **Webhooks**: golden samples for Twilio/Stripe/Google/Jobber with valid signatures.

---

## 4) Module‑Specific Test Plans

### 4.1 Telephony Ingestion

* **Signature verification**: valid vs tampered payloads → 200 vs 401.
* **Idempotency**: replay the same webhook 5× → one `webhook_events` row and one Outbox event.
* **Missed call classification**: table‑driven for `no-answer|busy|failed` (+ optional short‑complete rule off by default).
* **Number→tenant mapping**: unknown number → 200 no‑op + WARN.

### 4.2 Conversation & Messaging

* **State machine**: `open ↔ human`, `* → blocked`, auto‑close.
* **Compliance gate**: outbound denied when not approved → 403; unblocks on `ComplianceStatusChanged(approved)`.
* **First reply flow**: inbound → first outbound within budget (mock Twilio client latency to 0ms in unit; integration measures our server time only).
* **Idempotent delivery updates**: multiple status callbacks update once.
* **Template rendering**: missing variables fail fast with clear error.

### 4.3 Scheduling & Availability

* **No double‑booking**: property tests generate random busy blocks; assertion: DB constraint denies overlap.
* **Hold TTL**: expires at 15m; booking after expiry → 410.
* **Booking transaction**: hold → appointment → outbox emitted; idempotent on retries.
* **External sync**: webhook then poll; shadow table updated with minimal drift.

### 4.4 Catalog & Pricing

* **CRUD invariants**: unique name per tenant; price/duration bounds.
* **Matching**: aliases, ranking (length > priority > exact name).
* **Quoting**: inactive item → 410; values match DB.

### 4.5 Identity & Access

* **JWT verification**: issuer/audience/exp/nbf; bad token → 401.
* **RBAC**: OWNER vs TECH route access; tenant scoping enforced.
* **User deactivation**: active=false → 403 even if JWT valid.

### 4.6 Compliance

* **Submission**: creates brand/campaign pending.
* **Gating**: blocked before approval; event on approve/reject.
* **Phone mapping**: unique per tenant; webhook routing respects mapping.
* **STOP/HELP**: opt‑out ledger updated; no further sends.

### 4.7 Billing

* **Checkout**: session created with `client_reference_id=tenant_id`.
* **Webhooks**: idempotent mirror to `bill_subscriptions`; events emitted.
* **State transitions**: created→active, active→past\_due→active, active→canceled.

### 4.8 Reporting

* **First response tracker**: outbound before inbound → no latency until both present; then computed.
* **Daily rollups**: p50/p95 recompute with new data; UPSERT semantics.
* **Revenue attribution**: price snapshot at booking time.

---

## 5) Contract Tests (APIs & Events)

* **HTTP APIs**: generate tests from OpenAPI (schemathesis) covering edge cases (missing tenant header, bad role, invalid payloads).
* **Module boundaries**: provider/consumer tests for Conversation↔Scheduling↔Catalog. Example: Conversation consumes `AppointmentHeld` and sends a message; Scheduling consumes `CatalogUpdated` cache invalidation.
* **Event schemas**: validate `schema_version` and payload shape against `event-catalog.md` JSON Schemas.

---

## 6) E2E Flows (Playwright)

1. **Missed Call → First SMS**

   * Simulate Twilio voice status webhook → assert outbound queued within budget (mock Twilio status to success).
2. **Quote & Book**

   * Inbound SMS describes job → `/catalog/match` → show 2–3 slot offers → hold → book → confirmation.
3. **Human Takeover**

   * UI takeover → AI paused → human message sent.
4. **Compliance Block**

   * Tenant pending → outbound blocked; approve → unblocked.
5. **Billing**

   * Checkout session link visible; webhook updates plan; banner reflects state.

Each E2E run seeds an **ephemeral tenant** and tears it down.

---
## 7) Traceability to ADRs (governance → tests)

* **ADR-0006 (No Double-Booking)** → Scheduling property tests + DB constraint checks (see §4.3, §10 in Scheduling spec).
* **ADR-0007 (Webhook Idempotency)** → Telephony/Stripe/Google/Jobber webhook replay tests ensure single ingest + single Outbox event.
* **ADR-0008 (Retry & Backoff)** → Fault-injection tests assert exponential backoff with jitter and DLQ after max attempts.
* **ADR-0009 (SLOs & Measurements)** → Synthetic “Missed Call → First SMS” budgets enforced in staging; fail pipeline on P95 > 5s.
* *

---

## 8) Performance & SLO Tests

* **Synthetic SLO** (staging, nightly): end‑to‑end missed call → first SMS; collect 100 samples; assert **P95 ≤ 5s**.
* **Load test**: 50 concurrent missed calls/minute for 10 minutes; verify outbox lag < 60s and DB CPU < 80%.
* **Scheduling search**: p95 under 300ms for typical windows.

---

## 9) Resilience & Chaos

* **Provider 5xx/timeout**: simulate Twilio/Google/Jobber failures; verify retry with jitter and no duplicate side effects.
* **Outbox worker crash**: kill worker mid‑batch; ensure `FOR UPDATE SKIP LOCKED` prevents lost work.
* **Clock skew**: ensure DB `now()` is used for invariants (holds, booking, SLO trackers).

---

## 10) CI/CD Integration

* **Stages**: unit → integration (with Testcontainers) → contract → e2e (headless) → package → deploy → staging SLO job (nightly).
* **Artifacts**: coverage HTML, junit XML, cucumber JSON (Playwright), DB migration logs.
* **Flakes**: tests using backoff/jitter must stub RNG to deterministic sequence.

---

## 11) Test Utilities & Fakes

* **HTTP fakes** for Twilio/Stripe/Google/Jobber with recorded responses.
* **Signature helpers** to generate valid webhook signatures for tests.
* **Event bus helper** to insert into `outbox_events` and drain synchronously in tests.
* **Phone assertions** to check E.164 formatting and masking in logs.

---

## 12) Definition of Done (per PR)

* New logic covered by unit + integration tests.
* If an API or event changed: contract tests updated; **schema\_version** bump evaluated.
* Migrations added with rollback notes; CI migration test passes.
* Observability: new metrics/logs/traces added as specified; dashboards updated if needed.

---

## 13) Open Questions (non‑blocking)

* Do we need browser visual regression tests now (Playwright snapshots)? (Probably later.)
* Should we include canary deployments with SLO probes before full rollout? (Future.)
