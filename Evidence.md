# Capstone Requirements Evidence

## Metering
- [ ] Billable action creates exactly one event under retries
- [ ] Double-counting prevention proof

## Quotas
- [ ] Rejects over-limit requests
- [ ] Correct status codes (429/402) with clear error message

## Cost Calculation
- [ ] Rollup cost figure per tenant
- [ ] Token pricing logic (cached input + reasoning rules)

## Stripe Integration
- [ ] Checkout flow in test mode
- [ ] Signature verification and webhook deduplication

# Capstone Implementation Evidence

## Phase 1 Evidence: Design & Architecture Setup

### 1. Project Manifest Configuration (`capstone.yaml`)
The automated evaluation manifest is configured to handle startup, seeding, and execution:
- **Run Command**: `docker-compose up -d db` & `uvicorn src.main:app --reload`
- **Seed Command**: `python -m src.seed`
- **Environment**: Configured via `.env.example` template

### 2. Microcent Pricing Logic Verification
Monetary figures are pinned to integer microcents ($\$1\text{ USD} = 100,000,000\text{ microcents}$) to prevent floating-point rounding errors:
- **API Call Rate**: 1.00 microcent per call
- **Fresh Input Tokens**: 1.50 microcents per token
- **Cached Input Tokens**: 0.375 microcents per token
- **Output & Reasoning Tokens**: 6.00 microcents per token

### 3. Data Model Architecture
Database schemas designed for multi-tenant isolation, subscription handling, and idempotency guarantees:
- `tenants`: Primary account entity
- `plans`: Free vs. Pro tier limits
- `subscriptions`: Active tenant plan state
- `usage_events`: Unique constraint on `idempotency_key` to prevent double-counting

## Phase 2 Evidence: Core Metering & Quota Logic

### 1. Idempotency Test Output (Twice)
(1)```json
{
  "status": "success",
  "tenant_id": "12c481b6-6676-4da7-a447-6e444dde8829",
  "event_id": "86023dc1-8deb-4d4c-96fb-0dcc8c16e2dd",
  "message": "Usage recorded successfully.",
  "idempotent_replay": false
}
(2)
```json
{
   "status": "success",
  "tenant_id": "12c481b6-6676-4da7-a447-6e444dde8829",
  "event_id": "86023dc1-8deb-4d4c-96fb-0dcc8c16e2dd",
  "message": "Request already processed (idempotent replay)",
  "idempotent_replay": "true"
}
### 2. Quota logic test
{
  "detail": "Quota exceeded for event type 'api_call'. Current: 100, Limit: 1000, Requested: 1500."
}