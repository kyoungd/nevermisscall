# Software Design — Identity & Access Module

**Status:** Accepted • **Audience:** Engineering • **Context:** Bounded Context — Identity & Access (AuthN/AuthZ)

> Goal: Authenticate users with **Clerk (JWT)**, enforce **tenant-scoped RBAC** with roles `OWNER` and `TECH`, and ensure every request carries a **valid `tenant_id`**. No API keys in MVP. Webhooks (Twilio/Stripe/Google/Jobber) are **unauthenticated** but deduped and mapped to tenants by provider-specific identifiers.

---

## 1) Responsibilities

* Authenticate app users via **Clerk JWT**.
* Authorize requests via **RBAC** (roles: `OWNER`, `TECH`).
* Bind every request to a **single tenant** (multi-tenancy via `tenant_id` column).
* Manage tenant/users lifecycle (invite, role assignment, deactivation).
* Provide helpers for modules to retrieve **current tenant context** safely.

**Out of scope:** SSO providers config (handled by Clerk), fine-grained permissions beyond two roles, API key issuance (deferred).

---

## 2) Domain Model

### Aggregates / Entities

* **Tenant** (`id`, `name`, `created_at`)
* **User** (`id`, `tenant_id`, `email`, `role`, `created_at`)

  * `role ∈ {OWNER, TECH}`
  * Each user belongs to **one tenant** (1 business per tenant per product decision).

### Invariants

1. Every request in app code has **exactly one** `tenant_id` in context.
2. Only `OWNER` may manage users, billing, compliance.
3. `TECH` has read/write to operational features (conversations, scheduling) **within the tenant**.
4. Users cannot switch tenants (MVP); changing tenant requires re-invite and data migration.

---

## 3) Authentication (Clerk)

* **Token type:** JWT (access token) attached as `Authorization: Bearer <token>` on API requests.
* **Verification:**

  * Validate issuer (`CLERK_JWT_ISSUER`), audience (`CLERK_JWT_AUDIENCE`), and signature via JWKS (`CLERK_JWKS_URL`).
  * Cache JWKS for 15 minutes; refresh on `kid` miss.
  * Accept only tokens issued for our API audience.
* **Claims mapping (expected)**

  * `sub` → `user_id`
  * `email` → preferred email
  * `org_id` or custom claim → **`tenant_id`** (we will configure Clerk to embed `tenant_id` in a custom claim `nmc_tenant_id`).
  * `role` or custom metadata → `OWNER` or `TECH` (custom claim `nmc_role`).

**Failure handling**

* Missing/invalid token → 401.
* Token valid but missing `nmc_tenant_id` or `nmc_role` → 403 and log misconfiguration.

---

## 4) Authorization (RBAC)

### Roles

* **OWNER**: manage users, billing, compliance, catalogs, all runtime ops.
* **TECH**: runtime ops (conversations, scheduling), limited settings view, no billing/compliance/user management.

### Enforcement

* Implement a FastAPI **dependency** `require_role(*roles)` that:

  1. Validates JWT.
  2. Extracts `tenant_id`, `user_id`, `role`.
  3. Asserts role ∈ allowed roles.
  4. Populates request-scoped `Context(tenant_id, user_id, role, correlation_id)`.

**Pseudocode**

```python
from fastapi import Depends, HTTPException

class RequestContext(BaseModel):
    tenant_id: UUID
    user_id: UUID
    role: Literal['OWNER','TECH']
    correlation_id: UUID

_jwks_cache = JWKSCache(ttl=900)

def auth_dependency(allowed_roles: set[str]):
    def _inner(request: Request) -> RequestContext:
        token = extract_bearer(request.headers)
        claims = verify_with_jwks(token, issuer=ISS, audience=AUD, jwks=_jwks_cache)
        tenant_id = claims.get('nmc_tenant_id')
        role = claims.get('nmc_role')
        if tenant_id is None or role not in allowed_roles:
            raise HTTPException(status_code=403)
        ctx = RequestContext(
            tenant_id=UUID(tenant_id),
            user_id=UUID(claims['sub']),
            role=role,
            correlation_id=uuid4(),
        )
        request.state.ctx = ctx
        return ctx
    return _inner

# Usage
@app.post('/scheduling/book')
async def book(..., ctx: RequestContext = Depends(auth_dependency({'OWNER','TECH'}))):
    ...
```

