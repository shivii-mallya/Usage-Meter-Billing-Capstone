import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy_key")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy_secret")

def report_usage_to_stripe(stripe_customer_id: str, event_name: str, value: int, timestamp: int):
    """
    Reports metered usage events to Stripe's Billing Metering API.
    """
    try:
        # Uses Stripe Meter Events API for modern usage billing
        response = stripe.billing.MeterEvent.create(
            event_name=event_name,
            payload={
                "stripe_customer_id": stripe_customer_id,
                "value": str(value),
            },
            timestamp=timestamp
        )
        return response
    except stripe.error.StripeError as e:
        # In development/test mode without live keys, log and gracefully return
        print(f"[Stripe Meter Warning]: {e.user_message or e}")
        return None