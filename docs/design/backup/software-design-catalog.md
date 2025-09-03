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
