from fastapi import FastAPI, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import Optional
import uuid

from .database import engine, Base, get_db
from .models import Tenant, Plan, Subscription, UsageEvent
from .schemas import GenerateRequest, GenerateResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Usage Metering & Billing Engine")

@app.post("/v1/generate", response_model=GenerateResponse)
def generate_usage(
    payload: GenerateRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID header format.")

    # 1. Idempotency Check (Has this key been processed?)
    existing_event = db.query(UsageEvent).filter(UsageEvent.idempotency_key == idempotency_key).first()
    if existing_event:
        return GenerateResponse(
            status="success",
            tenant_id=existing_event.tenant_id,
            event_id=existing_event.id,
            message="Request already processed (idempotent replay).",
            idempotent_replay=True
        )

    # 2. Get Active Subscription & Plan
    sub = db.query(Subscription).filter(Subscription.tenant_id == tenant_uuid, Subscription.status == "active").first()
    if not sub:
        raise HTTPException(status_code=402, detail="No active subscription found. Payment required.")

    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()

    # 3. Calculate Current Usage
    total_used = db.query(func.coalesce(func.sum(UsageEvent.quantity), 0)).filter(
        UsageEvent.tenant_id == tenant_uuid,
        UsageEvent.event_type == payload.event_type
    ).scalar()

    # 4. Quota Enforcement
    limit = plan.api_call_limit if payload.event_type == "api_call" else plan.ai_token_limit
    if total_used + payload.quantity > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded for event type '{payload.event_type}'. Current: {total_used}, Limit: {limit}, Requested: {payload.quantity}."
        )

    # 5. Record Usage Event
    new_event = UsageEvent(
        tenant_id=tenant_uuid,
        event_type=payload.event_type,
        quantity=payload.quantity,
        cached_input_tokens=payload.cached_input_tokens,
        reasoning_tokens=payload.reasoning_tokens,
        idempotency_key=idempotency_key
    )

    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
    except IntegrityError:
        db.rollback()
        # Fallback handling for concurrent requests using same idempotency key
        existing_event = db.query(UsageEvent).filter(UsageEvent.idempotency_key == idempotency_key).first()
        return GenerateResponse(
            status="success",
            tenant_id=existing_event.tenant_id,
            event_id=existing_event.id,
            message="Request already processed (concurrent idempotent replay).",
            idempotent_replay=True
        )

    return GenerateResponse(
        status="success",
        tenant_id=new_event.tenant_id,
        event_id=new_event.id,
        message="Usage recorded successfully."
    )