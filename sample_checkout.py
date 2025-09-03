#!/usr/bin/env python3
"""

MADE USING GPT
Sample OpenTelemetry instrumented checkout service
Contains intentional violations for testing the validator
"""

import os
import logging
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import requests
import time
import uuid
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

# Set up tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=14268,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument Flask and requests
FlaskInstrumentor().instrument()
RequestsInstrumentor().instrument()
SQLAlchemyInstrumentor().instrument()

app = Flask(__name__)

# Database connection
engine = create_engine("sqlite:///checkout.db")

class CheckoutService:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
    
    def validate_cart_items(self, cart_items):
        """
        VIOLATION 1: Creating span for internal function
        This violates the boundary-only principle
        """
        with self.tracer.start_span("validate_cart_items") as span:
            span.set_attribute("cart.item_count", len(cart_items))
            
            for item in cart_items:
                # VIOLATION 2: Creating spans in loops
                with self.tracer.start_span("validate_item") as item_span:
                    item_span.set_attribute("item.id", item.get("id"))
                    
                    if not item.get("product_id"):
                        # VIOLATION 3: Recording error and raising exception
                        span.record_exception(ValueError("Missing product_id"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR))
                        raise ValueError(f"Invalid item: {item}")
                    
                    # VIOLATION 4: Internal processing span
                    with self.tracer.start_span("check_inventory") as inv_span:
                        inv_span.set_attribute("product.id", item["product_id"])
                        self._check_inventory(item["product_id"])
        
        return True
    
    def _check_inventory(self, product_id):
        """Internal inventory check - should not have spans"""
        # This is correct - no span for internal function
        time.sleep(0.1)  # Simulate inventory check
        return True
    
    def calculate_total(self, cart_items):
        """
        VIOLATION 5: Wrong span naming convention
        Should follow {verb} {object} pattern
        """
        with self.tracer.start_span("calculateTotal") as span:  # Wrong naming
            total = 0
            
            for item in cart_items:
                # VIOLATION 6: High cardinality attribute
                span.set_attribute(f"item.{item['id']}.price", item.get("price", 0))
                total += item.get("price", 0) * item.get("quantity", 1)
            
            # VIOLATION 7: Wrong metric naming with service name
            span.set_attribute("checkoutservice.cart.total", total)
            
            return total
    
    def process_payment(self, payment_info, amount):
        """Payment processing with proper span creation"""
        with self.tracer.start_span("POST /payment", kind=trace.SpanKind.CLIENT) as span:
            span.set_attribute("http.method", "POST")
            span.set_attribute("payment.amount", amount)
            span.set_attribute("payment.currency", payment_info.get("currency", "USD"))
            
            try:
                # Simulate payment API call
                response = requests.post(
                    "http://payment-service/charge",
                    json=payment_info,
                    timeout=5
                )
                
                if response.status_code == 200:
                    span.set_attribute("payment.status", "success")
                    return response.json()
                else:
                    # VIOLATION 8: Not recording error properly
                    span.set_attribute("payment.status", "failed")
                    return None
                    
            except Exception as e:
                # Correct: Record error and set status
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return None

    def save_order(self, order_data):
        """Database operation with proper instrumentation"""
        # Good: SQLAlchemy is already instrumented, just add business context
        with engine.connect() as conn:
            result = conn.execute(
                text("INSERT INTO orders (id, user_id, total) VALUES (:id, :user_id, :total)"),
                {
                    "id": order_data["id"],
                    "user_id": order_data["user_id"], 
                    "total": order_data["total"]
                }
            )
            
            # Add business context to existing span
            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute("order.id", order_data["id"])
                current_span.set_attribute("order.total", order_data["total"])
            
            return result.rowcount > 0

@app.route("/checkout", methods=["POST"])
def checkout():
    """Checkout endpoint - properly instrumented by Flask"""
    checkout_service = CheckoutService()
    
    try:
        data = request.json
        cart_items = data.get("items", [])
        payment_info = data.get("payment", {})
        user_id = data.get("user_id")
        
        # Add business context to the HTTP span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("user.id", user_id)
            current_span.set_attribute("cart.item_count", len(cart_items))
        
        # Validate cart (contains violations)
        checkout_service.validate_cart_items(cart_items)
        
        # Calculate total (contains violations)
        total = checkout_service.calculate_total(cart_items)
        
        # Process payment (mostly correct)
        payment_result = checkout_service.process_payment(payment_info, total)
        
        if not payment_result:
            return jsonify({"error": "Payment failed"}), 400
        
        # Save order
        order_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "total": total,
            "items": cart_items
        }
        
        if checkout_service.save_order(order_data):
            # VIOLATION 9: Missing business milestone event
            # Should record "order.placed" event
            return jsonify({
                "order_id": order_data["id"],
                "total": total,
                "status": "confirmed"
            })
        else:
            return jsonify({"error": "Failed to save order"}), 500
            
    except Exception as e:
        # Good: Let Flask instrumentation handle the error
        current_span = trace.get_current_span()
        if current_span:
            current_span.record_exception(e)
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        return jsonify({"error": "Checkout failed"}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=8080, debug=True)