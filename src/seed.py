import uuid
from .database import SessionLocal, engine, Base
from .models import Plan, Tenant, Subscription

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Seed Plans
        if not db.query(Plan).filter(Plan.id == "free").first():
            free_plan = Plan(id="free", name="Free Plan", api_call_limit=1000, ai_token_limit=100000) #
            pro_plan = Plan(id="pro", name="Pro Plan", api_call_limit=100000, ai_token_limit=10000000) #
            db.add_all([free_plan, pro_plan])

        # Seed Demo Tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            tenant = Tenant(id=uuid.uuid4(), name="Acme Corp Demo")
            db.add(tenant)
            db.commit()

            sub = Subscription(tenant_id=tenant.id, plan_id="free", status="active")
            db.add(sub)
            db.commit()

        print(f"Database seeded successfully!")
        print(f"Demo Tenant ID (use in X-Tenant-ID header): {tenant.id}")

    finally:
        db.close()

if __name__ == "__main__":
    seed_db()