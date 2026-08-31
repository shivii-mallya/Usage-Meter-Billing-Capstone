# Design Document: Usage Metering & Billing Engine

## 1. Problem Statement & Scope
This backend engine provides accurate usage metering, subscription quota enforcement, and automated billing synchronization for multi-tenant SaaS applications. 

### Non-Goals
* Real payment processing (uses Stripe Test Mode exclusively).
* Mid-cycle proration or custom enterprise contract logic.
* Actual LLM provider integration (AI token consumption is simulated).

---

## 2. Architecture & Tech Stack
* **Language & Framework:** Python 3.11+, FastAPI
* **Database:** PostgreSQL via Docker
* **Payments & Events:** Stripe Test Mode + Stripe CLI
* **Idempotency:** Unique Database Constraints on Idempotency Keys

---

## 3. Database Schema

### `tenants`
* `id` (UUID, Primary Key)
* `name` (VARCHAR)
* `created_at` (TIMESTAMP)

### `plans`
* `id` (VARCHAR, Primary Key) -- e.g., 'free', 'pro'
* `monthly_api_limit` (INTEGER)
* `monthly_token_limit` (INTEGER)
* `rate_cached_input_microcents` (INTEGER) -- $0.000001 = 1 microcent
* `rate_fresh_input_microcents` (INTEGER)
* `rate_output_microcents` (INTEGER)

### `subscriptions`
* `id` (UUID, Primary Key)
* `tenant_id` (UUID, Foreign Key -> tenants.id)
* `plan_id` (VARCHAR, Foreign Key -> plans.id)
* `stripe_customer_id` (VARCHAR)
* `stripe_subscription_id` (VARCHAR, Unique)
* `status` (VARCHAR) -- 'active', 'canceled', 'past_due'
* `current_period_start` (TIMESTAMP)
* `current_period_end` (TIMESTAMP)

### `usage_events`
* `id` (UUID, Primary Key)
* `tenant_id` (UUID, Foreign Key -> tenants.id)
* `usage_type` (VARCHAR) -- 'api_call', 'ai_token'
* `quantity` (INTEGER)
* `token_cached_input` (INTEGER, Default 0)
* `token_fresh_input` (INTEGER, Default 0)
* `token_output` (INTEGER, Default 0)
* `token_reasoning` (INTEGER, Default 0)
* `idempotency_key` (VARCHAR, Unique Index)
* `response_payload` (JSONB)
* `created_at` (TIMESTAMP)

---

## 4. Metering & Idempotency Strategy
1. The client sends a request with an `Idempotency-Key` header.
2. The service queries `usage_events` for `idempotency_key`.
3. If found, the service returns the previous response payload immediately without recalculating usage or enforcing quotas.
4. If not found, transaction processing proceeds.

---

## 5. Quota Enforcement Logic
* Before committing a billable action:
  * Sum all usage for `tenant_id` within the active billing cycle.
  * Compare `current_usage + requested_quantity` against current `plan` limits.
* **Over Plan Quota:** Returns `429 Too Many Requests` with header `Retry-After`.
* **Subscription Past Due / Lapsed:** Returns `402 Payment Required`.

---

## 6. Token Pricing Rules
Costs are calculated entirely in **integer microcents** ($1 = 100,000,000$ microcents) to guarantee zero floating-point rounding errors:

$$\text{Total Cost} = (\text{Cached Input} \times R_{\text{cached}}) + (\text{Fresh Input} \times R_{\text{fresh}}) + ((\text{Output} + \text{Reasoning}) \times R_{\text{output}})$$

*Reasoning tokens are explicitly billed at the standard output token rate.*