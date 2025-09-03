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

## 7) Performance & SLO Tests

* **Synthetic SLO** (staging, nightly): end‑to‑end missed call → first SMS; collect 100 samples; assert **P95 ≤ 5s**.
* **Load test**: 50 concurrent missed calls/minute for 10 minutes; verify outbox lag < 60s and DB CPU < 80%.
* **Scheduling search**: p95 under 300ms for typical windows.

---

## 8) Resilience & Chaos

* **Provider 5xx/timeout**: simulate Twilio/Google/Jobber failures; verify retry with jitter and no duplicate side effects.
* **Outbox worker crash**: kill worker mid‑batch; ensure `FOR UPDATE SKIP LOCKED` prevents lost work.
* **Clock skew**: ensure DB `now()` is used for invariants (holds, booking, SLO trackers).

---

## 9) CI/CD Integration

* **Stages**: unit → integration (with Testcontainers) → contract → e2e (headless) → package → deploy → staging SLO job (nightly).
* **Artifacts**: coverage HTML, junit XML, cucumber JSON (Playwright), DB migration logs.
* **Flakes**: tests using backoff/jitter must stub RNG to deterministic sequence.

---

## 10) Test Utilities & Fakes

* **HTTP fakes** for Twilio/Stripe/Google/Jobber with recorded responses.
* **Signature helpers** to generate valid webhook signatures for tests.
* **Event bus helper** to insert into `outbox_events` and drain synchronously in tests.
* **Phone assertions** to check E.164 formatting and masking in logs.

---

## 11) Definition of Done (per PR)

* New logic covered by unit + integration tests.
* If an API or event changed: contract tests updated; **schema\_version** bump evaluated.
* Migrations added with rollback notes; CI migration test passes.
* Observability: new metrics/logs/traces added as specified; dashboards updated if needed.

---

## 12) Open Questions (non‑blocking)

* Do we need browser visual regression tests now (Playwright snapshots)? (Probably later.)
* Should we include canary deployments with SLO probes before full rollout? (Future.)
