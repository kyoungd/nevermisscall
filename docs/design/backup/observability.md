# Observability — NeverMissCall (MVP)

**Status:** Accepted • **Audience:** Engineering/Ops • **Scope:** Metrics, Logs, Traces for Modular Monolith + Workers

> Principle: **you can’t manage what you can’t see**. We standardize metric names, logging fields, and trace context so on‑call can diagnose issues quickly and our SLOs aren’t theater.

---

## 1) SLOs & Golden Signals

* **SLO‑1 (Primary):** **P95 ≤ 5s** from **Twilio inbound** (CallDetected/InboundSmsReceived) to **Twilio outbound ‘queued’** (first SMS).
* **SLO‑2:** **P95 ≤ 500ms** for Booking API (excluding third‑party latency).

**Golden Signals**: latency, traffic, errors, saturation.

---

## 2) Metrics (canonical names)

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
* **Sampling:** head sampling 10% in prod; **100% for errors**.

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