---

## 5) Public API (Identity endpoints)

* `GET /me` → returns user & tenant context (id, email, role, tenant\_id).
* `POST /users/invite` (OWNER) → sends Clerk invite; on accept, we create `id_users` row.
* `POST /users/{id}/role` (OWNER) → change role (`OWNER` or `TECH`).
* `DELETE /users/{id}` (OWNER) → deactivate user (soft delete: flag or revoke in Clerk + local disable).

**AuthZ**: All endpoints require JWT; only OWNER can modify.

---

## 6) Data Model (adds/clarifies)

```sql
CREATE TABLE id_tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE id_users (
  id uuid PRIMARY KEY,         -- matches Clerk user id
  tenant_id uuid NOT NULL REFERENCES id_tenants(id) ON DELETE RESTRICT,
  email text NOT NULL,
  role text NOT NULL CHECK (role IN ('OWNER','TECH')),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
```

**Notes**

* We mirror minimal user data locally for RBAC and auditing; Clerk remains the source of truth for authn.
* We do **not** store passwords.

---

## 7) Context Ingestion (Unauthenticated Webhooks)

Not all inbound requests have JWTs. We establish `tenant_id` via deterministic mapping:

* **Twilio** (Telephony): map `To` number (E.164) → `tenant_id` via provisioned numbers table (Compliance owns). If not found, no-op 200.
* **Stripe** (Billing): parse event, extract `customer` or `subscription` id, look up in `bill_subscriptions` to resolve `tenant_id`.
* **Google/Jobber** (Scheduling): webhook includes calendar/account id; look up by provider ref under a single tenant.

If mapping fails: log WARN with provider refs; return **2xx** to avoid provider retries; create a manual investigation task.

---

## 8) Failure Modes & Policies

* **Role downgrade mid-session**: role checked per request; no long-lived sessions on server; next request reflects new role.
* **User removed**: set `active=false`; 403 on subsequent requests (even if token still valid) by checking local `id_users` state.
* **Missing tenant claim**: treat as configuration error; 403 and log.
* **Clock skew**: rely on JWT `exp`/`nbf`; require NTP on servers.

Retry policy for Clerk admin calls: jitter (base=1s, cap=30s, max\_attempts=6).

---

## 9) Observability

**Metrics**

* `auth_jwt_verify_failures_total{reason}` (signature, audience, issuer, expired)
* `auth_forbidden_total{endpoint}`
* `auth_user_deactivated_total`

**Logs**

* Include `tenant_id` (if resolved), `user_id`, `role`, `endpoint`, `decision` (allow|deny), `reason`.

**Tracing**

* Attach `user_id` and `tenant_id` as span attributes on entry spans.

---

## 10) Testing Strategy

* **JWT verification**: valid/invalid tokens, wrong audience/issuer, expired/nbf.
* **RBAC**: OWNER vs TECH coverage per endpoint.
* **Tenant scoping**: ensure all queries require `tenant_id`; add unit tests that reject empty scope.
* **Webhook resolution**: provider → tenant mapping happy/edge paths.

---

## 11) Config & Defaults

* `CLERK_JWT_CACHE_TTL_SECONDS = 900`
* `AUTH_REQUIRED_ROUTES = true`
* `ALLOW_ANONYMOUS = false` (except webhooks)

---

## 12) Security Notes

* Enforce HTTPS only; HSTS on frontends.
* Strict CORS origins for API.
* Principle of least privilege on DB and platform accounts.
* Log redaction for emails and tokens in error messages.

---

## 13) Open Questions (non-blocking)

* Do we need an **AGENT** role later (non-owner human responders)? (Deferred.)
* Should we allow **multiple tenants per user** (contractors)? (Out of MVP.)
* Self-service domain mapping for SMS numbers vs. manual provisioning? (Compliance doc.)
