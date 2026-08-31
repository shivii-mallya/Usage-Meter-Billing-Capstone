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