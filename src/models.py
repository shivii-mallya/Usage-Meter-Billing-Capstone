import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    stripe_customer_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True) # 'free' or 'pro'
    name = Column(String, nullable=False)
    api_call_limit = Column(Integer, nullable=False)
    ai_token_limit = Column(Integer, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    status = Column(String, nullable=False, default="active")

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String, nullable=False) # 'api_call' or 'ai_token'
    quantity = Column(Integer, nullable=False)
    cached_input_tokens = Column(Integer, default=0)
    reasoning_tokens = Column(Integer, default=0)
    idempotency_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('idempotency_key', name='uq_idempotency_key'),
    )