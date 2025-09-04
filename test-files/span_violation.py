# test_span.py
"""
Deliberate OpenTelemetry span *naming* violations for validator testing.
This file focuses on SPAN name issues (not metrics/attributes).

Violations included (grounded in your KB rules):
- Not following "{verb} {object}" pattern
- Reversed messaging order "{destination} publish"
- HTTP span without method or wrong order
- DB span with reversed "{target} {operation}" and fused camelCase
- RPC span without qualified "service/method" style
- Internal helper function span (anti-pattern: spans inside business logic)
"""

from opentelemetry import trace

tracer = trace.get_tracer("demo.bad.instrumentation")

# --- HTTP examples ---
def http_user_profile_handler(request):
    # Violation: single fused token, not "{verb} {object}"
    with tracer.start_as_current_span("userProfileGET"):
        # pretend to do work
        pass

def http_orders_handler(request):
    # Violation: only object, no verb (route only)
    with tracer.start_as_current_span("/api/orders"):
        pass

def http_wrong_order(request):
    # Violation: object then verb (reversed)
    with tracer.start_as_current_span("/api/users GET"):
        pass


# --- Database examples ---
def db_select_users():
    # Violation: reversed "{target} {operation}"
    with tracer.start_as_current_span("users SELECT"):
        pass

def db_select_users_camel():
    # Violation: fused camelCase, not "{verb} {object}"
    with tracer.start_as_current_span("selectUsers"):
        pass


# --- Messaging examples ---
def kafka_publish(topic: str):
    # Violation: "{destination} publish" (reversed), should be "publish {destination}" or "send {destination}"
    with tracer.start_as_current_span(f"{topic} publish"):
        pass

def kafka_receive(queue: str):
    # Violation: fused token, missing space between verb and object
    with tracer.start_as_current_span(f"receive{queue}"):
        pass


# --- RPC / gRPC examples ---
def grpc_payment_call():
    # Violation: no qualified "Service/Method" style, and fused token
    with tracer.start_as_current_span("PaymentServiceProcessPayment"):
        pass


# --- Internal helper span (anti-pattern) ---
def _calculate_totals(items):
    # Violation: spans inside internal helper/business logic (should use events/attributes on boundary span)
    with tracer.start_as_current_span("calculateTotals"):
        return sum(items)


def main():
    # Execute all functions so validators scanning context see multiple patterns
    http_user_profile_handler(None)
    http_orders_handler(None)
    http_wrong_order(None)
    db_select_users()
    db_select_users_camel()
    kafka_publish("topic.user-events")
    kafka_receive("queue.orders")
    grpc_payment_call()
    _ = _calculate_totals([1, 2, 3])


if __name__ == "__main__":
    main()
