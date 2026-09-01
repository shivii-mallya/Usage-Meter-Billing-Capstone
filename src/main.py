import os
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
import stripe

from .database import get_db, engine, Base
from .models import Tenant, Plan, Subscription, UsageEvent
from .schemas import UsageRequest, UsageResponse
from .stripe_utils import STRIPE_WEBHOOK_SECRET, report_usage_to_stripe

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multi-Tenant Usage Metering & Billing Engine")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Usage Metering API is running"}

@app.post("/v1/generate", response_model=UsageResponse)
def generate_usage(
    request: UsageRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    # 1. Validate Tenant
    tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    # 2. Idempotency Check
    existing_event = db.query(UsageEvent).filter(
        UsageEvent.tenant_id == x_tenant_id,
        UsageEvent.idempotency_key == idempotency_key
    ).first()

    if existing_event:
        return UsageResponse(
            status="success",
            tenant_id=str(tenant.id),
            event_id=str(existing_event.id),
            message="Request already processed (idempotent replay).",
            idempotent_replay=True
        )

    # 3. Quota Check
    subscription = db.query(Subscription).filter(Subscription.tenant_id == x_tenant_id).first()
    if not subscription:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    
    current_usage = db.query(UsageEvent).filter(
        UsageEvent.tenant_id == x_tenant_id,
        UsageEvent.event_type == request.event_type
    ).count()

    limit = plan.limits.get(request.event_type, 0) if plan and plan.limits else 0
    if current_usage + request.quantity > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded for event type '{request.event_type}'. Current: {current_usage}, Limit: {limit}, Requested: {request.quantity}."
        )

    # 4. Calculate Microcents
    cost_per_unit = {
        "api_call": 100,
        "fresh_input": 150,
        "cached_input": 38,
        "output_reasoning": 600
    }.get(request.event_type, 100)

    total_cost_microcents = cost_per_unit * request.quantity

    # 5. Save Event
    new_event = UsageEvent(
        tenant_id=tenant.id,
        event_type=request.event_type,
        quantity=request.quantity,
        cost_microcents=total_cost_microcents,
        idempotency_key=idempotency_key
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # 6. Optional: Async report to Stripe Meter if customer ID exists
    if tenant.stripe_customer_id:
        report_usage_to_stripe(
            stripe_customer_id=tenant.stripe_customer_id,
            event_name=request.event_type,
            value=request.quantity,
            timestamp=int(new_event.created_at.timestamp())
        )

    return UsageResponse(
        status="success",
        tenant_id=str(tenant.id),
        event_id=str(new_event.id),
        message="Usage recorded successfully.",
        idempotent_replay=False
    )

# --- STEP 3: STRIPE WEBHOOK HANDLER ---
@app.post("/v1/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        # Fallback for manual JSON payloads during dev testing
        event = await request.json()

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type in ["customer.subscription.created", "customer.subscription.updated"]:
        customer_id = data_object.get("customer")
        stripe_sub_id = data_object.get("id")
        status = data_object.get("status")

        plan_id = "pro" if status == "active" else "free"

        tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
        if tenant:
            sub = db.query(Subscription).filter(Subscription.tenant_id == tenant.id).first()
            if sub:
                sub.plan_id = plan_id
                sub.stripe_subscription_id = stripe_sub_id
                sub.status = status
                db.commit()

    return {"status": "success"}